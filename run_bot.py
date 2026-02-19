"""Script to run a trading bot."""

import logging
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.servicios.database import init_db, test_connection
from src.servicios.iqoption_auth import authenticate_or_raise
from src.servicios.trading_bot_service import TradingBotService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run a trading bot."""
    
    # Check if bot_id provided
    if len(sys.argv) < 4:
        logger.error("Usage: python run_bot.py <bot_id> <iq_email> <iq_password>")
        sys.exit(1)
    
    bot_id = int(sys.argv[1])
    iq_email = sys.argv[2]
    iq_password = sys.argv[3]
    
    logger.info("="*60)
    logger.info("Trading Bot Runner")
    logger.info("="*60)
    
    # Test database connection
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Failed to connect to database")
        sys.exit(1)
    
    logger.info("✓ Database connection successful")
    
    # Authenticate with IQ Option
    logger.info(f"Authenticating with IQ Option as {iq_email}...")
    try:
        client = authenticate_or_raise(iq_email, iq_password)
        logger.info("✓ IQ Option authentication successful")
    except Exception as e:
        logger.error(f"Failed to authenticate with IQ Option: {e}")
        sys.exit(1)
    
    # Initialize bot service
    logger.info(f"Initializing bot {bot_id}...")
    try:
        bot_service = TradingBotService(bot_id, client)
        logger.info(f"✓ Bot initialized: {bot_service.bot_config.name}")
        logger.info(f"  Strategy: {bot_service.bot_config.strategy}")
        logger.info(f"  Active: {bot_service.bot_config.active_id}")
        logger.info(f"  Initial Amount: {bot_service.bot_config.initial_amount}")
        logger.info(f"  Duration: {bot_service.bot_config.duration} minute(s)")
        logger.info(f"  Account Type: {bot_service.bot_config.account_type}")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        sys.exit(1)
    
    # Start bot
    logger.info("="*60)
    logger.info("Starting bot...")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    
    try:
        bot_service.start()
        
        # Keep running until interrupted
        while bot_service.is_running:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal, stopping bot...")
        bot_service.stop()
        logger.info("✓ Bot stopped successfully")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        bot_service.stop()
        sys.exit(1)
    
    finally:
        # Cleanup
        try:
            client.close()
        except:
            pass
    
    logger.info("="*60)
    logger.info("Bot runner finished")
    logger.info("="*60)


if __name__ == "__main__":
    main()
