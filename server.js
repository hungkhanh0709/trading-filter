const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;
// Maximum number of days to display in matrix view
const MAX_DAYS = 5;
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

// Price cache
let priceCache = {
    data: {},
    timestamp: 0,
    // Cache for 60 minutes
    ttl: 60 * 60 * 1000
};

// Analysis cache
let analysisCache = {
    data: {},
    // Cache for 60 minutes
    ttl: 60 * 60 * 1000
};

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Load VN30 list
let vn30List = [];
try {
    const vn30Data = JSON.parse(fs.readFileSync(VN30_FILE, 'utf8'));
    vn30List = vn30Data.symbols || [];
    console.log(`✅ Loaded ${vn30List.length} VN30 symbols`);
} catch (error) {
    console.error('❌ Error loading VN30 data:', error.message);
}

// Load VN100 list
let vn100List = [];
try {
    const vn100Data = JSON.parse(fs.readFileSync(VN100_FILE, 'utf8'));
    vn100List = vn100Data.symbols || [];
    console.log(`✅ Loaded ${vn100List.length} VN100 symbols`);
} catch (error) {
    console.error('❌ Error loading VN100 data:', error.message);
}

/**
 * Process filter result data, format: {date, HOSE: "...", HNX: "..."}
 * - Parse date
 * - Process each exchange
 * - Split symbols
 * - Deduplicate
 * - Add VN30 flag
 * - Generate TradingView URLs
 */
function processFilterData(entry) {
    const allStocks = [];

    // Process each exchange
    EXCHANGES.forEach(exchange => {
        const symbolsStr = entry[exchange] || '';
        if (!symbolsStr || symbolsStr.trim() === '') return;

        const symbols = symbolsStr.split(',').map(s => s.trim()).filter(s => s);
        const uniqueSymbols = [...new Set(symbols)];

        uniqueSymbols.forEach(symbol => {
            const isVN30 = vn30List.includes(symbol);
            const tradingViewUrl = getTradingViewUrl(exchange, symbol);
            allStocks.push({
                symbol,
                exchange,
                isVN30,
                tradingViewUrl,
            });
        });
    });

    return {
        totalStocks: allStocks.length,
        vn30Count: allStocks.filter(s => s.isVN30).length,
        stocks: allStocks
    };
}

/**
 * Load and process data from watch_list.json, format: {date, HOSE: "...", HNX: "..."}
 */
function loadFilterResults() {
    try {
        // Check if watch_list.json exists
        let filePath = WATCH_LIST_FILE;
        if (!fs.existsSync(WATCH_LIST_FILE)) {
            console.log('ℹ️  watch_list.json not found');
            return [];
        }

        const rawData = JSON.parse(fs.readFileSync(filePath, 'utf8'));

        // Support both single object and array
        const dataArray = Array.isArray(rawData) ? rawData : [rawData];

        // Process each entry with new format
        const results = dataArray.map(entry => processFilterData(entry));

        // Sort by date descending (newest first)
        results.sort((a, b) => b.date.localeCompare(a.date));

        return results;
    } catch (error) {
        console.error('❌ Error loading filter results:', error.message);
        return [];
    }
}

/**
 * GET /api/stocks
 * Returns processed stock data with VN30 flags and TradingView links
 */
app.get('/api/stocks', (req, res) => {
    try {
        const results = loadFilterResults();

        // Return latest date by default
        const latest = results[0] || {
            date: '',
            dateFormatted: '',
            totalStocks: 0,
            vn30Count: 0,
            stocks: []
        };

        res.json({
            success: true,
            data: latest,
            allDates: results.map(r => ({
                date: r.date,
                dateFormatted: r.dateFormatted,
                count: r.totalStocks
            }))
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Helper function to build matrix data from a predefined symbol list (VN30/VN100)
 * Shows FULL list of symbols with status based on actual appearance in data.json
 */
function buildMatrixFromSymbolList(symbolList, allResults, maxDays) {
    const latestDates = allResults.slice(0, maxDays);

    if (latestDates.length === 0) {
        return {
            latestDates: [],
            matrixData: [],
            dateSymbolsMap: {}
        };
    }

    // Build map of symbols appearing in each date
    const dateSymbolsMap = {};
    latestDates.forEach(dateData => {
        dateSymbolsMap[dateData.date] = new Set(dateData.stocks.map(s => s.symbol));
    });

    // Build matrix for WATCHLIST symbols in the list
    const matrixData = symbolList.map(symbol => {
        // Find exchange from stocks data (default to HOSE if not found)
        let exchange = 'HOSE';
        for (const dateData of latestDates) {
            const stock = dateData.stocks.find(s => s.symbol === symbol);
            if (stock && stock.exchange) {
                exchange = stock.exchange;
                break;
            }
        }

        // Check index membership
        const isVN30 = vn30List.includes(symbol);
        const isVN100 = vn100List.includes(symbol);

        // Build day status for each date
        const days = latestDates.map((dateData, index) => {
            const hasSymbol = dateSymbolsMap[dateData.date].has(symbol);

            // Determine status
            let status = 'absent'; // default for symbols not in data.json

            if (hasSymbol) {
                // Only mark as NEW if it's the FIRST date (most recent) AND not in second date
                if (index === 0) {
                    const hasInSecondDate = latestDates.length > 1
                        ? dateSymbolsMap[latestDates[1].date].has(symbol)
                        : false;
                    status = hasInSecondDate ? 'normal' : 'new';
                } else {
                    // For older dates, just mark as normal
                    status = 'normal';
                }
            }

            return {
                date: dateData.date,
                dateFormatted: dateData.dateFormatted,
                hasSymbol,
                status
            };
        });

        // Generate TradingView URL
        const tradingViewUrl = getTradingViewUrl(exchange, symbol);

        return {
            symbol,
            exchange,
            isVN30,
            isVN100,
            tradingViewUrl,
            days,
            price: null,
            changePercent: null,
            priceError: null
        };
    });

    return { latestDates, matrixData, dateSymbolsMap };
}

/**
 * GET /api/stocks/matrix
 * Returns matrix view of stocks across multiple dates
 * Shows NEW/NORMAL/REMOVED/ABSENT status for each symbol
 * 
 * For VN30/VN100: Shows FULL list (30/100 symbols) with status from watch_list.json
 * For WATCHLIST/HOSE/HNX: Shows only symbols appearing in watch_list.json
 */
app.get('/api/stocks/matrix', async (req, res) => {
    try {
        const exchangeFilter = req.query.exchange || 'WATCHLIST'; // WATCHLIST, HOSE, HNX, VN30, VN100
        const allResults = loadFilterResults();

        let latestDates, matrixData, dateSymbolsMap;

        // Handle VN30/VN100 differently - show FULL list
        if (exchangeFilter === 'VN30') {
            const result = buildMatrixFromSymbolList(vn30List, allResults, MAX_DAYS);
            latestDates = result.latestDates;
            matrixData = result.matrixData;
            dateSymbolsMap = result.dateSymbolsMap;
        } else if (exchangeFilter === 'VN100') {
            const result = buildMatrixFromSymbolList(vn100List, allResults, MAX_DAYS);
            latestDates = result.latestDates;
            matrixData = result.matrixData;
            dateSymbolsMap = result.dateSymbolsMap;
        } else {
            // WATCHLIST/HOSE/HNX: Filter from watch_list.json
            let results;
            if (exchangeFilter === 'WATCHLIST') {
                results = allResults;
            } else {
                // HOSE or HNX
                results = allResults.map(dateData => ({
                    ...dateData,
                    stocks: dateData.stocks.filter(s => s.exchange === exchangeFilter)
                }));
            }

            // Get latest N dates
            latestDates = results.slice(0, MAX_DAYS);

            // Get latest N dates
            latestDates = results.slice(0, MAX_DAYS);

            if (latestDates.length === 0) {
                return res.json({
                    success: true,
                    data: {
                        dates: [],
                        symbols: [],
                        stats: {
                            totalSymbols: 0,
                            totalDates: 0,
                            vn30Count: 0,
                            vn100Count: 0
                        }
                    }
                });
            }

            // Collect all unique symbols across all dates
            const allSymbolsSet = new Set();
            dateSymbolsMap = {}; // { '20260120': Set(['ACB', 'BID', ...]) }

            latestDates.forEach(dateData => {
                const symbols = new Set(dateData.stocks.map(s => s.symbol));
                dateSymbolsMap[dateData.date] = symbols;
                symbols.forEach(sym => allSymbolsSet.add(sym));
            });

            // Get all symbols (sorted)
            const allSymbols = Array.from(allSymbolsSet).sort();

            // Build matrix data
            matrixData = allSymbols.map(symbol => {
                // Find exchange from stocks data
                let exchange = 'HOSE';
                for (const dateData of latestDates) {
                    const stock = dateData.stocks.find(s => s.symbol === symbol);
                    if (stock && stock.exchange) {
                        exchange = stock.exchange;
                        break;
                    }
                }

                // Check if VN30
                const isVN30 = vn30List.includes(symbol);

                // Check if VN100
                const isVN100 = vn100List.includes(symbol);

                // Build day status for each date
                const days = latestDates.map((dateData, index) => {
                    const hasSymbol = dateSymbolsMap[dateData.date].has(symbol);

                    // Determine status
                    let status = 'absent'; // default

                    if (hasSymbol) {
                        // Only mark as NEW if it's the FIRST date (most recent) AND not in second date
                        if (index === 0) {
                            const hasInSecondDate = latestDates.length > 1 ? dateSymbolsMap[latestDates[1].date].has(symbol) : false;
                            status = hasInSecondDate ? 'normal' : 'new';
                        } else {
                            // For older dates, just mark as normal
                            status = 'normal';
                        }
                    }

                    return {
                        date: dateData.date,
                        dateFormatted: dateData.dateFormatted,
                        hasSymbol,
                        status
                    };
                });

                // Generate TradingView URL
                const tradingViewUrl = getTradingViewUrl(exchange, symbol);

                return {
                    symbol,
                    exchange,
                    isVN30,
                    isVN100,
                    tradingViewUrl,
                    days,
                    price: null,
                    changePercent: null,
                    priceError: null
                };
            });
        }

        // Common response handling for all filter types

        // Common response handling for all filter types
        if (latestDates.length === 0) {
            return res.json({
                success: true,
                data: {
                    dates: [],
                    symbols: [],
                    stats: {
                        totalSymbols: 0,
                        totalDates: 0,
                        vn30Count: 0,
                        vn100Count: 0
                    }
                }
            });
        }

        // Calculate stats
        const stats = {
            totalSymbols: matrixData.length,
            totalDates: latestDates.length,
            vn30Count: matrixData.filter(s => s.isVN30).length,
            vn100Count: matrixData.filter(s => s.isVN100).length,
            latestDate: latestDates[0].dateFormatted,
            // Additional stats
            newSymbols: matrixData.filter(s => s.days[0].status === 'new').length,
            removedSymbols: matrixData.filter(s => s.days.some(d => d.status === 'removed')).length
        };

        res.json({
            success: true,
            data: {
                dates: latestDates.map(d => {
                    const dateSymbols = d.stocks.map(s => s.symbol);
                    const vn30CountForDate = dateSymbols.filter(sym => vn30List.includes(sym)).length;
                    const vn100CountForDate = dateSymbols.filter(sym => vn100List.includes(sym)).length;
                    return {
                        date: d.date,
                        dateFormatted: d.dateFormatted,
                        count: d.totalStocks,
                        vn30Count: vn30CountForDate,
                        vn100Count: vn100CountForDate
                    };
                }),
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
 * Get current prices for symbols
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
 * GET /api/stocks/:date
 * Returns stock data for specific date (YYYYMMDD)
 */
app.get('/api/stocks/:date', (req, res) => {
    try {
        const requestedDate = req.params.date;
        const results = loadFilterResults();
        const result = results.find(r => r.date === requestedDate);

        if (result) {
            res.json({
                success: true,
                data: result
            });
        } else {
            res.status(404).json({
                success: false,
                error: 'Data not found for date: ' + requestedDate
            });
        }
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/vn30
 * Returns VN30 list
 */
app.get('/api/vn30', (req, res) => {
    res.json({
        success: true,
        data: vn30List
    });
});

/**
 * Fetch stock prices using Python vnstock script
 * @param {Array<string>} symbols - Stock symbols
 * @returns {Promise<Object>} Price data for each symbol
 */
async function fetchStockPrices(symbols) {
    // Check cache
    const now = Date.now();
    if (now - priceCache.timestamp < priceCache.ttl) {
        // Return cached data if available
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
        console.log(`🐍 Fetching prices for ${symbols.length} symbols (this may take ~${Math.ceil(symbols.length * 3.5 / 60)} minutes)...`);

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
 * GET /api/analyze/:symbol
 * Analyze a single stock with caching
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
 * Analyze multiple stocks one by one
 * Body: { symbols: ['VNM', 'FPT', 'HPG'] }
 * Returns: Stream of analysis results
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

        // Analyze each symbol one by one
        for (let i = 0; i < symbols.length; i++) {
            const symbol = symbols[i];

            try {
                console.log(`📊 [${i + 1}/${symbols.length}] Analyzing ${symbol}...`);

                const result = await analyzeStock(symbol);

                if (result.error) {
                    console.log(`❌ [${i + 1}/${symbols.length}] ${symbol}: ${result.error}`);
                    errorCount++;
                } else {
                    console.log(`✅ [${i + 1}/${symbols.length}] ${symbol}: ${result.tier_label}`);
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

            // Add delay to avoid rate limit (same as fetch_prices.py)
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

/**
 * Analyze a single stock using Python script
 * @param {string} symbol - Stock symbol
 * @returns {Promise<Object>} Analysis result
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
            // Log progress to console
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
                // Parse JSON from stdout
                // Strategy: Try to parse the entire stdout first (most common case)
                // If that fails, try to extract JSON from lines

                let result;
                const trimmedStdout = stdout.trim();

                // Try 1: Parse entire stdout as JSON
                try {
                    result = JSON.parse(trimmedStdout);
                    resolve(result);
                    return;
                } catch (e) {
                    // Not a single JSON object, try extracting from lines
                }

                // Try 2: Find JSON object in lines (may span multiple lines)
                // Look for first '{' and last '}'
                const firstBrace = trimmedStdout.indexOf('{');
                const lastBrace = trimmedStdout.lastIndexOf('}');

                if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                    const jsonStr = trimmedStdout.substring(firstBrace, lastBrace + 1);
                    try {
                        result = JSON.parse(jsonStr);
                        resolve(result);
                        return;
                    } catch (e) {
                        // Still failed, try line by line
                    }
                }

                // Try 3: Parse line by line (fallback)
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

// Start server
app.listen(PORT, () => {
    console.log('━'.repeat(50));
    console.log(`🚀 Server running at http://localhost:${PORT}`);
    console.log(`📊 VN30 symbols loaded: ${vn30List.length}`);
    console.log(`📊 VN100 symbols loaded: ${vn100List.length}`);
    console.log('━'.repeat(50));
});
