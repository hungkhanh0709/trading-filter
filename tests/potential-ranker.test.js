const test = require('node:test');
const assert = require('node:assert/strict');

const {
    RULES,
    evaluatePotentialSignal,
    evaluateSupportProximity,
    comparePotentialRows
} = require('../public/potential-ranker');

function analysis(overrides = {}) {
    const base = {
        perfect_order: false,
        price: { current: 100, tickSize: 0.1 },
        price_position: {
            ma10: 95,
            ma20: 92,
            ma50: 88
        },
        convergence: { convergence_pct: 3 },
        golden_cross: { crosses: [], recent_crosses: [] }
    };
    return {
        ...base,
        ...overrides,
        price: { ...base.price, ...(overrides.price || {}) },
        price_position: { ...base.price_position, ...(overrides.price_position || {}) },
        convergence: { ...base.convergence, ...(overrides.convergence || {}) },
        golden_cross: { ...base.golden_cross, ...(overrides.golden_cross || {}) }
    };
}

test('keeps every valid analysis in Potential even when it earns zero stars', () => {
    const result = evaluatePotentialSignal(analysis());

    assert.equal(result.stars, 0);
    assert.equal(result.badge, '0★');
    assert.equal(result.criteria.length, 6);
});

test('Perfect Order adds exactly one star', () => {
    const result = evaluatePotentialSignal(analysis({ perfect_order: true }));

    assert.equal(result.stars, 1);
    assert.deepEqual(result.achieved, ['PERFECT_ORDER']);
});

test('an MA20/50 Golden Cross no older than five sessions adds one star', () => {
    const fresh = evaluatePotentialSignal(analysis({
        golden_cross: { recent_crosses: [{ type: 'MA20_MA50', days_ago: 5 }] }
    }));
    const stale = evaluatePotentialSignal(analysis({
        golden_cross: { recent_crosses: [{ type: 'MA20_MA50', days_ago: 6 }] }
    }));

    assert.equal(fresh.stars, 1);
    assert.ok(fresh.achieved.includes('FRESH_MA20_MA50_GOLDEN_CROSS'));
    assert.equal(stale.stars, 0);
});

test('an MA10/20 Golden Cross remains diagnostic and earns no Potential star', () => {
    const result = evaluatePotentialSignal(analysis({
        golden_cross: { recent_crosses: [{ type: 'MA10_MA20', days_ago: 0 }] }
    }));

    assert.equal(result.stars, 0);
    assert.ok(!result.achieved.includes('FRESH_MA20_MA50_GOLDEN_CROSS'));
    assert.match(result.tooltip, /☆ Golden Cross MA20\/50/);
});

test('a cluster no wider than one percent adds one star', () => {
    const tight = evaluatePotentialSignal(analysis({ convergence: { convergence_pct: 1 } }));
    const wide = evaluatePotentialSignal(analysis({ convergence: { convergence_pct: 1.01 } }));

    assert.equal(tight.stars, 1);
    assert.ok(tight.achieved.includes('TIGHT_CLUSTER'));
    assert.equal(wide.stars, 0);
});

test('pullback near MA10 adds one support star after Perfect Order', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price_position: { ma10: 100, ma20: 94, ma50: 88 }
    }));

    assert.equal(result.supportDepth, 1);
    assert.equal(result.nearestSupport, 'MA10');
    assert.deepEqual(result.achieved, ['PERFECT_ORDER', 'NEAR_MA10']);
    assert.equal(result.stars, 2);
});

test('pullback near MA20 cumulatively includes MA10 after Perfect Order', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price_position: { ma10: 104, ma20: 100, ma50: 88 }
    }));

    assert.equal(result.supportDepth, 2);
    assert.equal(result.nearestSupport, 'MA20');
    assert.deepEqual(result.achieved, ['PERFECT_ORDER', 'NEAR_MA10', 'NEAR_MA20']);
    assert.equal(result.stars, 3);
});

test('pullback near MA50 cumulatively earns all three support stars after Perfect Order', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price_position: { ma10: 110, ma20: 105, ma50: 100 }
    }));

    assert.equal(result.supportDepth, 3);
    assert.equal(result.nearestSupport, 'MA50');
    assert.deepEqual(result.achieved, [
        'PERFECT_ORDER', 'NEAR_MA10', 'NEAR_MA20', 'NEAR_MA50'
    ]);
    assert.equal(result.stars, 4);
});

test('proximity to any MA cannot earn pullback stars without Perfect Order', () => {
    const cases = [
        { ma10: 100, ma20: 94, ma50: 88 },
        { ma10: 104, ma20: 100, ma50: 88 },
        { ma10: 110, ma20: 105, ma50: 100 }
    ];

    for (const pricePosition of cases) {
        const result = evaluatePotentialSignal(analysis({ price_position: pricePosition }));

        assert.equal(result.stars, 0);
        assert.equal(result.supportDepth, 0);
        assert.equal(result.nearestSupport, null);
        assert.match(result.tooltip, /cần Perfect Order/);
    }
});

test('support proximity uses the tradable tick for NVL-like prices', () => {
    const input = analysis({
        price: { current: 13.2, tickSize: 0.05 },
        price_position: { ma50: 13.2075 }
    });
    const support = evaluateSupportProximity(input, {
        name: 'MA50', positionKey: 'ma50', depth: 3
    });

    assert.equal(support.roundedMA, 13.2);
    assert.equal(support.distancePct, 0);
    assert.equal(support.isNear, true);
});

test('a close more than half a percent below support earns no proximity star', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price_position: { ma10: 100.6, ma20: 95, ma50: 90 }
    }));

    assert.equal(result.supportDepth, 0);
    assert.equal(result.stars, 1);
});

test('TCB-like resistance test earns no pullback star without Perfect Order', () => {
    const result = evaluatePotentialSignal(analysis({
        price: { current: 31, tickSize: 0.05 },
        price_position: { ma10: 30.9802, ma20: 30.7594, ma50: 31.1317 },
        convergence: { convergence_pct: 1.21 },
        golden_cross: { recent_crosses: [{ type: 'MA10_MA20', days_ago: 4 }] }
    }));

    assert.equal(result.stars, 0);
    assert.equal(result.nearestSupport, null);
});

test('DSE-like tight cluster keeps only its cluster star without Perfect Order', () => {
    const result = evaluatePotentialSignal(analysis({
        price: { current: 22.25, tickSize: 0.05 },
        price_position: { ma10: 22.2752, ma20: 22.2821, ma50: 22.3638 },
        convergence: { convergence_pct: 0.4 },
        golden_cross: { recent_crosses: [{ type: 'MA10_MA20', days_ago: 6 }] }
    }));

    assert.equal(result.stars, 1);
    assert.deepEqual(result.achieved, ['TIGHT_CLUSTER']);
    assert.equal(result.nearestSupport, null);
});

test('HDB-like overlapping ranges select only the nearest MA10 pullback tier', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price: { current: 26.7, tickSize: 0.05 },
        price_position: { ma10: 26.6917, ma20: 26.5468, ma50: 26.3694 },
        convergence: { convergence_pct: 1.22 },
        golden_cross: { recent_crosses: [{ type: 'MA20_MA50', days_ago: 8 }] }
    }));

    assert.equal(result.stars, 2);
    assert.equal(result.supportDepth, 1);
    assert.equal(result.nearestSupport, 'MA10');
    assert.deepEqual(result.achieved, ['PERFECT_ORDER', 'NEAR_MA10']);
    assert.deepEqual(
        result.supportChecks.map(check => check.isNear),
        [true, true, true]
    );
});

test('equal pullback distances conservatively select the shallower MA tier', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price_position: { ma10: 100, ma20: 100, ma50: 90 }
    }));

    assert.equal(result.supportDepth, 1);
    assert.equal(result.nearestSupport, 'MA10');
    assert.deepEqual(result.achieved, ['PERFECT_ORDER', 'NEAR_MA10']);
});

test('NVL-like setup does not earn the strict one-percent cluster star', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price: { current: 13.2, tickSize: 0.05 },
        price_position: {
            ma10: 13.3548,
            ma20: 13.2433,
            ma50: 13.2079
        },
        convergence: { convergence_pct: 1.11 },
        golden_cross: { recent_crosses: [{ type: 'MA20_MA50', days_ago: 5 }] }
    }));

    assert.equal(result.stars, 5);
    assert.equal(result.badge, '★★★★★');
    assert.equal(result.nearestSupport, 'MA50');
});

test('GMD-like stretched setup receives only its Perfect Order star', () => {
    const result = evaluatePotentialSignal(analysis({
        perfect_order: true,
        price: { current: 79.5, tickSize: 0.1 },
        price_position: {
            ma10: 77.9762,
            ma20: 77.1238,
            ma50: 76.3262
        },
        convergence: { convergence_pct: 2.16 },
        golden_cross: { recent_crosses: [{ type: 'MA20_MA50', days_ago: 8 }] }
    }));

    assert.equal(result.stars, 1);
    assert.deepEqual(result.achieved, ['PERFECT_ORDER']);
});

test('volume, momentum and market context cannot add or remove stars', () => {
    const input = analysis({
        perfect_order: true,
        volume_analysis: { volume_ratio: 0.1 },
        momentum: { alignment: 'MOSTLY_BEARISH' },
        death_cross: { has_cross: true }
    });
    const result = evaluatePotentialSignal(input, {
        analyzed: 100,
        aboveMA50Ratio: 0,
        bullishRatio: 0
    });

    assert.equal(result.stars, 1);
});

test('sorts by stars descending and alphabetically when tied', () => {
    const rows = [
        { symbol: 'VCB', potentialSignal: { stars: 2 } },
        { symbol: 'ACB', potentialSignal: { stars: 2 } },
        { symbol: 'NVL', potentialSignal: { stars: 6 } },
        { symbol: 'GMD', potentialSignal: { stars: 1 } }
    ];

    assert.deepEqual(
        rows.sort(comparePotentialRows).map(row => row.symbol),
        ['NVL', 'ACB', 'VCB', 'GMD']
    );
});

test('documents the intentionally small set of observable thresholds', () => {
    assert.deepEqual(RULES, {
        freshGoldenCrossDays: 5,
        tightClusterMaxPct: 1,
        nearSupportMinPct: -0.5,
        nearSupportMaxPct: 1.5
    });
});
