import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import Conflict, TimedOut, NetworkError
from AdvancedSMC import AdvancedSMC
import json
import os
import time
import signal
import sys
import re
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Cấu hình logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, token):
        self.token = token
        self.smc_analyzer = AdvancedSMC()
        self.application = None
        self.is_running = False
        # State management
        self.user_states = {}
        
        # Watchlist storage - file-based persistence
        self.watchlist_file = "user_watchlists.json"
        self.user_watchlists = self.load_watchlists()
        
        # Scheduler for auto updates
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.send_watchlist_updates,
            IntervalTrigger(hours=1),
            id='watchlist_updates',
            max_instances=1
        )
        
    def load_watchlists(self):
        """Load watchlists from file"""
        try:
            if os.path.exists(self.watchlist_file):
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading watchlists: {e}")
        return {}
    
    def save_watchlists(self):
        """Save watchlists to file"""
        try:
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_watchlists, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving watchlists: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping bot...")
        self.is_running = False
        if self.scheduler.running:
            self.scheduler.shutdown()
        if self.application:
            asyncio.create_task(self.application.stop())
        sys.exit(0)
        
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors globally"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Handle specific errors
        if isinstance(context.error, Conflict):
            logger.error("Bot conflict detected - another instance might be running")
            await asyncio.sleep(10)
        elif isinstance(context.error, (TimedOut, NetworkError)):
            logger.error("Network error, retrying...")
            await asyncio.sleep(5)
        
        # Try to inform user about the error
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ Đã xảy ra lỗi. Vui lòng thử lại sau."
                )
            except Exception as e:
                logger.error(f"Could not send error message to user: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho command /start"""
        try:
            # Reset user state
            user_id = update.effective_user.id
            self.user_states[user_id] = {"waiting_for": None}
            
            keyboard = [
                [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='analyze_BTC/USDT')],
                [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='analyze_ETH/USDT')],
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
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại /start")

    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho tin nhắn text - xử lý custom token input"""
        user_id = update.effective_user.id
        user_state = self.user_states.get(user_id, {})
        
        if user_state.get("waiting_for") == "custom_token":
            await self.process_custom_token(update, context)
        elif user_state.get("waiting_for") == "watchlist_token":
            await self.process_watchlist_token(update, context)
        else:
            # Nếu không trong state đặc biệt, có thể là lệnh trực tiếp
            text = update.message.text.upper().strip()
            
            # Kiểm tra format TOKEN/USDT hoặc TOKEN
            if re.match(r'^[A-Z0-9]+(/USDT)?$', text):
                if not text.endswith('/USDT'):
                    text += '/USDT'
                await self.analyze_custom_token(update, text)
            else:
                await update.message.reply_text(
                    "❓ Tôi không hiểu lệnh này.\n"
                    "Gửi /start để xem menu hoặc gửi tên token (VD: BTC hoặc BTC/USDT)"
                )

    # --- WATCHLIST FUNCTIONS ---
    
    async def show_watchlist_menu(self, query):
        """Hiển thị menu watchlist"""
        user_id = str(query.from_user.id)
        user_watchlist = self.user_watchlists.get(user_id, [])
        
        keyboard = []
        
        if len(user_watchlist) < 5:
            keyboard.append([InlineKeyboardButton("➕ Thêm token theo dõi", callback_data='add_to_watchlist')])
        
        if user_watchlist:
            keyboard.append([InlineKeyboardButton("📋 Xem danh sách theo dõi", callback_data='view_watchlist')])
            keyboard.append([InlineKeyboardButton("🗑️ Xóa token", callback_data='remove_from_watchlist')])
            keyboard.append([InlineKeyboardButton("🔄 Cập nhật ngay", callback_data='update_watchlist_now')])
        
        keyboard.append([InlineKeyboardButton("🏠 Quay lại Menu", callback_data='start')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        watchlist_info = f"**📊 DANH SÁCH THEO DÕI**\n\n"
        watchlist_info += f"👁️ **Đang theo dõi:** {len(user_watchlist)}/5 tokens\n"
        watchlist_info += f"⏱️ **Cập nhật:** Mỗi giờ tự động\n\n"
        
        if user_watchlist:
            watchlist_info += "**Tokens đang theo dõi:**\n"
            for i, item in enumerate(user_watchlist, 1):
                watchlist_info += f"{i}. {item['symbol']} ({item['timeframe']})\n"
        else:
            watchlist_info += "📝 Chưa có token nào trong danh sách.\n"
            watchlist_info += "Nhấn ➕ để thêm token đầu tiên!"
        
        await query.edit_message_text(watchlist_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_to_watchlist_step1(self, query):
        """Bước 1: Nhập token để thêm vào watchlist"""
        user_id = query.from_user.id
        self.user_states[user_id] = {"waiting_for": "watchlist_token"}
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        instruction_text = """
➕ **THÊM TOKEN VÀO WATCHLIST**

📝 **Nhập tên token:**
• Chỉ tên token: `BTC`, `PEPE`, `DOGE`
• Hoặc full pair: `BTC/USDT`, `PEPE/USDT`

💡 **Ví dụ:**
• `PEPE` → PEPE/USDT
• `WLD/USDT` → WLD/USDT
• `1000SATS` → 1000SATS/USDT

⚠️ **Giới hạn:** Tối đa 5 tokens

**Nhập tên token bây giờ:**
        """
        
        await query.edit_message_text(
            instruction_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def process_watchlist_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý token được nhập cho watchlist"""
        user_id = str(update.effective_user.id)
        token_input = update.message.text.upper().strip()
        
        # Reset state
        self.user_states[int(user_id)] = {"waiting_for": None}
        
        # Validate và format token
        if re.match(r'^[A-Z0-9]+$', token_input):
            symbol = f"{token_input}/USDT"
        elif re.match(r'^[A-Z0-9]+/USDT$', token_input):
            symbol = token_input
        else:
            await update.message.reply_text(
                "❌ **Format token không hợp lệ!**\n\n"
                "✅ **Ví dụ hợp lệ:** BTC, PEPE, BTC/USDT\n\n"
                "Vui lòng thử lại hoặc /start để quay về menu.",
                parse_mode='Markdown'
            )
            return
        
        # Kiểm tra giới hạn
        user_watchlist = self.user_watchlists.get(user_id, [])
        if len(user_watchlist) >= 5:
            await update.message.reply_text(
                "❌ **Đã đạt giới hạn!**\n\n"
                "Bạn chỉ có thể theo dõi tối đa 5 tokens.\n"
                "Xóa token cũ để thêm token mới.",
                parse_mode='Markdown'
            )
            return
        
        # Kiểm tra token đã có trong list chưa
        if any(item['symbol'] == symbol for item in user_watchlist):
            await update.message.reply_text(
                f"⚠️ **Token {symbol} đã có trong danh sách!**\n\n"
                "Chọn token khác hoặc /start để quay về menu.",
                parse_mode='Markdown'
            )
            return
        
        # Validate token trên Binance
        if not await self.validate_binance_symbol(symbol):
            await update.message.reply_text(
                f"❌ **Token {symbol} không tồn tại trên Binance!**\n\n"
                "Vui lòng kiểm tra lại tên token.",
                parse_mode='Markdown'
            )
            return
        
        # Hiển thị keyboard chọn timeframe
        await self.add_to_watchlist_step2(update, symbol)

    async def add_to_watchlist_step2(self, update, symbol):
        """Bước 2: Chọn timeframe cho token"""
        keyboard = [
            [InlineKeyboardButton("📊 15m", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_15m'),
             InlineKeyboardButton("📊 1h", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_1h'),
             InlineKeyboardButton("📊 4h", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_4h')],
            [InlineKeyboardButton("📊 1d", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_1d'),
             InlineKeyboardButton("📊 3d", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_3d'),
             InlineKeyboardButton("📊 1w", callback_data=f'watchlist_add_{symbol.replace("/", "_")}_1w')],
            [InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Token {symbol} hợp lệ!**\n\n"
            f"📊 **Chọn timeframe để theo dõi:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def finalize_add_to_watchlist(self, query, symbol, timeframe):
        """Hoàn tất thêm token vào watchlist"""
        user_id = str(query.from_user.id)
        
        # Initialize user watchlist if not exists
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = []
        
        # Add token
        self.user_watchlists[user_id].append({
            'symbol': symbol,
            'timeframe': timeframe,
            'added_at': datetime.now().isoformat()
        })
        
        # Save to file
        self.save_watchlists()
        
        await query.edit_message_text(
            f"✅ **Đã thêm thành công!**\n\n"
            f"📊 **Token:** {symbol}\n"
            f"⏱️ **Timeframe:** {timeframe}\n"
            f"🔔 **Cập nhật:** Mỗi giờ tự động\n\n"
            f"👁️ **Theo dõi:** {len(self.user_watchlists[user_id])}/5 tokens",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Xem watchlist", callback_data='view_watchlist'),
                InlineKeyboardButton("🏠 Menu", callback_data='start')
            ]]),
            parse_mode='Markdown'
        )

    async def view_watchlist(self, query):
        """Xem danh sách theo dõi chi tiết"""
        user_id = str(query.from_user.id)
        user_watchlist = self.user_watchlists.get(user_id, [])
        
        if not user_watchlist:
            await query.edit_message_text(
                "📝 **Danh sách trống!**\n\n"
                "Bạn chưa thêm token nào vào watchlist.\n"
                "Nhấn ➕ để thêm token đầu tiên!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Thêm token", callback_data='add_to_watchlist'),
                    InlineKeyboardButton("🏠 Menu", callback_data='start')
                ]]),
                parse_mode='Markdown'
            )
            return
        
        message = "📋 **DANH SÁCH THEO DÕI**\n\n"
        
        for i, item in enumerate(user_watchlist, 1):
            added_date = datetime.fromisoformat(item['added_at']).strftime('%d/%m/%Y')
            message += f"{i}. **{item['symbol']}** ({item['timeframe']})\n"
            message += f"   📅 Thêm: {added_date}\n\n"
        
        message += f"⏱️ **Cập nhật tiếp theo:** "
        next_hour = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        message += next_hour.strftime('%H:%M')
        
        keyboard = [
            [InlineKeyboardButton("🔄 Cập nhật ngay", callback_data='update_watchlist_now')],
            [InlineKeyboardButton("🗑️ Xóa token", callback_data='remove_from_watchlist'),
             InlineKeyboardButton("➕ Thêm token", callback_data='add_to_watchlist')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def remove_from_watchlist_menu(self, query):
        """Menu xóa token khỏi watchlist"""
        user_id = str(query.from_user.id)
        user_watchlist = self.user_watchlists.get(user_id, [])
        
        if not user_watchlist:
            await query.edit_message_text(
                "📝 **Danh sách trống!**\n\nKhông có token nào để xóa.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu chính", callback_data='start')
                ]]),
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for i, item in enumerate(user_watchlist):
            callback_data = f"watchlist_remove_{i}_{item['symbol'].replace('/', '_')}_{item['timeframe']}"
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {item['symbol']} ({item['timeframe']})",
                callback_data=callback_data
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ **CHỌN TOKEN ĐỂ XÓA**\n\n"
            "Nhấn vào token bạn muốn xóa khỏi danh sách theo dõi:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def remove_from_watchlist(self, query, index, symbol, timeframe):
        """Xóa token khỏi watchlist"""
        user_id = str(query.from_user.id)
        
        try:
            index = int(index)
            if user_id in self.user_watchlists and 0 <= index < len(self.user_watchlists[user_id]):
                removed_item = self.user_watchlists[user_id].pop(index)
                self.save_watchlists()
                
                await query.edit_message_text(
                    f"✅ **Đã xóa thành công!**\n\n"
                    f"🗑️ **Token:** {removed_item['symbol']}\n"
                    f"⏱️ **Timeframe:** {removed_item['timeframe']}\n\n"
                    f"👁️ **Còn lại:** {len(self.user_watchlists[user_id])}/5 tokens",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 Xem watchlist", callback_data='view_watchlist'),
                        InlineKeyboardButton("🏠 Menu", callback_data='start')
                    ]]),
                    parse_mode='Markdown'
                )
            else:
                raise IndexError("Invalid index")
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            await query.edit_message_text(
                "❌ **Lỗi khi xóa token!**\n\nVui lòng thử lại.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data='watchlist_menu')
                ]]),
                parse_mode='Markdown'
            )

    async def update_watchlist_now(self, query):
        """Cập nhật watchlist ngay lập tức"""
        user_id = str(query.from_user.id)
        
        await query.edit_message_text("🔄 **Đang cập nhật watchlist...**")
        
        # Gửi update cho user này
        await self.send_watchlist_update_for_user(user_id)
        
        await query.edit_message_text(
            "✅ **Cập nhật hoàn tất!**\n\n"
            "📊 Đã gửi báo cáo phân tích mới nhất.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Xem watchlist", callback_data='view_watchlist'),
                InlineKeyboardButton("🏠 Menu", callback_data='start')
            ]]),
            parse_mode='Markdown'
        )

    async def send_watchlist_updates(self):
        """Gửi cập nhật watchlist cho tất cả users (chạy mỗi giờ)"""
        if not self.application:
            return
            
        logger.info("Starting scheduled watchlist updates...")
        
        for user_id in self.user_watchlists:
            try:
                await self.send_watchlist_update_for_user(user_id)
                await asyncio.sleep(1)  # Tránh spam
            except Exception as e:
                logger.error(f"Error sending update to user {user_id}: {e}")
        
        logger.info("Completed scheduled watchlist updates")

    async def send_watchlist_update_for_user(self, user_id):
        """Gửi cập nhật watchlist cho 1 user cụ thể"""
        user_watchlist = self.user_watchlists.get(user_id, [])
        
        if not user_watchlist:
            return
        
        try:
            message = f"🔔 **WATCHLIST UPDATE** - {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
            
            for i, item in enumerate(user_watchlist, 1):
                try:
                    # Lấy phân tích cho từng token
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.smc_analyzer.get_trading_signals,
                            item['symbol'],
                            item['timeframe']
                        ),
                        timeout=15.0
                    )
                    
                    if result:
                        message += f"**{i}. {item['symbol']} ({item['timeframe']})**\n"
                        message += f"💰 Giá: ${result['current_price']:,.2f}\n"
                        
                        # Price change
                        price_change = result['indicators'].get('price_change_pct', 0)
                        change_emoji = "📈" if price_change > 0 else "📉"
                        message += f"{change_emoji} Thay đổi: {price_change:+.2f}%\n"
                        
                        # RSI
                        rsi = result['indicators'].get('rsi', 50)
                        rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")
                        message += f"📊 RSI: {rsi_emoji} {rsi:.1f}\n"
                        
                        # Latest signals
                        trading_signals = result.get('trading_signals', {})
                        entry_long = trading_signals.get('entry_long', [])
                        entry_short = trading_signals.get('entry_short', [])
                        
                        if entry_long:
                            message += f"🟢 Long Signal: ${entry_long[-1]['price']:,.2f}\n"
                        elif entry_short:
                            message += f"🔴 Short Signal: ${entry_short[-1]['price']:,.2f}\n"
                        else:
                            message += f"⏸️ Không có signal\n"
                        
                        message += "\n"
                    else:
                        message += f"**{i}. {item['symbol']} ({item['timeframe']})**\n"
                        message += f"❌ Không thể lấy dữ liệu\n\n"
                        
                except Exception as e:
                    logger.error(f"Error analyzing {item['symbol']}: {e}")
                    message += f"**{i}. {item['symbol']} ({item['timeframe']})**\n"
                    message += f"⚠️ Lỗi phân tích\n\n"
            
            message += f"⏰ Cập nhật tiếp theo: {(datetime.now() + timedelta(hours=1)).strftime('%H:%M')}"
            
            # Gửi message
            await self.application.bot.send_message(
                chat_id=int(user_id),
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending watchlist update to user {user_id}: {e}")

    # --- EXISTING FUNCTIONS (giữ nguyên) ---
    
    async def process_custom_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý token tùy chỉnh được nhập"""
        user_id = update.effective_user.id
        token_input = update.message.text.upper().strip()
        
        # Reset state
        self.user_states[user_id] = {"waiting_for": None}
        
        # Validate và format token
        if re.match(r'^[A-Z0-9]+$', token_input):
            symbol = f"{token_input}/USDT"
        elif re.match(r'^[A-Z0-9]+/USDT$', token_input):
            symbol = token_input
        else:
            await update.message.reply_text(
                "❌ **Format token không hợp lệ!**\n\n"
                "✅ **Ví dụ hợp lệ:**\n"
                "• BTC\n"
                "• BTC/USDT\n"
                "• PEPE\n"
                "• DOGE/USDT\n\n"
                "Vui lòng thử lại hoặc /start để quay về menu.",
                parse_mode='Markdown'
            )
            return
        
        await self.analyze_custom_token(update, symbol)

    async def analyze_custom_token(self, update, symbol):
        """Phân tích token tùy chỉnh"""
        # Kiểm tra xem symbol có tồn tại trên Binance không
        if not await self.validate_binance_symbol(symbol):
            suggestions = await self.get_similar_tokens(symbol)
            error_msg = f"❌ **Token {symbol} không tồn tại trên Binance!**\n\n"
            
            if suggestions:
                error_msg += "💡 **Có thể bạn muốn tìm:**\n"
                for suggestion in suggestions[:5]:
                    error_msg += f"• {suggestion}\n"
                error_msg += "\n📝 Nhập chính xác tên token hoặc /start để quay về menu."
            else:
                error_msg += "📝 Vui lòng kiểm tra lại tên token hoặc /start để quay về menu."
            
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return
        
        # Hiển thị keyboard timeframes cho token hợp lệ
        keyboard = [
            [InlineKeyboardButton("📊 15m", callback_data=f'tf_{symbol.replace("/", "_")}_15m'),
             InlineKeyboardButton("📊 1h", callback_data=f'tf_{symbol.replace("/", "_")}_1h'),
             InlineKeyboardButton("📊 4h", callback_data=f'tf_{symbol.replace("/", "_")}_4h')],
            [InlineKeyboardButton("📊 1d", callback_data=f'tf_{symbol.replace("/", "_")}_1d'),
             InlineKeyboardButton("📊 3d", callback_data=f'tf_{symbol.replace("/", "_")}_3d'),
             InlineKeyboardButton("📊 1w", callback_data=f'tf_{symbol.replace("/", "_")}_1w')],
            [InlineKeyboardButton("🏠 Menu chính", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Token {symbol} hợp lệ!**\n\n"
            f"📊 Chọn timeframe để phân tích:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def validate_binance_symbol(self, symbol):
        """Kiểm tra symbol có tồn tại trên Binance không"""
        try:
            # Sử dụng SMC analyzer để kiểm tra
            test_result = await asyncio.wait_for(
                asyncio.to_thread(self.smc_analyzer.get_trading_signals, symbol, '1h'),
                timeout=10.0
            )
            return test_result is not None
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False

    async def get_similar_tokens(self, symbol):
        """Tìm các token tương tự"""
        common_tokens = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'XRP/USDT',
            'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LTC/USDT', 'LINK/USDT', 'UNI/USDT',
            'ATOM/USDT', 'MATIC/USDT', 'FTT/USDT', 'NEAR/USDT', 'ALGO/USDT', 'VET/USDT',
            'TRX/USDT', 'FIL/USDT', 'MANA/USDT', 'SAND/USDT', 'CRV/USDT', 'SUSHI/USDT',
            'COMP/USDT', 'MKR/USDT', 'AAVE/USDT', 'SNX/USDT', 'YFI/USDT', 'BAL/USDT',
            'PEPE/USDT', 'SHIB/USDT', 'WLD/USDT', 'SEI/USDT', 'SUI/USDT', 'ARB/USDT',
            'OP/USDT', 'APT/USDT', 'STX/USDT', 'INJ/USDT', 'TIA/USDT', 'JUP/USDT'
        ]
        
        # Tìm tokens có chứa từ khóa
        token_base = symbol.replace('/USDT', '').upper()
        suggestions = []
        
        for token in common_tokens:
            if token_base in token or any(char in token_base for char in token.replace('/USDT', '')):
                suggestions.append(token)
        
        return suggestions[:10]
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho các nút inline với watchlist support"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        try:
            await query.answer()
            
            # Reset user state khi click button
            self.user_states[user_id] = {"waiting_for": None}
            
            # Watchlist handlers
            if query.data == 'watchlist_menu':
                await self.show_watchlist_menu(query)
            elif query.data == 'add_to_watchlist':
                await self.add_to_watchlist_step1(query)
            elif query.data == 'view_watchlist':
                await self.view_watchlist(query)
            elif query.data == 'remove_from_watchlist':
                await self.remove_from_watchlist_menu(query)
            elif query.data == 'update_watchlist_now':
                await self.update_watchlist_now(query)
            elif query.data.startswith('watchlist_add_'):
                # watchlist_add_BTC_USDT_4h
                parts = query.data.replace('watchlist_add_', '').split('_')
                symbol = '_'.join(parts[:-1]).replace('_', '/')
                timeframe = parts[-1]
                await self.finalize_add_to_watchlist(query, symbol, timeframe)
            elif query.data.startswith('watchlist_remove_'):
                # watchlist_remove_0_BTC_USDT_4h
                parts = query.data.replace('watchlist_remove_', '').split('_')
                index = parts[0]
                symbol = '_'.join(parts[1:-1]).replace('_', '/')
                timeframe = parts[-1]
                await self.remove_from_watchlist(query, index, symbol, timeframe)
            
            # Existing handlers
            elif query.data.startswith('analyze_'):
                symbol = query.data.replace('analyze_', '')
                await self.send_analysis(query, symbol, '4h')
            elif query.data == 'select_pair':
                await self.show_pair_selection(query)
            elif query.data == 'custom_token':
                await self.show_custom_token_input(query)
            elif query.data == 'help':
                await self.show_help(query)
            elif query.data == 'start':
                await self.show_main_menu(query)
            elif query.data.startswith('pair_'):
                symbol = query.data.replace('pair_', '')
                await self.send_analysis(query, symbol, '4h')
            elif query.data.startswith('tf_'):
                parts = query.data.replace('tf_', '').split('_')
                if len(parts) >= 2:
                    symbol = '_'.join(parts[:-1]).replace('_', '/')
                    timeframe = parts[-1]
                    await self.send_analysis(query, symbol, timeframe)
                    
        except Exception as e:
            logger.error(f"Error in button_handler: {e}")
            try:
                await query.edit_message_text("❌ Có lỗi xảy ra. Vui lòng thử lại.")
            except:
                pass

    async def show_custom_token_input(self, query):
        """Hiển thị hướng dẫn nhập token tùy chỉnh"""
        user_id = query.from_user.id
        self.user_states[user_id] = {"waiting_for": "custom_token"}
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        instruction_text = """
✏️ **NHẬP TOKEN TÙY CHỈNH**

📝 **Cách nhập:**
• Chỉ tên token: `BTC`, `PEPE`, `DOGE`
• Hoặc full pair: `BTC/USDT`, `PEPE/USDT`

💡 **Ví dụ:**
• `PEPE` → sẽ phân tích PEPE/USDT
• `WLD/USDT` → sẽ phân tích WLD/USDT
• `1000SATS` → sẽ phân tích 1000SATS/USDT

⚠️ **Lưu ý:**
• Chỉ hỗ trợ tokens trên Binance
• Chỉ pair với USDT

**Nhập tên token bây giờ:**
        """
        
        await query.edit_message_text(
            instruction_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def send_analysis(self, query, symbol, timeframe='4h'):
        """Gửi phân tích SMC với error handling improved"""
        try:
            await query.edit_message_text("🔄 Đang phân tích... Vui lòng đợi...")
            
            # Timeout cho việc lấy dữ liệu
            result = await asyncio.wait_for(
                asyncio.to_thread(self.smc_analyzer.get_trading_signals, symbol, timeframe),
                timeout=30.0
            )
            
            if result is None:
                await query.edit_message_text(
                    f"❌ Không thể lấy dữ liệu cho {symbol}.\n"
                    f"Token có thể không tồn tại trên Binance hoặc không có đủ dữ liệu.\n\n"
                    f"Vui lòng thử token khác hoặc /start để quay về menu."
                )
                return
            
            # Format message
            message = self.format_analysis_message(result)
            
            # Create keyboard
            symbol_encoded = symbol.replace('/', '_')
            keyboard = [
                [InlineKeyboardButton("📊 15m", callback_data=f'tf_{symbol_encoded}_15m'),
                 InlineKeyboardButton("📊 1h", callback_data=f'tf_{symbol_encoded}_1h'),
                 InlineKeyboardButton("📊 4h", callback_data=f'tf_{symbol_encoded}_4h')],
                [InlineKeyboardButton("📊 1d", callback_data=f'tf_{symbol_encoded}_1d'),
                 InlineKeyboardButton("📊 3d", callback_data=f'tf_{symbol_encoded}_3d'),
                 InlineKeyboardButton("📊 1w", callback_data=f'tf_{symbol_encoded}_1w')],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f'tf_{symbol_encoded}_{timeframe}'),
                 InlineKeyboardButton("✏️ Token khác", callback_data='custom_token'),
                 InlineKeyboardButton("🏠 Menu", callback_data='start')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message with fallback
            try:
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Markdown parse error: {e}")
                plain_message = message.replace('*', '').replace('_', '')
                await query.edit_message_text(plain_message, reply_markup=reply_markup)
        
        except asyncio.TimeoutError:
            await query.edit_message_text("⏰ Timeout - Phân tích mất quá nhiều thời gian. Vui lòng thử lại.")
        except Exception as e:
            logger.error(f"Error in send_analysis: {e}")
            error_msg = f"❌ Lỗi khi phân tích {symbol}: {str(e)[:100]}..."
            await query.edit_message_text(error_msg)

    def format_analysis_message(self, result):
        """Format kết quả phân tích thành message Telegram với thông tin chi tiết"""
        smc = result['smc_analysis']
        indicators = result['indicators']
        trading_signals = result.get('trading_signals', {})
        # entry = result.get('entry', None)
        # exit = result.get('exit', None)

        # Header
        message = f"📊 *Phân tích {result['symbol']} - {result['timeframe']}*\n\n"
        
        # Price info
        message += f"💰 *Giá hiện tại:* ${result['current_price']:,.2f}\n"
        
        # Indicators
        rsi = indicators.get('rsi', 50)
        rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")
        message += f"📈 *RSI:* {rsi_emoji} {rsi:.1f}\n"
        message += f"📊 *Giá sát:* ${indicators.get('sma_20', 0):,.2f}\n"
        message += f"📉 *Giá dự tốt:* ${indicators.get('ema_20', 0):,.2f}\n\n"
        
        # Price change
        price_change = indicators.get('price_change_pct', 0)
        change_emoji = "📈" if price_change > 0 else "📉"
        message += f"{change_emoji} *Thay đổi:* {price_change:+.2f}%\n\n"
        
        # SMC Analysis - Detailed
        message += "🔍 *ANALYSIS:*\n"
        
        # Order Blocks
        ob_count = len(smc['order_blocks'])
        message += f"📦 *Order Blocks:* {ob_count}\n"
        if ob_count > 0:
            try:
                latest_ob = smc['order_blocks'][-1]
                ob_emoji = "🟢" if latest_ob['type'] == 'bullish_ob' else "🔴"
                ob_type = latest_ob['type'].replace('_', ' ').upper()
                # message += f"   {ob_emoji} Gần nhất: {ob_type}\n"
                
                # Kiểm tra giá trị không phải None
                if latest_ob.get('low') is not None and latest_ob.get('high') is not None:
                    # message += f"   📍 Level: ${latest_ob['low']:,.0f} - ${latest_ob['high']:,.0f}\n"
                    print(f"Order Block: {latest_ob}")  # Debug log
            except (KeyError, TypeError, IndexError):
                print("Dữ liệu OB không đầy đủ")
    
        # Fair Value Gaps
        fvg_count = len(smc['fair_value_gaps'])
        # message += f"🎯 *Fair Value Gaps:* {fvg_count}\n"
        if fvg_count > 0:
            try:
                latest_fvg = smc['fair_value_gaps'][-1]
                fvg_emoji = "🟢" if latest_fvg['type'] == 'bullish_fvg' else "🔴"
                fvg_type = latest_fvg['type'].replace('_', ' ').upper()
                # message += f"   {fvg_emoji} Gần nhất: {fvg_type}\n"
                
                # Kiểm tra giá trị không phải None
                if latest_fvg.get('top') is not None and latest_fvg.get('bottom') is not None:
                    print(f"Fair Value Gap: {latest_fvg}")  # Debug log
                    # message += f"   📍 Gap: ${latest_fvg['bottom']:,.0f} - ${latest_fvg['top']:,.0f}\n"
            except (KeyError, TypeError, IndexError):
                print("Dữ liệu FVG không đầy đủ")
                # message += "   ⚠️ Dữ liệu FVG không đầy đủ\n"
    
        # Break of Structure
        bos_count = len(smc['break_of_structure'])
        message += f"🔄 *Structure:* {bos_count}\n"
        if bos_count > 0:
            try:
                latest_bos = smc['break_of_structure'][-1]
                bos_emoji = "🟢" if latest_bos['type'] == 'bullish_bos' else "🔴"
                bos_type = latest_bos['type'].replace('_', ' ').upper()
                message += f"   {bos_emoji} Gần nhất: {bos_type}\n"
                message += f"   📍 Price: ${latest_bos['price']:,.2f}\n"
            except (KeyError, TypeError, IndexError):
                print("Dữ liệu BOS không đầy đủ")
                # message += "   ⚠️ Dữ liệu BOS không đầy đủ\n"
    
        # Liquidity Zones
        lz_count = len(smc['liquidity_zones'])
        message += f"💧 *Liquidity Zones:* {lz_count}\n"
        if lz_count > 0:
            try:
                latest_lz = smc['liquidity_zones'][-1]
                lz_emoji = "🔵" if latest_lz['type'] == 'buy_side_liquidity' else "🟠"
                lz_type = latest_lz['type'].replace('_', ' ').title()
                message += f"   {lz_emoji} Gần nhất: {lz_type}\n"
                message += f"   📍 Level: ${latest_lz['price']:,.2f}\n"
            except (KeyError, TypeError, IndexError):
                print("Dữ liệu LZ không đầy đủ")

        message += "\n"
        
        # Trading Signals
        if trading_signals:
            message += "🔔 *TRADING SIGNALS:*\n"
            
            # Entry signals
            entry_long = trading_signals.get('entry_long', [])
            entry_short = trading_signals.get('entry_short', [])
            exit_long = trading_signals.get('exit_long', [])
            exit_short = trading_signals.get('exit_short', [])
            
            try:
                if entry_long:
                    latest_long = entry_long[-1]
                    message += f"🟢 *Long Signal:* ${latest_long['price']:,.2f}\n"
                    message += f"   🏷️ Tag: {latest_long.get('tag', 'N/A')}\n"
                
                if entry_short:
                    latest_short = entry_short[-1]
                    message += f"🔴 *Short Signal:* ${latest_short['price']:,.2f}\n"
                    message += f"   🏷️ Tag: {latest_short.get('tag', 'N/A')}\n"
                
                if exit_long:
                    message += f"❌ *Exit Long:* {len(exit_long)} signals\n"
                
                if exit_short:
                    message += f"❌ *Exit Short:* {len(exit_short)} signals\n"
                
                if not any([entry_long, entry_short, exit_long, exit_short]):
                    message += "⏸️ Không có signal nào\n"
                    
            except (KeyError, TypeError, IndexError):
                message += "⚠️ Dữ liệu signals không đầy đủ\n"
            
            message += "\n"
        
        # Trading suggestion (advanced)
        try:
            suggestion = self.get_trading_suggestion(smc, indicators, trading_signals)
            message += f"💡 *Gợi ý Trading:*\n{suggestion}\n\n"
        except Exception as e:
            message += "💡 *Gợi ý Trading:* Không thể tạo gợi ý\n\n"
        
        # Timestamp
        try:
            from datetime import datetime
            timestamp = datetime.fromtimestamp(result['timestamp'])
            message += f"🕐 *Cập nhật:* {timestamp.strftime('%H:%M:%S %d/%m/%Y')}"
        except:
            message += f"🕐 *Cập nhật:* {result.get('timestamp', 'N/A')}"
        
        return message
    
    def get_trading_suggestion(self, smc, indicators, trading_signals):
        """Đưa ra gợi ý trading chi tiết - với error handling"""
        suggestions = []
        
        try:
            rsi = indicators.get('rsi', 50)
            
            # RSI analysis
            if rsi > 70:
                suggestions.append("⚠️ Cân nhắc bán")
            elif rsi < 30:
                suggestions.append("🚀 Cân nhắc mua")

            # SMC analysis
            if smc.get('break_of_structure') and len(smc['break_of_structure']) > 0:
                latest_bos = smc['break_of_structure'][-1]
                if latest_bos.get('type') == 'bullish_bos':
                    suggestions.append("📈 Xu hướng tăng")
                elif latest_bos.get('type') == 'bearish_bos':
                    suggestions.append("📉 Xu hướng giảm")
            
            # FVG analysis
            if smc.get('fair_value_gaps'):
                fvg_count = len([fvg for fvg in smc['fair_value_gaps'] if not fvg.get('filled', True)])
                if fvg_count > 2:
                    suggestions.append(f"🎯 Chờ retest")
            
            # Trading signals
            if trading_signals:
                entry_long = trading_signals.get('entry_long', [])
                entry_short = trading_signals.get('entry_short', [])
                
                if entry_long:
                    suggestions.append("🟢 Signal Long xuất hiện")
                if entry_short:
                    suggestions.append("🔴 Signal Short xuất hiện")
            
            if not suggestions:
                suggestions.append("⏸️ Thị trường sideways - Chờ breakout")
                
        except Exception as e:
            logger.error(f"Error in get_trading_suggestion: {e}")
            suggestions.append("⚠️ Không thể phân tích - Kiểm tra lại dữ liệu")
        
        return "\n".join([f"• {s}" for s in suggestions])

    async def show_main_menu(self, query):
        """Hiển thị menu chính"""
        keyboard = [
            [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='analyze_BTC/USDT')],
            [InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='analyze_ETH/USDT')],
            [InlineKeyboardButton("🔍 Chọn cặp có sẵn", callback_data='select_pair')],
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
        
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_pair_selection(self, query):
        """Hiển thị menu chọn cặp trading với nhiều tùy chọn hơn"""
        keyboard = [
            [InlineKeyboardButton("₿ BTC/USDT", callback_data='pair_BTC/USDT'),
             InlineKeyboardButton("Ξ ETH/USDT", callback_data='pair_ETH/USDT')],
            [InlineKeyboardButton("🟡 BNB/USDT", callback_data='pair_BNB/USDT'),
             InlineKeyboardButton("🔵 WLD/USDT", callback_data='pair_WLD/USDT')],
            [InlineKeyboardButton("🟣 SOL/USDT", callback_data='pair_SOL/USDT'),
             InlineKeyboardButton("🔴 SEI/USDT", callback_data='pair_SEI/USDT')],
            [InlineKeyboardButton("🟠 BNB/USDT", callback_data='pair_BNB/USDT'),
             InlineKeyboardButton("🟢 AGT/USDT", callback_data='pair_AGT/USDT')],
            [InlineKeyboardButton("🟢 PEPE/USDT ", callback_data='pair_PEPE/USDT'),
             InlineKeyboardButton("🟢 SUI/USDT", callback_data='pair_SUI/USDT')],
            [InlineKeyboardButton("🏠 Quay lại", callback_data='start')],

        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 **Chọn cặp trading để phân tích:**", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_help(self, query):
        """Hiển thị hướng dẫn sử dụng"""
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

🔔 **Trading Signals:**
• Entry Long: BOS tăng + POI tăng + Swept
• Entry Short: BOS giảm + POI giảm + Swept
• Exit: CHoCH ngược chiều

⚠️ **Lưu ý:** 
Đây là công cụ hỗ trợ phân tích, không phải lời khuyên đầu tư. Luôn quản lý rủi ro và DYOR.
        """
        
        keyboard = [[InlineKeyboardButton("🏠 Quay lại Menu", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho command /analysis"""
        if context.args:
            symbol = context.args[0].upper()
            timeframe = context.args[1] if len(context.args) > 1 else '4h'
            
            await update.message.reply_text(f"🔄 Đang phân tích {symbol} {timeframe}...")
            
            result = self.smc_analyzer.get_trading_signals(symbol, timeframe)
            if result:
                message = self.format_analysis_message(result)
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Không thể phân tích cặp này.")
        else:
            await update.message.reply_text("Cách sử dụng: /analysis BTC/USDT 4h")
    
    def run(self):
        """Chạy bot với scheduler"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Tạo application
            self.application = Application.builder()\
                .token(self.token)\
                .read_timeout(30)\
                .write_timeout(30)\
                .connect_timeout(30)\
                .pool_timeout(30)\
                .build()
            
            # Add handlers
            self.application.add_error_handler(self.error_handler)
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("analysis", self.analysis_command))
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
            
            # Start scheduler
            self.scheduler.start()
            logger.info("📅 Scheduler started - Watchlist updates every hour")
            
            self.is_running = True
            logger.info("🤖 Bot đang khởi động...")
            
            # Run bot
            while self.is_running:
                try:
                    self.application.run_polling(
                        poll_interval=1.0,
                        timeout=30,
                        bootstrap_retries=3,
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                        pool_timeout=30
                    )
                except Conflict as e:
                    logger.error(f"Bot conflict: {e}")
                    time.sleep(30)
                except (TimedOut, NetworkError) as e:
                    logger.error(f"Network error: {e}")
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    time.sleep(15)
                    
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.is_running = False
            if self.scheduler.running:
                self.scheduler.shutdown()
            if self.application:
                try:
                    asyncio.run(self.application.stop())
                except:
                    pass
            logger.info("Bot shutdown complete")

if __name__ == "__main__":
    BOT_TOKEN = "7858582538:AAG4gosdOgbe7RsNb9nnYOMQJTohNSGcn6k"
    bot = TradingBot(BOT_TOKEN)
    bot.run()
