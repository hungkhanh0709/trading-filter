const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { exec, spawn } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

const app = express();
const PORT = process.env.PORT || 3000;
const MAX_DAYS = 10; // Maximum number of days to display in matrix view

// Supported exchanges
const EXCHANGES = ['HOSE', 'HNX'];

// TradingView URL helper
const getTradingViewUrl = (exchange, symbol) => {
    return `https://vn.tradingview.com/chart/27IsBTqc/?symbol=${exchange}%3A${symbol}`;
};

// File paths
const RAW_FILE = path.join(__dirname, 'data', 'raw.json');
const DATA_FILE = path.join(__dirname, 'data', 'data.json');
const VN30_FILE = path.join(__dirname, 'data', 'vn30.json');
const PYTHON_VENV = path.join(__dirname, '.venv', 'bin', 'python');
const FETCH_PRICES_SCRIPT = path.join(__dirname, 'fetch_prices.py');

// Price cache
let priceCache = {
    data: {},
    timestamp: 0,
    // Cache for 15 minutes
    ttl: 15 * 60 * 1000
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

/**
 * Get current date in YYYYMMDD format
 * @returns {string}
 */
function getCurrentDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
}

/**
 * Parse date string YYYYMMDD to Date object
 * @param {string} dateStr - Format: 20260119
 * @returns {Date}
 */
function parseDate(dateStr) {
    const year = parseInt(dateStr.substring(0, 4));
    const month = parseInt(dateStr.substring(4, 6)) - 1; // Month is 0-indexed
    const day = parseInt(dateStr.substring(6, 8));
    return new Date(year, month, day);
}

/**
 * Format date to readable string
 * @param {Date} date
 * @returns {string}
 */
function formatDate(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

/**
 * Process raw.json and append to data.json, format: {date, HOSE: "...", HNX: "..."}
 * - Read raw.json
 * - Get current date
 * - Read data.json
 * - Update or create entry for today
 * - Write back to data.json
 */
function processRawData() {
    try {
        const currentDate = getCurrentDate();

        // Read raw.json
        if (!fs.existsSync(RAW_FILE)) {
            console.log('ℹ️  raw.json not found, skipping process');
            return { success: false, message: 'raw.json not found' };
        }
        const rawData = JSON.parse(fs.readFileSync(RAW_FILE, 'utf8'));

        // Read existing data.json
        let dataArray = [];
        if (fs.existsSync(DATA_FILE)) {
            const existingData = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
            dataArray = Array.isArray(existingData) ? existingData : [existingData];
        }

        // Find or create entry for today
        let todayEntry = dataArray.find(item => item.date === currentDate);
        let isNew = false;

        if (!todayEntry) {
            todayEntry = { date: currentDate };
            dataArray.unshift(todayEntry);
            isNew = true;
        }

        // Process each exchange
        const results = [];
        EXCHANGES.forEach(exchange => {
            const symbolsStr = rawData[exchange] || '';

            if (symbolsStr && symbolsStr.trim() !== '') {
                const rawSymbols = symbolsStr.split(',').map(s => s.trim()).filter(s => s);
                const uniqueSymbols = [...new Set(rawSymbols)].sort();
                todayEntry[exchange] = uniqueSymbols.join(',');

                const action = isNew ? 'added' : 'replaced';
                console.log(`${isNew ? '➕' : '🔄'} ${action.charAt(0).toUpperCase() + action.slice(1)} ${currentDate} [${exchange}]: ${uniqueSymbols.length} symbols`);
                results.push({ exchange, action, count: uniqueSymbols.length });
            } else {
                // Set empty string if no symbols
                todayEntry[exchange] = '';
            }
        });

        if (results.length === 0) {
            console.log('ℹ️  No symbols to process');
            return { success: false, message: 'No symbols in raw.json' };
        }

        // Sort by date descending
        dataArray.sort((a, b) => b.date.localeCompare(a.date));

        // Write back to data.json
        fs.writeFileSync(DATA_FILE, JSON.stringify(dataArray, null, 2), 'utf8');

        return {
            success: true,
            date: currentDate,
            results: results,
            totalDates: dataArray.length
        };
    } catch (error) {
        console.error('❌ Error processing raw data:', error.message);
        return { success: false, error: error.message };
    }
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
    const dateStr = entry.date;
    const date = parseDate(dateStr);
    const formattedDate = formatDate(date);

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
                date: dateStr,
                dateFormatted: formattedDate
            });
        });
    });

    return {
        date: dateStr,
        dateFormatted: formattedDate,
        totalStocks: allStocks.length,
        vn30Count: allStocks.filter(s => s.isVN30).length,
        stocks: allStocks
    };
}

/**
 * Load and process data from data.json, format: {date, HOSE: "...", HNX: "..."}
 */
function loadFilterResults() {
    try {
        // Check if data.json exists, fallback to filter-result.json
        let filePath = DATA_FILE;
        if (!fs.existsSync(DATA_FILE) && fs.existsSync(path.join(__dirname, 'data', 'filter-result.json'))) {
            filePath = path.join(__dirname, 'data', 'filter-result.json');
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
 * GET /api/stocks/matrix
 * Returns matrix view of stocks across multiple dates
 * Shows NEW/NORMAL/REMOVED/ABSENT status for each symbol
 * Includes current price and percent change for each symbol
 */
app.get('/api/stocks/matrix', async (req, res) => {
    try {
        const exchangeFilter = req.query.exchange || 'ALL'; // ALL, HOSE, or HNX
        const allResults = loadFilterResults();

        // Filter by exchange if specified
        const results = exchangeFilter === 'ALL'
            ? allResults
            : allResults.map(dateData => ({
                ...dateData,
                stocks: dateData.stocks.filter(s => s.exchange === exchangeFilter)
            }));

        // Get latest N dates
        const latestDates = results.slice(0, MAX_DAYS);

        if (latestDates.length === 0) {
            return res.json({
                success: true,
                data: {
                    dates: [],
                    symbols: [],
                    stats: {
                        totalSymbols: 0,
                        totalDates: 0,
                        vn30Count: 0
                    }
                }
            });
        }

        // Collect all unique symbols across all dates
        const allSymbolsSet = new Set();
        const dateSymbolsMap = {}; // { '20260120': Set(['ACB', 'BID', ...]) }

        latestDates.forEach(dateData => {
            const symbols = new Set(dateData.stocks.map(s => s.symbol));
            dateSymbolsMap[dateData.date] = symbols;
            symbols.forEach(sym => allSymbolsSet.add(sym));
        });

        // Get all symbols (don't fetch prices here - let frontend do it separately)
        const allSymbols = Array.from(allSymbolsSet).sort();
        const priceData = {}; // Empty - prices will be fetched separately by frontend

        // Build matrix data
        const matrixData = allSymbols.map(symbol => {
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

            // Get price data
            const symbolPrice = priceData[symbol] || {};

            return {
                symbol,
                exchange,
                isVN30,
                tradingViewUrl,
                days,
                price: symbolPrice.price || null,
                changePercent: symbolPrice.changePercent || null,
                priceError: symbolPrice.error || null
            };
        });

        // Calculate stats
        const stats = {
            totalSymbols: allSymbols.length,
            totalDates: latestDates.length,
            vn30Count: matrixData.filter(s => s.isVN30).length,
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
                    return {
                        date: d.date,
                        dateFormatted: d.dateFormatted,
                        count: d.totalStocks,
                        vn30Count: vn30CountForDate
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
 * POST /api/process-raw
 * Process raw.json and update data.json
 */
app.post('/api/process-raw', (req, res) => {
    try {
        res.json(processRawData());
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Process raw data on startup
console.log('\n📥 Processing raw.json on startup...');
const initResult = processRawData();
if (initResult.success) {
    console.log(`   ✅ ${initResult.date}: ${initResult.symbolCount} symbols, ${initResult.totalDates} dates total`);
} else {
    console.log(`   ℹ️  ${initResult.message || initResult.error}`);
}

// Start server
app.listen(PORT, () => {
    console.log('━'.repeat(50));
    console.log(`🚀 Server running at http://localhost:${PORT}`);
    console.log(`📊 VN30 symbols loaded: ${vn30List.length}`);
    console.log('━'.repeat(50));
});
