const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const MAX_DAYS = 10; // Maximum number of days to display in matrix view

// File paths
const RAW_FILE = path.join(__dirname, 'data', 'raw.json');
const DATA_FILE = path.join(__dirname, 'data', 'data.json');
const VN30_FILE = path.join(__dirname, 'data', 'vn30.json');

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
 * Process raw.json and append to data.json
 * - Read raw.json
 * - Get current date
 * - Read data.json
 * - Check if date exists, merge or add new
 * - Write back to data.json
 */
function processRawData() {
    try {
        // Read raw.json
        if (!fs.existsSync(RAW_FILE)) {
            console.log('ℹ️  raw.json not found, skipping process');
            return { success: false, message: 'raw.json not found' };
        }

        const rawData = JSON.parse(fs.readFileSync(RAW_FILE, 'utf8'));
        const rawSymbols = (rawData.symbols || rawData.result || '').split(',').map(s => s.trim()).filter(s => s);

        if (rawSymbols.length === 0) {
            console.log('ℹ️  No symbols in raw.json');
            return { success: false, message: 'No symbols in raw.json' };
        }

        // Get current date
        const currentDate = getCurrentDate();

        // Read existing data.json
        let dataArray = [];
        if (fs.existsSync(DATA_FILE)) {
            const existingData = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
            dataArray = Array.isArray(existingData) ? existingData : [existingData];
        }

        // Find existing entry for today
        const existingIndex = dataArray.findIndex(item => item.date === currentDate);

        if (existingIndex >= 0) {
            // Replace existing entry (not merge)
            const uniqueSymbols = [...new Set(rawSymbols)].sort();
            dataArray[existingIndex].result = uniqueSymbols.join(',');
            console.log(`🔄 Replaced ${currentDate}: ${uniqueSymbols.length} symbols`);
        } else {
            // Add new entry
            const uniqueSymbols = [...new Set(rawSymbols)].sort();
            dataArray.unshift({
                date: currentDate,
                result: uniqueSymbols.join(',')
            });
            console.log(`➕ Added ${currentDate}: ${uniqueSymbols.length} symbols (new)`);
        }

        // Sort by date descending
        dataArray.sort((a, b) => b.date.localeCompare(a.date));

        // Write back to data.json
        fs.writeFileSync(DATA_FILE, JSON.stringify(dataArray, null, 2), 'utf8');

        return {
            success: true,
            date: currentDate,
            symbolCount: dataArray[0].result.split(',').length,
            totalDates: dataArray.length
        };
    } catch (error) {
        console.error('❌ Error processing raw data:', error.message);
        return { success: false, error: error.message };
    }
}

/**
 * Process filter result data
 * - Parse date
 * - Split symbols
 * - Deduplicate
 * - Add VN30 flag
 * - Generate TradingView URLs
 */
function processFilterData(rawData) {
    const dateStr = rawData.date;
    const symbols = rawData.result.split(',').map(s => s.trim()).filter(s => s);

    // Deduplicate symbols
    const uniqueSymbols = [...new Set(symbols)];

    // Parse date
    const date = parseDate(dateStr);
    const formattedDate = formatDate(date);

    // Process each symbol
    const stocks = uniqueSymbols.map(symbol => {
        const isVN30 = vn30List.includes(symbol);
        const tradingViewUrl = `https://vn.tradingview.com/chart/27IsBTqc/?symbol=HOSE%3A${symbol}`;

        return {
            symbol,
            isVN30,
            tradingViewUrl,
            date: dateStr,
            dateFormatted: formattedDate
        };
    });

    // Sort: VN30 first, then alphabetically
    stocks.sort((a, b) => {
        if (a.isVN30 !== b.isVN30) {
            return a.isVN30 ? -1 : 1;
        }
        return a.symbol.localeCompare(b.symbol);
    });

    return {
        date: dateStr,
        dateFormatted: formattedDate,
        totalStocks: stocks.length,
        vn30Count: stocks.filter(s => s.isVN30).length,
        stocks
    };
}

/**
 * Load and process data from data.json
 * Supports both single object and array of objects
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

        // Group by date and deduplicate
        const byDate = {};

        dataArray.forEach(entry => {
            const dateStr = entry.date;
            if (!byDate[dateStr]) {
                byDate[dateStr] = new Set();
            }

            // Add symbols to set (auto-deduplicates)
            const symbols = entry.result.split(',').map(s => s.trim()).filter(s => s);
            symbols.forEach(symbol => byDate[dateStr].add(symbol));
        });

        // Convert back to format and process
        const results = Object.entries(byDate).map(([dateStr, symbolsSet]) => {
            return processFilterData({
                date: dateStr,
                result: Array.from(symbolsSet).join(',')
            });
        });

        // Sort by date descending (newest first)
        results.sort((a, b) => b.date.localeCompare(a.date));

        return results;
    } catch (error) {
        console.error('❌ Error loading filter results:', error.message);
        return [];
    }
}

// API Endpoints

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
 */
app.get('/api/stocks/matrix', (req, res) => {
    try {
        const results = loadFilterResults();

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

        // Build matrix data
        const allSymbols = Array.from(allSymbolsSet).sort();
        const matrixData = allSymbols.map(symbol => {
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
            const tradingViewUrl = `https://vn.tradingview.com/chart/27IsBTqc/?symbol=HOSE%3A${symbol}`;

            return {
                symbol,
                isVN30,
                tradingViewUrl,
                days
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
 * POST /api/process-raw
 * Process raw.json and update data.json
 */
app.post('/api/process-raw', (req, res) => {
    try {
        const result = processRawData();
        res.json(result);
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
