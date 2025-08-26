import logging
import asyncio
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.user_watchlists = {}  # user_id: {tokens: [], last_signals: {}}
        
    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Add token to user's watchlist"""
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'last_signals': {},
                'notifications_enabled': True
            }
        
        # Check if already exists
        for token in self.user_watchlists[user_id]['tokens']:
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                return False  # Already exists
        
        # Check limit (max 10 tokens)
        if len(self.user_watchlists[user_id]['tokens']) >= 10:
            return False  # Limit exceeded
        
        self.user_watchlists[user_id]['tokens'].append({
            'symbol': symbol,
            'timeframe': timeframe,
            'added_at': datetime.now().isoformat()
        })
        
        logger.info(f"Added {symbol} {timeframe} to user {user_id} watchlist")
        return True
    
    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Remove token from user's watchlist"""
        if user_id not in self.user_watchlists:
            return False
        
        tokens = self.user_watchlists[user_id]['tokens']
        for i, token in enumerate(tokens):
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                del tokens[i]
                # Remove last signal data
                signal_key = f"{symbol}_{timeframe}"
                if signal_key in self.user_watchlists[user_id]['last_signals']:
                    del self.user_watchlists[user_id]['last_signals'][signal_key]
                logger.info(f"Removed {symbol} {timeframe} from user {user_id} watchlist")
                return True
        return False
    
    def get_user_watchlist(self, user_id: int):
        """Get user's watchlist"""
        return self.user_watchlists.get(user_id, {'tokens': [], 'last_signals': {}})
    
    def clear_watchlist(self, user_id: int):
        """Clear user's entire watchlist"""
        if user_id in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'last_signals': {},
                'notifications_enabled': True
            }
            return True
        return False
    
    def toggle_notifications(self, user_id: int):
        """Toggle notifications for user"""
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'last_signals': {},
                'notifications_enabled': True
            }
        
        current_state = self.user_watchlists[user_id].get('notifications_enabled', True)
        self.user_watchlists[user_id]['notifications_enabled'] = not current_state
        return not current_state
    
    async def update_all_watchlists(self):
        """Update all user watchlists - called every 10 minutes"""
        if not self.user_watchlists:
            logger.info("No watchlists to update")
            return
        
        logger.info(f"Starting watchlist update for {len(self.user_watchlists)} users")
        
        for user_id, watchlist_data in self.user_watchlists.items():
            if not watchlist_data.get('notifications_enabled', True):
                continue
                
            tokens = watchlist_data.get('tokens', [])
            if not tokens:
                continue
            
            logger.info(f"Updating watchlist for user {user_id} with {len(tokens)} tokens")
            await self.update_user_watchlist(user_id, tokens)
    
    async def update_user_watchlist(self, user_id: int, tokens: List[Dict]):
        """Update watchlist for a specific user"""
        try:
            # Import analysis service
            from handlers.callback_handlers import analysis_service, analyze_with_smc
            
            if not analysis_service:
                logger.error("Analysis service not available for watchlist update")
                return
            
            new_signals = []
            analyses = []
            
            # Analyze all tokens
            for token_data in tokens:
                symbol = token_data['symbol']
                timeframe = token_data['timeframe']
                
                try:
                    logger.info(f"Analyzing {symbol} {timeframe} for user {user_id}")
                    result = analyze_with_smc(symbol, timeframe)
                    
                    if not result.get('error'):
                        analyses.append(result)
                        
                        # Check for new signals
                        signal_key = f"{symbol}_{timeframe}"
                        current_signals = self.extract_signals(result)
                        last_signals = self.user_watchlists[user_id]['last_signals'].get(signal_key, {})
                        
                        if self.has_new_signals(current_signals, last_signals):
                            new_signals.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'signals': current_signals,
                                'analysis': result
                            })
                        
                        # Update last signals
                        self.user_watchlists[user_id]['last_signals'][signal_key] = current_signals
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol} {timeframe}: {e}")
                    continue
            
            # Send notifications if there are new signals
            if new_signals:
                await self.send_signal_notifications(user_id, new_signals)
            
            # Send periodic summary (every hour - 6 cycles of 10 minutes)
            current_time = datetime.now()
            if current_time.minute < 10:  # Send summary in first 10-minute window of each hour
                await self.send_watchlist_summary(user_id, analyses)
                
        except Exception as e:
            logger.error(f"Error updating watchlist for user {user_id}: {e}")
    
    def extract_signals(self, analysis_result):
        """Extract trading signals from analysis result"""
        trading_signals = analysis_result.get('analysis', {}).get('trading_signals', {})
        return {
            'entry_long': trading_signals.get('entry_long', []),
            'entry_short': trading_signals.get('entry_short', []),
            'timestamp': analysis_result.get('timestamp', 0)
        }
    
    def has_new_signals(self, current_signals, last_signals):
        """Check if there are new signals compared to last check"""
        if not last_signals:
            return bool(current_signals.get('entry_long') or current_signals.get('entry_short'))
        
        current_long_count = len(current_signals.get('entry_long', []))
        current_short_count = len(current_signals.get('entry_short', []))
        
        last_long_count = len(last_signals.get('entry_long', []))
        last_short_count = len(last_signals.get('entry_short', []))
        
        return (current_long_count > last_long_count or 
                current_short_count > last_short_count)
    
    async def send_signal_notifications(self, user_id: int, new_signals: List[Dict]):
        """Send notification for new signals"""
        try:
            message = "🚨 **NEW TRADING SIGNALS** 🚨\n\n"
            
            for signal_data in new_signals:
                symbol = signal_data['symbol']
                timeframe = signal_data['timeframe']
                signals = signal_data['signals']
                analysis = signal_data['analysis']
                
                message += f"📊 **{symbol} ({timeframe})**\n"
                
                # Current price
                current_price = analysis.get('analysis', {}).get('current_price', 0)
                from handlers.callback_handlers import format_price
                message += f"💰 Price: {format_price(current_price)}\n"
                
                # Signals
                entry_long = signals.get('entry_long', [])
                entry_short = signals.get('entry_short', [])
                
                if entry_long:
                    latest_long = entry_long[-1]
                    message += f"🟢 Long: {format_price(latest_long.get('price', 0))}\n"
                
                if entry_short:
                    latest_short = entry_short[-1]
                    message += f"🔴 Short: {format_price(latest_short.get('price', 0))}\n"
                
                message += "\n"
            
            message += f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            message += "Use /start to analyze or manage watchlist."
            
            # Send message
            self.bot.updater.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent signal notification to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending signal notification to user {user_id}: {e}")
    
    async def send_watchlist_summary(self, user_id: int, analyses: List[Dict]):
        """Send hourly watchlist summary"""
        try:
            if not analyses:
                return
            
            message = "📋 **WATCHLIST SUMMARY** 📋\n\n"
            
            for analysis in analyses:
                symbol = analysis.get('symbol', 'Unknown')
                timeframe = analysis.get('timeframe', '4h')
                analysis_data = analysis.get('analysis', {})
                
                current_price = analysis_data.get('current_price', 0)
                indicators = analysis_data.get('indicators', {})
                price_change = indicators.get('price_change_pct', 0)
                
                from handlers.callback_handlers import format_price
                change_emoji = "📈" if price_change > 0 else "📉"
                
                message += f"📊 **{symbol}** ({timeframe})\n"
                message += f"💰 {format_price(current_price)} {change_emoji} {price_change:+.2f}%\n\n"
            
            message += f"🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
            message += "Use /start for detailed analysis."
            
            # Send summary
            self.bot.updater.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent watchlist summary to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending watchlist summary to user {user_id}: {e}")