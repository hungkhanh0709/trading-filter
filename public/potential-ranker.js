(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.PotentialRanker = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    // Potential is deliberately an additive observation model. There are no
    // symbol rejection gates, negative points or hidden weights. Pullback
    // criteria have one explicit prerequisite: an existing Perfect Order.
    const RULES = Object.freeze({
        freshGoldenCrossDays: 5,
        tightClusterMaxPct: 1,
        nearSupportMinPct: -0.5,
        nearSupportMaxPct: 1.5
    });

    const SUPPORTS = Object.freeze([
        { name: 'MA10', positionKey: 'ma10', depth: 1 },
        { name: 'MA20', positionKey: 'ma20', depth: 2 },
        { name: 'MA50', positionKey: 'ma50', depth: 3 }
    ]);

    function numberOr(value, fallback = NaN) {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : fallback;
    }

    function roundToTick(price, tickSize) {
        if (!Number.isFinite(price) || !Number.isFinite(tickSize) || tickSize <= 0) return price;
        return Number((Math.round(price / tickSize) * tickSize).toFixed(6));
    }

    function distanceFromPrices(close, maPrice) {
        if (!Number.isFinite(close) || !Number.isFinite(maPrice) || maPrice === 0) return NaN;
        return (close - maPrice) / maPrice * 100;
    }

    function evaluateSupportProximity(analysis, support) {
        const close = numberOr(analysis.price?.current);
        const tickSize = numberOr(analysis.price?.tickSize);
        const mathematicalMA = numberOr(analysis.price_position?.[support.positionKey]);
        const roundedMA = roundToTick(mathematicalMA, tickSize);
        const distancePct = distanceFromPrices(close, roundedMA);
        const isNear = Number.isFinite(distancePct) &&
            distancePct >= RULES.nearSupportMinPct &&
            distancePct <= RULES.nearSupportMaxPct;

        return {
            ...support,
            close,
            tickSize,
            mathematicalMA,
            roundedMA,
            distancePct,
            isNear
        };
    }

    function selectNearestSupport(supportChecks) {
        return supportChecks
            .filter(check => check.isNear)
            .sort((a, b) => {
                const distanceDiff = Math.abs(a.distancePct) - Math.abs(b.distancePct);
                return distanceDiff !== 0 ? distanceDiff : a.depth - b.depth;
            })[0] || null;
    }

    function getFreshMa2050GoldenCross(analysis) {
        const recentCrosses = Array.isArray(analysis.golden_cross?.recent_crosses)
            ? analysis.golden_cross.recent_crosses
            : [];
        const todayCrosses = Array.isArray(analysis.golden_cross?.crosses)
            ? analysis.golden_cross.crosses.map(cross => ({ ...cross, days_ago: 0 }))
            : [];
        return [...recentCrosses, ...todayCrosses]
            .filter(cross => cross.type === 'MA20_MA50')
            .filter(cross => numberOr(cross.days_ago, Infinity) <= RULES.freshGoldenCrossDays)
            .sort((a, b) => numberOr(a.days_ago, Infinity) - numberOr(b.days_ago, Infinity))[0] || null;
    }

    function starText(stars) {
        return '★'.repeat(stars);
    }

    function evaluatePotentialSignal(analysis) {
        if (!analysis || analysis.error) return null;

        const perfectOrder = !!analysis.perfect_order;
        const supportChecks = SUPPORTS.map(support => evaluateSupportProximity(analysis, support));
        const nearestSupport = perfectOrder ? selectNearestSupport(supportChecks) : null;
        const supportDepth = nearestSupport?.depth || 0;
        const freshGoldenCross = getFreshMa2050GoldenCross(analysis);
        const convergencePct = numberOr(analysis.convergence?.convergence_pct, Infinity);
        const tightCluster = convergencePct <= RULES.tightClusterMaxPct;

        const criteria = [
            {
                key: 'PERFECT_ORDER',
                label: 'Perfect Order MA10 > MA20 > MA50',
                met: perfectOrder
            },
            {
                key: 'FRESH_MA20_MA50_GOLDEN_CROSS',
                label: freshGoldenCross
                    ? `Golden Cross MA20/50 mới (${numberOr(freshGoldenCross.days_ago, 0)} phiên)`
                    : `Golden Cross MA20/50 trong ${RULES.freshGoldenCrossDays} phiên`,
                met: !!freshGoldenCross
            },
            {
                key: 'TIGHT_CLUSTER',
                label: Number.isFinite(convergencePct)
                    ? `Cụm MA rất chặt (${convergencePct.toFixed(2)}% ≤ ${RULES.tightClusterMaxPct}%)`
                    : 'Cụm MA rất chặt',
                met: tightCluster
            },
            ...supportChecks.map(support => {
                return {
                    key: `NEAR_${support.name}`,
                    label: !perfectOrder
                        ? `Pullback đạt tầng ${support.name} (cần Perfect Order)`
                        : support.depth <= supportDepth
                        ? `Pullback đạt tầng ${support.name}${nearestSupport?.name === support.name ? ` (${support.distancePct.toFixed(2)}%)` : ''}`
                        : `Pullback đạt tầng ${support.name}`,
                    // The single nearest MA selects the tier; deeper tiers still
                    // include shallower ones through the cumulative ladder.
                    met: support.depth <= supportDepth
                };
            })
        ].map(criterion => ({ ...criterion, stars: criterion.met ? 1 : 0 }));

        const stars = criteria.reduce((total, criterion) => total + criterion.stars, 0);
        const achieved = criteria.filter(criterion => criterion.met);
        const scoreText = `${stars}/${criteria.length}`;
        const badge = stars > 0 ? starText(stars) : scoreText;
        const tooltip = [
            `<strong>${stars > 0 ? `${badge} · ` : ''}${scoreText} tiêu chí</strong>`,
            ...criteria.map(criterion => `${criterion.met ? '★' : '☆'} ${criterion.label}`),
        ].join('<br>');

        return {
            stars,
            maxStars: criteria.length,
            badge,
            label: stars > 0 ? `${badge} · ${scoreText}` : scoreText,
            tooltip,
            criteria,
            achieved: achieved.map(criterion => criterion.key),
            supportDepth,
            nearestSupport: nearestSupport?.name || null,
            supportChecks
        };
    }

    function comparePotentialRows(a, b) {
        const starDiff = (b?.potentialSignal?.stars ?? -1) - (a?.potentialSignal?.stars ?? -1);
        if (starDiff !== 0) return starDiff;
        return String(a?.symbol || '').localeCompare(String(b?.symbol || ''));
    }

    return {
        RULES,
        SUPPORTS,
        evaluatePotentialSignal,
        evaluateSupportProximity,
        comparePotentialRows
    };
});
