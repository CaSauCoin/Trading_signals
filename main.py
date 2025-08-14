# app.py

import dash
from dash import dcc, html, no_update
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import pandas as pd
from io import StringIO
from craw_data import fetch_ohlcv, calculate_market_structure, get_binance_usdt_pairs

# --- CONFIGURATION ---
CANDLE_LIMIT_DISPLAY = 300
CANDLE_LIMIT_CALC = 120
EXCHANGE = 'binance'
DATA_FETCH_INTERVAL_MS = 900000
TIMEFRAMES = ['1h', '4h', '1d', '3d', '1w']

# GET TOKEN LIST ON APP START
AVAILABLE_TOKENS = get_binance_usdt_pairs()

# Initialize Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div(id='root', children=[
    html.H1(id='main-title', style={'textAlign': 'center', 'padding': '10px'}),

    html.Div([
        dcc.Dropdown(
            id='token-selector',
            options=[{'label': token, 'value': token} for token in AVAILABLE_TOKENS],
            value='BTC/USDT',
            searchable=True,
            placeholder="Select or search for a token...",
            style={'width': '300px'}
        ),
        dcc.RadioItems(
            id='timeframe-selector',
            options=[{'label': tf.upper(), 'value': tf} for tf in TIMEFRAMES],
            value='4h',
            labelStyle={'display': 'inline-block', 'margin': '0 10px'},
        ),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'gap': '30px',
              'paddingBottom': '10px'}),

    dcc.Loading(
        id="loading-chart",
        type="default",
        children=dcc.Graph(
            id='live-graph',
            style={'height': '80vh'}
        )
    ),

    dcc.Interval(id='data-fetch-interval', interval=DATA_FETCH_INTERVAL_MS, n_intervals=0)
])


@app.callback(
    [Output('live-graph', 'figure'),
     Output('main-title', 'children')],
    [Input('data-fetch-interval', 'n_intervals'),
     Input('token-selector', 'value'),
     Input('timeframe-selector', 'value')]
)
def update_graph_live(n, selected_symbol, selected_timeframe):
    # This callback is triggered every 15 minutes, or when a new token or timeframe is selected.
    # The loading animation will appear while this callback is running.

    if not selected_symbol:
        fig = go.Figure()
        fig.update_layout(title_text="Please select a token to start", template='plotly_white')
        return fig, "Real-time Dashboard"

    # 1. Fetch data
    df_display = fetch_ohlcv(EXCHANGE, selected_symbol, selected_timeframe, CANDLE_LIMIT_DISPLAY)

    new_title = f"{selected_symbol}"

    if df_display is None or df_display.empty:
        fig = go.Figure()
        fig.update_layout(title_text=f"No data for {selected_symbol} - {selected_timeframe.upper()}",
                          template='plotly_white')
        return fig, new_title

    # 2. Calculate indicators
    df_calc = df_display.tail(CANDLE_LIMIT_CALC).copy()

    df_calc['is_bullish_fvg'] = df_calc['high'].shift(2) < df_calc['low']
    df_calc['bullish_fvg_top'] = df_calc['low']
    df_calc['bullish_fvg_bottom'] = df_calc['high'].shift(2)
    df_calc['is_bearish_fvg'] = df_calc['low'].shift(2) > df_calc['high']
    df_calc['bearish_fvg_top'] = df_calc['low'].shift(2)
    df_calc['bearish_fvg_bottom'] = df_calc['high']

    structure_high, structure_low, breaks, fibo_levels, structure_high_idx, structure_low_idx = calculate_market_structure(
        df_calc)

    if structure_high is None:
        fig = go.Figure()
        fig.update_layout(title_text=f"Not enough data to calculate indicators", template='plotly_white')
        return fig, new_title

    # 3. Draw chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    volume_colors = ['green' if row.close >= row.open else 'red' for index, row in df_display.iterrows()]
    fig.add_trace(
        go.Candlestick(x=df_display.index, open=df_display['open'], high=df_display['high'], low=df_display['low'],
                       close=df_display['close'], name='OHLC'), row=1, col=1)
    fig.add_trace(go.Bar(x=df_display.index, y=df_display['volume'], name='Volume', marker_color=volume_colors), row=2,
                  col=1)

    candle_duration = df_calc.index[1] - df_calc.index[0] if len(df_calc.index) > 1 else pd.Timedelta(hours=1)
    last_candle_time = df_display.index[-1]

    bullish_fvgs = df_calc[df_calc['is_bullish_fvg']]
    for i, fvg in bullish_fvgs.iterrows():
        start_time = i + candle_duration
        fig.add_shape(type="rect", x0=start_time, y0=fvg['bullish_fvg_bottom'], x1=last_candle_time,
                      y1=fvg['bullish_fvg_top'], line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(0, 255, 0, 0.15)",
                      layer="below", row=1, col=1)

    bearish_fvgs = df_calc[df_calc['is_bearish_fvg']]
    for i, fvg in bearish_fvgs.iterrows():
        start_time = i + candle_duration
        fig.add_shape(type="rect", x0=start_time, y0=fvg['bearish_fvg_bottom'], x1=last_candle_time,
                      y1=fvg['bearish_fvg_top'], line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(255, 0, 0, 0.15)",
                      layer="below", row=1, col=1)

    for b in breaks:
        break_color = 'green' if 'BOS' in b['type'] and b['color'] == 'lime' else 'red' if 'BOS' in b[
            'type'] else 'orange'
        fig.add_shape(type="line", x0=b['start_idx'], y0=b['price'], x1=b['end_idx'], y1=b['price'],
                      line=dict(color=break_color, width=1, dash="solid"), row=1, col=1)
        fig.add_annotation(x=b['start_idx'], y=b['price'], text=b['type'], showarrow=False, xanchor="right", xshift=-5,
                           yanchor="bottom", font=dict(color=break_color, size=12), row=1, col=1)

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
        fibo_colors = {0.382: 'rgba(255, 255, 0, 0.5)', 0.5: 'rgba(255, 165, 0, 0.5)',
                       0.618: 'rgba(255, 105, 180, 0.5)', 0.705: 'rgba(230, 230, 250, 0.8)',
                       0.786: 'rgba(135, 206, 250, 0.7)'}
        for level in fibo_levels:
            ratio = level['ratio']
            color = fibo_colors.get(ratio, 'gray')
            fig.add_shape(type="line", x0=fibo_start_idx, y0=level['price'], x1=last_candle_time, y1=level['price'],
                          line=dict(color=color, width=1.5, dash="dot"), row=1, col=1)
            fig.add_annotation(x=fibo_start_idx, y=level['price'], text=f"{ratio}", showarrow=False, xanchor="right",
                               xshift=-5,
                               font=dict(color=color.replace('0.5', '1').replace('0.7', '1').replace('0.8', '1'),
                                         size=10, weight='bold'), row=1, col=1)

    last_candle = df_display.iloc[-1]
    current_price = last_candle['close']
    current_price_color = 'green' if last_candle['close'] >= last_candle['open'] else 'red'
    fig.add_shape(type="line", x0=df_display.index[0], y0=current_price, x1=last_candle_time, y1=current_price,
                  line=dict(color=current_price_color, width=1.5, dash="dot"), row=1, col=1)

    # Format current price based on its value
    if int(current_price) == 0:
        price_text = f" {current_price} "
    else:
        price_text = f" {current_price:,.4f} "

    fig.add_annotation(x=last_candle_time, y=current_price, text=price_text, showarrow=False,
                       xanchor="left", xshift=5, font=dict(color="white", size=11), bgcolor=current_price_color,
                       borderpad=2, row=1, col=1)

    fig.update_layout(title_text=f'{time.strftime("%Y-%m-%d %H:%M:%S")}', template='plotly_white',
                      xaxis_rangeslider_visible=False, dragmode='pan', legend_traceorder="reversed")
    fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    print(f"Finished drawing chart for {selected_symbol}.")
    return fig, new_title


if __name__ == '__main__':
    app.run(debug=True, port=8051)