import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from AdvancedSMC import AdvancedSMC
import json
import os
import time
from datetime import datetime, timedelta

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, token):
        self.token = token
        self.smc_analyzer = AdvancedSMC()
        self.application = None
        # tracked_pairs: { chat_id: { symbol: {"job": Job, "pinned_message_id": int or None, "timeframe": str, "created_at":timestamp} } }
        self.tracked_pairs = {}
        self.MAX_TRACKS_PER_CHAT = 3

    def format_price(self, price: float) -> str:
        """
        Format giá token:
        - Nếu giá >= 1: hiển thị 2 chữ số thập phân
        - Nếu giá < 1: hiển thị tối đa 8 chữ số thập phân (không mất số 0)
        """
        try:
            if price >= 1:
                return f"{price:,.2f}"   # ví dụ: 63,245.15
            else:
                return f"{price:,.8f}".rstrip('0').rstrip('.')  # ví dụ: 0.00001234
        except Exception:
            return str(price)

    # Helper to build consistent keyboard (includes Track/Stop Track depending on state)
    def build_reply_markup(self, symbol: str, timeframe: str, chat_id: int):
        symbol_encoded = symbol.replace('/', '_')
        is_tracked = (chat_id in self.tracked_pairs and symbol in self.tracked_pairs[chat_id])
        track_button = InlineKeyboardButton(
            "🔔 Stop Tracking" if is_tracked else "🔔 Track",
            callback_data=(f'untrack_{symbol_encoded}' if is_tracked else f'track_{symbol_encoded}_{timeframe}')
        )

        keyboard = [
            [InlineKeyboardButton("📊 15m", callback_data=f'tf_{symbol_encoded}_15m'),
             InlineKeyboardButton("📊 1h", callback_data=f'tf_{symbol_encoded}_1h'),
             InlineKeyboardButton("📊 4h", callback_data=f'tf_{symbol_encoded}_4h')],
            [InlineKeyboardButton("📊 1d", callback_data=f'tf_{symbol_encoded}_1d'),
             InlineKeyboardButton("📊 3d", callback_data=f'tf_{symbol_encoded}_3d'),
             InlineKeyboardButton("📊 1w", callback_data=f'tf_{symbol_encoded}_1w')],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f'tf_{symbol_encoded}_{timeframe}'),
             InlineKeyboardButton("🏠 Menu", callback_data='start')],
            [track_button]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho command /start"""
        keyboard = [
            [InlineKeyboardButton("📊 Phân tích BTC/USDT", callback_data='analyze_BTC/USDT'),
             InlineKeyboardButton("📈 Phân tích ETH/USDT", callback_data='analyze_ETH/USDT')],
            [InlineKeyboardButton("📈 Phân tích BTCDOM/USDT", callback_data='analyze_BTCDOM/USDT'),
             InlineKeyboardButton("📈 Phân tích DOGE/USDT", callback_data='analyze_DOGE/USDT')],
            [InlineKeyboardButton("🔍 Chọn cặp khác", callback_data='select_pair')],
            [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = """
🚀 **Trading Bot SMC!**

Chọn một tùy chọn bên dưới để bắt đầu:
        """

        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler cho các nút inline"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith('analyze_'):
            symbol = query.data.replace('analyze_', '')
            await self.send_analysis(query, symbol, '4h')  # Default timeframe
        elif query.data == 'select_pair':
            await self.show_pair_selection(query)
        elif query.data == 'help':
            await self.show_help(query)
        elif query.data == 'start':
            await self.show_main_menu(query)
        elif query.data.startswith('pair_'):
            symbol = query.data.replace('pair_', '')
            await self.send_analysis(query, symbol, '4h')
        elif query.data.startswith('tf_'):
            # Xử lý timeframe: tf_SYMBOL_TIMEFRAME
            parts = query.data.replace('tf_', '').split('_')
            if len(parts) >= 2:
                symbol = '_'.join(parts[:-1])  # Ghép lại symbol (có thể chứa dấu /)
                symbol = symbol.replace('_', '/')  # Convert back to BTC/USDT format
                timeframe = parts[-1]
                await self.send_analysis(query, symbol, timeframe)
        elif query.data.startswith('track_'):
            # track_SYMBOL_TIMEFRAME
            inner = query.data.replace('track_', '')
            parts = inner.split('_')
            if len(parts) >= 2:
                timeframe = parts[-1]
                symbol = '_'.join(parts[:-1]).replace('_', '/')
                await self._start_tracking_from_callback(query, context, symbol, timeframe)
            else:
                await query.edit_message_text("Format track không hợp lệ.")
        elif query.data.startswith('untrack_'):
            # untrack_SYMBOL
            symbol = query.data.replace('untrack_', '').replace('_', '/')
            await self._stop_tracking_from_callback(query, context, symbol)
        elif query.data == 'input_pair':
            # Set flag to expect next text as pair
            context.user_data['awaiting_pair'] = True
            await query.edit_message_text("Vui lòng gửi cặp theo định dạng `PAIR TIMEFRAME` (ví dụ: `BTC/USDT 4h`). Hoặc chỉ gửi `BTC/USDT` để mặc định 4h.", parse_mode='Markdown')
        else:
            await query.edit_message_text("Chức năng chưa hỗ trợ")

    # === TỰ ĐỘNG THEO DÕI ===
    async def auto_track_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Cách dùng: /autotrack BTC/USDT 4h")
            return

        symbol = context.args[0].upper()
        timeframe = context.args[1] if len(context.args) > 1 else "4h"
        chat_id = update.message.chat_id

        # ensure chat dict
        if chat_id not in self.tracked_pairs:
            self.tracked_pairs[chat_id] = {}

        # enforce max 3
        if symbol not in self.tracked_pairs[chat_id] and len(self.tracked_pairs[chat_id]) >= self.MAX_TRACKS_PER_CHAT:
            await update.message.reply_text(f"⚠️ You already track {self.MAX_TRACKS_PER_CHAT} pairs. Please stop one before adding another.")
            return

        # Nếu đã có job -> hủy trước
        if symbol in self.tracked_pairs[chat_id]:
            try:
                self.tracked_pairs[chat_id][symbol]['job'].schedule_removal()
            except Exception:
                pass

        # Tạo job lặp lại 30 phút (first = 1800 để không duplicate ngay lập tức)
        job = self.application.job_queue.run_repeating(
            self.send_auto_analysis,
            interval=300,  # 30 phút
            first=300,
            chat_id=chat_id,
            name=f"autotrack_{chat_id}_{symbol}",
            data={"symbol": symbol, "timeframe": timeframe}
        )

        # Save without pinned_message_id (will be set if user pins an analysis message)
        self.tracked_pairs[chat_id][symbol] = {"job": job, "pinned_message_id": None, "timeframe": timeframe, "created_at": time.time()}
        await update.message.reply_text(f"✅ Đã bật auto theo dõi {symbol} {timeframe} (30 phút/lần). Lưu ý: để pin và auto-update trên 1 message, hãy nhấn nút 'Track' trên message phân tích tương ứng.")

    async def stop_track_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command /stoptrack SYMBOL"""
        if not context.args:
            await update.message.reply_text("Cách dùng: /stoptrack BTC/USDT")
            return

        symbol = context.args[0].upper()
        chat_id = update.message.chat_id

        if chat_id in self.tracked_pairs and symbol in self.tracked_pairs[chat_id]:
            info = self.tracked_pairs[chat_id].pop(symbol)
            try:
                info['job'].schedule_removal()
            except Exception:
                pass
            # unpin if pinned
            pinned_id = info.get('pinned_message_id')
            if pinned_id:
                try:
                    await self.application.bot.unpin_chat_message(chat_id=chat_id, message_id=pinned_id)
                except Exception as e:
                    logger.warning(f"Cannot unpin message: {e}")
            await update.message.reply_text(f"🛑 Đã tắt auto theo dõi {symbol}.")
        else:
            await update.message.reply_text(f"{symbol} chưa được theo dõi.")

    async def send_auto_analysis(self, context: ContextTypes.DEFAULT_TYPE):
        """Job tự động gửi phân tích - sẽ edit pinned message nếu có, else gửi message mới"""
        job_data = context.job.data or {}
        symbol = job_data.get("symbol")
        timeframe = job_data.get("timeframe", "4h")
        chat_id = context.job.chat_id

        try:
            result = self.smc_analyzer.get_trading_signals(symbol, timeframe)
            if not result:
                await context.bot.send_message(chat_id, f"⚠ Không lấy được dữ liệu cho {symbol}.")
                return

            message_text = self.format_analysis_message(result)
            # build reply_markup
            reply_markup = self.build_reply_markup(symbol, timeframe, chat_id)

            # find tracked info
            chat_tracks = self.tracked_pairs.get(chat_id, {})
            info = chat_tracks.get(symbol)

            # If pinned message exists -> edit it so tracking message doesn't drift
            if info and info.get('pinned_message_id'):
                pinned_id = info.get('pinned_message_id')
                try:
                    # edit pinned message
                    await context.bot.edit_message_text(
                        text=message_text,
                        chat_id=chat_id,
                        message_id=pinned_id,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    # done
                    return
                except Exception as e:
                    logger.warning(f"Failed to edit pinned message {pinned_id} for {symbol} in chat {chat_id}: {e}")
                    # fallback: send a new message and update pinned_message_id if pin successful
            # If pinned missing or edit failed -> send a new message (but we want tracking messages to be pinned by user action)
            sent = await context.bot.send_message(chat_id, message_text, reply_markup=reply_markup, parse_mode='Markdown')
            # If this symbol is tracked in our map but had no pinned_id, do NOT auto-pin here (we rely on user pressing Track on the message).
            # However if info exists and pinned_message_id is None, optionally update pinned_message_id to latest bot message
            # We will NOT auto-pin to avoid permission surprise; user asked pinned message comes from their Track action.
            # If you prefer auto-pin here, uncomment the following block (requires bot can pin messages automatically):
            # try:
            #     await context.bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id, disable_notification=True)
            #     if info is not None:
            #         info['pinned_message_id'] = sent.message_id
            # except Exception as e:
            #     logger.warning(f"Cannot auto-pin message: {e}")
        except Exception as e:
            logger.error(f"Error in auto-track job for {symbol}: {e}")
            try:
                await context.bot.send_message(chat_id, f"❌ Lỗi auto-track {symbol}: {e}")
            except Exception:
                pass

    # gửi phân tích (sửa thêm nút Track/Stop Track)
    async def send_analysis(self, query, symbol, timeframe='4h'):
        """Gửi phân tích SMC cho symbol với timeframe cụ thể"""
        await query.edit_message_text("🔄 Đang phân tích... Vui lòng đợi...")

        try:
            # Lấy phân tích từ SMC
            result = self.smc_analyzer.get_trading_signals(symbol, timeframe)

            if result is None:
                await query.edit_message_text("❌ Không thể lấy dữ liệu. Vui lòng thử lại sau.")
                return

            # Format message với error handling
            try:
                message = self.format_analysis_message(result)
            except Exception as e:
                logger.error(f"Error formatting message: {e}")
                message = f"❌ Lỗi khi format message cho {symbol}\nVui lòng thử lại sau."
                await query.edit_message_text(message)
                return

            # Build reply_markup using helper
            chat_id = query.message.chat_id
            reply_markup = self.build_reply_markup(symbol, timeframe, chat_id)

            # Edit the callback message with the analysis and include Track/Stop button
            try:
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Markdown parse error: {e}")
                # Fallback: gửi message không có markdown
                plain_message = message.replace('*', '').replace('_', '')
                sent = await query.edit_message_text(plain_message, reply_markup=reply_markup)
            # Note: when the user presses the Track button, _start_tracking_from_callback will pin this message and store pinned_message_id
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            error_msg = f"❌ Lỗi khi phân tích {symbol}:\n{str(e)[:100]}..."
            await query.edit_message_text(error_msg)

    def format_analysis_message(self, result):
        """Format kết quả phân tích thành message Telegram với thông tin chi tiết"""
        smc = result['smc_analysis']
        indicators = result['indicators']
        trading_signals = result.get('trading_signals', {})

        # Header
        message = f"📊 *Phân tích {result['symbol']} - {result['timeframe']}*\n\n"

        # Price info
        message += f"💰 *Giá hiện tại:* ${self.format_price(result['current_price'])}\n"

        # Indicators
        rsi = indicators.get('rsi', 50)
        rsi_emoji = "🟢" if rsi < 30 else ("🔴" if rsi > 70 else "🟡")
        message += f"📈 *RSI:* {rsi_emoji} {rsi:.1f}\n"
        message += f"📊 *Giá sát:* ${self.format_price(indicators.get('sma_20', 0))}\n"
        message += f"📉 *Giá dự tốt:* ${self.format_price(indicators.get('ema_20', 0))}\n\n"

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
                if latest_ob.get('low') is not None and latest_ob.get('high') is not None:
                    message += f"   {ob_emoji} Latest OB: ${self.format_price(latest_ob['low'])} - ${self.format_price(latest_ob['high'])}\n"
            except Exception:
                print("Dữ liệu OB không đầy đủ")

        # Fair Value Gaps
        fvg_count = len(smc['fair_value_gaps'])
        if fvg_count > 0:
            try:
                latest_fvg = smc['fair_value_gaps'][-1]
                fvg_emoji = "🟢" if latest_fvg['type'] == 'bullish_fvg' else "🔴"
                if latest_fvg.get('top') is not None and latest_fvg.get('bottom') is not None:
                    message += f"🎯 Latest FVG: ${self.format_price(latest_fvg['bottom'])} - ${self.format_price(latest_fvg['top'])}\n"
            except Exception:
                print("Dữ liệu FVG không đầy đủ")

        # Break of Structure
        bos_count = len(smc['break_of_structure'])
        message += f"🔄 *Structure:* {bos_count}\n"
        if bos_count > 0:
            try:
                latest_bos = smc['break_of_structure'][-1]
                bos_emoji = "🟢" if latest_bos['type'] == 'bullish_bos' else "🔴"
                bos_type = latest_bos['type'].replace('_', ' ').upper()
                message += f"   {bos_emoji} Gần nhất: {bos_type}\n"
                message += f"    Price: ${self.format_price(latest_bos['price'])}\n"
            except Exception:
                print("Dữ liệu BOS không đầy đủ")

        # Liquidity Zones
        lz_count = len(smc['liquidity_zones'])
        message += f"💧 *Liquidity Zones:* {lz_count}\n"
        if lz_count > 0:
            try:
                latest_lz = smc['liquidity_zones'][-1]
                lz_emoji = "🔵" if latest_lz['type'] == 'buy_side_liquidity' else "🟠"
                message += f"   {lz_emoji} Gần nhất: {latest_lz.get('type','N/A')}\n"
                if latest_lz.get('price') is not None:
                    message += f"    Level: ${self.format_price(latest_lz['price'])}\n"
            except Exception:
                print("Dữ liệu LZ không đầy đủ")

        message += "\n"

        # Trading Signals
        if trading_signals:
            message += "🔔 *TRADING SIGNALS:*\n"
            entry_long = trading_signals.get('entry_long', [])
            entry_short = trading_signals.get('entry_short', [])
            exit_long = trading_signals.get('exit_long', [])
            exit_short = trading_signals.get('exit_short', [])

            try:
                if entry_long:
                    latest_long = entry_long[-1]
                    message += f"🟢 *Long Signal:* ${self.format_price(latest_long['price'])}\n"
                    #message += f"    Tag: {latest_long.get('tag', 'N/A')}\n"

                if entry_short:
                    latest_short = entry_short[-1]
                    message += f"🔴 *Short Signal:* ${self.format_price(latest_short['price'])}\n"
                   # message += f"    Tag: {latest_short.get('tag', 'N/A')}\n"

                if exit_long:
                    message += f"❌ *Exit Long:* {len(exit_long)} signals\n"

                if exit_short:
                    message += f"❌ *Exit Short:* {len(exit_short)} signals\n"

                if not any([entry_long, entry_short, exit_long, exit_short]):
                    message += "⏸️ Không có signal nào\n"

            except Exception:
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
            [InlineKeyboardButton("🔍 Chọn cặp khác", callback_data='select_pair')],
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
            [InlineKeyboardButton("BNB/USDT", callback_data='pair_BNB/USDT'),
             InlineKeyboardButton("WLD/USDT", callback_data='pair_WLD/USDT')],
            [InlineKeyboardButton("SOL/USDT", callback_data='pair_SOL/USDT'),
             InlineKeyboardButton("SEI/USDT", callback_data='pair_SEI/USDT')],
            [InlineKeyboardButton("BNB/USDT", callback_data='pair_BNB/USDT'),
             InlineKeyboardButton("AGT/USDT", callback_data='pair_AGT/USDT')],
            [InlineKeyboardButton("PEPE/USDT ", callback_data='pair_PEPE/USDT'),
             InlineKeyboardButton("SUI/USDT", callback_data='pair_SUI/USDT')],
            [InlineKeyboardButton("LINK/USDT ", callback_data='pair_LINK/USDT'),
             InlineKeyboardButton("DOGE/USDT", callback_data='pair_DOGE/USDT')],
            [InlineKeyboardButton("✏️ Nhập cặp giao dịch mong muốn", callback_data='input_pair')],
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
                # build keyboard with track/untrack
                chat_id = update.message.chat_id
                reply_markup = self.build_reply_markup(symbol, timeframe, chat_id)
                await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Không thể phân tích cặp này.")
        else:
            await update.message.reply_text("Cách sử dụng: /analysis BTC/USDT 4h")

    # -------------------------
    # Start tracking from a callback (pin message and add job) - updated for pinned editing + max 3
    # -------------------------
    async def _start_tracking_from_callback(self, query, context, symbol: str, timeframe: str):
        chat_id = query.message.chat_id
        message_id = query.message.message_id

        # Ensure tracked_pairs structure for this chat exists
        if chat_id not in self.tracked_pairs:
            self.tracked_pairs[chat_id] = {}

        # Enforce max 3 per chat
        if symbol not in self.tracked_pairs[chat_id] and len(self.tracked_pairs[chat_id]) >= self.MAX_TRACKS_PER_CHAT:
            await query.edit_message_text(f"⚠️ You can track up to {self.MAX_TRACKS_PER_CHAT} pairs. Please stop one before adding another.")
            return

        # If symbol already tracked, cancel old job first (we'll replace)
        if symbol in self.tracked_pairs[chat_id]:
            try:
                self.tracked_pairs[chat_id][symbol]['job'].schedule_removal()
            except Exception:
                pass

        # Create job: run every 30 minutes, first run in 1800s (so we don't immediately duplicate)
        job = self.application.job_queue.run_repeating(
            self.send_auto_analysis,
            interval=1800,  # 30 minutes
            first=1800,
            chat_id=chat_id,
            name=f"autotrack_{chat_id}_{symbol}",
            data={"symbol": symbol, "timeframe": timeframe}
        )

        # Pin the current message (if bot has permission) and save pinned_message_id
        pinned_id = None
        try:
            await self.application.bot.pin_chat_message(chat_id=chat_id, message_id=message_id, disable_notification=True)
            pinned_id = message_id
        except Exception as e:
            logger.warning(f"Cannot pin message: {e}")
            pinned_id = None

        # save
        self.tracked_pairs[chat_id][symbol] = {"job": job, "pinned_message_id": pinned_id, "timeframe": timeframe, "created_at": time.time()}

        # update the button to show "Stop Tracking"
        reply_markup = self.build_reply_markup(symbol, timeframe, chat_id)
        try:
            await query.edit_message_text("✅ Tracking enabled. This message has been pinned (if bot has permission). It will be auto-updated.", reply_markup=reply_markup)
        except Exception:
            await context.bot.send_message(chat_id, f"✅ Tracking enabled for {symbol} {timeframe} (30 minutes interval).")

    # -------------------------
    # Stop tracking from callback (unpin & cancel job)
    # -------------------------
    async def _stop_tracking_from_callback(self, query, context, symbol: str):
        chat_id = query.message.chat_id

        if chat_id in self.tracked_pairs and symbol in self.tracked_pairs[chat_id]:
            info = self.tracked_pairs[chat_id].pop(symbol)
            try:
                info['job'].schedule_removal()
            except Exception:
                pass

            # unpin if pinned
            pinned_id = info.get('pinned_message_id')
            if pinned_id:
                try:
                    await self.application.bot.unpin_chat_message(chat_id=chat_id, message_id=pinned_id)
                except Exception as e:
                    logger.warning(f"Cannot unpin message: {e}")

            # update keyboard: show Track button again
            reply_markup = self.build_reply_markup(symbol, info.get('timeframe', '4h'), chat_id)
            try:
                await query.edit_message_text(f"🛑 Đã dừng theo dõi {symbol}.", reply_markup=reply_markup)
            except Exception:
                await context.bot.send_message(chat_id, f"🛑 Đã dừng theo dõi {symbol}.")
        else:
            await query.answer(text=f"{symbol} chưa được theo dõi.", show_alert=True)

    # -------------------------
    # Text handler to accept "Nhập cặp" input
    # -------------------------
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # If user clicked "input_pair" earlier, user_data will contain awaiting_pair=True
        if context.user_data.get('awaiting_pair'):
            context.user_data['awaiting_pair'] = False
            text = update.message.text.strip()
            parts = text.split()
            symbol = parts[0].upper()
            timeframe = parts[1] if len(parts) > 1 else '4h'
            # basic normalization: allow user to send BTC_USDT or BTC/USDT
            symbol = symbol.replace('_', '/')
            # present analysis as a new message
            await update.message.reply_text(f"🔄 Đang phân tích {symbol} {timeframe}...")
            result = self.smc_analyzer.get_trading_signals(symbol, timeframe)
            if result:
                message = self.format_analysis_message(result)
                # build keyboard with track button
                chat_id = update.message.chat_id
                reply_markup = self.build_reply_markup(symbol, timeframe, chat_id)
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Không thể phân tích cặp này.")
            return

        # else ignore or handle general messages
        return

    def run(self):
        """Chạy bot"""
        # Tạo application
        self.application = Application.builder().token(self.token).build()

        # Thêm handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("analysis", self.analysis_command))
        self.application.add_handler(CommandHandler("autotrack", self.auto_track_command))
        self.application.add_handler(CommandHandler("stoptrack", self.stop_track_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        # message handler for "Enter pair" flow
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.text_handler))

        # Chạy bot
        print("🤖 Bot đang chạy...")
        self.application.run_polling()

if __name__ == "__main__":
    # Thay YOUR_BOT_TOKEN bằng token thực của bot
    BOT_TOKEN = "7583449238:AAGWeKnbBqX1B1FB3MD3U_wR6xvphMG2gFw"
    bot = TradingBot(BOT_TOKEN)
    bot.run()
