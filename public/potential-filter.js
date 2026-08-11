(function (root, factory) {
    const api = factory();

    if (typeof module === 'object' && module.exports) {
        module.exports = api;
    }

    root.PotentialFilter = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    const STAGES = {
        BREAKOUT_EARLY: 'BREAKOUT EARLY',
        PULLBACK_MA20: 'PULLBACK MA20',
        PULLBACK_MA50: 'PULLBACK MA50'
    };

    const STAGE_META = {
        [STAGES.BREAKOUT_EARLY]: {
            short: 'BE',
            color: 'deep-purple',
            icon: 'mdi-rocket-launch',
            priority: 1
        },
        [STAGES.PULLBACK_MA20]: {
            short: 'PE20',
            color: 'teal',
            icon: 'mdi-chart-bell-curve-cumulative',
            priority: 2
        },
        [STAGES.PULLBACK_MA50]: {
            short: 'PE50',
            color: 'green',
            icon: 'mdi-target',
            priority: 3
        }
    };

    const RULES = {
        minBreakoutBaseDays: 3,
        minPerfectOrderDays: 3,
        breakoutVolumeMin: 1,
        breakoutVolumeMax: 2.5
    };

    const numberOr = (value, fallback = NaN) => {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : fallback;
    };

    const scorePart = (condition, points, matched, label) => {
        if (!condition) return 0;
        matched.push(label);
        return points;
    };

    function getMaPrice(close, distancePercent) {
        if (!Number.isFinite(close) || !Number.isFinite(distancePercent)) return NaN;
        const denominator = 1 + distancePercent / 100;
        return denominator > 0 ? close / denominator : NaN;
    }

    /**
     * A pullback is useful only when price actually reaches the MA and holds it.
     * Merely being within a wide percentage band is not treated as an entry.
     */
    function evaluateSupportTest(analysis, maName, distancePercent) {
        const price = analysis.price || {};
        const close = numberOr(price.current);
        const low = numberOr(price.low);
        const high = numberOr(price.high);
        const changePercent = numberOr(price.changePercent, 0);
        const maPrice = getMaPrice(close, distancePercent);
        const range = high - low;
        const closeLocation = range > 0 ? (close - low) / range : 0.5;

        // Touch includes a small tolerance for symbols whose tick size keeps the
        // intraday low just above the calculated EMA.
        const touched = Number.isFinite(maPrice) && Number.isFinite(low) && low <= maPrice * 1.008;
        // Touch may use a small tick-size tolerance, but a support "hold" is
        // confirmed only when the daily candle actually closes on/above it.
        const nearHold = touched && close >= maPrice * 0.995;
        const held = touched && close >= maPrice;
        const bullishReaction = held && (changePercent >= 0 || closeLocation >= 0.55);

        return {
            maName,
            maPrice,
            touched,
            nearHold,
            held,
            bullishReaction,
            closeLocation
        };
    }

    function evaluateBreakoutEarly(context) {
        const matched = [];
        const warnings = [];
        let structureScore = 0;
        let entryScore = 0;

        const {
            convergenceLevel,
            convergenceSlope,
            convergenceContracting,
            tightDays,
            momentumAlignment,
            ma20Slope,
            ma50Slope,
            priceVsMA20,
            priceVsMA50,
            volumeTrend,
            volumeRatio,
            positiveSession,
            hasDeathCross
        } = context;

        const tight = ['SUPER_TIGHT', 'TIGHT'].includes(convergenceLevel);
        const baseEstablished = tightDays >= RULES.minBreakoutBaseDays;
        const directionOkay = convergenceSlope === 'UP' && ma20Slope > 0 && ma50Slope > 0;
        const momentumOkay = ['BULLISH_ALIGNED', 'MOSTLY_BULLISH'].includes(momentumAlignment);
        const nonBearishMomentum = !['MOSTLY_BEARISH', 'BEARISH_ALIGNED'].includes(momentumAlignment);
        const aboveCluster = context.priceVsMA10 >= 0 && priceVsMA20 >= 0 && priceVsMA50 >= 0;
        const nearCluster = priceVsMA20 <= 3.5 && priceVsMA50 <= 4.5;
        const volumeConfirmed = volumeRatio >= RULES.breakoutVolumeMin &&
            volumeRatio <= RULES.breakoutVolumeMax;

        structureScore += scorePart(convergenceLevel === 'SUPER_TIGHT', 22, matched, 'MA co cực chặt');
        structureScore += scorePart(convergenceLevel === 'TIGHT', 18, matched, 'MA co chặt');
        structureScore += scorePart(convergenceContracting, 8, matched, 'Khoảng cách MA đang co');
        structureScore += scorePart(!convergenceContracting && tight, 4, matched, 'MA bắt đầu bung khỏi nền');
        structureScore += scorePart(convergenceSlope === 'UP', 8, matched, 'Cụm MA hướng lên');
        structureScore += scorePart(ma20Slope > 0, 6, matched, 'MA20 dốc lên');
        structureScore += scorePart(ma50Slope > 0, 6, matched, 'MA50 dốc lên');
        structureScore += scorePart(momentumOkay, 8, matched, 'Momentum xác nhận tăng');
        structureScore += scorePart(baseEstablished, 6, matched, `Nền MA duy trì ${tightDays} phiên`);

        entryScore += scorePart(aboveCluster, 15, matched, 'Giá đóng trên cả ba MA');
        entryScore += scorePart(nearCluster, 10, matched, 'Giá chưa rời xa cụm MA');
        entryScore += scorePart(positiveSession, 10, matched, 'Phiên hiện tại xác nhận tăng');
        entryScore += scorePart(volumeConfirmed, 5, matched, 'Volume xác nhận, không đột biến');

        if (!tight) warnings.push('Ba EMA chưa co đủ chặt');
        if (!baseEstablished) warnings.push(`Nền MA mới ${tightDays} phiên; cần tối thiểu ${RULES.minBreakoutBaseDays} phiên`);
        if (!directionOkay) warnings.push('Hướng MA chưa ủng hộ breakout tăng');
        if (!momentumOkay) {
            warnings.push(nonBearishMomentum ? 'Momentum chưa đồng thuận' : 'Momentum đang bearish');
        }
        if (!aboveCluster) warnings.push('Giá chưa đóng trên cả ba MA');
        if (!nearCluster) warnings.push('Giá đã rời xa cụm MA');
        if (!positiveSession) warnings.push('Phiên hiện tại chưa xác nhận tăng');
        if (!volumeConfirmed) warnings.push(volumeRatio > RULES.breakoutVolumeMax
            ? 'Volume đột biến, rủi ro phiên phân phối/hưng phấn'
            : 'Volume chưa xác nhận breakout');
        if (hasDeathCross) warnings.push('Death Cross vừa xuất hiện');

        const score = structureScore + entryScore;
        const isMatch = tight && baseEstablished && directionOkay && momentumOkay && aboveCluster &&
            nearCluster && positiveSession && volumeConfirmed && !hasDeathCross && score >= 85;
        const isWatch = !isMatch && tight && baseEstablished && nonBearishMomentum && aboveCluster &&
            nearCluster && !hasDeathCross && score >= 70;
        return {
            stage: STAGES.BREAKOUT_EARLY,
            isMatch,
            isWatch,
            score,
            structureScore,
            entryScore,
            matched,
            warnings
        };
    }

    function evaluatePullback(context, support) {
        const matched = [];
        const warnings = [];
        let structureScore = 0;
        let entryScore = 0;

        const {
            hasPerfectOrder,
            perfectOrderDays,
            momentumAlignment,
            ma20Slope,
            ma50Slope,
            priceVsMA20,
            priceVsMA50,
            volumeRatio,
            hasDeathCross
        } = context;

        const isMA50 = support.maName === 'MA50';
        const distance = isMA50 ? priceVsMA50 : priceVsMA20;
        const inEntryBand = isMA50
            ? distance >= -0.5 && distance <= 2.5
            : distance >= -0.5 && distance <= 2.2;
        const trendHealthy = ma50Slope > 0 && ma20Slope > 0;
        const trendEstablished = perfectOrderDays >= RULES.minPerfectOrderDays;
        const bullishMomentum = ['BULLISH_ALIGNED', 'MOSTLY_BULLISH'].includes(momentumAlignment);
        const momentumOkay = !['MOSTLY_BEARISH', 'BEARISH_ALIGNED'].includes(momentumAlignment);

        structureScore += scorePart(hasPerfectOrder, 30, matched, 'Perfect Order EMA10 > EMA20 > EMA50');
        structureScore += scorePart(ma50Slope > 0, 12, matched, 'MA50 dốc lên');
        structureScore += scorePart(ma20Slope > 0, 8, matched, 'MA20 dốc lên');
        structureScore += scorePart(bullishMomentum, 10, matched, 'Momentum bullish');
        structureScore += scorePart(momentumAlignment === 'MIXED', 5, matched, 'Momentum chậm lại khi pullback');

        entryScore += scorePart(inEntryBand && support.touched, isMA50 ? 22 : 19, matched, `Giá test ${support.maName}`);
        entryScore += scorePart(support.held, 5, matched, `Giữ được ${support.maName}`);
        entryScore += scorePart(support.bullishReaction, 9, matched, `Có phản ứng tăng tại ${support.maName}`);
        entryScore += scorePart(volumeRatio > 0 && volumeRatio <= 1.3, 4, matched, 'Volume không phân phối mạnh');

        if (!hasPerfectOrder) warnings.push('Không còn Perfect Order');
        if (!trendEstablished) warnings.push(
            `Perfect Order mới ${perfectOrderDays} phiên; cần tối thiểu ${RULES.minPerfectOrderDays} phiên`
        );
        if (perfectOrderDays > 60) warnings.push(`Perfect Order đã kéo dài ${perfectOrderDays} phiên`);
        if (!trendHealthy) warnings.push('Độ dốc MA20/MA50 chưa tích cực');
        if (!momentumOkay) warnings.push('Momentum không còn bullish');
        if (!support.touched) warnings.push(`Chưa thực sự test ${support.maName}`);
        else if (!support.held) warnings.push(
            `Đóng cửa dưới ${support.maName} (${distance.toFixed(2)}%); chưa giữ được hỗ trợ`
        );
        else if (!support.bullishReaction) warnings.push(`Chưa có phản ứng tăng tại ${support.maName}`);
        if (hasDeathCross) warnings.push('Death Cross vừa xuất hiện');

        const score = structureScore + entryScore;
        const isMatch = hasPerfectOrder && trendEstablished && trendHealthy && momentumOkay &&
            inEntryBand && support.bullishReaction && !hasDeathCross && score >= 75;
        const isWatch = !isMatch && hasPerfectOrder && trendEstablished && trendHealthy && momentumOkay &&
            inEntryBand && support.held && !hasDeathCross && score >= 70;
        return {
            stage: isMA50 ? STAGES.PULLBACK_MA50 : STAGES.PULLBACK_MA20,
            support: support.maName,
            isMatch,
            isWatch,
            score,
            structureScore,
            entryScore,
            matched,
            warnings
        };
    }

    function evaluatePotentialSignal(analysis, marketContext = null) {
        if (!analysis || analysis.error) return null;

        const priceVsMA10 = numberOr(analysis.price_position?.vs_ma10);
        const priceVsMA20 = numberOr(analysis.price_position?.vs_ma20);
        const priceVsMA50 = numberOr(analysis.price_position?.vs_ma50);
        if (![priceVsMA10, priceVsMA20, priceVsMA50].every(Number.isFinite)) return null;
        const hasPerfectOrder = !!analysis.perfect_order;
        const perfectOrderDays = Number.isFinite(Number(analysis.expansion?.perfect_order_days))
            ? Number(analysis.expansion.perfect_order_days)
            : (hasPerfectOrder ? 10 : 0);

        const context = {
            priceVsMA10,
            priceVsMA20,
            priceVsMA50,
            convergenceLevel: analysis.convergence?.level || 'NA',
            convergenceSlope: analysis.convergence?.slope || 'NA',
            convergenceContracting: analysis.convergence?.is_contracting !== false,
            tightDays: Math.max(0, Math.floor(numberOr(analysis.convergence?.tight_days, 0))),
            momentumAlignment: analysis.momentum?.alignment || 'NEUTRAL',
            ma20Slope: numberOr(analysis.momentum?.ma20?.slope, -Infinity),
            ma50Slope: numberOr(analysis.momentum?.ma50?.slope, -Infinity),
            volumeTrend: analysis.volume_analysis?.trend || 'NA',
            volumeRatio: numberOr(analysis.volume_analysis?.volume_ratio, 0),
            positiveSession: numberOr(analysis.price?.changePercent, -Infinity) >= 0,
            hasPerfectOrder,
            perfectOrderDays,
            hasDeathCross: !!analysis.death_cross?.has_cross
        };

        const ma20Support = evaluateSupportTest(analysis, 'MA20', priceVsMA20);
        const ma50Support = evaluateSupportTest(analysis, 'MA50', priceVsMA50);
        // A tight cluster is a breakout base even if the EMA ordering has just
        // become perfect. Pullback labels are reserved for an established,
        // already-expanded trend, avoiding a misleading MA50 classification
        // when all three averages occupy the same narrow price zone.
        const candidates = [
            evaluateBreakoutEarly(context),
            evaluatePullback(context, ma50Support),
            evaluatePullback(context, ma20Support)
        ];
        const selected = candidates.find(candidate => candidate.isMatch) ||
            candidates.filter(candidate => candidate.isWatch).sort((a, b) => b.score - a.score)[0] ||
            candidates.slice().sort((a, b) => b.score - a.score)[0];
        const hasMarketContext = marketContext && numberOr(marketContext.analyzed, 0) >= 10;
        const marketReady = !hasMarketContext || (
            numberOr(marketContext.aboveMA50Ratio, 0) >= 0.5 &&
            numberOr(marketContext.bullishRatio, 0) >= 0.4
        );
        if (selected.isMatch && !marketReady) {
            selected.warnings.push('Breadth yếu: dưới 50% mã trên MA50 hoặc dưới 40% mã có momentum bullish');
        }
        // Breadth is portfolio context, not an individual setup condition.
        // Keep valid setups visible and downgrade their confirmation instead of
        // turning the entire POTENTIAL tab empty during a weak market regime.
        const isReady = selected.isMatch;
        const isWatchCandidate = !isReady && !!selected.isWatch;
        const isPotential = isReady || isWatchCandidate;
        const status = isReady ? 'READY' : (isWatchCandidate ? 'WATCH' : 'REJECTED');
        const marketConfirmed = isReady && !!hasMarketContext && marketReady;
        const stage = isPotential ? selected.stage : null;
        const meta = stage ? STAGE_META[stage] : null;
        const marketSuffix = isReady && hasMarketContext && !marketReady ? ' · ⚠ TT yếu' : '';
        const badge = isReady
            ? `${meta.short} · ${selected.score}đ${marketSuffix}`
            : (isWatchCandidate ? `WATCH ${meta.short} · ${selected.score}đ` : 'Loại');
        const label = isReady
            ? `${stage} · ${selected.score}đ${marketSuffix}`
            : (isWatchCandidate ? `WATCH ${stage} · ${selected.score}đ` : `Chưa đạt · ${selected.score}đ`);
        const tooltip = [
            `<strong>${isPotential ? '🎯' : 'ℹ️'} ${label}</strong>`,
            `Structure score: ${selected.structureScore}`,
            `Entry score: ${selected.entryScore}`,
            `Total score: ${selected.score}`,
            stage ? `Setup: ${stage}` : 'Setup: Chưa đủ điều kiện',
            selected.matched.length ? `Khớp: ${selected.matched.join(', ')}` : 'Khớp: Chưa có tín hiệu nổi bật',
            selected.warnings.length ? `Rủi ro: ${selected.warnings.join(', ')}` : 'Rủi ro: Không có tín hiệu xấu nổi bật'
        ].join('<br>');

        return {
            isPotential,
            isReady,
            isWatchCandidate,
            status,
            score: selected.score,
            structureScore: selected.structureScore,
            entryScore: selected.entryScore,
            stage,
            setup: stage,
            support: selected.support || null,
            marketReady,
            marketConfirmed,
            marketBreadth: hasMarketContext ? marketContext : null,
            dataAsOf: analysis.data_as_of || null,
            statusPriority: isReady ? 2 : (isWatchCandidate ? 1 : 0),
            stagePriority: meta?.priority ?? 0,
            matched: selected.matched,
            warnings: selected.warnings,
            badge,
            label,
            color: isWatchCandidate
                ? 'amber-darken-2'
                : (isReady && hasMarketContext && !marketReady ? 'orange-darken-2' : (meta?.color || 'grey')),
            icon: isWatchCandidate
                ? 'mdi-eye-outline'
                : (isReady && hasMarketContext && !marketReady ? 'mdi-weather-cloudy-alert' : (meta?.icon || 'mdi-filter-remove')),
            tooltip
        };
    }

    function summarizePotentialSignal(signal) {
        if (!signal) return null;
        return {
            isPotential: !!signal.isPotential,
            status: signal.status || 'REJECTED',
            stage: signal.stage || null,
            score: numberOr(signal.score, 0),
            matched: Array.isArray(signal.matched) ? signal.matched.slice() : [],
            warnings: Array.isArray(signal.warnings) ? signal.warnings.slice() : [],
            dataAsOf: signal.dataAsOf || null
        };
    }

    function comparePotentialSignals(previous, current) {
        const before = summarizePotentialSignal(previous);
        const after = summarizePotentialSignal(current);
        if (!before || !after) return null;

        if (!before.isPotential && after.isPotential) {
            return { type: 'ENTERED', label: 'Mới vào', color: 'blue', reason: after.matched[0] || null };
        }
        if (before.isPotential && !after.isPotential) {
            return {
                type: 'EXITED',
                label: 'Rời Potential',
                color: 'red',
                reason: after.warnings[0] || 'Không còn đạt ngưỡng setup'
            };
        }
        if (before.isPotential && after.isPotential &&
            (before.status !== after.status || before.stage !== after.stage)) {
            return {
                type: 'CHANGED',
                label: `${before.status} → ${after.status}`,
                color: after.status === 'READY' ? 'green' : 'amber-darken-2',
                reason: before.stage !== after.stage ? `${before.stage} → ${after.stage}` : null
            };
        }
        if (before.isPotential && after.isPotential) {
            return { type: 'STABLE', label: 'Còn giữ', color: 'grey', reason: null };
        }
        return null;
    }

    return {
        STAGES,
        STAGE_META,
        RULES,
        evaluatePotentialSignal,
        evaluateSupportTest,
        summarizePotentialSignal,
        comparePotentialSignals
    };
});
