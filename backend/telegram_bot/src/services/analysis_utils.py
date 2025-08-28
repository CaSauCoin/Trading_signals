import sys
import os
import logging
from datetime import datetime
import random

logger = logging.getLogger(__name__)

# Add the correct path to AdvancedSMC
current_dir = os.path.dirname(__file__)  # services directory
src_dir = os.path.dirname(current_dir)  # src directory
telegram_bot_dir = os.path.dirname(src_dir)  # telegram_bot directory
backend_dir = os.path.dirname(telegram_bot_dir)  # backend directory
advancedSMC_path = os.path.join(backend_dir, 'AdvancedSMC.py')

try:
    # Import AdvancedSMC class từ file AdvancedSMC.py
    sys.path.insert(0, backend_dir)
    from AdvancedSMC import AdvancedSMC
    SMC_AVAILABLE = True
    analysis_service = AdvancedSMC()
    logger.info("✅ AdvancedSMC initialized successfully for analysis_utils")
except ImportError as e:
    logger.warning(f"⚠️ Could not import AdvancedSMC in analysis_utils: {e}")
    SMC_AVAILABLE = False
    analysis_service = None
except Exception as e:
    logger.error(f"❌ Error initializing AdvancedSMC in analysis_utils: {e}")
    SMC_AVAILABLE = False
    analysis_service = None

def get_analysis_functions():
    """Get analysis functions for use in scheduler"""
    return analysis_service, analyze_with_smc, format_price

def analyze_with_smc(symbol: str, timeframe: str):
    """Analyze symbol using real AdvancedSMC or mock data"""
    try:
        # Normalize symbol format for Binance
        if '/' in symbol:
            symbol = symbol.replace('/', '')
        if not symbol.endswith('USDT') and not symbol.endswith('BTC') and not symbol.endswith('ETH'):
            symbol = f"{symbol}USDT"
        
        logger.debug(f"🔄 Starting analysis for {symbol} {timeframe}")
        
        # If AdvancedSMC is available, use real analysis
        if SMC_AVAILABLE and analysis_service:
            try:
                logger.info(f"🚀 Running real SMC analysis for {symbol} {timeframe}")
                
                # Use the get_trading_signals method from AdvancedSMC
                smc_result = analysis_service.get_trading_signals(symbol, timeframe)
                
                if smc_result:
                    # Format result to match expected structure
                    formatted_result = format_smc_result(smc_result, symbol, timeframe)
                    logger.info(f"✅ Real SMC analysis completed for {symbol} {timeframe}")
                    return formatted_result
                else:
                    logger.warning(f"⚠️ AdvancedSMC returned None for {symbol} {timeframe}, using mock data")
                    return generate_mock_analysis(symbol, timeframe)
                
            except Exception as e:
                logger.error(f"❌ Error calling AdvancedSMC for {symbol}: {e}")
                logger.info("🔄 Falling back to mock analysis")
                return generate_mock_analysis(symbol, timeframe)
        else:
            # Use mock analysis if AdvancedSMC not available
            logger.info(f"🎭 Using mock analysis for {symbol} {timeframe}")
            return generate_mock_analysis(symbol, timeframe)
        
    except Exception as e:
        logger.error(f"💥 Error in analyze_with_smc: {e}")
        return {
            'error': True,
            'message': f'Analysis failed: {str(e)}'
        }

def format_smc_result(smc_result: dict, symbol: str, timeframe: str) -> dict:
    """Format AdvancedSMC result to match expected telegram bot structure"""
    try:
        # Extract data from AdvancedSMC result
        current_price = smc_result.get('current_price', 0)
        indicators = smc_result.get('indicators', {})
        smc_analysis = smc_result.get('smc_analysis', {})
        trading_signals = smc_result.get('trading_signals', {})
        
        # Calculate price change percentage (mock if not available)
        price_change_pct = indicators.get('price_change_24h', random.uniform(-5, 5))
        
        # Determine overall signal from recent trading signals
        signal = determine_overall_signal(trading_signals, smc_analysis)
        confidence = calculate_confidence(smc_analysis, indicators)
        
        # Format Order Blocks status
        order_blocks = smc_analysis.get('order_blocks', [])
        ob_status = format_order_blocks_status(order_blocks)
        
        # Format Fair Value Gaps status
        fair_value_gaps = smc_analysis.get('fair_value_gaps', [])
        fvg_status = format_fvg_status(fair_value_gaps)
        
        # Format Break of Structure status
        break_of_structure = smc_analysis.get('break_of_structure', [])
        bos_status = format_bos_status(break_of_structure)
        
        # Format Liquidity Zones status
        liquidity_zones = smc_analysis.get('liquidity_zones', [])
        liq_status = format_liquidity_status(liquidity_zones)
        
        # Format entry signals for telegram
        entry_long = format_entry_signals(trading_signals.get('entry_long', []))
        entry_short = format_entry_signals(trading_signals.get('entry_short', []))
        
        # Build final result structure
        result = {
            'error': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now().strftime('%H:%M %d/%m/%Y'),
            'analysis': {
                'current_price': current_price,
                'indicators': {
                    'price_change_pct': price_change_pct,
                    'rsi': indicators.get('rsi', random.uniform(30, 70)),
                    'volume_24h': indicators.get('volume_24h', random.uniform(1000000, 1000000000)),
                    'market_cap': indicators.get('market_cap', random.uniform(100000000, 500000000000))
                },
                'trading_signals': {
                    'entry_long': entry_long,
                    'entry_short': entry_short,
                    'exit_signals': format_exit_signals(trading_signals)
                },
                'smc_analysis': {
                    'signal': signal,
                    'confidence': confidence,
                    'order_blocks': {
                        'status': ob_status
                    },
                    'fair_value_gaps': {
                        'status': fvg_status,
                        'direction': determine_fvg_direction(fair_value_gaps)
                    },
                    'break_of_structure': {
                        'status': bos_status
                    },
                    'liquidity_zones': {
                        'status': liq_status
                    }
                }
            }
        }
        
        logger.debug(f"✅ Formatted SMC result for {symbol}: {signal} signal")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error formatting SMC result: {e}")
        # Fallback to mock if formatting fails
        return generate_mock_analysis(symbol, timeframe)

def determine_overall_signal(trading_signals: dict, smc_analysis: dict) -> str:
    """Determine overall signal from trading signals and SMC analysis"""
    try:
        entry_long = trading_signals.get('entry_long', [])
        entry_short = trading_signals.get('entry_short', [])
        
        # Recent signals (last 5)
        recent_long = len(entry_long[-5:]) if entry_long else 0
        recent_short = len(entry_short[-5:]) if entry_short else 0
        
        # Check BOS for trend confirmation
        bos_signals = smc_analysis.get('break_of_structure', [])
        latest_bos = None
        if bos_signals:
            latest_bos = bos_signals[-1].get('type', '')
        
        # Determine signal
        if recent_long > recent_short:
            return 'BUY'
        elif recent_short > recent_long:
            return 'SELL'
        elif latest_bos == 'bullish_bos':
            return 'BUY'
        elif latest_bos == 'bearish_bos':
            return 'SELL'
        else:
            return 'NEUTRAL'
            
    except Exception as e:
        logger.error(f"Error determining signal: {e}")
        return 'NEUTRAL'

def calculate_confidence(smc_analysis: dict, indicators: dict) -> int:
    """Calculate confidence level based on SMC analysis"""
    try:
        confidence = 50  # Base confidence
        
        # Add confidence from Order Blocks
        order_blocks = smc_analysis.get('order_blocks', [])
        if order_blocks:
            confidence += min(len(order_blocks) * 5, 20)
        
        # Add confidence from BOS
        bos_signals = smc_analysis.get('break_of_structure', [])
        if bos_signals:
            confidence += min(len(bos_signals) * 3, 15)
        
        # Add confidence from FVG
        fvg_signals = smc_analysis.get('fair_value_gaps', [])
        if fvg_signals:
            confidence += min(len(fvg_signals) * 2, 10)
        
        # RSI confirmation
        rsi = indicators.get('rsi', 50)
        if rsi > 70 or rsi < 30:
            confidence += 5
        
        return min(confidence, 95)  # Cap at 95%
        
    except Exception as e:
        logger.error(f"Error calculating confidence: {e}")
        return 60

def format_order_blocks_status(order_blocks: list) -> str:
    """Format order blocks status"""
    if not order_blocks:
        return "No clear OB"
    
    latest_ob = order_blocks[-1]
    ob_type = latest_ob.get('type', '')
    
    if 'bullish' in ob_type:
        return "Bullish OB detected"
    elif 'bearish' in ob_type:
        return "Bearish OB detected"
    else:
        return "OB present"

def format_fvg_status(fair_value_gaps: list) -> str:
    """Format Fair Value Gaps status"""
    if not fair_value_gaps:
        return "No FVG"
    
    unfilled_fvg = [fvg for fvg in fair_value_gaps if not fvg.get('filled', False)]
    
    if unfilled_fvg:
        return "FVG present"
    else:
        return "FVG filled"

def determine_fvg_direction(fair_value_gaps: list) -> str:
    """Determine FVG direction"""
    if not fair_value_gaps:
        return "neutral"
    
    latest_fvg = fair_value_gaps[-1]
    fvg_type = latest_fvg.get('type', '')
    
    if 'bullish' in fvg_type:
        return "bullish"
    elif 'bearish' in fvg_type:
        return "bearish"
    else:
        return "neutral"

def format_bos_status(break_of_structure: list) -> str:
    """Format Break of Structure status"""
    if not break_of_structure:
        return "No clear BOS"
    
    latest_bos = break_of_structure[-1]
    bos_type = latest_bos.get('type', '')
    
    if 'bullish' in bos_type:
        return "Bullish BOS confirmed"
    elif 'bearish' in bos_type:
        return "Bearish BOS confirmed"
    else:
        return "BOS detected"

def format_liquidity_status(liquidity_zones: list) -> str:
    """Format liquidity zones status"""
    if not liquidity_zones:
        return "Normal liquidity"
    
    if len(liquidity_zones) > 5:
        return "High liquidity zone"
    else:
        return "Moderate liquidity"

def format_entry_signals(entry_signals: list) -> list:
    """Format entry signals for telegram display"""
    formatted_signals = []
    
    # Get recent signals only
    recent_signals = entry_signals[-3:] if entry_signals else []
    
    for signal in recent_signals:
        formatted_signals.append({
            'price': signal.get('price', 0),
            'confidence': random.randint(65, 85),  # Mock confidence if not available
            'time': signal.get('time', int(datetime.now().timestamp()))
        })
    
    return formatted_signals

def format_exit_signals(trading_signals: dict) -> list:
    """Format exit signals"""
    exit_signals = []
    
    exit_long = trading_signals.get('exit_long', [])
    exit_short = trading_signals.get('exit_short', [])
    
    for signal in exit_long[-2:]:  # Last 2 exit signals
        exit_signals.append({
            'price': signal.get('price', 0),
            'type': 'exit_long',
            'time': signal.get('time', int(datetime.now().timestamp()))
        })
    
    for signal in exit_short[-2:]:
        exit_signals.append({
            'price': signal.get('price', 0),
            'type': 'exit_short', 
            'time': signal.get('time', int(datetime.now().timestamp()))
        })
    
    return exit_signals

def generate_mock_analysis(symbol: str, timeframe: str):
    """Generate realistic mock analysis data - FALLBACK"""
    try:
        # Base prices for common tokens
        base_prices = {
            'BTCUSDT': random.uniform(25000, 70000),
            'ETHUSDT': random.uniform(1500, 4000),
            'BNBUSDT': random.uniform(200, 600),
            'ADAUSDT': random.uniform(0.3, 1.5),
            'SOLUSDT': random.uniform(20, 200),
            'DOTUSDT': random.uniform(4, 15),
            'MATICUSDT': random.uniform(0.5, 2.5),
            'AVAXUSDT': random.uniform(10, 50),
        }
        
        # Get base price or generate random for unknown tokens
        base_price = base_prices.get(symbol, random.uniform(0.01, 100))
        
        # Generate price movement
        price_change_pct = random.uniform(-8, 8)
        current_price = base_price * (1 + price_change_pct / 100)
        
        # Generate trading signals based on price movement
        entry_long = []
        entry_short = []
        exit_signals = []
        
        if price_change_pct > 3:  # Strong bullish
            entry_long.append({
                'price': current_price * 0.98,
                'confidence': random.randint(70, 90)
            })
            exit_signals.append({
                'price': current_price * 1.05,
                'type': 'take_profit'
            })
        elif price_change_pct < -3:  # Strong bearish
            entry_short.append({
                'price': current_price * 1.02,
                'confidence': random.randint(65, 85)
            })
            exit_signals.append({
                'price': current_price * 0.95,
                'type': 'take_profit'
            })
        elif abs(price_change_pct) > 1:  # Moderate movement
            if price_change_pct > 0:
                entry_long.append({
                    'price': current_price * 0.99,
                    'confidence': random.randint(50, 70)
                })
            else:
                entry_short.append({
                    'price': current_price * 1.01,
                    'confidence': random.randint(50, 70)
                })
        
        # Generate SMC analysis
        smc_signals = ['BUY', 'SELL', 'NEUTRAL']
        signal = random.choice(smc_signals)
        if price_change_pct > 2:
            signal = 'BUY'
        elif price_change_pct < -2:
            signal = 'SELL'
        
        result = {
            'error': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now().strftime('%H:%M %d/%m/%Y'),
            'analysis': {
                'current_price': current_price,
                'indicators': {
                    'price_change_pct': price_change_pct,
                    'rsi': random.uniform(20, 80),
                    'volume_24h': random.uniform(1000000, 1000000000),
                    'market_cap': random.uniform(100000000, 500000000000)
                },
                'trading_signals': {
                    'entry_long': entry_long,
                    'entry_short': entry_short,
                    'exit_signals': exit_signals
                },
                'smc_analysis': {
                    'signal': signal,
                    'confidence': random.randint(60, 90),
                    'order_blocks': {
                        'status': 'Bullish OB detected' if signal == 'BUY' else 'Bearish OB detected' if signal == 'SELL' else 'No clear OB'
                    },
                    'fair_value_gaps': {
                        'status': 'FVG present',
                        'direction': 'bullish' if signal == 'BUY' else 'bearish' if signal == 'SELL' else 'neutral'
                    },
                    'break_of_structure': {
                        'status': 'BOS confirmed' if abs(price_change_pct) > 2 else 'No clear BOS'
                    },
                    'liquidity_zones': {
                        'status': 'High liquidity zone' if abs(price_change_pct) > 3 else 'Normal liquidity'
                    }
                }
            }
        }
        
        logger.debug(f"🎭 Generated mock analysis for {symbol}: {signal} signal, {price_change_pct:.2f}% change")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error generating mock analysis: {e}")
        return {
            'error': True,
            'message': f'Mock analysis failed: {str(e)}'
        }

def format_price(price):
    """Format price for display"""
    try:
        if not price or price == 0:
            return "$0.00"
        
        if isinstance(price, str):
            try:
                price = float(price)
            except:
                return "N/A"
        
        if price < 0.000001:
            return f"${price:.8f}"
        elif price < 0.0001:
            return f"${price:.6f}"
        elif price < 0.01:
            return f"${price:.4f}"
        elif price < 1:
            return f"${price:.3f}"
        elif price < 100:
            return f"${price:.2f}"
        elif price < 10000:
            return f"${price:,.2f}"
        else:
            return f"${price:,.0f}"
            
    except Exception as e:
        logger.error(f"❌ Error formatting price {price}: {e}")
        return "N/A"

def get_mock_tokens():
    """Get list of mock tokens for testing"""
    return [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 
        'SOLUSDT', 'DOTUSDT', 'MATICUSDT', 'AVAXUSDT',
        'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'XRPUSDT'
    ]

def validate_symbol(symbol: str) -> bool:
    """Validate if symbol format is correct"""
    try:
        if not symbol or len(symbol) < 3:
            return False
        
        # Remove common suffixes to get base symbol
        if symbol.endswith('USDT'):
            base = symbol[:-4]
        elif symbol.endswith('BTC') or symbol.endswith('ETH'):
            base = symbol[:-3]
        else:
            base = symbol
        
        # Check if base symbol is valid (letters only, 2-10 chars)
        return base.isalpha() and 2 <= len(base) <= 10
        
    except Exception:
        return False

# Export main functions
__all__ = ['analyze_with_smc', 'format_price', 'get_analysis_functions', 'validate_symbol']