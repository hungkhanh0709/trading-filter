'use strict';

const { randomUUID } = require('crypto');
const { spawn } = require('child_process');
const os = require('os');
const path = require('path');

class PythonAnalysisWorker {
    constructor({ pythonPath, scriptPath, timeoutMs = 120000, spawnProcess = spawn }) {
        this.pythonPath = pythonPath;
        this.scriptPath = scriptPath;
        this.timeoutMs = timeoutMs;
        this.spawnProcess = spawnProcess;
        this.child = null;
        this.ready = false;
        this.startPromise = null;
        this.queue = [];
        this.current = null;
        this.stdoutBuffer = '';
    }

    start() {
        if (this.ready) return Promise.resolve();
        if (this.startPromise) return this.startPromise;

        this.startPromise = new Promise((resolve, reject) => {
            const cacheRoot = path.join(os.tmpdir(), 'trading-filter-python-cache');
            const child = this.spawnProcess(this.pythonPath, [this.scriptPath], {
                env: {
                    ...process.env,
                    MPLCONFIGDIR: process.env.MPLCONFIGDIR || path.join(cacheRoot, 'matplotlib'),
                    XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || cacheRoot
                }
            });
            this.child = child;
            this.stdoutBuffer = '';

            const rejectStartup = error => {
                if (!this.ready) reject(error);
            };

            child.stdout.on('data', data => {
                if (this.child === child) this.handleStdout(data, resolve);
            });
            child.stderr.on('data', data => process.stderr.write(data));
            child.stdin.on?.('error', error => {
                if (this.child === child) {
                    console.warn(`⚠️ Analysis worker stdin failed: ${error.message}`);
                }
            });
            child.on('error', error => rejectStartup(error));
            child.on('close', (code, signal) => {
                // A timed-out worker may close after its replacement is live.
                // Never let stale process events reset the new worker's state.
                if (this.child !== child) return;

                const wasReady = this.ready;
                this.ready = false;
                this.child = null;
                this.startPromise = null;

                if (!wasReady) {
                    rejectStartup(new Error(`Analysis worker exited during startup (${code ?? signal})`));
                }
                if (this.current) {
                    const request = this.current;
                    this.current = null;
                    clearTimeout(request.timeout);
                    request.resolve({
                        symbol: request.symbol,
                        error: `Analysis worker stopped (${code ?? signal})`
                    });
                }
                if (this.queue.length > 0) {
                    this.start().then(() => this.pump()).catch(error => this.failQueued(error));
                }
            });
        });

        return this.startPromise;
    }

    analyze(symbol, exchange = 'HOSE') {
        return new Promise(resolve => {
            this.queue.push({
                id: randomUUID(),
                symbol,
                exchange,
                resolve,
                timeout: null
            });

            this.start().then(() => this.pump()).catch(error => this.failQueued(error));
        });
    }

    handleStdout(data, resolveStartup) {
        this.stdoutBuffer += data.toString();
        const lines = this.stdoutBuffer.split('\n');
        this.stdoutBuffer = lines.pop();

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) continue;

            let message;
            try {
                message = JSON.parse(line);
            } catch {
                console.warn(`⚠️ Ignoring non-JSON analysis worker output: ${line}`);
                continue;
            }

            if (message.type === 'ready') {
                this.ready = true;
                resolveStartup();
                this.pump();
            } else if (message.type === 'result') {
                this.handleResult(message);
            }
        }
    }

    handleResult(message) {
        if (!this.current || message.id !== this.current.id) return;

        const request = this.current;
        this.current = null;
        clearTimeout(request.timeout);
        request.resolve(message.result);
        this.pump();
    }

    pump() {
        if (!this.ready || this.current || this.queue.length === 0) return;

        const request = this.queue.shift();
        this.current = request;
        request.timeout = setTimeout(() => {
            if (this.current !== request) return;

            this.current = null;
            request.resolve({
                symbol: request.symbol,
                error: `Analysis timed out after ${Math.ceil(this.timeoutMs / 1000)} seconds`
            });
            console.error(`⏱️ Analysis timed out for ${request.symbol} after ${this.timeoutMs}ms`);
            const timedOutChild = this.child;
            this.ready = false;
            this.child = null;
            this.startPromise = null;
            timedOutChild?.kill('SIGTERM');
            setTimeout(() => {
                if (timedOutChild?.exitCode === null && timedOutChild?.signalCode === null) {
                    timedOutChild.kill('SIGKILL');
                }
            }, 5000).unref();
        }, this.timeoutMs);
        request.timeout.unref();

        this.child.stdin.write(JSON.stringify({
            id: request.id,
            symbol: request.symbol,
            exchange: request.exchange
        }) + '\n');
    }

    failQueued(error) {
        const queued = this.queue.splice(0);
        queued.forEach(request => request.resolve({
            symbol: request.symbol,
            error: `Failed to start analysis worker: ${error.message}`
        }));
    }
}

module.exports = { PythonAnalysisWorker };
