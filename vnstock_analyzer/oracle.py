"""Leakage-safe, explainable forecasts from a stock's own price memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


MODEL_VERSION = "oracle-analog-v1.1"
HORIZONS = (5, 10, 20)
FEATURE_COLUMNS = (
    "return_3",
    "return_5",
    "return_10",
    "return_20",
    "vs_ema10",
    "vs_ema20",
    "vs_ema50",
    "ema_spread",
    "ema20_slope",
    "ema50_slope",
    "atr_pct",
    "volatility_10",
    "volume_ratio",
    "range_position_20",
)


def _number(value, default=0.0):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _round(value, digits=2):
    return round(_number(value), digits)


@dataclass(frozen=True)
class BarrierResult:
    outcome: str
    return_pct: float
    mfe_pct: float
    mae_pct: float
    days_to_event: int


class OracleForecaster:
    """Forecast target/stop outcomes using only observations before ``as_of``."""

    min_history = 80
    min_analogs = 12
    max_analogs = 40

    def __init__(self, history: pd.DataFrame):
        self.raw = self._normalize(history)
        self.frame = self._build_features(self.raw)

    @staticmethod
    def _normalize(history: pd.DataFrame) -> pd.DataFrame:
        required = {"open", "high", "low", "close", "volume"}
        if history is None or history.empty or not required.issubset(history.columns):
            return pd.DataFrame()

        frame = history.copy()
        date_column = "time" if "time" in frame.columns else "date" if "date" in frame.columns else None
        if date_column:
            frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
            frame = frame.sort_values(date_column).drop_duplicates(date_column, keep="last")
            frame = frame.rename(columns={date_column: "trading_date"})
        else:
            frame["trading_date"] = pd.RangeIndex(len(frame))

        for column in required:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    @staticmethod
    def _build_features(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame.copy()

        result = frame.copy()
        close = result["close"]
        previous_close = close.shift(1)
        true_range = pd.concat(
            [
                result["high"] - result["low"],
                (result["high"] - previous_close).abs(),
                (result["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        for span in (10, 20, 50):
            result[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()
            result[f"vs_ema{span}"] = (close / result[f"ema{span}"] - 1.0) * 100.0

        for period in (3, 5, 10, 20):
            result[f"return_{period}"] = close.pct_change(period, fill_method=None) * 100.0

        result["ema_spread"] = (
            (result[["ema10", "ema20", "ema50"]].max(axis=1)
             - result[["ema10", "ema20", "ema50"]].min(axis=1))
            / result["ema50"]
            * 100.0
        )
        result["ema20_slope"] = result["ema20"].pct_change(5, fill_method=None) * 20.0
        result["ema50_slope"] = result["ema50"].pct_change(10, fill_method=None) * 10.0
        result["atr"] = true_range.rolling(14, min_periods=10).mean()
        result["atr_pct"] = result["atr"] / close * 100.0
        result["volatility_10"] = close.pct_change(fill_method=None).rolling(10).std() * 100.0
        average_volume = result["volume"].rolling(20, min_periods=10).mean()
        result["volume_ratio"] = result["volume"] / average_volume.replace(0, np.nan)
        rolling_low = result["low"].rolling(20, min_periods=10).min()
        rolling_high = result["high"].rolling(20, min_periods=10).max()
        result["range_position_20"] = (close - rolling_low) / (rolling_high - rolling_low).replace(0, np.nan)
        result["turnover_value"] = close * result["volume"]
        result["avg_turnover_20"] = result["turnover_value"].rolling(20, min_periods=10).mean()
        return result.replace([np.inf, -np.inf], np.nan)

    @staticmethod
    def evaluate_barriers(
        future: pd.DataFrame,
        reference_price: float,
        stop_pct: float,
        target_pct: float,
    ) -> BarrierResult:
        stop_price = reference_price * (1.0 - stop_pct / 100.0)
        target_price = reference_price * (1.0 + target_pct / 100.0)
        outcome = "TIMEOUT"
        days_to_event = len(future)

        for day, (_, row) in enumerate(future.iterrows(), start=1):
            hit_stop = _number(row["low"]) <= stop_price
            hit_target = _number(row["high"]) >= target_price
            # Daily OHLC cannot reveal which barrier came first. Be conservative.
            if hit_stop:
                outcome, days_to_event = "STOP", day
                break
            if hit_target:
                outcome, days_to_event = "TARGET", day
                break

        highs = future["high"] / reference_price - 1.0
        lows = future["low"] / reference_price - 1.0
        last_close = _number(future.iloc[-1]["close"], reference_price) if len(future) else reference_price
        realized = target_pct if outcome == "TARGET" else -stop_pct if outcome == "STOP" else (last_close / reference_price - 1.0) * 100.0
        return BarrierResult(
            outcome=outcome,
            return_pct=_round(realized, 4),
            mfe_pct=_round(highs.max() * 100.0 if len(highs) else 0.0, 4),
            mae_pct=_round(lows.min() * 100.0 if len(lows) else 0.0, 4),
            days_to_event=days_to_event,
        )

    def _setup(self, row: pd.Series) -> str:
        perfect_order = row["ema10"] > row["ema20"] > row["ema50"]
        tight = _number(row["ema_spread"], 99) <= 2.0
        near_ema20 = -1.2 <= _number(row["vs_ema20"], -99) <= 2.5
        above_all = min(_number(row[f"vs_ema{span}"], -99) for span in (10, 20, 50)) >= 0
        if perfect_order and near_ema20:
            return "PULLBACK ENTRY"
        if perfect_order and above_all:
            return "PERFECT ORDER CONTINUATION"
        if tight and above_all:
            return "BREAKOUT EARLY"
        if tight:
            return "PRE-BREAKOUT"
        return "DEVELOPING"

    def _analog_indices(self, as_of_index: int, horizon: int) -> List[tuple]:
        latest = self.frame.iloc[as_of_index]
        last_candidate = as_of_index - horizon
        if last_candidate < 50 or latest[list(FEATURE_COLUMNS)].isna().any():
            return []

        candidates = self.frame.iloc[49:last_candidate + 1].dropna(subset=list(FEATURE_COLUMNS)).copy()
        if candidates.empty:
            return []
        scale = candidates[list(FEATURE_COLUMNS)].std(ddof=0).replace(0, 1.0).fillna(1.0)
        center = candidates[list(FEATURE_COLUMNS)].median()
        candidate_values = ((candidates[list(FEATURE_COLUMNS)] - center) / scale).astype(float)
        latest_values = ((latest[list(FEATURE_COLUMNS)].astype(float) - center) / scale).astype(float)
        distances = np.sqrt(((candidate_values - latest_values) ** 2).mean(axis=1))
        nearest = distances.nsmallest(min(self.max_analogs, len(distances)))
        return [(int(index), _number(distance)) for index, distance in nearest.items()]

    def _forecast_horizon(self, as_of_index: int, horizon: int) -> Dict:
        row = self.frame.iloc[as_of_index]
        atr_pct = min(max(_number(row["atr_pct"], 3.0), 1.5), 7.0)
        stop_pct = atr_pct
        target_pct = atr_pct * 2.0
        analogs = self._analog_indices(as_of_index, horizon)
        outcomes = []

        for index, distance in analogs:
            reference = _number(self.frame.iloc[index]["close"])
            future = self.frame.iloc[index + 1:index + horizon + 1]
            if reference <= 0 or len(future) < horizon:
                continue
            result = self.evaluate_barriers(future, reference, stop_pct, target_pct)
            outcomes.append((index, distance, result))

        sample_size = len(outcomes)
        target_count = sum(item[2].outcome == "TARGET" for item in outcomes)
        stop_count = sum(item[2].outcome == "STOP" for item in outcomes)
        timeout_count = sample_size - target_count - stop_count
        # Symmetric Beta prior prevents tiny samples from producing extreme claims.
        denominator = sample_size + 6.0
        p_target = (target_count + 2.0) / denominator
        p_stop = (stop_count + 2.0) / denominator
        p_timeout = (timeout_count + 2.0) / denominator
        returns = np.array([item[2].return_pct for item in outcomes], dtype=float)
        mfe = np.array([item[2].mfe_pct for item in outcomes], dtype=float)
        mae = np.array([item[2].mae_pct for item in outcomes], dtype=float)
        expected_return = float(returns.mean()) if sample_size else 0.0
        expected_r = expected_return / stop_pct if stop_pct else 0.0
        median_distance = float(np.median([item[1] for item in outcomes])) if sample_size else 99.0

        if sample_size >= 30 and median_distance <= 1.0:
            confidence = "A"
        elif sample_size >= 20 and median_distance <= 1.35:
            confidence = "B"
        elif sample_size >= self.min_analogs:
            confidence = "C"
        else:
            confidence = "INSUFFICIENT"

        # A 2R target does not need a 50% hit rate to have positive expectancy.
        # Require both empirical expectancy and a probability margin instead.
        actionable = (
            sample_size >= self.min_analogs
            and expected_r > 0.15
            and (p_target * 2.0 - p_stop) > 0.10
        )
        decision = "SETUP" if actionable and confidence in {"A", "B"} else "WATCH" if actionable else "NO_TRADE"
        opportunity_score = max(0.0, min(100.0, 50.0 + expected_r * 20.0 + (p_target - p_stop) * 30.0))
        price = _number(row["close"])
        entry_half_width = price * min(atr_pct * 0.20, 1.0) / 100.0

        analog_preview = []
        for index, distance, result in outcomes[:5]:
            date_value = self.frame.iloc[index]["trading_date"]
            date_text = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
            analog_preview.append({
                "date": date_text,
                "distance": _round(distance),
                "outcome": result.outcome,
                "return_pct": _round(result.return_pct),
            })

        quantiles = np.quantile(returns, [0.1, 0.5, 0.9]).tolist() if sample_size else [0.0, 0.0, 0.0]
        return {
            "horizon": horizon,
            "decision": decision,
            "probability_target": _round(p_target * 100.0, 1),
            "probability_stop": _round(p_stop * 100.0, 1),
            "probability_timeout": _round(p_timeout * 100.0, 1),
            "expected_return_pct": _round(expected_return),
            "expected_r": _round(expected_r),
            "return_quantiles": {"q10": _round(quantiles[0]), "q50": _round(quantiles[1]), "q90": _round(quantiles[2])},
            "median_mfe_pct": _round(np.median(mfe) if sample_size else 0.0),
            "median_mae_pct": _round(np.median(mae) if sample_size else 0.0),
            "entry": {"low": _round(price - entry_half_width), "high": _round(price + entry_half_width)},
            "stop": _round(price * (1.0 - stop_pct / 100.0)),
            "target": _round(price * (1.0 + target_pct / 100.0)),
            "stop_pct": _round(stop_pct),
            "target_pct": _round(target_pct),
            "reward_risk": 2.0,
            "sample_size": sample_size,
            "confidence": confidence,
            "similarity_distance": _round(median_distance),
            "opportunity_score": _round(opportunity_score, 1),
            "outcome_counts": {"target": target_count, "stop": stop_count, "timeout": timeout_count},
            "analog_examples": analog_preview,
        }

    def forecast(self, as_of_index: Optional[int] = None, horizons: Iterable[int] = HORIZONS) -> Dict:
        if self.frame.empty or len(self.frame) < self.min_history:
            return {
                "status": "INSUFFICIENT_DATA",
                "model_version": MODEL_VERSION,
                "reason": f"Cần tối thiểu {self.min_history} phiên dữ liệu",
                "horizons": {},
            }

        index = len(self.frame) - 1 if as_of_index is None else int(as_of_index)
        if index < 0 or index >= len(self.frame):
            raise IndexError("as_of_index ngoài phạm vi dữ liệu")
        row = self.frame.iloc[index]
        date_value = row["trading_date"]
        as_of = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
        forecasts = {str(horizon): self._forecast_horizon(index, int(horizon)) for horizon in horizons}
        primary = forecasts.get("10") or next(iter(forecasts.values()))
        warnings = []
        if _number(row["avg_turnover_20"]) <= 0:
            warnings.append("Không xác định được thanh khoản bình quân")
        if primary["confidence"] == "INSUFFICIENT":
            warnings.append("Số mẫu lịch sử tương đồng còn ít")

        return {
            "status": "READY",
            "model_version": MODEL_VERSION,
            "as_of": as_of,
            "generated_at": datetime.now().isoformat(),
            "method": "SELF_HISTORY_ANALOG",
            "setup": self._setup(row),
            "primary_horizon": primary["horizon"],
            "primary": primary,
            "horizons": forecasts,
            "liquidity": {
                "average_turnover_20": _round(row["avg_turnover_20"], 0),
                "volume_ratio": _round(row["volume_ratio"]),
            },
            "warnings": warnings,
            "disclaimer": "Ước lượng xác suất từ các mẫu quá khứ; không phải cam kết lợi nhuận.",
        }

    def walk_forward_backtest(self, horizon: int = 10, minimum_train: int = 100) -> Dict:
        predictions = []
        last_index = len(self.frame) - horizon - 1
        for index in range(minimum_train, last_index + 1):
            forecast = self._forecast_horizon(index, horizon)
            if forecast["sample_size"] < self.min_analogs:
                continue
            row = self.frame.iloc[index]
            actual = self.evaluate_barriers(
                self.frame.iloc[index + 1:index + horizon + 1],
                _number(row["close"]),
                forecast["stop_pct"],
                forecast["target_pct"],
            )
            predictions.append((forecast, actual))

        if not predictions:
            return {"status": "INSUFFICIENT_DATA", "samples": 0, "horizon": horizon}
        probabilities = np.array([item[0]["probability_target"] / 100.0 for item in predictions])
        actuals = np.array([1.0 if item[1].outcome == "TARGET" else 0.0 for item in predictions])
        returns_r = np.array([item[1].return_pct / item[0]["stop_pct"] for item in predictions])
        selected = np.array([item[0]["decision"] != "NO_TRADE" for item in predictions])
        return {
            "status": "READY",
            "model_version": MODEL_VERSION,
            "horizon": horizon,
            "samples": len(predictions),
            "brier_score": _round(np.mean((probabilities - actuals) ** 2), 4),
            "base_rate": _round(actuals.mean() * 100.0, 1),
            "mean_predicted_probability": _round(probabilities.mean() * 100.0, 1),
            "selected_samples": int(selected.sum()),
            "selected_hit_rate": _round(actuals[selected].mean() * 100.0, 1) if selected.any() else 0.0,
            "selected_expectancy_r": _round(returns_r[selected].mean(), 3) if selected.any() else 0.0,
        }

    @staticmethod
    def assess_validation(backtest: Dict) -> Dict:
        if backtest.get("status") != "READY" or backtest.get("samples", 0) < 50:
            return {
                "status": "UNVALIDATED",
                "reason": "Chưa đủ mẫu walk-forward để kiểm định",
            }
        base_rate = _number(backtest.get("base_rate")) / 100.0
        naive_brier = base_rate * (1.0 - base_rate)
        calibrated = _number(backtest.get("brier_score"), 1.0) <= naive_brier + 0.01
        enough_selections = backtest.get("selected_samples", 0) >= 10
        positive_edge = _number(backtest.get("selected_expectancy_r")) > 0.0
        passed = calibrated and enough_selections and positive_edge
        reasons = []
        if not calibrated:
            reasons.append("Brier score chưa thắng xác suất nền")
        if not enough_selections:
            reasons.append("Chưa đủ giao dịch được chọn ngoài mẫu")
        if enough_selections and not positive_edge:
            reasons.append("Expectancy ngoài mẫu chưa dương")
        return {
            "status": "PASS" if passed else "REJECT",
            "naive_brier_score": _round(naive_brier, 4),
            "reasons": reasons,
        }

    def forecast_validated(self, horizon: int = 10) -> Dict:
        """Forecast with a walk-forward gate that can veto actionable output."""
        result = self.forecast()
        if result.get("status") != "READY":
            return result
        backtest = self.walk_forward_backtest(horizon=horizon)
        health = self.assess_validation(backtest)
        result["validation"] = backtest
        result["model_health"] = health
        primary = result.get("horizons", {}).get(str(horizon))
        if primary is not None:
            result["primary_horizon"] = horizon
            result["primary"] = primary
            if primary.get("decision") != "NO_TRADE" and health.get("status") != "PASS":
                primary["raw_decision"] = primary["decision"]
                primary["decision"] = "NO_TRADE"
                warning = "Model health chưa PASS; Oracle đã chặn tín hiệu giao dịch"
                result.setdefault("warnings", []).append(warning)
        return result
