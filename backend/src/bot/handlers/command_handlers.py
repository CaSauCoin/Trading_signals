from telegram import Update
from telegram.ext import CallbackContext
from src.bot import constants as const
from src.bot import keyboards
from src.bot.utils.state_manager import reset_user_state
from src.bot.formatters import format_analysis_result
from .callback_handlers import show_watchlist_menu, perform_analysis

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
    if '/' not in symbol:
        symbol += "/USDT"
    timeframe = context.args[1].lower() if len(context.args) > 1 else '4h'
    
    loading_msg = update.message.reply_text(f"🔄 Đang phân tích {symbol} {timeframe}...", parse_mode='Markdown')
    perform_analysis(loading_msg, context, symbol, timeframe)

def watchlist_command(update: Update, context: CallbackContext):
    """Hiển thị menu watchlist khi người dùng gõ lệnh."""
    show_watchlist_menu(update, context)