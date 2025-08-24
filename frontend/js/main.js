// frontend/js/main.js
console.log("Đang chạy main.js - phiên bản cập nhật hoàn chỉnh");

// --- Cấu hình ---
const API_BASE_URL = 'http://127.0.0.1:5000';
const TIMEFRAMES = ['1h', '4h', '1d', '3d', '1w'];
const EXCHANGES = ['Binance', 'Bitget', 'Bybit', 'MEXC', 'KuCoin', 'OKX', 'Gate.io', 'Huobi'];
let chart, candlestickSeries, volumeSeries, rsiSeries;
let drawnPriceLines = [];
let otherSeries = []; // Dùng để quản lý các series phụ (FVG, BOS...)

// --- DOM Elements ---
let chartContainer, exchangeSelector, tokenSelector, timeframeSelector, mainTitle, loadingSpinner;

// --- Hàm Khởi tạo Biểu đồ ---
function initializeChart() {
    chartContainer = document.getElementById('chart-container');
    if (!chartContainer) {
        console.error("Chart container not found");
        return false;
    }

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
        layout: { backgroundColor: '#FFFFFF', textColor: '#333' },
        grid: { vertLines: { color: '#e1e1e1' }, horzLines: { color: '#e1e1e1' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#cccccc' },
        timeScale: { borderColor: '#cccccc', timeVisible: true, secondsVisible: false },
    });

    // Main Price Chart
    candlestickSeries = chart.addCandlestickSeries({
        upColor: 'rgba(0, 150, 136, 1)', downColor: 'rgba(255, 82, 82, 1)',
        borderDownColor: 'rgba(255, 82, 82, 1)', borderUpColor: 'rgba(0, 150, 136, 1)',
        wickDownColor: 'rgba(255, 82, 82, 1)', wickUpColor: 'rgba(0, 150, 136, 1)',
        priceScaleId: 'right',
    });

    // Volume Series
    volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
        lastValueVisible: false,
        priceLineVisible: false,
    });
    chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.7, bottom: 0 }, height: 80,
    });

    // RSI Series
    rsiSeries = chart.addLineSeries({
        color: 'purple', lineWidth: 2, priceScaleId: 'rsi',
        lastValueVisible: false, priceLineVisible: false,
    });
    // *** CẤU HÌNH RSI SCALE CHÍNH XÁC ***
    chart.priceScale('rsi').applyOptions({
        height: 100, // Chiều cao cố định cho pane RSI
        scaleMargins: { top: 0.9, bottom: 0 },
        visible: false, // Ban đầu ẩn đi, chỉ hiện khi có dữ liệu
    });

    // Thêm các đường tham chiếu cho RSI
    rsiSeries.createPriceLine({ price: 70, color: '#FF6B6B', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '70' });
    rsiSeries.createPriceLine({ price: 30, color: '#4CAF50', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: '30' });
    rsiSeries.createPriceLine({ price: 50, color: '#95A5A6', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: '50' });

    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartContainer.clientWidth, height: chartContainer.clientHeight });
    });

    return true;
}

// --- Hàm chính: Lấy dữ liệu và vẽ biểu đồ ---
async function fetchAndDrawChart() {
    if (!exchangeSelector || !tokenSelector || !timeframeSelector) return;

    loadingSpinner.classList.remove('hidden');

    const exchange = exchangeSelector.value.toLowerCase();
    const symbol = tokenSelector.value;
    const timeframe = timeframeSelector.querySelector('.timeframe-btn.active')?.dataset.value;

    if (!exchange || !symbol || !timeframe) {
        loadingSpinner.classList.add('hidden');
        return;
    }

    mainTitle.innerText = `Dashboard Real-time cho ${symbol} - ${exchange.toUpperCase()}`;

    try {
        const response = await fetch(`${API_BASE_URL}/api/chart-data?exchange=${exchange}&symbol=${symbol}&timeframe=${timeframe}`);
        if (!response.ok) throw new Error(`Lỗi API: ${response.statusText}.`);
        const data = await response.json();

        console.log("Full response data:", data);

        // Xóa dữ liệu cũ
        otherSeries.forEach(series => chart.removeSeries(series));
        otherSeries = [];
        drawnPriceLines.forEach(line => candlestickSeries.removePriceLine(line));
        drawnPriceLines = [];

        // Kiểm tra data hợp lệ
        if (!data || !data.ohlc || data.ohlc.length === 0) {
            candlestickSeries.setData([]);
            volumeSeries.setData([]);
            rsiSeries.setData([]);
            loadingSpinner.classList.add('hidden');
            return;
        }

        // Vẽ dữ liệu chính
        candlestickSeries.setData(data.ohlc);
        volumeSeries.setData(data.volume);

        // *** LOGIC XỬ LÝ VÀ VẼ RSI ***
        if (data.rsi && data.rsi.length > 0) {
            console.log("Setting RSI data:", data.rsi.length, "points");
            chart.priceScale('rsi').applyOptions({ visible: true }); // Bật hiển thị
            rsiSeries.setData(data.rsi);
        } else {
            console.log("No RSI data, hiding RSI pane");
            chart.priceScale('rsi').applyOptions({ visible: false }); // Ẩn đi nếu không có data
            rsiSeries.setData([]);
        }

        let allMarkers = [];

        // Vẽ BOS/CHoCH
        if (data.breaks && data.breaks.length > 0) {
            data.breaks.forEach(breakData => {
                const breakLine = chart.addLineSeries({
                    color: breakData.color, lineWidth: 1,
                    priceLineVisible: false, lastValueVisible: false,
                });
                breakLine.setData([
                    { time: breakData.startTime, value: breakData.price },
                    { time: breakData.endTime, value: breakData.price }
                ]);
                otherSeries.push(breakLine);

                allMarkers.push({
                    time: breakData.startTime,
                    position: breakData.direction === 'bullish' ? 'belowBar' : 'aboveBar',
                    color: breakData.color, shape: 'arrowUp', text: breakData.type
                });
            });
        }
        candlestickSeries.setMarkers(allMarkers);

        // Vẽ Fibonacci
        if (data.fibos && data.fibos.length > 0) {
            data.fibos.forEach(level => {
                const fiboLine = candlestickSeries.createPriceLine({
                    price: level.price, color: level.color, lineWidth: 1,
                    lineStyle: LightweightCharts.LineStyle.Dotted,
                    axisLabelVisible: true, title: level.ratio.toString()
                });
                drawnPriceLines.push(fiboLine);
            });
        }

        chart.timeScale().fitContent();

    } catch (error) {
        console.error("Lỗi khi lấy hoặc vẽ dữ liệu:", error);
        alert("Không thể kết nối đến server backend hoặc có lỗi xảy ra.");
    } finally {
        loadingSpinner.classList.add('hidden');
    }
}

// --- Khởi tạo ứng dụng ---
async function initializeApp() {
    // Gán giá trị cho biến DOM
    exchangeSelector = document.getElementById('exchange-selector');
    tokenSelector = document.getElementById('token-selector');
    timeframeSelector = document.getElementById('timeframe-selector');
    mainTitle = document.getElementById('main-title');
    loadingSpinner = document.getElementById('loading-spinner');

    if (!initializeChart()) return;

    // Tạo danh sách exchanges
    EXCHANGES.forEach(exchange => {
        const option = document.createElement('option');
        option.value = exchange;
        option.innerText = exchange;
        exchangeSelector.appendChild(option);
    });

    // Tạo các nút timeframe
    TIMEFRAMES.forEach(tf => {
        const btn = document.createElement('button');
        btn.className = 'timeframe-btn';
        btn.innerText = tf.toUpperCase();
        btn.dataset.value = tf;
        if (tf === '4h') btn.classList.add('active');
        timeframeSelector.appendChild(btn);
    });

    // Gắn sự kiện
    exchangeSelector.addEventListener('change', async () => {
        await loadTokensForExchange();
        fetchAndDrawChart();
    });
    tokenSelector.addEventListener('change', fetchAndDrawChart);
    timeframeSelector.addEventListener('click', (e) => {
        if (e.target.classList.contains('timeframe-btn')) {
            timeframeSelector.querySelector('.active').classList.remove('active');
            e.target.classList.add('active');
            fetchAndDrawChart();
        }
    });

    // Tải dữ liệu lần đầu
    await loadTokensForExchange();
    fetchAndDrawChart();
}

// Hàm load tokens cho exchange được chọn
async function loadTokensForExchange() {
    const exchange = exchangeSelector.value.toLowerCase();
    loadingSpinner.classList.remove('hidden');
    try {
        const response = await fetch(`${API_BASE_URL}/api/tokens?exchange=${exchange}`);
        const tokens = await response.json();
        tokenSelector.innerHTML = '';
        tokens.forEach(token => {
            const option = document.createElement('option');
            option.value = token;
            option.innerText = token;
            if (token === 'BTC/USDT') option.selected = true;
            tokenSelector.appendChild(option);
        });
    } catch (error) {
        console.error("Không thể tải danh sách token:", error);
        tokenSelector.innerHTML = '<option value="">Lỗi tải</option>';
    } finally {
        loadingSpinner.classList.add('hidden');
    }
}

// Chạy ứng dụng khi DOM đã sẵn sàng
document.addEventListener('DOMContentLoaded', initializeApp);
