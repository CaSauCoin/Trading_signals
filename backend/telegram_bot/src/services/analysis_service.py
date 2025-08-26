from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

async def analyze_trading_signals(symbol, timeframe, smc_analyzer):
    """Analyze trading signals for a given symbol and timeframe."""
    try:
        result = await smc_analyzer.get_trading_signals(symbol, timeframe)
        if result is None:
            logger.warning(f"No trading signals found for {symbol} in {timeframe}.")
            return None
        return result
    except Exception as e:
        logger.error(f"Error analyzing trading signals for {symbol}: {e}")
        return None

def format_analysis_message(result):
    """Format the analysis result into a message."""
    message = f"📊 *Analysis for {result['symbol']} - {result['timeframe']}*\n\n"
    message += f"💰 *Current Price:* ${result['current_price']:,.2f}\n"
    
    # Add more details to the message as needed
    # ...

    return message

def save_analysis_to_file(symbol, analysis_data):
    """Save the analysis data to a JSON file."""
    filename = f"analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Analysis saved to {filename}.")
    except Exception as e:
        logger.error(f"Error saving analysis to file: {e}")