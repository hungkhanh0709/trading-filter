'use strict';

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const test = require('node:test');
const { PythonAnalysisWorker } = require('../src/python-analysis-worker');

test('reuses one Python process for sequential analyses', async () => {
    let spawnCount = 0;
    const requests = [];

    const spawnProcess = () => {
        spawnCount++;
        const child = new EventEmitter();
        child.stdout = new EventEmitter();
        child.stderr = new EventEmitter();
        child.stdin = {
            write(line) {
                const request = JSON.parse(line);
                requests.push(request.symbol);
                setImmediate(() => {
                    child.stdout.emit('data', Buffer.from(JSON.stringify({
                        type: 'result',
                        id: request.id,
                        result: { symbol: request.symbol }
                    }) + '\n'));
                });
            }
        };
        child.kill = () => {};
        setImmediate(() => {
            child.stdout.emit('data', Buffer.from('{"type":"ready"}\n'));
        });
        return child;
    };

    const worker = new PythonAnalysisWorker({
        pythonPath: 'python',
        scriptPath: 'worker.py',
        timeoutMs: 1000,
        spawnProcess
    });

    const results = await Promise.all([
        worker.analyze('CTR'),
        worker.analyze('FPT')
    ]);

    assert.equal(spawnCount, 1);
    assert.deepEqual(requests, ['CTR', 'FPT']);
    assert.deepEqual(results, [{ symbol: 'CTR' }, { symbol: 'FPT' }]);
});

test('restarts the worker before processing the symbol after a timeout', async () => {
    let spawnCount = 0;

    const spawnProcess = () => {
        spawnCount++;
        const workerNumber = spawnCount;
        const child = new EventEmitter();
        child.stdout = new EventEmitter();
        child.stderr = new EventEmitter();
        child.stdin = new EventEmitter();
        child.stdin.write = line => {
            const request = JSON.parse(line);
            if (workerNumber === 1) return;
            setImmediate(() => child.stdout.emit('data', Buffer.from(JSON.stringify({
                type: 'result',
                id: request.id,
                result: { symbol: request.symbol }
            }) + '\n')));
        };
        child.kill = () => setImmediate(() => child.emit('close', null, 'SIGTERM'));
        child.exitCode = null;
        child.signalCode = null;
        setImmediate(() => child.stdout.emit('data', Buffer.from('{"type":"ready"}\n')));
        return child;
    };

    const worker = new PythonAnalysisWorker({
        pythonPath: 'python',
        scriptPath: 'worker.py',
        timeoutMs: 10,
        spawnProcess
    });

    const timedOut = await worker.analyze('CTR');
    const recovered = await worker.analyze('FPT');

    assert.match(timedOut.error, /timed out/);
    assert.deepEqual(recovered, { symbol: 'FPT' });
    assert.equal(spawnCount, 2);
});
