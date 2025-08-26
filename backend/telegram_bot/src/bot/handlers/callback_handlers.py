import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Add the correct path to AdvancedSMC
current_dir = os.path.dirname(__file__)  # handlers directory
src_dir = os.path.dirname(os.path.dirname(current_dir))  # src directory
telegram_bot_dir = os.path.dirname(src_dir)  # telegram_bot directory
backend_dir = os.path.dirname(telegram_bot_dir)  # backend directory
advancedSMC_path = os.path.join(backend_dir, 'AdvancedSMC')
sys.path.insert(0, advancedSMC_path)

try:
    from AdvancedSMC import AdvancedSMC
    SMC_AVAILABLE = True
    # Initialize analysis service
    analysis_service = AdvancedSMC()
    print("AdvancedSMC initialized successfully")
except ImportError as e:
    print(f"Warning: Could not import AdvancedSMC: {e}")
    SMC_AVAILABLE = False
    AdvancedSMC = None
    analysis_service = None
except Exception as e:
    print(f"Error initializing AdvancedSMC: {e}")
    analysis_service = None

logger = logging.getLogger(__name__)

def handle_callback(update: Update, context: CallbackContext):
    """Main callback handler for inline keyboard buttons"""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Initialize user states if not exists
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    # Route callbacks
    if data == 'custom_token':
        handle_custom_token_callback(query, context, user_id)
    elif data.startswith('analyze_'):
        handle_analyze_callback(query, context, data)
    elif data == 'select_pair':
        handle_select_pair_callback(query, context)
    elif data == 'watchlist_menu':
        show_watchlist_menu(query, context)
    elif data.startswith('watchlist_'):
        handle_watchlist_callback(query, context, data)
    elif data.startswith('timeframe_'):
        handle_timeframe_callback(query, context, data)
    elif data.startswith('refresh_'):
        handle_refresh_callback(query, context, data)
    elif data.startswith('tf_'):
        handle_tf_callback(query, context, data)
    elif data.startswith('pair_'):
        handle_pair_callback(query, context, data)
    elif data == 'back_to_main' or data == 'start':
        handle_back_to_main(query, context)
    elif data == 'help':
        show_help(query)
    else:
        query.edit_message_text("⚠️ Feature under development...")

def handle_custom_token_callback(query, context, user_id):
    """Handle custom token input callback"""
    context.bot_data['user_states'][user_id] = {"waiting_for": "custom_token"}
    query.edit_message_text(
        "✏️ **Enter Custom Token**\n\n"
        "Send the token name you want to analyze:\n"
        "• Example: BTC, ETH, PEPE\n"
        "• Or pair: BTC/USDT, ETH/USDT\n\n"
        "💡 Supports all tokens on Binance!",
        parse_mode='Markdown'
    )

def handle_analyze_callback(query, context, data):
    """Handle analysis callback"""
    parts = data.split('_')
    if len(parts) >= 3:
        symbol = '_'.join(parts[1:-1])  # Handle symbols with underscores
        timeframe = parts[-1]
    else:
        symbol = parts[1] if len(parts) > 1 else 'BTC/USDT'
        timeframe = '4h'
    
    perform_analysis_callback(query, context, symbol, timeframe)

def handle_tf_callback(query, context, data):
    """Handle timeframe callback (tf_SYMBOL_TIMEFRAME)"""
    parts = data.replace('tf_', '').split('_')
    if len(parts) >= 2:
        symbol = '_'.join(parts[:-1])  # Rejoin symbol
        symbol = symbol.replace('_', '/')  # Convert back to BTC/USDT format
        timeframe = parts[-1]
        perform_analysis_callback(query, context, symbol, timeframe)

def handle_pair_callback(query, context, data):
    """Handle pair selection callback"""
    symbol = data.replace('pair_', '')
    perform_analysis_callback(query, context, symbol, '4h')

def handle_select_pair_callback(query, context):
    """Handle select pair callback"""
    keyboard = [
        [InlineKeyboardButton("₿ BTC/USDT", callback_data='pair_BTC/USDT'),
         InlineKeyboardButton("Ξ ETH/USDT", callback_data='pair_ETH/USDT')],
        [InlineKeyboardButton("🟡 BNB/USDT", callback_data='pair_BNB/USDT'),
         InlineKeyboardButton("🔵 WLD/USDT", callback_data='pair_WLD/USDT')],
        [InlineKeyboardButton("🟣 SOL/USDT", callback_data='pair_SOL/USDT'),
         InlineKeyboardButton("🔴 SEI/USDT", callback_data='pair_SEI/USDT')],
        [InlineKeyboardButton("🟢 PEPE/USDT", callback_data='pair_PEPE/USDT'),
         InlineKeyboardButton("🟢 SUI/USDT", callback_data='pair_SUI/USDT')],
        [InlineKeyboardButton("🔙 Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "📊 **Select trading pair for analysis:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_timeframe_callback(query, context, data):
    """Handle timeframe selection callback"""
    symbol = data.replace('timeframe_', '')
    
    keyboard = [
        [InlineKeyboardButton("15m", callback_data=f'analyze_{symbol}_15m'),
         InlineKeyboardButton("1h", callback_data=f'analyze_{symbol}_1h')],
        [InlineKeyboardButton("4h", callback_data=f'analyze_{symbol}_4h'),
         InlineKeyboardButton("1d", callback_data=f'analyze_{symbol}_1d')],
        [InlineKeyboardButton("3d", callback_data=f'analyze_{symbol}_3d'),
         InlineKeyboardButton("1w", callback_data=f'analyze_{symbol}_1w')],
        [InlineKeyboardButton("🔙 Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"⏱️ **Select timeframe for {symbol}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def handle_refresh_callback(query, context, data):
    """Handle refresh analysis callback"""
    parts = data.replace('refresh_', '').split('_')
    symbol = '_'.join(parts[:-1])
    timeframe = parts[-1]
    
    perform_analysis_callback(query, context, symbol, timeframe)

def perform_analysis_callback(query, context, symbol: str, timeframe: str):
    """Perform analysis and update message"""
    # Show loading
    query.edit_message_text(f"🔄 **Analyzing {symbol} {timeframe}...**", parse_mode='Markdown')
    
    try:
        # Check if analysis service is available
        if not analysis_service:
            query.edit_message_text(
                "❌ **Error:** Analysis service not available.\n"
                "Please try again later.",
                parse_mode='Markdown'
            )
            return
        
        # Perform analysis using AdvancedSMC
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            query.edit_message_text(
                f"❌ **Analysis error for {symbol}:**\n{result.get('message', 'Unknown error')}",
                parse_mode='Markdown'
            )
            return
        
        # Format results
        formatted_result = format_analysis_result(result)
        
        # Create action buttons
        symbol_encoded = symbol.replace('/', '_')  # BTC/USDT -> BTC_USDT for callback
        keyboard = [
            [InlineKeyboardButton("📊 15m", callback_data=f'tf_{symbol_encoded}_15m'),
             InlineKeyboardButton("📊 1h", callback_data=f'tf_{symbol_encoded}_1h'),
             InlineKeyboardButton("📊 4h", callback_data=f'tf_{symbol_encoded}_4h')],
            [InlineKeyboardButton("📊 1d", callback_data=f'tf_{symbol_encoded}_1d'),
             InlineKeyboardButton("📊 3d", callback_data=f'tf_{symbol_encoded}_3d'),
             InlineKeyboardButton("📊 1w", callback_data=f'tf_{symbol_encoded}_1w')],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f'tf_{symbol_encoded}_{timeframe}'),
             InlineKeyboardButton("🏠 Menu", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send formatted result
        try:
            query.edit_message_text(formatted_result, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Markdown parse error: {e}")
            # Fallback: send message without markdown
            plain_message = formatted_result.replace('*', '').replace('_', '')
            query.edit_message_text(plain_message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        query.edit_message_text(f"❌ **Error analyzing {symbol}:**\n{str(e)[:100]}...")

def analyze_with_smc(symbol: str, timeframe: str):
    """Analyze symbol using AdvancedSMC"""
    try:
        if not analysis_service:
            return {
                'error': True,
                'message': 'AdvancedSMC service not available'
            }
        
        # Normalize symbol format for Binance
        if '/' not in symbol and not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"
        elif '/' in symbol:
            symbol = symbol.replace('/', '')
        
        logger.info(f"Analyzing {symbol} {timeframe} with AdvancedSMC...")
        
        # Call AdvancedSMC analysis method
        analysis_result = analysis_service.get_trading_signals(symbol, timeframe)
        
        if analysis_result is None:
            return {
                'error': True,
                'message': 'Unable to fetch data from exchange'
            }
        
        # Format the result
        result = {
            'error': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'analysis': analysis_result,
            'timestamp': analysis_result.get('timestamp') if analysis_result else None
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in SMC analysis: {e}")
        return {
            'error': True,
            'message': f'Analysis failed: {str(e)}'
        }

def format_analysis_result(result: dict) -> str:
    """Format analysis results for display"""
    if result.get('error'):
        return f"❌ **Error:** {result.get('message', 'Unknown error')}"
    
    analysis_data = result.get('analysis', {})
    symbol = result.get('symbol', 'Unknown')
    timeframe = result.get('timeframe', '4h')
    
    # Use the same formatting logic from your TradingBot class
    smc = analysis_data.get('smc_analysis', {})
    indicators = analysis_data.get('indicators', {})
    trading_signals = analysis_data.get('trading_signals', {})
    
    # Header
    message = f"📊 *Analysis {symbol} - {timeframe}*\n\n"
    
    # Price info
    current_price = analysis_data.get('current_price', 0)
    message += f"💰 *Current Price:* ${current_price:,.2f}\n"
    
    # Indicators
    rsi = indicators.get('rsi', 50)
    rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")
    message += f"📈 *RSI:* {rsi_emoji} {rsi:.1f}\n"
    message += f"📊 *SMA 20:* ${indicators.get('sma_20', 0):,.2f}\n"
    message += f"📉 *EMA 20:* ${indicators.get('ema_20', 0):,.2f}\n\n"
    
    # Price change
    price_change = indicators.get('price_change_pct', 0)
    change_emoji = "📈" if price_change > 0 else "📉"
    message += f"{change_emoji} *Change:* {price_change:+.2f}%\n\n"
    
    # SMC Analysis
    message += "🔍 *SMC ANALYSIS:*\n"
    
    # Order Blocks
    ob_count = len(smc.get('order_blocks', []))
    message += f"📦 *Order Blocks:* {ob_count}\n"
    
    # Fair Value Gaps
    fvg_count = len(smc.get('fair_value_gaps', []))
    message += f"🎯 *Fair Value Gaps:* {fvg_count}\n"
    
    # Break of Structure
    bos_count = len(smc.get('break_of_structure', []))
    message += f"🔄 *Structure Breaks:* {bos_count}\n"
    
    # Liquidity Zones
    lz_count = len(smc.get('liquidity_zones', []))
    message += f"💧 *Liquidity Zones:* {lz_count}\n\n"
    
    # Trading Signals
    if trading_signals:
        message += "🔔 *TRADING SIGNALS:*\n"
        
        entry_long = trading_signals.get('entry_long', [])
        entry_short = trading_signals.get('entry_short', [])
        
        if entry_long:
            latest_long = entry_long[-1]
            message += f"🟢 *Long Signal:* ${latest_long.get('price', 0):,.2f}\n"
        
        if entry_short:
            latest_short = entry_short[-1]
            message += f"🔴 *Short Signal:* ${latest_short.get('price', 0):,.2f}\n"
        
        if not entry_long and not entry_short:
            message += "⏸️ No active signals\n"
        
        message += "\n"
    
    # Timestamp
    try:
        from datetime import datetime
        timestamp = datetime.fromtimestamp(result.get('timestamp', 0))
        message += f"🕐 *Updated:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"
    except:
        message += f"🕐 *Updated:* {result.get('timestamp', 'N/A')}"
    
    return message.strip()

def handle_watchlist_callback(query, context, data):
    """Handle watchlist related callbacks"""
    if data == 'watchlist_add':
        query.edit_message_text("🚧 Watchlist feature under development...")
    elif data.startswith('watchlist_add_'):
        symbol = data.replace('watchlist_add_', '')
        add_to_watchlist_callback(query, context, symbol, '4h')
    else:
        query.edit_message_text("🚧 Watchlist feature under development...")

def add_to_watchlist_callback(query, context, symbol: str, timeframe: str):
    """Add token to watchlist via callback"""
    query.edit_message_text(
        f"✅ **Added {symbol} ({timeframe}) to watchlist!**\n\n"
        "📋 Use Watchlist menu to manage your tracking list.",
        parse_mode='Markdown'
    )

def handle_back_to_main(query, context):
    """Handle back to main menu"""
    keyboard = [
        [InlineKeyboardButton("📊 Analyze BTC/USDT", callback_data='pair_BTC/USDT')],
        [InlineKeyboardButton("📈 Analyze ETH/USDT", callback_data='pair_ETH/USDT')],
        [InlineKeyboardButton("🔍 Select Other Pair", callback_data='select_pair')],
        [InlineKeyboardButton("✏️ Enter Custom Token", callback_data='custom_token')],
        [InlineKeyboardButton("👁️ Watchlist", callback_data='watchlist_menu')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🚀 **Trading Bot SMC**

**Features:**
• 📊 Order Blocks Analysis
• 🎯 Fair Value Gaps Detection  
• 📈 Break of Structure Signals
• 💧 Liquidity Zones Mapping
• 🔔 Entry/Exit Signals

Select a pair to analyze:
    """
    
    query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_watchlist_menu(query, context):
    """Show watchlist management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Token", callback_data='watchlist_add')],
        [InlineKeyboardButton("📋 View List", callback_data='watchlist_view')],
        [InlineKeyboardButton("🗑️ Remove Token", callback_data='watchlist_remove')],
        [InlineKeyboardButton("🔙 Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "👁️ **Watchlist Management**\n\n"
        "• Maximum 5 tokens\n"
        "• Auto-update every hour\n"
        "• Notifications for signals\n\n"
        "Choose an action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_help(query):
    """Show help information"""
    help_text = """
📖 **Trading Bot SMC Guide**

**Smart Money Concepts:**

🎯 **Order Blocks (OB):** 
• Areas where smart money places large orders
• Bullish OB: Red candle before bullish BOS
• Bearish OB: Green candle before bearish BOS

📈 **Fair Value Gap (FVG):**
• Price gaps on the chart
• Usually get "filled" by price
• Entry signal when retesting FVG

🔄 **Break of Structure (BOS):**
• Breaking previous swing high/low
• Confirms trend change
• Bullish BOS: Break swing high
• Bearish BOS: Break swing low

💧 **Liquidity Zones:**
• High liquidity areas
• Smart money often sweeps liquidity
• BSL: Buy Side Liquidity (above)
• SSL: Sell Side Liquidity (below)

⚠️ **Note:** 
This is an analysis tool, not financial advice.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')