import logging
import json
import os
import time  # Add this import
from datetime import datetime
from typing import Dict, List
from telegram.error import Unauthorized, BadRequest, NetworkError

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.user_watchlists = {}
        self.last_update_hour = -1
        self.data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'watchlists.json')
        self.load_watchlists()
        
    def load_watchlists(self):
        """Load watchlists from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    self.user_watchlists = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded watchlists for {len(self.user_watchlists)} users")
            else:
                self.user_watchlists = {}
                logger.info("No existing watchlist file found")
        except Exception as e:
            logger.error(f"Error loading watchlists: {e}")
            self.user_watchlists = {}
    
    def save_watchlists(self):
        """Save watchlists to file"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            # Convert integer keys to strings for JSON
            data = {str(k): v for k, v in self.user_watchlists.items()}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Watchlists saved to file")
        except Exception as e:
            logger.error(f"Error saving watchlists: {e}")
    
    def add_to_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Add token to user's watchlist"""
        logger.info(f"Adding {symbol} {timeframe} to watchlist for user {user_id}")
        
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'notifications_enabled': True,
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
        
        # Update last active
        self.user_watchlists[user_id]['last_active'] = datetime.now().isoformat()
        
        # Check if already exists
        for token in self.user_watchlists[user_id]['tokens']:
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                logger.info(f"Token {symbol} {timeframe} already exists for user {user_id}")
                return False
        
        # Check limit (max 10 tokens)
        current_count = len(self.user_watchlists[user_id]['tokens'])
        if current_count >= 10:
            logger.warning(f"User {user_id} reached watchlist limit ({current_count}/10)")
            return False
        
        # Add token
        self.user_watchlists[user_id]['tokens'].append({
            'symbol': symbol,
            'timeframe': timeframe,
            'added_at': datetime.now().isoformat()
        })
        
        # Save to file
        self.save_watchlists()
        
        logger.info(f"Successfully added {symbol} {timeframe} to user {user_id} watchlist. Total: {current_count + 1}/10")
        return True
    
    def remove_from_watchlist(self, user_id: int, symbol: str, timeframe: str = '4h'):
        """Remove token from user's watchlist"""
        logger.info(f"Removing {symbol} {timeframe} from watchlist for user {user_id}")
        
        if user_id not in self.user_watchlists:
            return False
        
        tokens = self.user_watchlists[user_id]['tokens']
        for i, token in enumerate(tokens):
            if token['symbol'] == symbol and token['timeframe'] == timeframe:
                tokens.pop(i)
                self.user_watchlists[user_id]['last_active'] = datetime.now().isoformat()
                self.save_watchlists()
                logger.info(f"Successfully removed {symbol} {timeframe} from user {user_id} watchlist")
                return True
        
        logger.warning(f"Token {symbol} {timeframe} not found in user {user_id} watchlist")
        return False
    
    def get_user_watchlist(self, user_id: int):
        """Get user's watchlist"""
        if user_id not in self.user_watchlists:
            return {'tokens': [], 'notifications_enabled': True}
        
        # Update last active
        self.user_watchlists[user_id]['last_active'] = datetime.now().isoformat()
        return self.user_watchlists[user_id]
    
    def clear_watchlist(self, user_id: int):
        """Clear user's entire watchlist"""
        if user_id in self.user_watchlists:
            token_count = len(self.user_watchlists[user_id]['tokens'])
            self.user_watchlists[user_id]['tokens'] = []
            self.user_watchlists[user_id]['last_active'] = datetime.now().isoformat()
            self.save_watchlists()
            logger.info(f"Cleared {token_count} tokens from user {user_id} watchlist")
            return True
        return False
    
    def delete_user_data(self, user_id: int):
        """Completely delete user data"""
        if user_id in self.user_watchlists:
            del self.user_watchlists[user_id]
            self.save_watchlists()
            logger.info(f"Deleted all data for user {user_id}")
            return True
        return False
    
    def toggle_notifications(self, user_id: int):
        """Toggle notifications for user"""
        if user_id not in self.user_watchlists:
            self.user_watchlists[user_id] = {
                'tokens': [],
                'notifications_enabled': True,
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
        
        current_state = self.user_watchlists[user_id].get('notifications_enabled', True)
        new_state = not current_state
        self.user_watchlists[user_id]['notifications_enabled'] = new_state
        self.user_watchlists[user_id]['last_active'] = datetime.now().isoformat()
        self.save_watchlists()
        
        logger.info(f"User {user_id} notifications: {'enabled' if new_state else 'disabled'}")
        return new_state
    
    def update_all_watchlists(self):
        """Update all user watchlists and send notifications - SYNC VERSION"""
        current_time = datetime.now()
        current_hour = current_time.hour
        
        self.last_update_hour = current_hour
        logger.info(f"🚀 Starting watchlist analysis for {len(self.user_watchlists)} users")
        
        # Track users to remove (blocked/unauthorized)
        users_to_remove = []
        
        for user_id, watchlist in self.user_watchlists.items():
            try:
                tokens = watchlist.get('tokens', [])
                notifications_enabled = watchlist.get('notifications_enabled', True)
                
                if not tokens or not notifications_enabled:
                    logger.debug(f"⏭️ Skipping user {user_id}: no tokens or notifications disabled")
                    continue
                
                logger.info(f"📊 Processing watchlist for user {user_id} ({len(tokens)} tokens)")
                
                # Test if user is still accessible - SYNC VERSION
                try:
                    bot = self.bot.updater.bot
                    chat = bot.get_chat(user_id)  # Sync call
                    logger.debug(f"✅ User {user_id} is accessible")
                except Unauthorized:
                    logger.warning(f"🚫 User {user_id} blocked the bot - marking for removal")
                    users_to_remove.append(user_id)
                    continue
                except BadRequest as e:
                    if "chat not found" in str(e).lower():
                        logger.warning(f"👻 User {user_id} chat not found - marking for removal")
                        users_to_remove.append(user_id)
                        continue
                    else:
                        logger.error(f"❌ BadRequest for user {user_id}: {e}")
                        continue
                except NetworkError as e:
                    logger.warning(f"🌐 Network error checking user {user_id}: {e} - skipping this update")
                    continue
                except Exception as e:
                    logger.error(f"💥 Error checking user {user_id} accessibility: {e}")
                    continue
                
                # Update watchlist for this user - SYNC VERSION
                self.update_user_watchlist_sync(user_id, tokens, current_time)
                
                # Add small delay between users to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"💥 Error processing watchlist for user {user_id}: {e}")
                if "unauthorized" in str(e).lower() or "forbidden" in str(e).lower():
                    users_to_remove.append(user_id)
    
        # Remove blocked/unauthorized users
        for user_id in users_to_remove:
            logger.info(f"🗑️ Removing data for blocked/unauthorized user {user_id}")
            self.delete_user_data(user_id)
        
        if users_to_remove:
            logger.info(f"🧹 Cleaned up {len(users_to_remove)} blocked/unauthorized users")
        
        logger.info("🎉 Watchlist analysis cycle completed successfully")
    
    def update_user_watchlist_sync(self, user_id: int, tokens: List[Dict], current_time: datetime):
        """Update watchlist for a specific user - RUN REAL ANALYSIS"""
        try:
            # Import analysis functions
            try:
                from services.analysis_utils import analyze_with_smc, format_price
                logger.debug("✅ Successfully imported analysis functions")
            except ImportError as e:
                logger.error(f"❌ Failed to import analysis_utils: {e}")
                return
            
            analyses = []
            
            for token in tokens:
                symbol = token['symbol']
                timeframe = token['timeframe']
                
                try:
                    logger.info(f"🔄 Analyzing {symbol} {timeframe} for user {user_id}")
                    
                    # RUN REAL analyze_with_smc
                    analysis_result = analyze_with_smc(symbol, timeframe)
                    
                    if not analysis_result.get('error'):
                        analyses.append(analysis_result)
                        logger.info(f"✅ Analysis completed for {symbol} {timeframe}")
                    else:
                        logger.warning(f"⚠️ Analysis failed for {symbol} {timeframe}: {analysis_result.get('message')}")
                
                except Exception as e:
                    logger.error(f"💥 Error analyzing {symbol} {timeframe} for user {user_id}: {e}")
        
            # Send results to Telegram if any analysis succeeded
            if analyses:
                self.send_analysis_results_to_telegram(user_id, analyses, current_time, format_price)
                logger.info(f"📤 Sent {len(analyses)} analysis results to user {user_id}")
            else:
                logger.warning(f"⚠️ No successful analyses for user {user_id}")
            
            # Update last_active for user
            self.user_watchlists[user_id]['last_active'] = current_time.isoformat()
            self.save_watchlists()
            
        except Exception as e:
            logger.error(f"💥 Error in update_user_watchlist_sync for user {user_id}: {e}")

    def send_analysis_results_to_telegram(self, user_id: int, analyses: List[Dict], current_time: datetime, format_price_func):
        """Send analysis results to Telegram - ENGLISH VERSION"""
        try:
            # Build header
            message = f"📊 **Watchlist Analysis Report**\n"
            message += f"🕐 {current_time.strftime('%H:%M %d/%m/%Y')}\n"
            message += "=" * 40 + "\n\n"
            
            # Send each analysis
            for i, analysis in enumerate(analyses, 1):
                symbol = analysis.get('symbol', 'Unknown')
                timeframe = analysis.get('timeframe', '4h')
                analysis_data = analysis.get('analysis', {})
                
                # Extract data
                smc_data = analysis_data.get('smc_analysis', {})
                current_price = analysis_data.get('current_price', 0)
                indicators = analysis_data.get('indicators', {})
                trading_signals = analysis_data.get('trading_signals', {})
                
                # Format signal emoji
                signal = smc_data.get('signal', 'NEUTRAL')
                signal_emoji = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"
                
                # Format price change
                price_change = indicators.get('price_change_pct', 0)
                change_emoji = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
                
                # Build analysis message
                token_msg = f"""**{i}. {symbol} ({timeframe})**

💰 **Price:** {format_price_func(current_price)} {change_emoji} {price_change:+.2f}%

{signal_emoji} **Signal:** {signal}
📈 **Confidence:** {smc_data.get('confidence', 0)}%

🔲 **Order Blocks:** {smc_data.get('order_blocks', {}).get('status', 'N/A')}
⚡ **Fair Value Gaps:** {smc_data.get('fair_value_gaps', {}).get('status', 'N/A')}
📊 **Break of Structure:** {smc_data.get('break_of_structure', {}).get('status', 'N/A')}
💧 **Liquidity Zones:** {smc_data.get('liquidity_zones', {}).get('status', 'N/A')}

📊 **RSI:** {indicators.get('rsi', 0):.1f}"""

                # Add trading signals if available
                entry_long = trading_signals.get('entry_long', [])
                entry_short = trading_signals.get('entry_short', [])
                
                if entry_long:
                    token_msg += f"\n🟢 **Entry Long:** {format_price_func(entry_long[0].get('price'))} ({entry_long[0].get('confidence', 0)}%)"
                
                if entry_short:
                    token_msg += f"\n🔴 **Entry Short:** {format_price_func(entry_short[0].get('price'))} ({entry_short[0].get('confidence', 0)}%)"
                
                message += token_msg + "\n\n"
                
                # Add separator if not last item
                if i < len(analyses):
                    message += "─" * 30 + "\n\n"
            
            # Add footer
            message += "=" * 40 + "\n"
            message += "💡 *Use /start for detailed analysis*\n"
            message += "🔔 *Automatic reports every hour*\n"
            message += "⚠️ *For reference only, not financial advice*"
            
            # Send message với retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    bot = self.bot.updater.bot
                    bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"📤 Successfully sent analysis report to user {user_id} - {len(analyses)} tokens analyzed")
                    break  # Success, exit retry loop
                    
                except NetworkError as e:
                    logger.warning(f"🌐 Network error sending to user {user_id} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"❌ Failed to send report to user {user_id} after {max_retries} attempts")
                        raise
                except Unauthorized:
                    logger.warning(f"🚫 User {user_id} blocked the bot - cannot send report")
                    raise  # Re-raise to trigger user removal
                except Exception as e:
                    logger.error(f"💥 Error sending analysis report to user {user_id}: {e}")
                    raise
        
        except Exception as e:
            logger.error(f"💥 Error in send_analysis_results_to_telegram for user {user_id}: {e}")
            raise
    
    def get_statistics(self):
        """Get watchlist statistics"""
        total_users = len(self.user_watchlists)
        total_tokens = sum(len(wl.get('tokens', [])) for wl in self.user_watchlists.values())
        active_users = sum(1 for wl in self.user_watchlists.values() if wl.get('notifications_enabled', True))
        
        return {
            'total_users': total_users,
            'total_tokens': total_tokens,
            'active_users': active_users,
            'average_tokens_per_user': total_tokens / total_users if total_users > 0 else 0
        }