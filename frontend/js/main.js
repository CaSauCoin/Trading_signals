// frontend/js/main.js
console.log("Đang chạy main.js phiên bản 3.2 (đã sửa lỗi library loading)");

// --- Cấu hình ---
const API_BASE_URL = 'http://127.0.0.1:5000';
const TIMEFRAMES = ['1h', '4h', '1d', '3d', '1w'];
let chart, candlestickSeries, volumeSeries;
let currentPriceLine = null;
let drawnObjects = [];

// --- DOM Elements ---
const chartContainer = document.getElementById('chart-container');
const tokenSelector = document.getElementById('token-selector');
const timeframeSelector = document.getElementById('timeframe-selector');
const mainTitle = document.getElementById('main-title');
const loadingSpinner = document.getElementById('loading-spinner');

// --- Hàm Khởi tạo Biểu đồ ---
function initializeChart() {
    if (chart) {
        chart.remove();
    }

    // Kiểm tra xem thư viện đã sẵn sàng chưa
    if (typeof LightweightCharts === 'undefined') {
        console.error("Thư viện LightweightCharts chưa được tải!");
        alert("Lỗi tải thư viện biểu đồ. Vui lòng thử tải lại trang.");
        return;
    }

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight || 600,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333',
        },
        grid: {
            vertLines: { color: '#e1ecf2' },
            horzLines: { color: '#e1ecf2' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
        },
    });

    candlestickSeries = chart.addCandlestickSeries({
        upColor: '#089981',
        downColor: '#f23645',
        borderDownColor: '#f23645',
        borderUpColor: '#089981',
        wickDownColor: '#f23645',
        wickUpColor: '#089981',
    });

    volumeSeries = chart.addHistogramSeries({
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: '', // Đặt trên một thang giá riêng
    });

    chart.priceScale('').applyOptions({
        scaleMargins: {
            top: 0.85,
            bottom: 0,
        },
    });
}


// --- Hàm chính: Lấy dữ liệu và vẽ biểu đồ ---
async function fetchAndDrawChart() {
    loadingSpinner.classList.remove('hidden');
    
    const symbol = tokenSelector.value;
    const activeTimeframeBtn = document.querySelector('.timeframe-btn.active');
    if (!symbol || !activeTimeframeBtn) {
        loadingSpinner.classList.add('hidden');
        return;
    }
    const timeframe = activeTimeframeBtn.dataset.value;
    mainTitle.innerText = `Dashboard Real-time cho ${symbol}`;

    try {
        const response = await fetch(`${API_BASE_URL}/api/chart-data?symbol=${symbol}&timeframe=${timeframe}`);
        if (!response.ok) {
            throw new Error(`Lỗi API: ${response.statusText}.`);
        }
        const data = await response.json();

        // Xóa các đối tượng đã vẽ trước đó
        drawnObjects.forEach(obj => candlestickSeries.removePriceLine(obj));
        drawnObjects = [];
        if (currentPriceLine) {
            candlestickSeries.removePriceLine(currentPriceLine);
            currentPriceLine = null;
        }

        if (data && data.ohlc && data.ohlc.length > 0) {
            candlestickSeries.setData(data.ohlc);
            volumeSeries.setData(data.volume);

            if (data.fvgs) {
                data.fvgs.forEach(fvg => {
                    const fvgTopLine = candlestickSeries.createPriceLine({ price: fvg.top, color: fvg.color, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: false });
                    const fvgBottomLine = candlestickSeries.createPriceLine({ price: fvg.bottom, color: fvg.color, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: false });
                    drawnObjects.push(fvgTopLine);
                    drawnObjects.push(fvgBottomLine);
                });
            }
            
            if (data.breaks) {
                data.breaks.forEach(b => {
                    const line = candlestickSeries.createPriceLine({ price: b.price, color: b.color, lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid, axisLabelVisible: true, title: b.type });
                    drawnObjects.push(line);
                });
            }

            if (data.fibos) {
                data.fibos.forEach(level => {
                    const line = candlestickSeries.createPriceLine({ price: level.price, color: level.color, lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: level.ratio.toString() });
                    drawnObjects.push(line);
                });
            }

            if (data.currentPrice) {
                const currentPriceData = data.currentPrice;
                currentPriceLine = candlestickSeries.createPriceLine({
                    price: currentPriceData.price,
                    color: currentPriceData.color,
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Dotted,
                    axisLabelVisible: true,
                    title: ` ${currentPriceData.price.toFixed(4)} `,
                    axisLabelBackgroundColor: currentPriceData.color,
                    axisLabelTextColor: 'white',
                });
            }
            
            chart.timeScale().fitContent();
        } else {
            candlestickSeries.setData([]);
            volumeSeries.setData([]);
        }

    } catch (error) {
        console.error("Lỗi khi lấy hoặc vẽ dữ liệu:", error);
        candlestickSeries.setData([]);
        volumeSeries.setData([]);
        alert("Không thể kết nối đến server backend. Vui lòng đảm bảo server đang chạy và kiểm tra lại địa chỉ API.");
    } finally {
        loadingSpinner.classList.add('hidden');
    }
}

// --- Khởi tạo ứng dụng ---
async function initializeApp() {
    initializeChart();

    try {
        const tokenResponse = await fetch(`${API_BASE_URL}/api/tokens`);
        const tokens = await tokenResponse.json();
        tokens.forEach(token => {
            const option = document.createElement('option');
            option.value = token;
            option.innerText = token;
            if (token === 'BTC/USDT') {
                option.selected = true;
            }
            tokenSelector.appendChild(option);
        });
    } catch (error) {
        console.error("Không thể tải danh sách token:", error);
        tokenSelector.innerHTML = '<option value="">Lỗi tải</option>';
    }

    TIMEFRAMES.forEach(tf => {
        const btn = document.createElement('button');
        btn.className = 'timeframe-btn';
        btn.innerText = tf.toUpperCase();
        btn.dataset.value = tf;
        if (tf === '4h') {
            btn.classList.add('active');
        }
        timeframeSelector.appendChild(btn);
    });

    tokenSelector.addEventListener('change', fetchAndDrawChart);
    timeframeSelector.addEventListener('click', (e) => {
        if (e.target.classList.contains('timeframe-btn')) {
            document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            fetchAndDrawChart();
        }
    });

    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].contentRect.width === 0) { return; }
        const { width, height } = entries[0].contentRect;
        chart.applyOptions({ width, height });
    }).observe(chartContainer);

    await fetchAndDrawChart();
    
    // setInterval(fetchAndDrawChart, 900000); // Tạm thời tắt để dễ debug
}

// ========================================================= #
// == THAY ĐỔI CHÍNH: CHẠY SAU KHI TẤT CẢ TÀI NGUYÊN ĐÃ TẢI XONG == #
// ========================================================= #
window.addEventListener('load', initializeApp);

document.addEventListener('DOMContentLoaded', function() {
    console.log("Đang chạy main.js phiên bản 3.2 (đã sửa lỗi library loading)");
    
    const API_BASE_URL = 'http://localhost:5000/api';
    let chart;
    let candleSeries;

    function waitForLibrary(maxAttempts = 10) {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            const check = () => {
                attempts++;
                if (typeof window.LightweightCharts !== 'undefined') {
                    resolve(window.LightweightCharts);
                } else if (attempts >= maxAttempts) {
                    reject(new Error('LightweightCharts library failed to load'));
                } else {
                    setTimeout(check, 200);
                }
            };
            check();
        });
    }

    async function initializeChart() {
        try {
            // Wait for library to load
            const LightweightCharts = await waitForLibrary();
            
            const chartContainer = document.getElementById('chart-container');
            
            chart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: chartContainer.clientHeight || 600,
                layout: {
                    background: { color: '#ffffff' },
                    textColor: '#333',
                },
                grid: {
                    vertLines: { color: '#e1ecf2' },
                    horzLines: { color: '#e1ecf2' },
                },
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                }
            });

            candleSeries = chart.addCandlestickSeries({
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderVisible: false,
                wickUpColor: '#26a69a',
                wickDownColor: '#ef5350'
            });

            console.log('Chart initialized successfully');
            return true;
        } catch (error) {
            console.error('Error initializing chart:', error);
            return false;
        }
    }

    async function fetchChartData(symbol = 'BTC/USDT', timeframe = '4h') {
        try {
            const response = await fetch(`${API_BASE_URL}/chart-data?symbol=${symbol}&timeframe=${timeframe}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            
            // Format data for chart
            const formattedData = data.candles.map(candle => ({
                time: candle[0] / 1000, // Convert milliseconds to seconds
                open: candle[1],
                high: candle[2],
                low: candle[3],
                close: candle[4]
            }));

            return formattedData;
        } catch (error) {
            console.error('Error fetching data:', error);
            return [];
        }
    }

    async function updateChart(symbol, timeframe) {
        try {
            const loadingSpinner = document.getElementById('loading-spinner');
            loadingSpinner.classList.remove('hidden');

            const data = await fetchChartData(symbol, timeframe);
            if (data.length > 0) {
                candleSeries.setData(data);
                chart.timeScale().fitContent();
            }

            loadingSpinner.classList.add('hidden');
        } catch (error) {
            console.error('Error updating chart:', error);
            document.getElementById('loading-spinner').classList.add('hidden');
        }
    }

    async function initializeApp() {
        const chartInitialized = await initializeChart();
        if (!chartInitialized) {
            console.error('Failed to initialize chart');
            return;
        }

        // Load initial data
        await updateChart('BTC/USDT', '4h');

        // Setup event listeners
        const tokenSelector = document.getElementById('token-selector');
        tokenSelector.addEventListener('change', (e) => {
            updateChart(e.target.value, '4h');
        });

        // Fetch available tokens
        try {
            const response = await fetch(`${API_BASE_URL}/tokens`);
            const tokens = await response.json();
            
            tokenSelector.innerHTML = tokens
                .map(token => `<option value="${token}">${token}</option>`)
                .join('');
        } catch (error) {
            console.error('Error fetching tokens:', error);
        }
    }

    initializeApp();
});

// Thêm xử lý resize
window.addEventListener('resize', () => {
    if (chart) {
        chart.applyOptions({
            width: chartContainer.clientWidth,
            height: chartContainer.clientHeight || 600,
        });
    }
});
