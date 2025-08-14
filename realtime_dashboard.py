import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from craw_data import *

SYMBOL_TO_TRADE = 'ETH/USDT'
TIMEFRAME = 'd'
CANDLE_LIMIT = 200
EXCHANGE = 'binance'
UPDATE_INTERVAL_MS = 5000

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__)

# Giao diện của ứng dụng web
app.layout = html.Div(id='root', children=[
    html.H1(f'Dashboard Real-time cho {SYMBOL_TO_TRADE}', style={'textAlign': 'center', 'padding': '10px'}),

    # ========================================================= #
    # == THÊM BỘ NÚT CHỌN KHUNG THỜI GIAN == #
    # ========================================================= #
    dcc.RadioItems(
        id='timeframe-selector',
        options=[
            {'label': '1H', 'value': '1h'},
            {'label': '4H', 'value': '4h'},
            {'label': '1D', 'value': '1d'},
            {'label': '3D', 'value': '3d'},
            {'label': '1W', 'value': '1w'},
        ],
        value='4h',  # Khung thời gian mặc định khi mở app
        labelStyle={'display': 'inline-block', 'margin': '0 10px'},
        style={'textAlign': 'center', 'paddingBottom': '10px'}
    ),

    dcc.Graph(id='live-graph'),

    dcc.Interval(
        id='interval-component',
        interval=UPDATE_INTERVAL_MS,
        n_intervals=0
    )
])

@app.callback(
    Output('live-graph', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('timeframe-selector', 'value')]
)
def update_graph_live(n, selected_timeframe):
    df = fetch_ohlcv(EXCHANGE, SYMBOL_TO_TRADE, selected_timeframe, CANDLE_LIMIT)  # Lấy nhiều nến hơn để phân tích cấu trúc
    if df is None or df.empty:
        return dash.no_update

    # ================================================================= #
    # == BẮT ĐẦU LOGIC TÍNH TOÁN MARKET STRUCTURE (BOS/CHoCH) & FIBO == #
    # ================================================================= #
    # --- TÍNH TOÁN FVG CHÍNH XÁC ---
    # isBullishFVG = high[3] < low[1]
    df['is_bullish_fvg'] = df['high'].shift(3) < df['low'].shift(1)
    df['bullish_fvg_top'] = df['low'].shift(1)
    df['bullish_fvg_bottom'] = df['high'].shift(3)

    # isBearishFVG = low[3] > high[1]
    df['is_bearish_fvg'] = df['low'].shift(3) > df['high'].shift(1)
    df['bearish_fvg_top'] = df['low'].shift(3)
    df['bearish_fvg_bottom'] = df['high'].shift(1)

    # -- Khởi tạo các biến trạng thái --
    structure_high = df.iloc[0]['high']
    structure_low = df.iloc[0]['low']
    structure_high_idx = df.index[0]
    structure_low_idx = df.index[0]
    direction = 0
    breaks = []
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # -- Vòng lặp để xác định cấu trúc --
    for i in range(1, len(df)):
        current_candle = df.iloc[i]
        window = df.iloc[max(0, i - 10):i]
        swing_high = window['high'].max()
        swing_low = window['low'].min()
        swing_high_idx = window['high'].idxmax()
        swing_low_idx = window['low'].idxmin()

        is_high_broken = current_candle['close'] > structure_high
        is_low_broken = current_candle['close'] < structure_low

        if direction in [0, 2] and is_high_broken:
            break_type = 'BOS' if direction == 2 else 'CHoCH'
            breaks.append({'price': structure_high, 'start_idx': structure_high_idx, 'end_idx': current_candle.name,
                           'type': break_type, 'color': 'lime'})
            direction, structure_high, structure_high_idx, structure_low, structure_low_idx = 2, current_candle[
                'high'], current_candle.name, swing_low, swing_low_idx
        elif direction in [0, 1] and is_low_broken:
            break_type = 'BOS' if direction == 1 else 'CHoCH'
            breaks.append({'price': structure_low, 'start_idx': structure_low_idx, 'end_idx': current_candle.name,
                           'type': break_type, 'color': 'red'})
            direction, structure_low, structure_low_idx, structure_high, structure_high_idx = 1, current_candle[
                'low'], current_candle.name, swing_high, swing_high_idx
        else:
            if direction in [0, 2] and current_candle['high'] > structure_high:
                structure_high, structure_high_idx = current_candle['high'], current_candle.name
            elif direction in [0, 1] and current_candle['low'] < structure_low:
                structure_low, structure_low_idx = current_candle['low'], current_candle.name

    # -- Tính toán Fibonacci cho cấu trúc cuối cùng --
    fibo_levels = []
    fibo_ratios = [0.382, 0.5, 0.618, 0.705, 0.786]
    structure_range = structure_high - structure_low
    if structure_range > 0:
        for ratio in fibo_ratios:
            if direction == 2:  # Xu hướng tăng, fibo tính từ đỉnh xuống
                price = structure_high - structure_range * ratio
            else:  # Xu hướng giảm, fibo tính từ đáy lên
                price = structure_low + structure_range * ratio
            fibo_levels.append({'ratio': ratio, 'price': price})

    # ================================================================= #
    # == BẮT ĐẦU VẼ BIỂU ĐỒ VỚI CÁC CHỈ BÁO ĐÃ TÍNH TOÁN == #
    # ================================================================= #

    # -- Vẽ Nến và Volume --
    volume_colors = ['green' if row.close >= row.open else 'red' for index, row in df.iterrows()]
    fig.add_trace(
        go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='OHLC'),
        row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=volume_colors), row=2, col=1)

    candle_duration = df.index[1] - df.index[0]
    last_candle_time = df.index[-1]

    # Vùng Bullish FVG
    bullish_fvgs = df[df['is_bullish_fvg']]
    for i, fvg in bullish_fvgs.iterrows():
        # Hộp FVG nằm ở cây nến thứ 2 trong mô hình 3 nến
        # Tức là 1 cây nến trước cây nến hiện tại (nơi FVG được xác nhận)
        start_time = fvg.name - 2 * candle_duration
        fig.add_shape(type="rect",
                      x0=start_time, y0=fvg['bullish_fvg_bottom'],
                      x1=last_candle_time, y1=fvg['bullish_fvg_top'],
                      line=dict(color="rgba(0,0,0,0)"),
                      fillcolor="rgba(0, 255, 0, 0.2)",
                      row=1, col=1)

    # Vùng Bearish FVG
    bearish_fvgs = df[df['is_bearish_fvg']]
    for i, fvg in bearish_fvgs.iterrows():
        start_time = fvg.name - 2 * candle_duration
        fig.add_shape(type="rect",
                      x0=start_time, y0=fvg['bearish_fvg_bottom'],
                      x1=last_candle_time, y1=fvg['bearish_fvg_top'],
                      line=dict(color="rgba(0,0,0,0)"),
                      fillcolor="rgba(255, 0, 0, 0.2)",
                      row=1, col=1)

    # -- Vẽ các đường BOS/CHoCH đã xảy ra --
    for b in breaks:
        fig.add_shape(type="line", x0=b['start_idx'], y0=b['price'], x1=b['end_idx'], y1=b['price'],
                      line=dict(color=b['color'], width=1, dash="dash"), row=1, col=1)
        fig.add_annotation(x=b['end_idx'], y=b['price'], text=b['type'], showarrow=False,
                           xanchor="left", xshift=5, font=dict(color=b['color'], size=10), row=1, col=1)

    # -- Vẽ cấu trúc hiện tại --
    fig.add_shape(type="line", x0=structure_high_idx, y0=structure_high, x1=df.index[-1], y1=structure_high,
                  line=dict(color="aqua", width=2), row=1, col=1)
    fig.add_shape(type="line", x0=structure_low_idx, y0=structure_low, x1=df.index[-1], y1=structure_low,
                  line=dict(color="aqua", width=2), row=1, col=1)
    fig.add_annotation(x=df.index[-1], y=structure_high, text="Structure High", showarrow=False, xanchor="left",
                       xshift=5, font=dict(color="aqua"), row=1, col=1)
    fig.add_annotation(x=df.index[-1], y=structure_low, text="Structure Low", showarrow=False, xanchor="left", xshift=5,
                       font=dict(color="aqua"), row=1, col=1)

    # -- Vẽ các mức Fibonacci --
    fibo_start_idx = min(structure_high_idx, structure_low_idx)
    for level in fibo_levels:
        fig.add_shape(type="line", x0=fibo_start_idx, y0=level['price'], x1=df.index[-1], y1=level['price'],
                      line=dict(color="rgba(255, 255, 255, 0.4)", width=1, dash="dot"), row=1, col=1)
        fig.add_annotation(x=df.index[-1], y=level['price'], text=f"{level['ratio']}", showarrow=False,
                           xanchor="left", xshift=5, font=dict(color="rgba(255, 255, 255, 0.5)", size=9), row=1, col=1)

    # -- Cập nhật layout --
    fig.update_layout(
        title_text=f'Cập nhật khung {selected_timeframe.upper()} lúc: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        template='plotly_dark', xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Giá (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=1)

    return fig

if __name__ == '__main__':
    # Chạy server
    app.run(debug=True, port=8051)
