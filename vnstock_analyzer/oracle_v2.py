"""Oracle V2: cross-sectional, bidirectional forecasts over the whole market panel."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .oracle import OracleForecaster, _number, _round


MODEL_VERSION = "oracle-panel-v2.1"
DEFAULT_HORIZON = 10
PANEL_FEATURES = (
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
    "market_return_5",
    "market_return_20",
    "breadth_above_ema20",
    "relative_strength_5",
    "relative_strength_20",
    "rs_rank_20",
    "liquidity_rank",
)


class PanelOracle:
    """Pool all stocks while preserving strict point-in-time training cutoffs."""

    min_symbols = 30
    min_training_rows = 2_000
    neighbors = 160
    candidate_pool = 500
    per_symbol_cap = 8

    def __init__(self, panel_history: pd.DataFrame):
        self.raw = self._normalize(panel_history)
        self.panel = self._build_panel(self.raw)
        self.symbol_count = int(self.panel["symbol"].nunique()) if not self.panel.empty else 0

    @staticmethod
    def _normalize(history):
        required = {"symbol", "trading_date", "open", "high", "low", "close", "volume"}
        if history is None or history.empty or not required.issubset(history.columns):
            return pd.DataFrame()
        frame = history.copy()
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
        frame["trading_date"] = pd.to_datetime(frame["trading_date"], errors="coerce")
        for column in ("open", "high", "low", "close", "volume"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return (
            frame.dropna(subset=["symbol", "trading_date", "open", "high", "low", "close"])
            .sort_values(["symbol", "trading_date"])
            .drop_duplicates(["symbol", "trading_date"], keep="last")
            .reset_index(drop=True)
        )

    @staticmethod
    def _build_panel(history):
        if history.empty:
            return history.copy()
        frames = []
        for symbol, group in history.groupby("symbol", sort=False):
            features = OracleForecaster._build_features(group.sort_values("trading_date").reset_index(drop=True))
            features["return_1"] = features["close"].pct_change(fill_method=None) * 100.0
            features["symbol"] = symbol
            frames.append(features)
        panel = pd.concat(frames, ignore_index=True)
        by_date = panel.groupby("trading_date")
        panel["market_return_5"] = by_date["return_5"].transform("median")
        panel["market_return_20"] = by_date["return_20"].transform("median")
        panel["breadth_above_ema20"] = by_date["vs_ema20"].transform(lambda values: (values > 0).mean())
        panel["relative_strength_5"] = panel["return_5"] - panel["market_return_5"]
        panel["relative_strength_20"] = panel["return_20"] - panel["market_return_20"]
        panel["rs_rank_20"] = by_date["relative_strength_20"].rank(pct=True)
        panel["liquidity_rank"] = by_date["avg_turnover_20"].rank(pct=True)
        return panel.sort_values(["trading_date", "symbol"]).reset_index(drop=True)

    def _labeled(self, horizon):
        panel = self.panel.copy()
        grouped = panel.groupby("symbol", sort=False)
        panel["label_end_date"] = grouped["trading_date"].shift(-horizon)
        panel["future_return"] = (grouped["close"].shift(-horizon) / panel["close"] - 1.0) * 100.0
        market_future = panel.groupby("trading_date")["future_return"].transform("median")
        panel["future_excess"] = panel["future_return"] - market_future
        panel["future_rank"] = panel.groupby("trading_date")["future_excess"].rank(pct=True)
        return panel

    @staticmethod
    def _setup(row):
        perfect = row["ema10"] > row["ema20"] > row["ema50"]
        tight = _number(row["ema_spread"], 99) <= 2.0
        near_20 = -1.2 <= _number(row["vs_ema20"], -99) <= 2.5
        above = min(_number(row[f"vs_ema{span}"], -99) for span in (10, 20, 50)) >= 0
        if perfect and near_20:
            return "PULLBACK ENTRY"
        if perfect and above:
            return "PERFECT ORDER CONTINUATION"
        if tight and above:
            return "BREAKOUT EARLY"
        if tight:
            return "PRE-BREAKOUT"
        return "DEVELOPING"

    def _training_context(self, labeled, as_of):
        candidates = labeled[
            (labeled["label_end_date"].notna())
            & (labeled["label_end_date"] <= as_of)
        ].dropna(subset=list(PANEL_FEATURES) + ["future_return", "future_excess"])
        if len(candidates) < self.min_training_rows:
            return None
        values = candidates[list(PANEL_FEATURES)].astype(float)
        center = values.median()
        scale = values.std(ddof=0).replace(0, 1.0).fillna(1.0)
        matrix = ((values - center) / scale).to_numpy(dtype=float)
        return {"candidates": candidates, "center": center, "scale": scale, "matrix": matrix}

    def _select_analogs(self, row, context):
        query = ((row[list(PANEL_FEATURES)].astype(float) - context["center"]) / context["scale"]).to_numpy(dtype=float)
        distances = np.sqrt(np.mean((context["matrix"] - query) ** 2, axis=1))
        pool_size = min(self.candidate_pool, len(distances))
        pool_indices = np.argpartition(distances, pool_size - 1)[:pool_size]
        order = pool_indices[np.argsort(distances[pool_indices])]
        selected = []
        symbol_counts = {}
        candidates = context["candidates"]
        for position in order:
            symbol = candidates.iloc[position]["symbol"]
            if symbol_counts.get(symbol, 0) >= self.per_symbol_cap:
                continue
            selected.append(position)
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            if len(selected) >= self.neighbors:
                break
        return np.asarray(selected, dtype=int), distances

    def _predict_row(self, row, context, horizon):
        if row[list(PANEL_FEATURES)].isna().any():
            return None
        positions, all_distances = self._select_analogs(row, context)
        if len(positions) < 40:
            return None
        analogs = context["candidates"].iloc[positions]
        distances = all_distances[positions]
        distance_scale = max(float(np.median(distances)), 0.1)
        weights = np.exp(-distances / distance_scale)
        weights = weights / weights.sum()
        future_return = analogs["future_return"].to_numpy(dtype=float)
        future_excess = analogs["future_excess"].to_numpy(dtype=float)
        future_rank = analogs["future_rank"].to_numpy(dtype=float)
        p_up = float(np.sum(weights * (future_return > 0)))
        p_down = float(np.sum(weights * (future_return < 0)))
        p_outperform = float(np.sum(weights * (future_excess > 0)))
        p_top = float(np.sum(weights * (future_rank >= 0.8)))
        expected_return = float(np.sum(weights * future_return))
        expected_excess = float(np.sum(weights * future_excess))
        q10, q50, q90 = np.quantile(future_return, [0.1, 0.5, 0.9])
        effective_sample = float(1.0 / np.sum(weights ** 2))
        if expected_return >= 0.35 and p_up >= 0.53:
            direction = "BULLISH"
        elif expected_return <= -0.35 and p_down >= 0.53:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"
        evidence = "A" if effective_sample >= 100 and np.median(distances) <= 1.1 else "B" if effective_sample >= 70 else "C"
        score = np.clip(50 + expected_excess * 7 + (p_outperform - 0.5) * 35 + (p_up - p_down) * 12, 0, 100)
        return {
            "horizon": horizon,
            "direction": direction,
            "probability_up": _round(p_up * 100, 1),
            "probability_down": _round(p_down * 100, 1),
            "probability_outperform": _round(p_outperform * 100, 1),
            "probability_top_quintile": _round(p_top * 100, 1),
            "expected_return_pct": _round(expected_return),
            "expected_excess_return_pct": _round(expected_excess),
            "return_quantiles": {"q10": _round(q10), "q50": _round(q50), "q90": _round(q90)},
            "opportunity_score": _round(score, 1),
            "evidence": evidence,
            "effective_sample_size": _round(effective_sample, 1),
            "analog_count": int(len(positions)),
            "median_distance": _round(np.median(distances)),
            "analog_symbol_count": int(analogs["symbol"].nunique()),
            "analog_examples": [
                {
                    "symbol": item["symbol"],
                    "date": item["trading_date"].strftime("%Y-%m-%d"),
                    "return_pct": _round(item["future_return"]),
                    "excess_pct": _round(item["future_excess"]),
                }
                for _, item in analogs.head(5).iterrows()
            ],
        }

    def _snapshot(self, as_of, horizon=DEFAULT_HORIZON):
        labeled = self._labeled(horizon)
        context = self._training_context(labeled, as_of)
        if context is None:
            return [], labeled
        latest = labeled[labeled["trading_date"] == as_of].drop_duplicates("symbol", keep="last")
        predictions = []
        for _, row in latest.iterrows():
            prediction = self._predict_row(row, context, horizon)
            if prediction is not None:
                predictions.append((row, prediction))
        if predictions:
            scores = pd.Series([item[1]["opportunity_score"] for item in predictions])
            percentiles = scores.rank(method="average", pct=True) * 100
            for (_, prediction), percentile in zip(predictions, percentiles):
                prediction["relative_rank_percentile"] = _round(percentile, 1)
        return predictions, labeled

    def _reliable_as_of(self):
        """Avoid switching the whole panel to a date only a few symbols have."""
        coverage = self.panel.groupby("trading_date")["symbol"].nunique()
        minimum = max(self.min_symbols, int(np.ceil(self.symbol_count * 0.80)))
        eligible = coverage[coverage >= minimum]
        return pd.Timestamp(eligible.index.max()) if not eligible.empty else pd.Timestamp(self.panel["trading_date"].max())

    def validate(self, horizon=DEFAULT_HORIZON, evaluation_dates=20):
        if self.panel.empty:
            return {"status": "UNVALIDATED", "reason": "Panel rỗng"}
        labeled = self._labeled(horizon)
        viable_dates = sorted(labeled.loc[labeled["label_end_date"].notna(), "trading_date"].unique())
        viable_dates = viable_dates[-min(len(viable_dates), evaluation_dates * 5)::5]
        records = []
        for date_value in viable_dates:
            as_of = pd.Timestamp(date_value)
            predictions, evaluation_panel = self._snapshot(as_of, horizon)
            actual_rows = evaluation_panel[evaluation_panel["trading_date"] == as_of].set_index("symbol")
            for row, prediction in predictions:
                actual = actual_rows.loc[row["symbol"]]
                records.append({
                    "date": as_of,
                    "symbol": row["symbol"],
                    "p_up": prediction["probability_up"] / 100.0,
                    "predicted_excess": prediction["expected_excess_return_pct"],
                    "score": prediction["opportunity_score"],
                    "actual_up": float(actual["future_return"] > 0),
                    "actual_excess": float(actual["future_excess"]),
                })
        if len(records) < 200:
            return {"status": "UNVALIDATED", "reason": "Chưa đủ mẫu panel walk-forward", "samples": len(records)}
        results = pd.DataFrame(records)
        brier = float(np.mean((results["p_up"] - results["actual_up"]) ** 2))
        base_rate = float(results["actual_up"].mean())
        naive_brier = base_rate * (1 - base_rate)
        daily_ic = []
        top_excess = []
        for _, group in results.groupby("date"):
            if group["predicted_excess"].nunique() > 1:
                predicted_rank = group["predicted_excess"].rank(pct=True)
                actual_rank = group["actual_excess"].rank(pct=True)
                daily_ic.append(predicted_rank.corr(actual_rank))
            cutoff = group["score"].quantile(0.8)
            top_excess.append(group.loc[group["score"] >= cutoff, "actual_excess"].mean())
        mean_ic = float(np.nanmean(daily_ic)) if daily_ic else 0.0
        mean_top_excess = float(np.nanmean(top_excess)) if top_excess else 0.0
        # Direction probabilities must beat the unconditional base rate; no
        # tolerance is granted merely to manufacture a PASS label.
        direction_passed = brier < naive_brier
        ranking_passed = mean_ic >= 0.03 and mean_top_excess >= 0.10
        overall_status = "PASS" if direction_passed and ranking_passed else "RANK_PASS" if ranking_passed else "REJECT"
        return {
            "status": overall_status,
            "direction_status": "PASS" if direction_passed else "REJECT",
            "ranking_status": "PASS" if ranking_passed else "REJECT",
            "samples": len(results),
            "dates": int(results["date"].nunique()),
            "brier_score": _round(brier, 4),
            "naive_brier_score": _round(naive_brier, 4),
            "mean_rank_ic": _round(mean_ic, 4),
            "top_quintile_excess_pct": _round(mean_top_excess, 3),
        }

    def forecast_universe(self, horizon=DEFAULT_HORIZON, model_health: Optional[Dict] = None):
        if self.panel.empty or self.symbol_count < self.min_symbols:
            return {
                "status": "INSUFFICIENT_PANEL",
                "model_version": MODEL_VERSION,
                "symbol_count": self.symbol_count,
                "forecasts": {},
            }
        as_of = self._reliable_as_of()
        predictions, _ = self._snapshot(as_of, horizon)
        health = model_health or {"status": "UNVALIDATED"}
        forecasts = {}
        for row, prediction in predictions:
            rank = prediction["relative_rank_percentile"]
            direction = prediction["direction"]
            if direction == "BEARISH":
                decision = "AVOID_LONG"
            elif direction == "BULLISH" and rank >= 80:
                decision = "LONG_SETUP" if health.get("status") == "PASS" else "RANK_ONLY"
            elif rank >= 65 and prediction["expected_excess_return_pct"] > 0:
                decision = "WATCH_LONG"
            else:
                decision = "WAIT"

            price = _number(row["close"])
            atr_pct = min(max(_number(row["atr_pct"], 3.0), 1.5), 7.0)
            risk_plan = None
            if decision in {"LONG_SETUP", "RANK_ONLY", "WATCH_LONG"}:
                half_width = price * min(atr_pct * 0.2, 1.0) / 100.0
                risk_plan = {
                    "entry": {"low": _round(price - half_width), "high": _round(price + half_width)},
                    "risk_barrier": _round(price * (1 - atr_pct / 100.0)),
                    "profit_barrier": _round(price * (1 + 2 * atr_pct / 100.0)),
                    "risk_pct": _round(atr_pct),
                    "reward_risk": 2.0,
                }
            forecasts[row["symbol"]] = {
                **prediction,
                "price": _round(price),
                "change_percent": _round(row["return_1"]),
                "decision": decision,
                "setup": self._setup(row),
                "risk_plan": risk_plan,
                "liquidity_rank_percentile": _round(_number(row["liquidity_rank"]) * 100, 1),
            }
        return {
            "status": "READY",
            "model_version": MODEL_VERSION,
            "as_of": as_of.strftime("%Y-%m-%d"),
            "horizon": horizon,
            "symbol_count": self.symbol_count,
            "model_health": health,
            "market_state": {
                "proxy_return_5d": _round(self.panel.loc[self.panel["trading_date"] == as_of, "market_return_5"].median()),
                "proxy_return_20d": _round(self.panel.loc[self.panel["trading_date"] == as_of, "market_return_20"].median()),
                "breadth_above_ema20_pct": _round(self.panel.loc[self.panel["trading_date"] == as_of, "breadth_above_ema20"].median() * 100, 1),
            },
            "forecasts": forecasts,
            "disclaimer": "Dự báo panel theo dữ liệu quá khứ; relative rank không phải cam kết lợi nhuận.",
        }

    def forecast_symbol(self, symbol, horizon=DEFAULT_HORIZON, model_health: Optional[Dict] = None):
        universe = self.forecast_universe(horizon=horizon, model_health=model_health)
        if universe.get("status") != "READY":
            return universe
        symbol = str(symbol).upper()
        forecast = universe["forecasts"].get(symbol)
        if forecast is None:
            return {
                "status": "INSUFFICIENT_DATA",
                "model_version": MODEL_VERSION,
                "symbol": symbol,
                "reason": "Mã chưa có snapshot cùng ngày với panel",
            }
        return {
            "status": "READY",
            "model_version": MODEL_VERSION,
            "symbol": symbol,
            "as_of": universe["as_of"],
            "horizon": horizon,
            "symbol_count": universe["symbol_count"],
            "model_health": universe["model_health"],
            "market_state": universe["market_state"],
            "forecast": forecast,
            "disclaimer": universe["disclaimer"],
        }
