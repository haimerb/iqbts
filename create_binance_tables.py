"""Create database tables for Binance bot functionality.""""""Create Binance trading bot tables in the database."""







































        sys.exit(1)        print(f"❌ Error creating tables: {e}")    except Exception as e:        create_binance_tables()    try:if __name__ == "__main__":    print("\n🚀 You can now use Binance trading bots!")    print("  - binance_positions")    print("  - binance_trades")    print("  - binance_bots")    print("  - binance_api_keys")    print("\nCreated tables:")    print("✅ Binance tables created successfully!")        ])        BinancePosition.__table__        BinanceTrade.__table__,        BinanceBot.__table__,        BinanceApiKey.__table__,    Base.metadata.create_all(engine, tables=[    # Create tables        print("Creating Binance tables...")    """Create all Binance-related tables."""def create_binance_tables():)    BinancePosition    BinanceTrade,    BinanceBot,    BinanceApiKey,from src.servicios.models import (from src.servicios.database import engine, Basesys.path.insert(0, '.')import sys
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.servicios.database import engine, Base
from src.servicios.models import (
    BinanceApiKey, BinanceBot, BinanceTrade, BinancePosition
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_binance_tables():
    """Create all Binance-related tables."""
    try:
        logger.info("Creating Binance tables...")
        
        # Create tables
        Base.metadata.create_all(
            engine,
            tables=[
                BinanceApiKey.__table__,
                BinanceBot.__table__,
                BinanceTrade.__table__,
                BinancePosition.__table__
            ]
        )
        
        logger.info("✅ Binance tables created successfully!")
        logger.info("")
        logger.info("Created tables:")
        logger.info("  - binance_api_keys")
        logger.info("  - binance_bots")
        logger.info("  - binance_trades")
        logger.info("  - binance_positions")
        logger.info("")
        logger.info("You can now:")
        logger.info("  1. Add your Binance API key: POST /binance/api-key/create")
        logger.info("  2. Create a bot: POST /binance/bot/create")
        logger.info("  3. Start trading: POST /binance/bot/<id>/start")
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    create_binance_tables()
