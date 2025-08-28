# src/bot/handlers/callback_handlers.py
import logging
from telegram import Update, Message
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from src.bot import constants as const
from src.bot import keyboards
from src.bot import formatters
from src.bot.utils.state_manager import set_user_state

logger = logging.getLogger(__name__)

# --- Reusable Function ---
def show_watchlist_menu(update: Update, context: CallbackContext):
    """
    Hiển thị menu quản lý watchlist. 
    Hàm này có thể được gọi từ command hoặc callback.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    watchlist = scheduler_service.get_user_watchlist(user_id)
    keyboard = keyboards.create_watchlist_menu_keyboard(watchlist)
    text = "👁️ **Quản lý Watchlist**\n\nTheo dõi các token yêu thích và nhận thông báo tín hiệu tự động."
    
    # Nếu là từ nút bấm (callback), sửa tin nhắn cũ
    if query:
        try:
            query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Lỗi khi sửa menu watchlist: {e}")
    # Nếu là từ lệnh gõ (/watchlist), gửi tin nhắn mới
    else:
        update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

# --- Main Router ---
def handle_callback(update: Update, context: CallbackContext):
    """Bộ định tuyến chính cho tất cả các callback query."""
    query = update.callback_query
    query.answer()
    
    parts = query.data.split(':', 3)
    action = parts[0]
    
    if action == const.CB_ANALYZE or action == const.CB_REFRESH:
        _, symbol, timeframe = parts
        perform_analysis(query.message, context, symbol, timeframe)
    elif action == const.CB_TIMEFRAME:
        _, symbol = parts
        handle_timeframe_selection(query, context, symbol)
    elif action == const.CB_WATCHLIST:
        handle_watchlist_router(update, context, parts)
    elif action == const.CB_BACK_MAIN:
        handle_back_to_main(query, context)
    elif action == const.CB_SELECT_PAIR:
        handle_select_pair(query, context)
    elif action == const.CB_CUSTOM_TOKEN:
        handle_custom_token(query, context)
    elif action == const.CB_HELP:
        show_help(query, context)
    else:
        query.edit_message_text("⚠️ Tính năng đang được phát triển...")

# --- Detailed Handlers ---

def perform_analysis(message: Message, context: CallbackContext, symbol: str, timeframe: str):
    """Thực hiện phân tích và cập nhật tin nhắn."""
    message.edit_text(f"🔄 **Đang phân tích {symbol} {timeframe}...**", parse_mode='Markdown')
    analysis_service = context.bot_data['analysis_service']
    result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
    if result.get('error'):
        message.edit_text(f"❌ **Lỗi phân tích**\n\n{result.get('message')}", parse_mode='Markdown')
        return
    formatted_result = formatters.format_analysis_result(result)
    keyboard = keyboards.create_analysis_options_keyboard(symbol, timeframe)
    message.edit_text(formatted_result, reply_markup=keyboard, parse_mode='Markdown')

def handle_watchlist_router(update: Update, context: CallbackContext, parts: list):
    """Định tuyến các hành động liên quan đến watchlist."""
    query = update.callback_query
    sub_action = parts[1]
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']

    if sub_action == 'menu':
        show_watchlist_menu(update, context)

    elif sub_action == 'view':
        watchlist = scheduler_service.get_user_watchlist(user_id)
        text = f"📋 **Watchlist của bạn ({len(watchlist)}/10):**\n\n"
        if not watchlist:
            text += "Watchlist của bạn đang trống."
        else:
            for i, item in enumerate(watchlist, 1):
                text += f"{i}. **{item['symbol']}** (Khung: {item['timeframe']})\n"
        
        keyboard = keyboards.create_watchlist_menu_keyboard(watchlist)
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    elif sub_action == 'add_prompt':
        set_user_state(user_id, context, const.STATE_ADD_WATCHLIST)
        text = "➕ **Thêm vào Watchlist**\n\nNhập token và khung thời gian theo định dạng:\n`TOKEN timeframe`\n\n*Ví dụ:*\n`PEPE 4h`\n`BTC/USDT 1d`"
        query.edit_message_text(text, parse_mode='Markdown')
        
    elif sub_action == 'add_direct':
        if len(parts) < 4:
            logger.error(f"Callback 'add_direct' không đủ tham số: {query.data}")
            return
        _, _, symbol, timeframe = parts
        result = scheduler_service.add_to_watchlist(user_id, symbol, timeframe)
        query.answer(result['message'], show_alert=True)
        if result['success']:
            keyboard = keyboards.create_post_add_watchlist_keyboard()
            text = f"✅ **Thành công!**\n\n{result['message']}\n\nBạn muốn làm gì tiếp theo?"
            query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    elif sub_action == 'remove_menu':
        watchlist = scheduler_service.get_user_watchlist(user_id)
        if not watchlist:
            query.answer("Watchlist của bạn đang trống!", show_alert=True)
            return
        keyboard = keyboards.create_remove_token_keyboard(watchlist)
        query.edit_message_text("🗑️ Chọn token bạn muốn xóa khỏi watchlist:", reply_markup=keyboard, parse_mode='Markdown')
        
    elif sub_action == 'remove_confirm':
        if len(parts) < 4:
            logger.error(f"Callback 'remove_confirm' không đủ tham số: {query.data}")
            return
        _, _, symbol, timeframe = parts
        success = scheduler_service.remove_from_watchlist(user_id, symbol, timeframe)
        if success:
            query.answer(f"Đã xóa {symbol} ({timeframe})", show_alert=True)
            show_watchlist_menu(update, context)
            
def handle_back_to_main(query, context: CallbackContext):
    """Quay về menu chính."""
    keyboard = keyboards.create_main_menu_keyboard()
    try:
        query.edit_message_text(const.WELCOME_TEXT, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Lỗi BadRequest không xác định: {e}")

def handle_timeframe_selection(query, context, symbol):
    """Hiển thị menu chọn khung thời gian."""
    keyboard = keyboards.create_timeframe_selection_keyboard(symbol)
    query.edit_message_text(f"⏱️ **Chọn khung thời gian cho {symbol}:**", reply_markup=keyboard, parse_mode='Markdown')
    
def handle_select_pair(query, context: CallbackContext):
    """Hiển thị menu chọn cặp token phổ biến."""
    keyboard = keyboards.create_popular_pairs_keyboard()
    query.edit_message_text("🔍 **Chọn cặp Token phổ biến:**", reply_markup=keyboard, parse_mode='Markdown')

def handle_custom_token(query, context: CallbackContext):
    """Yêu cầu người dùng nhập token tùy chỉnh."""
    user_id = query.from_user.id
    set_user_state(user_id, context, const.STATE_CUSTOM_TOKEN)
    query.edit_message_text(
        "✏️ **Nhập Token tùy chỉnh**\n\nHãy gửi tên token bạn muốn phân tích (ví dụ: BTC, PEPE, SOL/USDT).",
        parse_mode='Markdown'
    )

def show_help(query, context: CallbackContext):
    """Hiển thị tin nhắn hướng dẫn."""
    keyboard = keyboards.create_back_to_main_keyboard()
    query.edit_message_text(const.HELP_TEXT, reply_markup=keyboard, parse_mode='Markdown')