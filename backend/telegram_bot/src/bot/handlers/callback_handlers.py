from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import sys
import os

# Add the correct path to AdvancedSMC
# Navigate from current file to the AdvancedSMC directory
current_dir = os.path.dirname(__file__)  # handlers directory
src_dir = os.path.dirname(os.path.dirname(current_dir))  # src directory
telegram_bot_dir = os.path.dirname(src_dir)  # telegram_bot directory
backend_dir = os.path.dirname(telegram_bot_dir)  # backend directory
advancedSMC_path = os.path.join(backend_dir, 'AdvancedSMC')
sys.path.insert(0, advancedSMC_path)

try:
    from AdvancedSMC import AdvancedSMC
    SMC_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import AdvancedSMC: {e}")
    SMC_AVAILABLE = False
    AdvancedSMC = None

# Initialize analysis service if available
if SMC_AVAILABLE and AdvancedSMC:
    try:
        analysis_service = AdvancedSMC()
        print("AdvancedSMC initialized successfully")
    except Exception as e:
        print(f"Error initializing AdvancedSMC: {e}")
        analysis_service = None
else:
    analysis_service = None

def handle_callback(update: Update, context: CallbackContext):
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
    elif data == 'back_to_main':
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

def handle_select_pair_callback(query, context):
    """Handle select pair callback"""
    keyboard = [
        [InlineKeyboardButton("BTC/USDT", callback_data='analyze_BTC/USDT_4h'),
         InlineKeyboardButton("ETH/USDT", callback_data='analyze_ETH/USDT_4h')],
        [InlineKeyboardButton("BNB/USDT", callback_data='analyze_BNB/USDT_4h'),
         InlineKeyboardButton("ADA/USDT", callback_data='analyze_ADA/USDT_4h')],
        [InlineKeyboardButton("SOL/USDT", callback_data='analyze_SOL/USDT_4h'),
         InlineKeyboardButton("DOT/USDT", callback_data='analyze_DOT/USDT_4h')],
        [InlineKeyboardButton("MATIC/USDT", callback_data='analyze_MATIC/USDT_4h'),
         InlineKeyboardButton("AVAX/USDT", callback_data='analyze_AVAX/USDT_4h')],
        [InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "🔍 **Chọn cặp token phổ biến:**",
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
        [InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main')]
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
                f"❌ **Lỗi hệ thống**\n\n"
                f"AdvancedSMC service không khả dụng.",
                parse_mode='Markdown'
            )
            return
        
        # Perform analysis using AdvancedSMC
        result = analyze_with_smc(symbol, timeframe)
        
        if result.get('error'):
            query.edit_message_text(
                f"❌ **Lỗi phân tích {symbol}**\n\n"
                f"Chi tiết: {result.get('message', 'Unknown error')}",
                parse_mode='Markdown'
            )
            return
        
        # Format results
        formatted_result = format_analysis_result(result)
        
        # Create action buttons
        keyboard = [
            [InlineKeyboardButton("➕ Thêm vào Watchlist", callback_data=f'watchlist_add_{symbol}_{timeframe}')],
            [InlineKeyboardButton("🔄 Làm mới", callback_data=f'refresh_{symbol}_{timeframe}')],
            [InlineKeyboardButton("⏱️ Đổi timeframe", callback_data=f'timeframe_{symbol}')],
            [InlineKeyboardButton("🔙 Menu chính", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(formatted_result, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        query.edit_message_text(
            f"❌ **Lỗi phân tích {symbol}**\n\n"
            f"Chi tiết: {str(e)}",
            parse_mode='Markdown'
        )

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
        
        print(f"Analyzing {symbol} {timeframe} with AdvancedSMC...")
        
        # Call your AdvancedSMC methods here
        # Adjust these method names based on your actual AdvancedSMC class
        
        # Example calls (you need to replace with actual method names):
        # order_blocks = analysis_service.get_order_blocks(symbol, timeframe)
        # fvg = analysis_service.get_fair_value_gaps(symbol, timeframe)
        # bos = analysis_service.get_break_of_structure(symbol, timeframe)
        # signal = analysis_service.get_trading_signal(symbol, timeframe)
        
        # For now, return mock data - replace with actual analysis
        result = {
            'error': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'analysis': {
                'signal': {'signal': 'BUY', 'confidence': 75},
                'order_blocks': {'status': 'Bullish OB found', 'count': 2},
                'fair_value_gaps': {'status': 'FVG detected', 'direction': 'bullish'},
                'break_of_structure': {'status': 'BOS confirmed', 'direction': 'up'},
                'liquidity_zones': {'status': 'Liquidity swept', 'level': 'high'},
                'timestamp': '2025-08-26T15:30:00'
            }
        }
        
        return result
        
    except Exception as e:
        print(f"Error in SMC analysis: {e}")
        return {
            'error': True,
            'message': f'Analysis failed: {str(e)}'
        }

def handle_watchlist_callback(query, context, data):
    """Handle watchlist related callbacks"""
    if data == 'watchlist_add':
        user_id = query.from_user.id
        context.bot_data['user_states'][user_id] = {"waiting_for": "watchlist_add"}
        query.edit_message_text(
            "➕ **Thêm token vào Watchlist**\n\n"
            "Gửi tên token bạn muốn theo dõi:\n"
            "• Ví dụ: BTC, ETH, PEPE\n"
            "• Hoặc cặp: BTC/USDT, ETH/USDT\n\n"
            "💡 Sẽ sử dụng timeframe 4h mặc định.",
            parse_mode='Markdown'
        )
    elif data.startswith('watchlist_add_'):
        # Extract symbol and timeframe from callback
        parts = data.replace('watchlist_add_', '').split('_')
        symbol = '_'.join(parts[:-1])
        timeframe = parts[-1]
        add_to_watchlist_callback(query, context, symbol, timeframe)
    else:
        query.edit_message_text("⚠️ Chức năng watchlist đang được phát triển...")

def add_to_watchlist_callback(query, context, symbol: str, timeframe: str):
    """Add token to watchlist via callback"""
    # TODO: Implement actual watchlist storage
    query.edit_message_text(
        f"✅ **Đã thêm {symbol} ({timeframe}) vào watchlist!**\n\n"
        "📋 Sử dụng menu Watchlist để quản lý danh sách theo dõi.",
        parse_mode='Markdown'
    )

def handle_back_to_main(query, context):
    """Handle back to main menu"""
    keyboard = [
        [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='analyze_BTC/USDT_4h')],
        [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='analyze_ETH/USDT_4h')],
        [InlineKeyboardButton("🔍 Chọn cặp có sẵn", callback_data='select_pair')],
        [InlineKeyboardButton("✏️ Nhập token tùy chỉnh", callback_data='custom_token')],
        [InlineKeyboardButton("👁️ Danh sách theo dõi", callback_data='watchlist_menu')],
        [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🚀 **Trading Bot SMC!**

Chọn một tùy chọn bên dưới để bắt đầu:

💡 **Mới:** 
• Nhập bất kỳ token nào trên Binance!
• Theo dõi tự động với cập nhật mỗi giờ!
    """
    
    query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

def format_analysis_result(result: dict) -> str:
    """Format analysis results for display"""
    if result.get('error'):
        return f"❌ **Lỗi:** {result.get('message')}"
    
    symbol = result.get('symbol', 'Unknown')
    timeframe = result.get('timeframe', '4h')
    analysis = result.get('analysis', {})
    
    # Extract analysis data
    signal = analysis.get('signal', {})
    order_blocks = analysis.get('order_blocks', {})
    fvg = analysis.get('fair_value_gaps', {})
    bos = analysis.get('break_of_structure', {})
    liquidity = analysis.get('liquidity_zones', {})
    
    # Format signal emoji
    signal_emoji = "🟢" if signal.get('signal') == 'BUY' else "🔴" if signal.get('signal') == 'SELL' else "🟡"
    
    # Format the message
    formatted_msg = f"""
📊 **Phân tích SMC: {symbol} ({timeframe})**

{signal_emoji} **Tín hiệu:** {signal.get('signal', 'NEUTRAL')}
📈 **Độ tin cậy:** {signal.get('confidence', 0)}%

🔲 **Order Blocks:** {order_blocks.get('status', 'N/A')}
⚡ **Fair Value Gaps:** {fvg.get('status', 'N/A')}
📊 **Break of Structure:** {bos.get('status', 'N/A')}
💧 **Liquidity Zones:** {liquidity.get('status', 'N/A')}

⏰ **Cập nhật:** {analysis.get('timestamp', 'N/A')}

⚠️ *Chỉ mang tính chất tham khảo, không phải lời khuyên đầu tư.*
    """
    
    return formatted_msg.strip()

def show_watchlist_menu(query, context):
    """Show watchlist management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Thêm token", callback_data='watchlist_add')],
        [InlineKeyboardButton("📋 Xem danh sách", callback_data='watchlist_view')],
        [InlineKeyboardButton("🗑️ Xóa token", callback_data='watchlist_remove')],
        [InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main')]
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
ℹ️ **Hướng dẫn sử dụng Trading Bot SMC**

**🎯 Tính năng chính:**
• Phân tích SMC (Smart Money Concepts)
• Order Blocks, Fair Value Gaps
• Break of Structure, Liquidity Zones
• Watchlist tự động cập nhật

**📱 Cách sử dụng:**
1️⃣ Chọn token từ menu
2️⃣ Hoặc nhập token tùy chỉnh
3️⃣ Xem kết quả phân tích
4️⃣ Thêm vào watchlist nếu muốn

**⚡ Lệnh nhanh:**
• /start - Hiển thị menu
• /analysis BTC/USDT 4h - Phân tích trực tiếp

**⚠️ Lưu ý:**
Bot chỉ hỗ trợ phân tích, không phải lời khuyên đầu tư.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')