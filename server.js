const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { AnalysisJobManager } = require('./src/analysis-job-manager');
const { PythonAnalysisWorker } = require('./src/python-analysis-worker');

const app = express();
const PORT = process.env.PORT || 3000;

// Supported exchanges
const EXCHANGES = ['HOSE', 'HNX'];

// TradingView URL helper
const getTradingViewUrl = (exchange, symbol) => {
    return `https://vn.tradingview.com/chart/27IsBTqc/?symbol=${exchange}%3A${symbol}`;
};

// File paths
const WATCH_LIST_FILE = path.join(__dirname, 'data', 'watch-list.json');
const VN30_FILE = path.join(__dirname, 'data', 'vn30.json');
const VN100_FILE = path.join(__dirname, 'data', 'vn100.json');
const HNX30_FILE = path.join(__dirname, 'data', 'hnx30.json');
const PYTHON_VENV = path.join(__dirname, '.venv', 'bin', 'python');
const ANALYSIS_WORKER_SCRIPT = path.join(__dirname, 'scripts', 'analysis_worker.py');
const ANALYSIS_TIMEOUT_MS = Number(process.env.ANALYSIS_TIMEOUT_MS) || 120 * 1000;
const ANALYSIS_JOB_DELAY_MS = Number(process.env.ANALYSIS_JOB_DELAY_MS) || 1000;
const analysisWorker = new PythonAnalysisWorker({
    pythonPath: PYTHON_VENV,
    scriptPath: ANALYSIS_WORKER_SCRIPT,
    timeoutMs: ANALYSIS_TIMEOUT_MS
});

// Analysis cache - 180 minutes TTL
const analysisCache = {
    data: {},
    ttl: 180 * 60 * 1000
};
const inFlightAnalyses = new Map();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Load VN30 index list
let vn30List = [];
try {
    const vn30Data = JSON.parse(fs.readFileSync(VN30_FILE, 'utf8'));
    vn30List = vn30Data.symbols || [];
    console.log(`✅ Loaded ${vn30List.length} VN30 symbols`);
} catch (error) {
    console.error('❌ Error loading VN30 data:', error.message);
}

// Load VN100 index list
let vn100List = [];
try {
    const vn100Data = JSON.parse(fs.readFileSync(VN100_FILE, 'utf8'));
    vn100List = vn100Data.symbols || [];
    console.log(`✅ Loaded ${vn100List.length} VN100 symbols`);
} catch (error) {
    console.error('❌ Error loading VN100 data:', error.message);
}

// Load HNX30 index list
let hnx30List = [];
try {
    const hnx30Data = JSON.parse(fs.readFileSync(HNX30_FILE, 'utf8'));
    hnx30List = hnx30Data.symbols || [];
    console.log(`✅ Loaded ${hnx30List.length} HNX30 symbols`);
} catch (error) {
    console.error('❌ Error loading HNX30 data:', error.message);
}



/**
 * GET /api/symbols
 * Get symbols list
 * 
 * Query params:
 *   - exchange: WATCHLIST (default), VN30, VN100, HNX30, ALL, POTENTIAL, HOSE, HNX
 */
app.get('/api/symbols', async (req, res) => {
    try {
        const exchange = req.query.exchange || 'WATCHLIST';

        // Get symbols
        const symbols = getSymbols(exchange);

        res.json({
            success: true,
            data: {
                symbols
            }
        });
    } catch (error) {
        console.error('❌ Error in /api/symbols:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/analyze/:symbol
 * Analyze a single stock with caching (180-minute TTL)
 * 
 * Query params:
 *   - force: "1" to force refresh analysis
 */
app.get('/api/analyze/:symbol', async (req, res) => {
    try {
        const symbol = req.params.symbol.toUpperCase();
        const forceRefresh = req.query.force === '1';

        const { result, cached } = await getOrAnalyzeStock(symbol, forceRefresh);

        if (result.error) {
            return res.json({
                success: false,
                error: result.error,
                symbol: symbol
            });
        }

        res.json({
            success: true,
            data: result,
            cached
        });
    } catch (error) {
        console.error(`❌ Error analyzing ${req.params.symbol}:`, error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

const analysisJobs = new AnalysisJobManager({
    analyze: async symbol => (await getOrAnalyzeStock(symbol)).result,
    delayMs: ANALYSIS_JOB_DELAY_MS
});

app.post('/api/analysis-jobs', (req, res) => {
    const requestedSymbols = Array.isArray(req.body?.symbols) ? req.body.symbols : [];
    const symbols = [...new Set(
        requestedSymbols
            .filter(symbol => typeof symbol === 'string')
            .map(symbol => symbol.trim().toUpperCase())
            .filter(symbol => /^[A-Z0-9]{1,10}$/.test(symbol))
    )];

    if (symbols.length === 0) {
        return res.status(400).json({ success: false, error: 'No valid symbols provided' });
    }

    const job = analysisJobs.create(symbols);
    console.log(`🚀 Started analysis job ${job.id} for ${job.total} symbols`);
    res.status(202).json({ success: true, data: job });
});

app.get('/api/analysis-jobs/:id', (req, res) => {
    const job = analysisJobs.get(req.params.id);
    if (!job) {
        return res.status(404).json({ success: false, error: 'Analysis job not found' });
    }
    res.json({ success: true, data: job });
});

app.delete('/api/analysis-jobs/:id', (req, res) => {
    const job = analysisJobs.cancel(req.params.id);
    if (!job) {
        return res.status(404).json({ success: false, error: 'Analysis job not found' });
    }
    res.json({ success: true, data: job });
});

async function getOrAnalyzeStock(symbol, forceRefresh = false) {
    const now = Date.now();
    const cached = analysisCache.data[symbol];

    if (!forceRefresh && cached && now - cached.timestamp < analysisCache.ttl) {
        console.log(`📦 Using cached analysis for ${symbol}`);
        return { result: cached.result, cached: true };
    }

    if (!forceRefresh && inFlightAnalyses.has(symbol)) {
        console.log(`🔄 Joining in-flight analysis for ${symbol}`);
        return { result: await inFlightAnalyses.get(symbol), cached: false };
    }

    console.log(`📊 Analyzing ${symbol}...`);
    const symbolMeta = getSymbols('ALL').find(item => item.symbol === symbol);
    const promise = analyzeStock(symbol, symbolMeta?.exchange || 'HOSE');
    inFlightAnalyses.set(symbol, promise);

    try {
        const result = await promise;
        if (!result.error) {
            analysisCache.data[symbol] = { result, timestamp: Date.now() };
        }
        return { result, cached: false };
    } finally {
        if (inFlightAnalyses.get(symbol) === promise) {
            inFlightAnalyses.delete(symbol);
        }
    }
}

/**
 * Get symbols list based on exchange filter
 * Unified logic for loading watchlist, VN30, VN100, HNX30 symbols
 * 
 * @param {string} exchange - 'WATCHLIST', 'VN30', 'VN100', 'HNX30', 'ALL', 'POTENTIAL', 'HOSE', or 'HNX'
 * @returns {Array} Array of symbol objects with metadata
 */
function getSymbols(exchange) {
    const watchlistSymbols = new Set();
    const watchlistData = {};

    // Load watchlist
    try {
        if (fs.existsSync(WATCH_LIST_FILE)) {
            const rawData = JSON.parse(fs.readFileSync(WATCH_LIST_FILE, 'utf8'));

            EXCHANGES.forEach(ex => {
                const symbolsStr = rawData[ex] || '';
                if (!symbolsStr || symbolsStr.trim() === '') return;

                const symbols = symbolsStr.split(',').map(s => s.trim()).filter(s => s);
                symbols.forEach(symbol => {
                    watchlistSymbols.add(symbol);
                    watchlistData[symbol] = ex;
                });
            });
        }
    } catch (error) {
        console.error('⚠️ Error loading watchlist:', error.message);
    }

    // Helper to create symbol object
    const createSymbol = (symbol, exchangeHint) => {
        const isVN30 = vn30List.includes(symbol);
        const isVN100 = vn100List.includes(symbol);
        const isHNX30 = hnx30List.includes(symbol);
        const inWatchlist = watchlistSymbols.has(symbol);
        const symbolExchange = watchlistData[symbol] || exchangeHint || 'HOSE';

        return {
            symbol,
            exchange: symbolExchange,
            isVN30,
            isVN100,
            isHNX30,
            inWatchlist,
            tradingViewUrl: getTradingViewUrl(symbolExchange, symbol)
        };
    };

    // Return symbols based on exchange filter
    if (exchange === 'VN30') {
        return vn30List.map(s => createSymbol(s, 'HOSE'));
    }

    if (exchange === 'VN100') {
        return vn100List.map(s => createSymbol(s, 'HOSE'));
    }

    if (exchange === 'HNX30') {
        return hnx30List.map(s => createSymbol(s, 'HNX'));
    }

    if (exchange === 'WATCHLIST') {
        return Array.from(watchlistSymbols).map(s => createSymbol(s));
    }

    if (exchange === 'ALL' || exchange === 'POTENTIAL') {
        const allSymbols = new Set([
            ...Array.from(watchlistSymbols),
            ...vn30List,
            ...vn100List,
            ...hnx30List
        ]);

        return Array.from(allSymbols).map(s =>
            createSymbol(s, hnx30List.includes(s) ? 'HNX' : 'HOSE')
        );
    }

    if (exchange === 'HOSE' || exchange === 'HNX') {
        return Array.from(watchlistSymbols)
            .filter(s => watchlistData[s] === exchange)
            .map(s => createSymbol(s));
    }

    return [];
}

/**
 * Analyze a single stock using the persistent Python worker
 * 
 * @param {string} symbol - Stock symbol
 * @returns {Promise<Object>} Analysis result or error object
 */
async function analyzeStock(symbol, exchange = 'HOSE') {
    return analysisWorker.analyze(symbol, exchange);
}

// ==================== START SERVER ====================

console.log('⏳ Warming up persistent Python analysis worker...');
analysisWorker.start()
    .then(() => console.log('✅ Python analysis worker warmed up'))
    .catch(error => console.warn(`⚠️ Python analysis worker warm-up failed: ${error.message}`))
    .finally(() => {
        app.listen(PORT, () => {
            console.log('━'.repeat(50));
            console.log(`🚀 Server running at http://localhost:${PORT}`);
            console.log(`📊 VN30 symbols loaded: ${vn30List.length}`);
            console.log(`📊 HNX30 symbols loaded: ${hnx30List.length}`);
            console.log(`📊 VN100 symbols loaded: ${vn100List.length}`);
            console.log('━'.repeat(50));
        });
    });
