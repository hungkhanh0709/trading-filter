'use strict';

const { randomUUID } = require('crypto');

const DEFAULT_JOB_TTL_MS = 60 * 60 * 1000;

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

class AnalysisJobManager {
    constructor({ analyze, delayMs = 1000, jobTtlMs = DEFAULT_JOB_TTL_MS }) {
        if (typeof analyze !== 'function') {
            throw new TypeError('analyze must be a function');
        }

        this.analyze = analyze;
        this.delayMs = delayMs;
        this.jobTtlMs = jobTtlMs;
        this.jobs = new Map();
    }

    create(symbols) {
        this.pruneExpiredJobs();

        const job = {
            id: randomUUID(),
            status: 'queued',
            symbols: [...symbols],
            completed: 0,
            total: symbols.length,
            results: {},
            createdAt: Date.now(),
            finishedAt: null
        };

        this.jobs.set(job.id, job);

        // Detach processing from the HTTP request so it survives browser tab
        // throttling and suspension.
        setImmediate(() => {
            this.run(job).catch(error => {
                job.status = 'failed';
                job.error = error.message;
                job.finishedAt = Date.now();
                console.error(`❌ Analysis job ${job.id} failed:`, error);
            });
        });

        return this.toResponse(job);
    }

    get(id) {
        const job = this.jobs.get(id);
        return job ? this.toResponse(job) : null;
    }

    async run(job) {
        job.status = 'running';

        for (let index = 0; index < job.symbols.length; index++) {
            const symbol = job.symbols[index];

            try {
                const result = await this.analyze(symbol);
                job.results[symbol] = result?.error
                    ? { success: false, error: result.error }
                    : { success: true, data: result };
            } catch (error) {
                job.results[symbol] = { success: false, error: error.message };
            } finally {
                job.completed++;
            }

            if (this.delayMs > 0 && index < job.symbols.length - 1) {
                await wait(this.delayMs);
            }
        }

        job.status = 'completed';
        job.finishedAt = Date.now();
    }

    pruneExpiredJobs() {
        const cutoff = Date.now() - this.jobTtlMs;

        for (const [id, job] of this.jobs) {
            if (job.finishedAt && job.finishedAt < cutoff) {
                this.jobs.delete(id);
            }
        }
    }

    toResponse(job) {
        return {
            id: job.id,
            status: job.status,
            completed: job.completed,
            total: job.total,
            results: { ...job.results },
            error: job.error || null
        };
    }
}

module.exports = { AnalysisJobManager };
