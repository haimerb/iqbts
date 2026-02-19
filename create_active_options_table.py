"""Script to create the active_options table in the database."""

import logging
from src.servicios.database import init_db, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Failed to connect to database. Please check your configuration.")
        exit(1)
    
    logger.info("Creating/updating database tables...")
    try:
        init_db()
        logger.info("✓ Tables created/updated successfully!")
        logger.info("The 'active_options' table is now ready to use.")
    except Exception as e:
        logger.error("Failed to create tables: %s", str(e))
        exit(1)
