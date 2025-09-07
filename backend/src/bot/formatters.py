from datetime import datetime

def format_price(price: float) -> str:
    """Format token price flexibly."""
    if not isinstance(price, (int, float)) or price == 0:
        return "N/A"
    if price >= 1:
        return f"{price:,.2f}"
    else:
        # Display maximum 8 decimal places, remove trailing zeros
        return f"{price:,.8f}".rstrip('0').rstrip('.')

def format_analysis_result(result: dict) -> str:
    """Format detailed analysis result according to required format."""
    if result.get('error'):
        return f"❌ **Error:** {result.get('message')}"

    # --- 1. Extract data ---
    symbol = result.get('symbol', 'N/A')
    timeframe = result.get('timeframe', 'N/A')
    price = result.get('current_price', 0)
    
    indicators = result.get('indicators', {})
    smc = result.get('smc_analysis', {})
    trading_signals = result.get('trading_signals', {})
    suggestion = result.get('analysis', {}).get('suggestion', 'No suggestion available.')
    
    # --- 2. Build each section of the message ---
    
    # Header
    header = f"📊 *Analysis {symbol} - {timeframe}*\n"
    
    # Price Info
    price_info = (
        f"💰 *Current Price:* ${format_price(price)}\n"
        f"📈 *RSI:* {indicators.get('rsi', 0):.1f}\n"
        # f"📊 *SMA20:* ${format_price(indicators.get('sma_20', 0))}\n"
        # f"📉 *EMA20:* ${format_price(indicators.get('ema_20', 0))}\n"
        f"📈 *24h Change:* {indicators.get('price_change_pct', 0):+.2f}%\n"
    )

    # ANALYSIS Section
    analysis_section = "🔍 *ANALYSIS:*\n"
    
    ob_list = smc.get('order_blocks', [])
    analysis_section += f"📦 *Order Blocks:* {len(ob_list)}\n"

    bos_list = smc.get('break_of_structure', [])
    analysis_section += f"🔄 *Structure:* {len(bos_list)}\n"
    if bos_list:
        latest_bos = bos_list[-1]
        bos_type = latest_bos.get('type', 'N/A').replace('_', ' ').upper()
        analysis_section += f"    *Latest:* {bos_type}\n"
        analysis_section += f"    *Price:* ${format_price(latest_bos.get('price', 0))}\n"

    lz_list = smc.get('liquidity_zones', [])
    analysis_section += f"💧 *Liquidity Zones:* {len(lz_list)}\n"
    if lz_list:
        latest_lz = lz_list[-1]
        lz_type = latest_lz.get('type', 'N/A').replace('_', ' ').title()
        analysis_section += f"    *Latest:* {lz_type}\n"
        analysis_section += f"    *Level:* ${format_price(latest_lz.get('price', 0))}\n"

    # TRADING SIGNALS Section
    signals_section = "🔔 *TRADING SIGNALS:*\n"
    has_signal = False
    if trading_signals:
        entry_short = trading_signals.get('entry_short', [])
        if entry_short:
            has_signal = True
            latest_short = entry_short[-1]
            signals_section += f"🔴 *Short Signal:* ${format_price(latest_short.get('price', 0))}\n"
            signals_section += f"    *Tag:* {latest_short.get('tag', 'N/A')}\n"
    
    if not has_signal:
        signals_section += "⏸️ No new entry signals.\n"

    # Trading Suggestion
    suggestion_section = f"💡 *Trading Suggestion:*\n{suggestion}\n"

    # Timestamp
    timestamp = datetime.fromtimestamp(result.get('timestamp', datetime.now().timestamp()))
    footer = f"🕐 *Updated:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"

    # Combine everything
    full_message = (
        f"{header}\n"
        f"{price_info}\n"
        f"{analysis_section}\n"
        f"{signals_section}\n"
        f"{suggestion_section}\n"
        f"{footer}"
    )

    return full_message

def format_scanner_notification(flipped_tokens: list, timeframe: str) -> str:
    """Format market scanner notification."""
    
    bullish_flips = [t for t in flipped_tokens if t['to'] == 'Long']
    bearish_flips = [t for t in flipped_tokens if t['to'] == 'Short']
    
    timestamp = datetime.now().strftime('%H:%M %d/%m/%Y')
    message = f"🚨 **Market Reversal Signals - {timeframe} Timeframe**\n_{timestamp}_\n\n"
    
    if bullish_flips:
        message += "--- BULLISH SIGNALS (Bullish Flips) ---\n"
        for token in bullish_flips:
            message += f"🟢 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"
    
    if bearish_flips:
        message += "--- BEARISH SIGNALS (Bearish Flips) ---\n"
        for token in bearish_flips:
            message += f"🔴 `{token['symbol']}`\n"
            message += f"    `{token['from']} -> {token['to']}`\n\n"
            
    message += "_These are early signals, please analyze thoroughly before trading._"
    
    return message