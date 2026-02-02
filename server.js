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

// Price cache - 60 minutes TTL
let priceCache = {
    data: {},
    timestamp: 0,
    ttl: 60 * 60 * 1000
};

// Analysis cache - 60 minutes TTL
let analysisCache = {
    data: {},
    ttl: 60 * 60 * 1000
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
 * Load and process watchlist from watch_list.json
 * Format: { "HOSE": "FPT,MSN,HDB,...", "HNX": "IDC,..." }
 * 
 * @returns {Object} { totalStocks, vn30Count, vn100Count, stocks: [...] }
 */
function loadWatchlist() {
    try {
        if (!fs.existsSync(WATCH_LIST_FILE)) {
            console.log('ℹ️  watch_list.json not found');
            return {
                totalStocks: 0,
                vn30Count: 0,
                vn100Count: 0,
                stocks: []
            };
        }

        const rawData = JSON.parse(fs.readFileSync(WATCH_LIST_FILE, 'utf8'));
        const allStocks = [];

        // Process each exchange (HOSE, HNX)
        EXCHANGES.forEach(exchange => {
            const symbolsStr = rawData[exchange] || '';
            if (!symbolsStr || symbolsStr.trim() === '') return;

            const symbols = symbolsStr.split(',').map(s => s.trim()).filter(s => s);
            const uniqueSymbols = [...new Set(symbols)]; // Deduplicate

            uniqueSymbols.forEach(symbol => {
                const isVN30 = vn30List.includes(symbol);
                const isVN100 = vn100List.includes(symbol);
                const tradingViewUrl = getTradingViewUrl(exchange, symbol);

                allStocks.push({
                    symbol,
                    exchange,
                    isVN30,
                    isVN100,
                    tradingViewUrl,
                });
            });
        });

        return {
            totalStocks: allStocks.length,
            vn30Count: allStocks.filter(s => s.isVN30).length,
            vn100Count: allStocks.filter(s => s.isVN100).length,
            stocks: allStocks
        };
    } catch (error) {
        console.error('❌ Error loading watchlist:', error.message);
        return {
            totalStocks: 0,
            vn30Count: 0,
            vn100Count: 0,
            stocks: []
        };
    }
}

/**
 * Create a matrix row for a symbol with watchlist status
 * 
 * @param {string} symbol - Stock symbol
 * @param {Set} watchlistSymbols - Set of symbols in watchlist
 * @param {Object} watchlist - Full watchlist object
 * @returns {Object} Matrix row data
 */
function createMatrixRow(symbol, watchlistSymbols, watchlist) {
    const inWatchlist = watchlistSymbols.has(symbol);
    
    // Find stock details from watchlist if exists
    const stockInWatchlist = watchlist.stocks.find(s => s.symbol === symbol);
    const exchange = stockInWatchlist ? stockInWatchlist.exchange : 'HOSE'; // Default to HOSE
    const isVN30 = vn30List.includes(symbol);
    const isVN100 = vn100List.includes(symbol);
    const tradingViewUrl = getTradingViewUrl(exchange, symbol);

    return {
        symbol,
        exchange,
        isVN30,
        isVN100,
        tradingViewUrl,
        inWatchlist,
        price: null,          // To be filled by price fetch
        changePercent: null,  // To be filled by price fetch
        priceError: null      // Error message if price fetch fails
    };
}

// ==================== API ENDPOINTS ====================

/**
 * GET /api/stocks
 * Returns current watchlist with VN30/VN100 flags and TradingView links
 */
app.get('/api/stocks', (req, res) => {
    try {
        const watchlist = loadWatchlist();
        res.json({
            success: true,
            data: watchlist
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/stocks/matrix
 * Returns matrix view of stocks
 * 
 * Query params:
 *   - exchange: WATCHLIST (default, all symbols), VN30, VN100, HOSE, HNX
 * 
 * For VN30/VN100: Shows FULL index list with watchlist status
 * For WATCHLIST/HOSE/HNX: Shows only symbols in watchlist
 */
app.get('/api/stocks/matrix', async (req, res) => {
    try {
        const exchangeFilter = req.query.exchange || 'WATCHLIST';
        const watchlist = loadWatchlist();
        const watchlistSymbols = new Set(watchlist.stocks.map(s => s.symbol));

        let matrixData;

        if (exchangeFilter === 'VN30') {
            // Show FULL VN30 index list
            matrixData = vn30List.map(symbol => 
                createMatrixRow(symbol, watchlistSymbols, watchlist)
            );
        } else if (exchangeFilter === 'VN100') {
            // Show FULL VN100 index list
            matrixData = vn100List.map(symbol => 
                createMatrixRow(symbol, watchlistSymbols, watchlist)
            );
        } else {
            // WATCHLIST/HOSE/HNX - filter from watchlist only
            let filteredStocks = watchlist.stocks;
            
            if (exchangeFilter !== 'WATCHLIST') {
                filteredStocks = filteredStocks.filter(s => s.exchange === exchangeFilter);
            }

            matrixData = filteredStocks.map(stock => ({
                symbol: stock.symbol,
                exchange: stock.exchange,
                isVN30: stock.isVN30,
                isVN100: stock.isVN100,
                tradingViewUrl: stock.tradingViewUrl,
                inWatchlist: true, // Always true for watchlist stocks
                price: null,
                changePercent: null,
                priceError: null
            }));
        }

        // Calculate stats
        const stats = {
            totalSymbols: matrixData.length,
            vn30Count: matrixData.filter(s => s.isVN30).length,
            vn100Count: matrixData.filter(s => s.isVN100).length,
            inWatchlistCount: matrixData.filter(s => s.inWatchlist).length
        };

        res.json({
            success: true,
            data: {
                symbols: matrixData,
                stats
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/stocks/prices
 * Get current prices for specified symbols
 * 
 * Query params:
 *   - symbols: Comma-separated list (e.g., "ACB,HPG,VNM")
 *   - force: "1" to clear cache and force refresh
 */
app.get('/api/stocks/prices', async (req, res) => {
    try {
        const symbols = req.query.symbols ? req.query.symbols.split(',') : [];
        const forceRefresh = req.query.force === '1';

        if (symbols.length === 0) {
            return res.status(400).json({
                success: false,
                error: 'No symbols provided. Use ?symbols=ACB,HPG,VNM'
            });
        }

        // Clear cache if force refresh
        if (forceRefresh) {
            console.log('🔄 Force refresh - clearing price cache');
            priceCache.timestamp = 0;
        }

        const prices = await fetchStockPrices(symbols);

        res.json({
            success: true,
            data: prices
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/vn30
 * Returns VN30 index symbol list
 */
app.get('/api/vn30', (req, res) => {
    res.json({
        success: true,
        data: vn30List
    });
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
 * POST /api/analyze-stocks
 * Analyze multiple stocks sequentially with streaming response
 * 
 * Body: { symbols: ['VNM', 'FPT', 'HPG'] }
 * 
 * Returns streaming JSON responses:
 *   - type: 'progress' - per-symbol result
 *   - type: 'error' - per-symbol error
 *   - type: 'complete' - final summary
 */
app.post('/api/analyze-stocks', async (req, res) => {
    try {
        const { symbols } = req.body;

        if (!symbols || !Array.isArray(symbols) || symbols.length === 0) {
            return res.status(400).json({
                success: false,
                error: 'Symbols array is required'
            });
        }

        // Set headers for streaming response
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        console.log(`🚀 Starting analysis for ${symbols.length} symbols...`);

        const results = [];
        let successCount = 0;
        let errorCount = 0;

        // Analyze each symbol sequentially
        for (let i = 0; i < symbols.length; i++) {
            const symbol = symbols[i];

            try {
                console.log(`📊 [${i + 1}/${symbols.length}] Analyzing ${symbol}...`);

                const result = await analyzeStock(symbol);

                if (result.error) {
                    console.log(`❌ [${i + 1}/${symbols.length}] ${symbol}: ${result.error}`);
                    errorCount++;
                } else {
                    console.log(`✅ [${i + 1}/${symbols.length}] ${symbol}: ${result.status || 'OK'}`);
                    successCount++;
                }

                results.push(result);

                // Send progress update to client
                res.write(JSON.stringify({
                    type: 'progress',
                    current: i + 1,
                    total: symbols.length,
                    symbol: symbol,
                    result: result
                }) + '\n');

            } catch (error) {
                console.error(`❌ [${i + 1}/${symbols.length}] ${symbol}: ${error.message}`);
                errorCount++;

                results.push({
                    symbol: symbol,
                    error: error.message
                });

                res.write(JSON.stringify({
                    type: 'error',
                    current: i + 1,
                    total: symbols.length,
                    symbol: symbol,
                    error: error.message
                }) + '\n');
            }

            // Rate limiting delay (3.5s between requests to avoid API throttling)
            if (i < symbols.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 3500));
            }
        }

        // Send final summary
        res.write(JSON.stringify({
            type: 'complete',
            total: symbols.length,
            success: successCount,
            errors: errorCount,
            results: results
        }) + '\n');

        res.end();

        console.log(`🎯 Analysis complete: ${successCount}/${symbols.length} successful`);

    } catch (error) {
        console.error('❌ Error in analyze-stocks:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// ==================== HELPER FUNCTIONS ====================

/**
 * Fetch stock prices using Python vnstock script
 * 
 * @param {Array<string>} symbols - Stock symbols
 * @returns {Promise<Object>} Price data for each symbol
 */
async function fetchStockPrices(symbols) {
    // Check cache
    const now = Date.now();
    if (now - priceCache.timestamp < priceCache.ttl) {
        const cachedResults = {};
        let allCached = true;
        
        for (const symbol of symbols) {
            if (priceCache.data[symbol]) {
                cachedResults[symbol] = priceCache.data[symbol];
            } else {
                allCached = false;
                break;
            }
        }
        
        if (allCached) {
            console.log('📦 Using cached price data');
            return cachedResults;
        }
    }

    return new Promise((resolve, reject) => {
        const args = [FETCH_PRICES_SCRIPT, ...symbols];
        const estimatedMinutes = Math.ceil(symbols.length * 3.5 / 60);
        console.log(`🐍 Fetching prices for ${symbols.length} symbols (~${estimatedMinutes} minutes)...`);

        const pythonProcess = spawn(PYTHON_VENV, args);

        let stdout = '';
        let stderr = '';

        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            const line = data.toString().trim();
            if (line) {
                console.log(line); // Real-time progress logging
            }
            stderr += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error('❌ Python script failed with code:', code);
                console.error('stderr:', stderr);
                return reject(new Error(`Python script failed with code ${code}`));
            }

            try {
                // Parse JSON from stdout
                const lines = stdout.split('\n');
                const jsonLine = lines.find(line => line.trim().startsWith('{'));

                if (!jsonLine) {
                    console.error('❌ No JSON output from Python script');
                    console.error('stdout:', stdout);
                    return resolve({});
                }

                const results = JSON.parse(jsonLine);

                // Update cache
                priceCache.data = { ...priceCache.data, ...results };
                priceCache.timestamp = now;

                console.log(`✅ Fetched prices for ${Object.keys(results).length} symbols`);
                resolve(results);
            } catch (error) {
                console.error('❌ Error parsing Python output:', error.message);
                reject(error);
            }
        });

        pythonProcess.on('error', (error) => {
            console.error('❌ Failed to start Python process:', error);
            reject(error);
        });
    });
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
