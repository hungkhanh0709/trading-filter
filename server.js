const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Supported exchanges
const EXCHANGES = ['HOSE', 'HNX'];

// TradingView URL helper
const getTradingViewUrl = (exchange, symbol) => {
    return `https://vn.tradingview.com/chart/27IsBTqc/?symbol=${exchange}%3A${symbol}`;
};

// File paths
const WATCH_LIST_FILE = path.join(__dirname, 'data', 'watch_list.json');
const VN30_FILE = path.join(__dirname, 'data', 'vn30.json');
const VN100_FILE = path.join(__dirname, 'data', 'vn100.json');
const PYTHON_VENV = path.join(__dirname, '.venv', 'bin', 'python');
const FETCH_PRICES_SCRIPT = path.join(__dirname, 'scripts', 'fetch_prices.py');
const ANALYZE_STOCK_SCRIPT = path.join(__dirname, 'scripts', 'analyze_stock.py');

// Analysis cache - 180 minutes TTL
let analysisCache = {
    data: {},
    ttl: 180 * 60 * 1000
};

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



/**
 * GET /api/symbols
 * Get symbols list
 * 
 * Query params:
 *   - exchange: WATCHLIST (default), VN30, VN100, HOSE, HNX
 */
app.get('/api/symbols', async (req, res) => {
    try {
        const exchange = req.query.exchange || 'WATCHLIST';

        // Get symbols
        const symbols = getSymbols(exchange);

        // Calculate stats
        const stats = {
            total: symbols.length,
            vn30: symbols.filter(s => s.isVN30).length,
            vn100: symbols.filter(s => s.isVN100).length,
            inWatchlist: symbols.filter(s => s.inWatchlist).length
        };

        res.json({
            success: true,
            data: {
                symbols,
                stats
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
 * Analyze a single stock with caching (60min TTL)
 * 
 * Query params:
 *   - force: "1" to force refresh analysis
 */
app.get('/api/analyze/:symbol', async (req, res) => {
    try {
        const symbol = req.params.symbol.toUpperCase();
        const forceRefresh = req.query.force === '1';

        // Check cache
        const now = Date.now();
        if (!forceRefresh && analysisCache.data[symbol]) {
            const cached = analysisCache.data[symbol];
            if (now - cached.timestamp < analysisCache.ttl) {
                console.log(`📦 Using cached analysis for ${symbol}`);
                return res.json({
                    success: true,
                    data: cached.result,
                    cached: true
                });
            }
        }

        // Analyze
        console.log(`📊 Analyzing ${symbol}...`);
        const result = await analyzeStock(symbol);

        if (result.error) {
            return res.json({
                success: false,
                error: result.error,
                symbol: symbol
            });
        }

        // Cache result
        analysisCache.data[symbol] = {
            result: result,
            timestamp: now
        };

        res.json({
            success: true,
            data: result,
            cached: false
        });
    } catch (error) {
        console.error(`❌ Error analyzing ${req.params.symbol}:`, error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Get symbols list based on exchange filter
 * Unified logic for loading watchlist, VN30, VN100 symbols
 * 
 * @param {string} exchange - 'WATCHLIST', 'VN30', 'VN100', 'HOSE', or 'HNX'
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
        const inWatchlist = watchlistSymbols.has(symbol);
        const symbolExchange = watchlistData[symbol] || exchangeHint || 'HOSE';

        return {
            symbol,
            exchange: symbolExchange,
            isVN30,
            isVN100,
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

    if (exchange === 'WATCHLIST') {
        return Array.from(watchlistSymbols).map(s => createSymbol(s));
    }

    if (exchange === 'HOSE' || exchange === 'HNX') {
        return Array.from(watchlistSymbols)
            .filter(s => watchlistData[s] === exchange)
            .map(s => createSymbol(s));
    }

    return [];
}

/**
 * Analyze a single stock using Python script
 * 
 * @param {string} symbol - Stock symbol
 * @returns {Promise<Object>} Analysis result or error object
 */
async function analyzeStock(symbol) {
    return new Promise((resolve, reject) => {
        const args = [ANALYZE_STOCK_SCRIPT, symbol];
        const pythonProcess = spawn(PYTHON_VENV, args);

        let stdout = '';
        let stderr = '';

        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            // Log progress (but filter out excessive logging)
            const line = data.toString().trim();
            if (line && !line.includes('⏳') && !line.includes('✅')) {
                console.log(`  ${line}`);
            }
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error(`❌ Analysis failed for ${symbol} with code ${code}`);
                if (stderr) console.error('stderr:', stderr);
                return resolve({
                    symbol: symbol,
                    error: `Analysis failed with exit code ${code}`
                });
            }

            try {
                // Parse JSON from stdout (try multiple strategies)
                let result;
                const trimmedStdout = stdout.trim();

                // Strategy 1: Parse entire stdout as JSON
                try {
                    result = JSON.parse(trimmedStdout);
                    resolve(result);
                    return;
                } catch (e) {
                    // Continue to next strategy
                }

                // Strategy 2: Find JSON object in stdout (first '{' to last '}')
                const firstBrace = trimmedStdout.indexOf('{');
                const lastBrace = trimmedStdout.lastIndexOf('}');

                if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                    const jsonStr = trimmedStdout.substring(firstBrace, lastBrace + 1);
                    try {
                        result = JSON.parse(jsonStr);
                        resolve(result);
                        return;
                    } catch (e) {
                        // Continue to next strategy
                    }
                }

                // Strategy 3: Parse line by line (fallback)
                const lines = stdout.split('\n');
                for (let i = lines.length - 1; i >= 0; i--) {
                    const line = lines[i].trim();
                    if (line.startsWith('{')) {
                        try {
                            result = JSON.parse(line);
                            resolve(result);
                            return;
                        } catch (e) {
                            // Continue to next line
                        }
                    }
                }

                // All parsing strategies failed
                console.error(`❌ No valid JSON output for ${symbol}`);
                console.error('stdout:', stdout);
                resolve({
                    symbol: symbol,
                    error: 'No valid JSON output from analysis script'
                });
            } catch (error) {
                console.error(`❌ Error parsing JSON for ${symbol}:`, error.message);
                console.error('stdout:', stdout);
                resolve({
                    symbol: symbol,
                    error: `Failed to parse JSON: ${error.message}`
                });
            }
        });

        pythonProcess.on('error', (error) => {
            console.error(`❌ Failed to start analysis for ${symbol}:`, error);
            reject(error);
        });
    });
}

// ==================== START SERVER ====================

app.listen(PORT, () => {
    console.log('━'.repeat(50));
    console.log(`🚀 Server running at http://localhost:${PORT}`);
    console.log(`📊 VN30 symbols loaded: ${vn30List.length}`);
    console.log(`📊 VN100 symbols loaded: ${vn100List.length}`);
    console.log('━'.repeat(50));
});
