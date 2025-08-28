# src/bot/handlers/command_handlers.py
from telegram import Update
from telegram.ext import CallbackContext
from src.bot import constants as const
from src.bot import keyboards
from src.bot.utils.state_manager import reset_user_state
from src.bot.formatters import format_analysis_result
from .callback_handlers import show_watchlist_menu

def start_command(update: Update, context: CallbackContext):
    """Gửi tin nhắn chào mừng và menu chính."""
    user_id = update.effective_user.id
    reset_user_state(user_id, context)
    
    reply_markup = keyboards.create_main_menu_keyboard()
    update.message.reply_text(const.WELCOME_TEXT, reply_markup=reply_markup, parse_mode='Markdown')

def analysis_command(update: Update, context: CallbackContext):
    """Xử lý lệnh /analysis <SYMBOL> <TIMEFRAME>."""
    if not context.args or len(context.args) < 1:
        usage_text = "📖 **Cách dùng:** `/analysis BTC/USDT 4h`"
        update.message.reply_text(usage_text, parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else '4h'
    
    loading_msg = update.message.reply_text(f"🔄 Đang phân tích {symbol} {timeframe}...", parse_mode='Markdown')
    
    analysis_service = context.bot_data['analysis_service']
    result = analysis_service.get_analysis_for_symbol(symbol, timeframe)
    
    if result.get('error'):
        error_message = f"❌ **Lỗi phân tích**\n\n{result.get('message')}"
        loading_msg.edit_text(error_message, parse_mode='Markdown')
    else:
        formatted_result = format_analysis_result(result)
        keyboard = keyboards.create_analysis_options_keyboard(symbol, timeframe)
        loading_msg.edit_text(formatted_result, reply_markup=keyboard, parse_mode='Markdown')

def watchlist_command(update: Update, context: CallbackContext):
    """Hiển thị menu watchlist khi người dùng gõ lệnh."""
    show_watchlist_menu(update, context)

