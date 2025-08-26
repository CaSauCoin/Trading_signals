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
        query.edit_message_text("⚠️ Chức năng đang được phát triển...")

def handle_custom_token_callback(query, context, user_id):
    """Handle custom token input callback"""
    context.bot_data['user_states'][user_id] = {"waiting_for": "custom_token"}
    query.edit_message_text(
        "✏️ **Nhập token tùy chỉnh**\n\n"
        "Gửi tên token bạn muốn phân tích:\n"
        "• Ví dụ: BTC, ETH, PEPE\n"
        "• Hoặc cặp: BTC/USDT, ETH/USDT\n\n"
        "💡 Hỗ trợ tất cả token trên Binance!",
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
        symbol = '_'.join(parts[:-1])  # Ghép lại symbol
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
        [InlineKeyboardButton("🔙 Quay lại", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "📊 **Chọn cặp trading để phân tích:**",
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
        [InlineKeyboardButton("🔙 Quay lại", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"⏱️ **Chọn timeframe cho {symbol}:**",
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
    query.edit_message_text(f"🔄 **Đang phân tích {symbol} {timeframe}...**", parse_mode='Markdown')
    
    try:
        # Check if analysis service is available
        if not analysis_service:
            query.edit_message_text(
                "❌ **Lỗi:** Dịch vụ phân tích không khả dụng.\n"
                "Vui lòng thử lại sau.",
                parse_mode='Markdown'
            )
            return
        
        # Perform analysis using AdvancedSMC
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            query.edit_message_text(
                f"❌ **Lỗi phân tích {symbol}:**\n{result.get('message', 'Unknown error')}",
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
        query.edit_message_text(f"❌ **Lỗi khi phân tích {symbol}:**\n{str(e)[:100]}...")

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
                'message': 'Không thể lấy dữ liệu từ exchange'
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
        return f"❌ **Lỗi:** {result.get('message', 'Unknown error')}"
    
    analysis_data = result.get('analysis', {})
    symbol = result.get('symbol', 'Unknown')
    timeframe = result.get('timeframe', '4h')
    
    # Use the same formatting logic from your TradingBot class
    smc = analysis_data.get('smc_analysis', {})
    indicators = analysis_data.get('indicators', {})
    trading_signals = analysis_data.get('trading_signals', {})
    
    # Header
    message = f"📊 *Phân tích {symbol} - {timeframe}*\n\n"
    
    # Price info
    current_price = analysis_data.get('current_price', 0)
    message += f"💰 *Giá hiện tại:* ${current_price:,.2f}\n"
    
    # Indicators
    rsi = indicators.get('rsi', 50)
    rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")
    message += f"📈 *RSI:* {rsi_emoji} {rsi:.1f}\n"
    message += f"📊 *SMA 20:* ${indicators.get('sma_20', 0):,.2f}\n"
    message += f"📉 *EMA 20:* ${indicators.get('ema_20', 0):,.2f}\n\n"
    
    # Price change
    price_change = indicators.get('price_change_pct', 0)
    change_emoji = "📈" if price_change > 0 else "📉"
    message += f"{change_emoji} *Thay đổi:* {price_change:+.2f}%\n\n"
    
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
            message += "⏸️ Không có signal nào\n"
        
        message += "\n"
    
    # Timestamp
    try:
        from datetime import datetime
        timestamp = datetime.fromtimestamp(result.get('timestamp', 0))
        message += f"🕐 *Cập nhật:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"
    except:
        message += f"🕐 *Cập nhật:* {result.get('timestamp', 'N/A')}"
    
    return message.strip()

def handle_watchlist_callback(query, context, data):
    """Handle watchlist related callbacks"""
    if data == 'watchlist_add':
        query.edit_message_text("🚧 Tính năng watchlist đang được phát triển...")
    elif data.startswith('watchlist_add_'):
        symbol = data.replace('watchlist_add_', '')
        add_to_watchlist_callback(query, context, symbol, '4h')
    else:
        query.edit_message_text("🚧 Tính năng watchlist đang được phát triển...")

def add_to_watchlist_callback(query, context, symbol: str, timeframe: str):
    """Add token to watchlist via callback"""
    query.edit_message_text(
        f"✅ **Đã thêm {symbol} ({timeframe}) vào watchlist!**\n\n"
        "📋 Sử dụng menu Watchlist để quản lý danh sách theo dõi.",
        parse_mode='Markdown'
    )

def handle_back_to_main(query, context):
    """Handle back to main menu"""
    keyboard = [
        [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='pair_BTC/USDT')],
        [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='pair_ETH/USDT')],
        [InlineKeyboardButton("🔍 Chọn cặp khác", callback_data='select_pair')],
        [InlineKeyboardButton("✏️ Nhập token tùy chỉnh", callback_data='custom_token')],
        [InlineKeyboardButton("👁️ Danh sách theo dõi", callback_data='watchlist_menu')],
        [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🚀 **Trading Bot SMC**

**Các tính năng:**
• 📊 Order Blocks Analysis
• 🎯 Fair Value Gaps Detection  
• 📈 Break of Structure Signals
• 💧 Liquidity Zones Mapping
• 🔔 Entry/Exit Signals

Chọn cặp để phân tích:
    """
    
    query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_watchlist_menu(query, context):
    """Show watchlist management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Thêm token", callback_data='watchlist_add')],
        [InlineKeyboardButton("📋 Xem danh sách", callback_data='watchlist_view')],
        [InlineKeyboardButton("🗑️ Xóa token", callback_data='watchlist_remove')],
        [InlineKeyboardButton("🔙 Quay lại", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "👁️ **Quản lý Watchlist**\n\n"
        "• Tối đa 5 tokens\n"
        "• Cập nhật tự động mỗi giờ\n"
        "• Thông báo khi có tín hiệu\n\n"
        "Chọn hành động:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_help(query):
    """Show help information"""
    help_text = """
📖 **Hướng dẫn Trading Bot SMC**

**Smart Money Concepts:**

🎯 **Order Blocks (OB):** 
• Khu vực mà smart money đặt lệnh lớn
• Bullish OB: Nến giảm trước BOS tăng
• Bearish OB: Nến tăng trước BOS giảm

📈 **Fair Value Gap (FVG):**
• Khoảng trống giá trên chart
• Thường được "fill" lại bởi giá
• Signal entry khi retest FVG

🔄 **Break of Structure (BOS):**
• Phá vỡ mức swing high/low trước đó
• Xác nhận thay đổi xu hướng
• Bullish BOS: Phá swing high
• Bearish BOS: Phá swing low

💧 **Liquidity Zones:**
• Khu vực có thanh khoản cao
• Smart money thường quét thanh khoản
• BSL: Buy Side Liquidity (trên)
• SSL: Sell Side Liquidity (dưới)

⚠️ **Lưu ý:** 
Đây là công cụ hỗ trợ phân tích, không phải lời khuyên đầu tư.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')