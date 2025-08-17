# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
from craw_data import get_binance_usdt_pairs, fetch_ohlcv, calculate_indicators

app = Flask(__name__)
CORS(app) # Cho phép truy cập từ domain khác (Frontend)

# --- CẤU HÌNH ---
CANDLE_LIMIT_DISPLAY = 300
CANDLE_LIMIT_CALC = 120
EXCHANGE = 'binance'

# --- API Endpoints ---

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    """Cung cấp danh sách các token."""
    tokens = get_binance_usdt_pairs()
    return jsonify(tokens)

@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    """Cung cấp dữ liệu đã xử lý để vẽ biểu đồ."""
    symbol = request.args.get('symbol', 'BTC/USDT')
    timeframe = request.args.get('timeframe', '4h')
    print(f"Nhận yêu cầu cho {symbol} - {timeframe}")

    # 1. Lấy dữ liệu nến
    df_display = fetch_ohlcv(EXCHANGE, symbol, timeframe, CANDLE_LIMIT_DISPLAY)
    if df_display is None or df_display.empty:
        return jsonify({"error": f"Không có dữ liệu cho {symbol}"}), 404

    # 2. Cắt dữ liệu để tính toán
    df_calc = df_display.tail(CANDLE_LIMIT_CALC).copy()
    
    # 3. Tính toán tất cả chỉ báo và định dạng dữ liệu
    response_data = calculate_indicators(df_display, df_calc)
    
    if not response_data:
        return jsonify({"error": "Không đủ dữ liệu để tính toán chỉ báo"}), 400

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
