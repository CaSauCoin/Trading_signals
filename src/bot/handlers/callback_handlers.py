# src/bot/handlers/callback_handlers.py
import logging
from telegram import Update, Message
from telegram.ext import CallbackContext
from telegram.error import BadRequest

from src.bot import constants as const
from src.bot import keyboards
from src.bot import formatters
from src.bot.services.scheduler_service import WATCHLIST_LIMIT
from src.bot.utils.state_manager import set_user_state
from src.bot.utils.menu_manager import delete_active_menu, set_active_menu

logger = logging.getLogger(__name__)


def show_watchlist_menu(update: Update, context: CallbackContext):
    """
    Show watchlist management menu. 
    This function can be called from command or callback.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    scheduler_service = context.bot_data['scheduler_service']
    
    watchlist = scheduler_service.get_user_watchlist(user_id)
    current_interval = scheduler_service.get_user_watchlist_subscription(user_id)
    keyboard = keyboards.create_watchlist_menu_keyboard(watchlist, current_interval)
    text = "👁️ **Quản lý Watchlist**\n\nTheo dõi các token yêu thích và nhận thông báo tín hiệu tự động."

    # If from button (callback), edit old message
    if query:
        try:
            query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            set_active_menu(user_id, context, query.message.message_id)
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                logger.error(f"Error editing watchlist menu: {e}")
    # If from typed command (/watchlist), send new message
    else:
        new_msg = update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        delete_active_menu(user_id, context)  # Xóa menu cũ
        set_active_menu(user_id, context, new_msg.message_id)


def handle_copy_signal(query, context: CallbackContext):
    data = query.data
    try:
        _, symbol, timeframe = data.split("_", 2)

        loading_msg = query.message.reply_text("⏳ Đang tính toán Entry/TP/SL mới nhất...", parse_mode='Markdown')

        analysis_service = context.bot_data['analysis_service']
        result = analysis_service.get_analysis_for_symbol(symbol, timeframe)

        if result and not result.get('error'):
            short_msg = formatters.format_short_signal_message(result)
            loading_msg.delete()

            query.message.reply_text(
                f"```\n{short_msg}\n```",
                parse_mode='Markdown',
                reply_to_message_id=query.message.message_id
            )
        else:
            loading_msg.edit_text("❌ Không lấy được dữ liệu thị trường lúc này.")

    except Exception as e:
        logger.error(f"Error handling copy signal: {e}")
        query.message.reply_text("❌ Có lỗi xảy ra khi tạo signal.", parse_mode='Markdown')

# --- Main Router ---
def handle_callback(update: Update, context: CallbackContext):
    """Main router for all callback queries."""
    query = update.callback_query
    if query.data.startswith("sig_"):
        query.answer()  # Xác nhận interaction ngay
        handle_copy_signal(query, context)
        return

    if query.data == "cmd_main_menu":
        query.answer()
        handle_back_to_main(query, context)
        return

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
    # elif action == const.CB_SCANNER_MENU:
    #     handle_scanner_menu(query, context)
    elif action == const.CB_SCANNER_SET:
        timeframe_choice = parts[1]  # ("5m", "15m", "off", ...)
        handle_scanner_set(query, context, timeframe_choice)
    elif action == const.CB_HELP:
        show_help(query, context)
    else:
        query.edit_message_text("⚠️ Feature is under development...")

# --- Detailed Handlers ---

def perform_analysis(message: Message, context: CallbackContext, symbol: str, timeframe: str):
    """Perform analysis and update message."""
    user_id = message.chat.id
    message.edit_text(f"🔄 **Đang phân tích {symbol} {timeframe}...**", parse_mode='Markdown')
    analysis_service = context.bot_data['analysis_service']
    result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
    if result.get('error'):
        message.edit_text(f"❌ **Lỗi Phân tích**\n\n{result.get('message')}", parse_mode='Markdown')
        return
    formatted_result = formatters.format_analysis_result(result)
    keyboard = keyboards.create_analysis_options_keyboard(symbol, timeframe)
    message.edit_text(formatted_result, reply_markup=keyboard, parse_mode='Markdown')
    set_active_menu(user_id, context, message.message_id)

def handle_watchlist_router(update: Update, context: CallbackContext, parts: list):
    """Route watchlist-related actions."""
    query = update.callback_query
    sub_action = parts[1]
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']

    if sub_action == 'menu':
        show_watchlist_menu(update, context)

    elif sub_action == 'view':
        watchlist = scheduler_service.get_user_watchlist(user_id)
        text = f"📋 **Watchlist của bạn ({len(watchlist)}/{WATCHLIST_LIMIT}):**\n\n"
        if not watchlist:
            text += "Watchlist của bạn đang trống."
        else:
            for i, item in enumerate(watchlist, 1):
                text += f"{i}. **{item['symbol']}** (Timeframe: {item['timeframe']})\n"
        
        keyboard = keyboards.create_watchlist_menu_keyboard(watchlist)
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    elif sub_action == 'add_prompt':
        set_user_state(user_id, context, const.STATE_ADD_WATCHLIST)
        text = "➕ **Thêm vào Watchlist**\n\nNhập token và khung thời gian theo định dạng:\n`TOKEN khung_thời_gian`\n\n*Ví dụ:*\n`PEPE 4h`\n`BTC/USDT 1d` \n`PEPE 15m`"
        query.edit_message_text(text, parse_mode='Markdown')
        
    elif sub_action == 'add_direct':
        if len(parts) < 4:
            logger.error(f"Callback 'add_direct' insufficient parameters: {query.data}")
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
        query.edit_message_text("🗑️ Chọn token bạn muốn xóa khỏi watchlist:", reply_markup=keyboard,
                                parse_mode='Markdown')

    elif sub_action == 'remove_confirm':
        if len(parts) < 4:
            query.answer("Watchlist của bạn đang trống!", show_alert=True)
            return
        _, _, symbol, timeframe = parts
        success = scheduler_service.remove_from_watchlist(user_id, symbol, timeframe)
        if success:
            query.answer(f"Đã xóa {symbol} ({timeframe})", show_alert=True)
            show_watchlist_menu(update, context)

    elif sub_action == 'notify_menu':
        handle_watchlist_notify_menu(query, context)

    elif sub_action == 'notify_set':
        if len(parts) < 3:
            logger.error(f"Callback 'notify_set' insufficient parameters: {query.data}")
            return
        choice = parts[2]  # "5m", "15m", "off", v.v...
        handle_watchlist_notify_set(query, context, choice)


def handle_back_to_main(query, context: CallbackContext):
    """Trở về menu chính bằng cách xóa menu hiện tại và gửi một menu mới."""
    user_id = query.from_user.id

    try:
        query.message.delete()
    except BadRequest as e:
        logger.warning(f"Không thể xóa message khi 'back_main': {e}")

    delete_active_menu(user_id, context)
    scheduler_service = context.bot_data['scheduler_service']
    current_sub = scheduler_service.get_user_scanner_subscription(user_id)
    keyboard = keyboards.create_main_menu_keyboard(current_sub)
    new_menu_message = context.bot.send_message(
        chat_id=user_id,
        text=const.WELCOME_TEXT,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

    set_active_menu(user_id, context, new_menu_message.message_id)


def handle_timeframe_selection(query, context, symbol):
    """Show timeframe selection menu."""
    user_id = query.from_user.id
    keyboard = keyboards.create_timeframe_selection_keyboard(symbol)
    query.edit_message_text(f"⏱️ **Choose timeframe for {symbol}:**", reply_markup=keyboard, parse_mode='Markdown')
    set_active_menu(user_id, context, query.message.message_id)

def handle_select_pair(query, context: CallbackContext):
    """Show popular token pairs selection menu."""
    keyboard = keyboards.create_popular_pairs_keyboard()
    query.edit_message_text("🔍 **Choose Popular Token Pair:**", reply_markup=keyboard, parse_mode='Markdown')

def handle_custom_token(query, context: CallbackContext):
    """Request user to enter custom token."""
    user_id = query.from_user.id
    set_user_state(user_id, context, const.STATE_CUSTOM_TOKEN)
    query.edit_message_text(
        "✏️ **Enter Custom Token**\n\nSend the token name you want to analyze (example: BTC, PEPE, SOL/USDT).",
        parse_mode='Markdown'
    )


def handle_scanner_menu(query, context: CallbackContext):
    """Hiển thị menu lựa chọn timeframe cho market scanner."""
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']
    current_sub = scheduler_service.get_user_scanner_subscription(user_id)

    keyboard = keyboards.create_scanner_menu_keyboard(current_sub)
    text = "🔔 **Cài đặt Thông báo Market Scan**\n\nChọn khung thời gian bạn muốn nhận thông báo. Bot sẽ quét thị trường định kỳ theo khung thời gian này."
    query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


def handle_scanner_set(query, context: CallbackContext, choice: str):
    """Lưu lựa chọn timeframe của người dùng."""
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']

    new_sub = None
    alert_text = ""

    if choice == "off":
        scheduler_service.remove_scanner_subscriber(user_id)
        new_sub = None
        alert_text = "Đã tắt thông báo Market Scan."
    else:
        # choice là "5m", "15m", ...
        scheduler_service.add_scanner_subscriber(user_id, choice)
        new_sub = choice
        alert_text = f"Đã bật thông báo Market Scan cho khung {choice}."

    query.answer(alert_text, show_alert=True)

    keyboard = keyboards.create_scanner_menu_keyboard(new_sub)
    text = "🔔 **Cài đặt Thông báo Market Scan**\n\nChọn khung thời gian bạn muốn nhận thông báo. Bot sẽ quét thị trường định kỳ theo khung thời gian này."
    try:
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"Error updating scanner menu: {e}")


def handle_watchlist_notify_menu(query, context: CallbackContext):
    """Hiển thị menu cài đặt tần suất thông báo watchlist."""
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']
    current_interval = scheduler_service.get_user_watchlist_subscription(user_id)

    keyboard = keyboards.create_watchlist_notify_menu_keyboard(current_interval)
    text = "🔔 **Cài đặt Thông báo Watchlist**\n\nChọn tần suất bạn muốn bot kiểm tra watchlist của bạn.\n(Mặc định: Tắt)"
    try:
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"Error updating watchlist notify menu: {e}")


def handle_watchlist_notify_set(query, context: CallbackContext, choice: str):
    """Lưu lựa chọn tần suất thông báo watchlist của người dùng."""
    user_id = query.from_user.id
    scheduler_service = context.bot_data['scheduler_service']

    new_interval = None
    alert_text = ""

    if choice == "off":
        scheduler_service.remove_watchlist_subscription(user_id)
        new_interval = None
        alert_text = "Đã tắt thông báo Watchlist."
    else:
        scheduler_service.set_watchlist_subscription(user_id, choice)
        new_interval = choice
        alert_text = f"Đã bật thông báo Watchlist mỗi {choice}."

    query.answer(alert_text, show_alert=True)

    keyboard = keyboards.create_watchlist_notify_menu_keyboard(new_interval)
    text = "🔔 **Cài đặt Thông báo Watchlist**\n\nChọn tần suất bạn muốn bot kiểm tra watchlist của bạn."
    try:
        query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"Error updating watchlist notify set: {e}")

def show_help(query, context: CallbackContext):
    """Show help message."""
    keyboard = keyboards.create_back_to_main_keyboard()
    query.edit_message_text(const.HELP_TEXT, reply_markup=keyboard, parse_mode='Markdown')