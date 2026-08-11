const test = require('node:test');
const assert = require('node:assert/strict');

const {
    evaluatePotentialSignal,
    evaluateSupportTest,
    comparePotentialSignals
} = require('../public/potential-filter');

function analysis(overrides = {}) {
    const base = {
        perfect_order: false,
        price: {
            current: 100,
            open: 99,
            high: 102,
            low: 98.5,
            changePercent: 1
        },
        price_position: { vs_ma10: 0.5, vs_ma20: 1, vs_ma50: 1.5 },
        convergence: { level: 'SUPER_TIGHT', slope: 'UP', is_contracting: true, tight_days: 8 },
        expansion: { perfect_order_days: 10 },
        momentum: {
            alignment: 'BULLISH_ALIGNED',
            ma20: { slope: 0.2 },
            ma50: { slope: 0.1 }
        },
        volume_analysis: { trend: 'INCREASING', volume_ratio: 1.1 },
        death_cross: { has_cross: false }
    };

    return {
        ...base,
        ...overrides,
        price: { ...base.price, ...(overrides.price || {}) },
        price_position: { ...base.price_position, ...(overrides.price_position || {}) },
        convergence: { ...base.convergence, ...(overrides.convergence || {}) },
        expansion: { ...base.expansion, ...(overrides.expansion || {}) },
        momentum: {
            ...base.momentum,
            ...(overrides.momentum || {}),
            ma20: { ...base.momentum.ma20, ...(overrides.momentum?.ma20 || {}) },
            ma50: { ...base.momentum.ma50, ...(overrides.momentum?.ma50 || {}) }
        },
        volume_analysis: { ...base.volume_analysis, ...(overrides.volume_analysis || {}) },
        death_cross: { ...base.death_cross, ...(overrides.death_cross || {}) }
    };
}

test('accepts a bullish tight MA cluster as BREAKOUT EARLY even in perfect order', () => {
    const result = evaluatePotentialSignal(analysis({ perfect_order: true }));

    assert.equal(result.isPotential, true);
    assert.equal(result.stage, 'BREAKOUT EARLY');
    assert.match(result.badge, /^BE/);
    assert.equal(result.status, 'READY');
});

test('accepts breakout release when a tight bullish MA cluster starts expanding', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        convergence: { is_contracting: false }
    }));

    assert.equal(result.isReady, true);
    assert.equal(result.stage, 'BREAKOUT EARLY');
    assert.ok(result.matched.includes('MA bắt đầu bung khỏi nền'));
});

test('surfaces a high-score pre-breakout candidate as WATCH', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: false,
        convergence: { level: 'SUPER_TIGHT', slope: 'NEUTRAL', is_contracting: true },
        momentum: {
            alignment: 'MOSTLY_BULLISH',
            ma20: { slope: 0.13 },
            ma50: { slope: -0.13 }
        },
        price_position: { vs_ma10: 2.4, vs_ma20: 3.1, vs_ma50: 2 }
    }));

    assert.equal(result.isPotential, true);
    assert.equal(result.isReady, false);
    assert.equal(result.isWatchCandidate, true);
    assert.equal(result.status, 'WATCH');
    assert.match(result.badge, /^WATCH BE/);
});

test('rejects a one-session MA base instead of promoting it to Potential', () => {
    const result = evaluatePotentialSignal(analysis({
        convergence: { tight_days: 1 }
    }));

    assert.equal(result.isPotential, false);
    assert.ok(result.warnings.some(warning => warning.includes('cần tối thiểu 3 phiên')));
});

test('keeps an established breakout base at WATCH until volume confirms', () => {
    const result = evaluatePotentialSignal(analysis({
        volume_analysis: { volume_ratio: 0.7 }
    }));

    assert.equal(result.isReady, false);
    assert.equal(result.isWatchCandidate, true);
    assert.ok(result.warnings.includes('Volume chưa xác nhận breakout'));
});

test('rejects tight convergence when the MA cluster points down', () => {
    const result = evaluatePotentialSignal(analysis({
        convergence: { slope: 'DOWN' },
        momentum: {
            alignment: 'MOSTLY_BEARISH',
            ma20: { slope: -0.12 },
            ma50: { slope: -0.08 }
        }
    }));

    assert.equal(result.isPotential, false);
    assert.equal(result.stage, null);
});

test('detects a confirmed perfect-order pullback to MA20', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        convergence: { level: 'LOOSE', slope: 'UP' },
        price_position: { vs_ma10: -1, vs_ma20: 1, vs_ma50: 8 }
    }));

    assert.equal(result.isPotential, true);
    assert.equal(result.stage, 'PULLBACK MA20');
    assert.equal(result.support, 'MA20');
});

test('rejects a pullback when Perfect Order has existed for only one session', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        expansion: { perfect_order_days: 1 },
        convergence: { level: 'LOOSE', slope: 'UP' },
        price_position: { vs_ma10: -1, vs_ma20: 1, vs_ma50: 8 }
    }));

    assert.equal(result.isPotential, false);
    assert.ok(result.warnings.some(warning => warning.includes('cần tối thiểu 3 phiên')));
});

test('allows a genuine MA50 pullback below MA20 instead of rejecting it as pressure', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        convergence: { level: 'LOOSE', slope: 'UP' },
        price_position: { vs_ma10: -6, vs_ma20: -4, vs_ma50: 1 }
    }));

    assert.equal(result.isPotential, true);
    assert.equal(result.stage, 'PULLBACK MA50');
    assert.equal(result.support, 'MA50');
});

test('does not call proximity a pullback when the candle has not tested the MA', () => {
    const input = analysis({
        perfect_order: true,
        convergence: { level: 'LOOSE', slope: 'UP' },
        price: { low: 99.9 },
        price_position: { vs_ma10: 0.5, vs_ma20: 1, vs_ma50: 8 }
    });
    const support = evaluateSupportTest(input, 'MA20', 1);
    const result = evaluatePotentialSignal(input);

    assert.equal(support.touched, false);
    assert.equal(result.isPotential, false);
});

test('rejects a marginal MA50 undercut that still closes below support', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        convergence: { level: 'LOOSE', slope: 'UP' },
        price: { current: 99.7, open: 101, high: 101.5, low: 98, changePercent: -1.2 },
        price_position: { vs_ma10: -7, vs_ma20: -5, vs_ma50: -0.3 }
    }));

    assert.equal(result.isPotential, false);
    assert.equal(result.isReady, false);
    assert.equal(result.isWatchCandidate, false);
    assert.equal(result.stage, null);
    assert.ok(result.warnings.some(warning => warning.includes('Đóng cửa dưới MA50')));
});

test('distinguishes a near MA50 undercut from a confirmed support hold', () => {
    const input = analysis({
        price: { current: 99.8, high: 101, low: 98 },
        price_position: { vs_ma50: -0.2 }
    });

    const support = evaluateSupportTest(input, 'MA50', -0.2);

    assert.equal(support.touched, true);
    assert.equal(support.nearHold, true);
    assert.equal(support.held, false);
    assert.equal(support.bullishReaction, false);
});

test('keeps a mature perfect-order pullback ready but exposes its age risk', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        expansion: { perfect_order_days: 82 },
        convergence: { level: 'LOOSE', slope: 'UP' },
        price_position: { vs_ma10: -1, vs_ma20: 1, vs_ma50: 8 }
    }));

    assert.equal(result.isReady, true);
    assert.ok(result.warnings.some(warning => warning.includes('82 phiên')));
});

test('accepts a perfect-order MA50 rejection while short momentum is mixed', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        expansion: { perfect_order_days: 20 },
        price: { current: 136, open: 135, high: 136, low: 133.5, changePercent: 0.82 },
        price_position: { vs_ma10: 0.14, vs_ma20: 0.45, vs_ma50: 1.25 },
        momentum: {
            alignment: 'MIXED',
            ma20: { slope: 0.09 },
            ma50: { slope: 0.06 }
        }
    }));

    assert.equal(result.isReady, true);
    assert.equal(result.stage, 'PULLBACK MA50');
    assert.equal(result.score, 95);
});

test('keeps a valid setup visible while weak breadth downgrades confirmation', () => {
    const input = analysis({ perfect_order: true });
    const base = evaluatePotentialSignal(input);
    const weakMarket = evaluatePotentialSignal(input, {
        analyzed: 100,
        aboveMA50Ratio: 0.45,
        bullishRatio: 0.35
    });
    const healthyMarket = evaluatePotentialSignal(input, {
        analyzed: 100,
        aboveMA50Ratio: 0.55,
        bullishRatio: 0.45
    });

    assert.equal(base.isPotential, true);
    assert.equal(weakMarket.isPotential, true);
    assert.equal(weakMarket.stage, base.stage);
    assert.equal(weakMarket.score, base.score);
    assert.equal(weakMarket.marketReady, false);
    assert.equal(weakMarket.marketConfirmed, false);
    assert.match(weakMarket.badge, /TT yếu/);
    assert.equal(healthyMarket.isPotential, true);
    assert.equal(healthyMarket.marketConfirmed, true);
});

test('keeps cached perfect-order analysis compatible before age field exists', () => {
    const input = analysis({
        perfect_order: true,
        expansion: { perfect_order_days: undefined },
        convergence: { level: 'LOOSE', slope: 'UP' },
        price_position: { vs_ma10: -1, vs_ma20: 1, vs_ma50: 8 }
    });

    const result = evaluatePotentialSignal(input);

    assert.equal(result.isPotential, true);
    assert.equal(result.stage, 'PULLBACK MA20');
});

test('keeps the UI return contract and handles invalid analysis safely', () => {
    const result = evaluatePotentialSignal(analysis());

    for (const key of [
        'isPotential', 'score', 'structureScore', 'entryScore', 'stage',
        'isReady', 'isWatchCandidate', 'status', 'statusPriority', 'stagePriority',
        'matched', 'warnings', 'badge', 'label', 'color', 'icon', 'tooltip'
    ]) {
        assert.ok(Object.hasOwn(result, key), `missing ${key}`);
    }
    assert.equal(evaluatePotentialSignal(null), null);
    assert.equal(evaluatePotentialSignal({ error: 'failed' }), null);
});

test('explains entry and exit relative to the previous completed session', () => {
    const entered = comparePotentialSignals(
        { isPotential: false, status: 'REJECTED', score: 65, warnings: [] },
        { isPotential: true, status: 'WATCH', stage: 'BREAKOUT EARLY', score: 74, warnings: [] }
    );
    const exited = comparePotentialSignals(
        { isPotential: true, status: 'READY', stage: 'PULLBACK MA20', score: 86, warnings: [] },
        { isPotential: false, status: 'REJECTED', score: 64, warnings: ['Đóng cửa chưa giữ được MA20'] }
    );

    assert.equal(entered.type, 'ENTERED');
    assert.equal(exited.type, 'EXITED');
    assert.equal(exited.reason, 'Đóng cửa chưa giữ được MA20');
});
