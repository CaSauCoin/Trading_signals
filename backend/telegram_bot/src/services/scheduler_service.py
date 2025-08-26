import logging
import time
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.user_watchlists = {}
        self.last_update_hour = -1
        
    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Add token to user's watchlist"""
        logger.info(f"Adding {symbol} {timeframe} to watchlist for user {user_id}")
        
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'last_signals': {},
                'notifications_enabled': True
            }
            logger.info(f"Created new watchlist for user {user_id}")
        
        # Check if already exists
        for token in self.user_watchlists[user_id]['tokens']:
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                logger.info(f"Token {symbol} {timeframe} already exists for user {user_id}")
                return False  # Already exists
        
        # Check limit (max 10 tokens)
        current_count = len(self.user_watchlists[user_id]['tokens'])
        if current_count >= 10:
            logger.info(f"Watchlist limit reached for user {user_id}: {current_count}/10")
            return False  # Limit exceeded
        
        # Add token
        self.user_watchlists[user_id]['tokens'].append({
            'symbol': symbol,
            'timeframe': timeframe,
            'added_at': datetime.now().isoformat()
        })
        
        logger.info(f"Successfully added {symbol} {timeframe} to user {user_id} watchlist. Total: {current_count + 1}/10")
        return True
    
    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Remove token from user's watchlist"""
        logger.info(f"Removing {symbol} {timeframe} from watchlist for user {user_id}")
        
        if user_id not in self.user_watchlists:
            logger.warning(f"No watchlist found for user {user_id}")
            return False
        
        tokens = self.user_watchlists[user_id]['tokens']
        for i, token in enumerate(tokens):
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                del tokens[i]
                # Remove last signal data
                signal_key = f"{symbol}_{timeframe}"
                if signal_key in self.user_watchlists[user_id]['last_signals']:
                    del self.user_watchlists[user_id]['last_signals'][signal_key]
                logger.info(f"Successfully removed {symbol} {timeframe} from user {user_id} watchlist")
                return True
        
        logger.warning(f"Token {symbol} {timeframe} not found in user {user_id} watchlist")
        return False
    
    def get_user_watchlist(self, user_id: int):
        """Get user's watchlist"""
        watchlist = self.user_watchlists.get(user_id, {
            'tokens': [], 
            'last_signals': {},
            'notifications_enabled': True
        })
        logger.info(f"Retrieved watchlist for user {user_id}: {len(watchlist.get('tokens', []))} tokens")
        return watchlist
    
    def clear_watchlist(self, user_id: int):
        """Clear user's entire watchlist"""
        if user_id in self.user_watchlists:
            token_count = len(self.user_watchlists[user_id]['tokens'])
            self.user_watchlists[user_id] = {
                'tokens': [],
                'last_signals': {},
                'notifications_enabled': True
            }
            logger.info(f"Cleared {token_count} tokens from user {user_id} watchlist")
            return True
        logger.warning(f"No watchlist found to clear for user {user_id}")
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
        new_state = not current_state
        self.user_watchlists[user_id]['notifications_enabled'] = new_state
        
        logger.info(f"Toggled notifications for user {user_id}: {current_state} -> {new_state}")
        return new_state
    
    def update_all_watchlists(self):
        """Update all user watchlists - called every 1 hour"""
        if not self.user_watchlists:
            logger.info("No watchlists to update")
            return
        
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Prevent duplicate updates in the same hour
        if self.last_update_hour == current_hour:
            logger.info(f"Already updated in hour {current_hour}, skipping...")
            return
        
        self.last_update_hour = current_hour
        
        logger.info(f"Starting HOURLY watchlist update at {current_time.strftime('%H:%M:%S')} for {len(self.user_watchlists)} users")
        
        for user_id, watchlist_data in self.user_watchlists.items():
            if not watchlist_data.get('notifications_enabled', True):
                logger.info(f"Notifications disabled for user {user_id}, skipping...")
                continue
                
            tokens = watchlist_data.get('tokens', [])
            if not tokens:
                logger.info(f"No tokens in watchlist for user {user_id}, skipping...")
                continue
            
            logger.info(f"Updating watchlist for user {user_id} with {len(tokens)} tokens")
            self.update_user_watchlist(user_id, tokens, current_time)
    
    def update_user_watchlist(self, user_id: int, tokens: List[Dict], current_time: datetime):
        """Update watchlist for a specific user"""
        try:
            # Import analysis functions using utility module
            from .analysis_utils import get_analysis_functions
            
            analysis_service, analyze_with_smc, format_price = get_analysis_functions()
            
            if not analysis_service or not analyze_with_smc:
                logger.error("Analysis functions not available for watchlist update")
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
                        
                        # Check for NEW signals
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
                            logger.info(f"New signal detected for {symbol} {timeframe}")
                        
                        # Update last signals
                        self.user_watchlists[user_id]['last_signals'][signal_key] = current_signals
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol} {timeframe}: {e}")
                    continue
            
            # Send comprehensive hourly report
            self.send_hourly_watchlist_report(user_id, analyses, new_signals, current_time, format_price)
                
        except Exception as e:
            logger.error(f"Error updating watchlist for user {user_id}: {e}")
    
    def extract_signals(self, analysis_result):
        """Extract trading signals from analysis result"""
        trading_signals = analysis_result.get('analysis', {}).get('trading_signals', {})
        return {
            'entry_long': trading_signals.get('entry_long', []),
            'entry_short': trading_signals.get('entry_short', []),
            'exit_signals': trading_signals.get('exit_signals', []),
            'timestamp': analysis_result.get('timestamp', 0)
        }
    
    def has_new_signals(self, current_signals, last_signals):
        """Check if there are NEW signals compared to last check"""
        if not last_signals:
            # First time checking - only notify if there are active signals
            has_signals = bool(current_signals.get('entry_long') or current_signals.get('entry_short'))
            if has_signals:
                logger.info("First time analysis - signals detected")
            return has_signals
        
        # Compare signal counts to detect NEW signals
        current_long_count = len(current_signals.get('entry_long', []))
        current_short_count = len(current_signals.get('entry_short', []))
        current_exit_count = len(current_signals.get('exit_signals', []))
        
        last_long_count = len(last_signals.get('entry_long', []))
        last_short_count = len(last_signals.get('entry_short', []))
        last_exit_count = len(last_signals.get('exit_signals', []))
        
        has_new = (current_long_count > last_long_count or 
                   current_short_count > last_short_count or
                   current_exit_count > last_exit_count)
        
        if has_new:
            logger.info(f"New signals detected: Long {last_long_count}->{current_long_count}, Short {last_short_count}->{current_short_count}")
        
        return has_new
    
    def send_hourly_watchlist_report(self, user_id: int, analyses: List[Dict], new_signals: List[Dict], current_time: datetime, format_price_func=None):
        """Send comprehensive hourly watchlist report"""
        try:
            if not analyses:
                logger.info(f"No analyses to report for user {user_id}")
                return
            
            # Default format_price function if not provided
            if not format_price_func:
                format_price_func = lambda x: f"${x:.4f}" if x else "$0.00"
            
            # Build comprehensive message
            message = f"📊 **HOURLY WATCHLIST REPORT** 📊\n"
            message += f"🕐 {current_time.strftime('%H:00 - %d/%m/%Y')}\n\n"
            
            # 1. New Signals Section (if any)
            if new_signals:
                message += "🚨 **NEW TRADING SIGNALS:** 🚨\n\n"
                
                for signal_data in new_signals:
                    symbol = signal_data['symbol']
                    timeframe = signal_data['timeframe']
                    signals = signal_data['signals']
                    analysis = signal_data['analysis']
                    
                    # Current price
                    current_price = analysis.get('analysis', {}).get('current_price', 0)
                    
                    message += f"📈 **{symbol} ({timeframe})**\n"
                    message += f"💰 Price: {format_price_func(current_price)}\n"
                    
                    # Show NEW signals
                    entry_long = signals.get('entry_long', [])
                    entry_short = signals.get('entry_short', [])
                    exit_signals = signals.get('exit_signals', [])
                    
                    if entry_long:
                        latest_long = entry_long[-1]
                        message += f"🟢 **NEW Long:** {format_price_func(latest_long.get('price', 0))}\n"
                    
                    if entry_short:
                        latest_short = entry_short[-1]
                        message += f"🔴 **NEW Short:** {format_price_func(latest_short.get('price', 0))}\n"
                    
                    if exit_signals:
                        latest_exit = exit_signals[-1]
                        message += f"🚪 **Exit:** {format_price_func(latest_exit.get('price', 0))}\n"
                    
                    message += "\n"
            
            # 2. Market Overview Section  
            message += "📋 **MARKET OVERVIEW:**\n\n"
            
            gainers = []
            losers = []
            stable = []
            
            for analysis in analyses:
                symbol = analysis.get('symbol', 'Unknown')
                timeframe = analysis.get('timeframe', '4h')
                analysis_data = analysis.get('analysis', {})
                
                current_price = analysis_data.get('current_price', 0)
                indicators = analysis_data.get('indicators', {})
                price_change = indicators.get('price_change_pct', 0)
                rsi = indicators.get('rsi', 50)
                
                token_info = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'price': current_price,
                    'change': price_change,
                    'rsi': rsi
                }
                
                if price_change > 2:
                    gainers.append(token_info)
                elif price_change < -2:
                    losers.append(token_info)
                else:
                    stable.append(token_info)
            
            # Sort by change percentage
            gainers.sort(key=lambda x: x['change'], reverse=True)
            losers.sort(key=lambda x: x['change'])
            
            # Show top performers
            if gainers:
                message += "📈 **TOP GAINERS:**\n"
                for token in gainers[:3]:  # Top 3
                    rsi_status = "🔴" if token['rsi'] > 70 else "🟡"
                    message += f"🟢 {token['symbol']} {format_price_func(token['price'])} (+{token['change']:.2f}%) {rsi_status}\n"
                message += "\n"
            
            if losers:
                message += "📉 **TOP LOSERS:**\n"
                for token in losers[:3]:  # Top 3
                    rsi_status = "🟢" if token['rsi'] < 30 else "🟡"
                    message += f"🔴 {token['symbol']} {format_price_func(token['price'])} ({token['change']:.2f}%) {rsi_status}\n"
                message += "\n"
            
            if stable:
                message += f"⚖️ **STABLE:** {len(stable)} tokens (-2% to +2%)\n\n"
            
            # 3. Statistics
            total_tokens = len(analyses)
            total_gainers = len(gainers)
            total_losers = len(losers)
            
            message += "📊 **STATISTICS:**\n"
            if total_tokens > 0:
                message += f"📈 Gainers: {total_gainers}/{total_tokens} ({total_gainers/total_tokens*100:.1f}%)\n"
                message += f"📉 Losers: {total_losers}/{total_tokens} ({total_losers/total_tokens*100:.1f}%)\n"
            else:
                message += f"📈 Gainers: 0/0 (0%)\n"
                message += f"📉 Losers: 0/0 (0%)\n"
            message += f"🚨 New Signals: {len(new_signals)}\n\n"
            
            message += f"🔔 Next update: {(current_time.hour + 1) % 24:02d}:00\n"
            message += f"💡 Use /start for detailed analysis."
            
            # Send report
            if self.bot and hasattr(self.bot, 'updater'):
                try:
                    self.bot.updater.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Sent hourly watchlist report to user {user_id} - {total_tokens} tokens, {len(new_signals)} new signals")
                except Exception as e:
                    logger.error(f"Error sending Telegram message to user {user_id}: {e}")
            else:
                logger.error("Bot instance not available for sending messages")
            
        except Exception as e:
            logger.error(f"Error sending hourly watchlist report to user {user_id}: {e}")