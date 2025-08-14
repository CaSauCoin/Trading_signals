# app.py
from io import StringIO
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import pandas as pd
from craw_data import fetch_ohlcv, calculate_market_structure

# --- CẤU HÌNH ---
SYMBOL_TO_TRADE = 'ETH/USDT'
CANDLE_LIMIT_DISPLAY = 300
CANDLE_LIMIT_CALC = 120
EXCHANGE = 'binance'
UI_UPDATE_INTERVAL_MS = 5000
DATA_FETCH_INTERVAL_MS = 900000
TIMEFRAMES = ['1h', '4h', '1d', '3d', '1w']

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__)

# Giao diện của ứng dụng web
app.layout = html.Div(id='root', children=[
    dcc.Store(id='data-store'),
    html.H1(f'Dashboard Real-time cho {SYMBOL_TO_TRADE}', style={'textAlign': 'center', 'padding': '10px'}),
    dcc.RadioItems(
        id='timeframe-selector',
        options=[{'label': tf.upper(), 'value': tf} for tf in TIMEFRAMES],
        value='4h',
        labelStyle={'display': 'inline-block', 'margin': '0 10px'},
        style={'textAlign': 'center', 'paddingBottom': '10px'}
    ),
    dcc.Graph(id='live-graph'),
    dcc.Interval(id='ui-update-interval', interval=UI_UPDATE_INTERVAL_MS, n_intervals=0),
    dcc.Interval(id='data-fetch-interval', interval=DATA_FETCH_INTERVAL_MS, n_intervals=0)
])


# --- CALLBACK 1: LẤY DỮ LIỆU NỀN (Không đổi) ---
@app.callback(
    Output('data-store', 'data'),
    Input('data-fetch-interval', 'n_intervals')
)
def update_data_store(n):
    print("--- Bắt đầu tác vụ nền: Lấy dữ liệu mới ---")
    all_data = {}
    for tf in TIMEFRAMES:
        df = fetch_ohlcv(EXCHANGE, SYMBOL_TO_TRADE, tf, CANDLE_LIMIT_DISPLAY)
        if df is not None:
            all_data[tf] = df.to_json(date_format='iso', orient='split')
    print("--- Tác vụ nền hoàn tất: Đã lưu dữ liệu vào kho ---")
    return all_data


# --- CALLBACK 2: VẼ BIỂU ĐỒ ---
@app.callback(
    Output('live-graph', 'figure'),
    [Input('ui-update-interval', 'n_intervals'),
     Input('timeframe-selector', 'value')],
    State('data-store', 'data')
)
def update_graph_live(n, selected_timeframe, stored_data):
    if not stored_data:
        return dash.no_update

    json_data_for_tf = stored_data.get(selected_timeframe)
    if not json_data_for_tf:
        return dash.no_update

    df_display = pd.read_json(StringIO(json_data_for_tf), orient='split')
    df_calc = df_display.tail(CANDLE_LIMIT_CALC).copy()

    # Tính toán chỉ báo
    df_calc['is_bullish_fvg'] = df_calc['high'].shift(3) < df_calc['low'].shift(1)
    df_calc['bullish_fvg_top'] = df_calc['low'].shift(1)
    df_calc['bullish_fvg_bottom'] = df_calc['high'].shift(3)
    df_calc['is_bearish_fvg'] = df_calc['low'].shift(3) > df_calc['high'].shift(1)
    df_calc['bearish_fvg_top'] = df_calc['low'].shift(3)
    df_calc['bearish_fvg_bottom'] = df_calc['high'].shift(1)

    structure_high, structure_low, breaks, fibo_levels, structure_high_idx, structure_low_idx = calculate_market_structure(
        df_calc)
    if structure_high is None: return dash.no_update

    # Bắt đầu vẽ
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    volume_colors = ['green' if row.close >= row.open else 'red' for index, row in df_display.iterrows()]
    fig.add_trace(
        go.Candlestick(x=df_display.index, open=df_display['open'], high=df_display['high'], low=df_display['low'],
                       close=df_display['close'], name='OHLC'), row=1, col=1)
    fig.add_trace(go.Bar(x=df_display.index, y=df_display['volume'], name='Volume', marker_color=volume_colors), row=2,
                  col=1)

    candle_duration = df_calc.index[1] - df_calc.index[0]
    last_candle_time = df_display.index[-1]

    bullish_fvgs = df_calc[df_calc['is_bullish_fvg']]
    for i, fvg in bullish_fvgs.iterrows():
        start_time = fvg.name - 2 * candle_duration
        fig.add_shape(type="rect", x0=start_time, y0=fvg['bullish_fvg_bottom'], x1=last_candle_time,
                      y1=fvg['bullish_fvg_top'], line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(0, 255, 0, 0.15)",
                      layer="below", row=1, col=1)

    bearish_fvgs = df_calc[df_calc['is_bearish_fvg']]
    for i, fvg in bearish_fvgs.iterrows():
        start_time = fvg.name - 2 * candle_duration
        fig.add_shape(type="rect", x0=start_time, y0=fvg['bearish_fvg_bottom'], x1=last_candle_time,
                      y1=fvg['bearish_fvg_top'], line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(255, 0, 0, 0.15)",
                      layer="below", row=1, col=1)

    for b in breaks:
        # Thay đổi màu cho dễ nhìn trên nền trắng
        break_color = 'green' if 'BOS' in b['type'] and b['color'] == 'lime' else 'red' if 'BOS' in b[
            'type'] else 'orange'
        fig.add_shape(type="line", x0=b['start_idx'], y0=b['price'], x1=b['end_idx'], y1=b['price'],
                      line=dict(color=break_color, width=1, dash="solid"), row=1, col=1)
        fig.add_annotation(x=b['start_idx'], y=b['price'], text=b['type'], showarrow=False, xanchor="right", xshift=-5,
                           yanchor="bottom", font=dict(color=break_color, size=12), row=1, col=1)

    # Thay màu 'aqua' thành 'blue'
    fig.add_shape(type="line", x0=structure_high_idx, y0=structure_high, x1=last_candle_time, y1=structure_high,
                  line=dict(color="blue", width=1.5, dash="dash"), row=1, col=1)
    fig.add_shape(type="line", x0=structure_low_idx, y0=structure_low, x1=last_candle_time, y1=structure_low,
                  line=dict(color="blue", width=1.5, dash="dash"), row=1, col=1)
    fig.add_annotation(x=last_candle_time, y=structure_high, text="SH", showarrow=False, xanchor="left", xshift=5,
                       font=dict(color="blue"), row=1, col=1)
    fig.add_annotation(x=last_candle_time, y=structure_low, text="SL", showarrow=False, xanchor="left", xshift=5,
                       font=dict(color="blue"), row=1, col=1)

    if fibo_levels:
        fibo_start_idx = min(structure_high_idx, structure_low_idx)
        for level in fibo_levels:
            # Thay màu fibo thành màu đen
            fig.add_shape(type="line", x0=fibo_start_idx, y0=level['price'], x1=last_candle_time, y1=level['price'],
                          line=dict(color="rgba(0, 0, 0, 0.4)", width=1, dash="dot"), row=1, col=1)
            fig.add_annotation(x=fibo_start_idx, y=level['price'], text=f"{level['ratio']}", showarrow=False,
                               xanchor="right", xshift=-5, font=dict(color="rgba(0, 0, 0, 0.5)", size=9), row=1, col=1)

    # ========================================================= #
    # == THAY ĐỔI CHÍNH: ĐỔI SANG NỀN TRẮNG == #
    # ========================================================= #
    fig.update_layout(
        title_text=f'Cập nhật khung {selected_timeframe.upper()} lúc: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        template='plotly_white',  # <--- ĐỔI TẠI ĐÂY
        xaxis_rangeslider_visible=False,
        legend_traceorder="reversed"  # Đảo ngược thứ tự chú thích
    )
    fig.update_yaxes(title_text="Giá (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=1)

    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8051)