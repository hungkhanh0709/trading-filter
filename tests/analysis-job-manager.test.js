'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { AnalysisJobManager } = require('../src/analysis-job-manager');

async function waitForCompletion(manager, id) {
    for (let attempt = 0; attempt < 100; attempt++) {
        const job = manager.get(id);
        if (job.status === 'completed' || job.status === 'failed') return job;
        await new Promise(resolve => setTimeout(resolve, 2));
    }
    throw new Error('Timed out waiting for test job');
}

test('server-owned job continues through all symbols and accumulates results', async () => {
    const calls = [];
    const manager = new AnalysisJobManager({
        delayMs: 0,
        analyze: async symbol => {
            calls.push(symbol);
            return { symbol };
        }
    });

    const created = manager.create(['FPT', 'IDC']);
    const completed = await waitForCompletion(manager, created.id);

    assert.deepEqual(calls, ['FPT', 'IDC']);
    assert.equal(completed.status, 'completed');
    assert.equal(completed.completed, 2);
    assert.deepEqual(completed.results.FPT, {
        success: true,
        data: { symbol: 'FPT' }
    });
});

test('one failed symbol does not block the next symbol', async () => {
    const calls = [];
    const manager = new AnalysisJobManager({
        delayMs: 0,
        analyze: async symbol => {
            calls.push(symbol);
            if (symbol === 'IDC') throw new Error('upstream timeout');
            return { symbol };
        }
    });

    const created = manager.create(['IDC', 'FPT']);
    const completed = await waitForCompletion(manager, created.id);

    assert.deepEqual(calls, ['IDC', 'FPT']);
    assert.equal(completed.status, 'completed');
    assert.equal(completed.completed, 2);
    assert.deepEqual(completed.results.IDC, {
        success: false,
        error: 'upstream timeout'
    });
    assert.equal(completed.results.FPT.success, true);
});
