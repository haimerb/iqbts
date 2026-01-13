"""Database connection module for PostgreSQL."""

import logging
import os
from typing import Any, Dict

import yaml
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
Base = declarative_base()


def _load_settings() -> Dict[str, Any]:
    """Load settings from YAML configuration file."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        content = SETTINGS_PATH.read_text(encoding="utf-8")
    except OSError:
        logger.warning(
            "Unable to read %s; proceeding with defaults.", SETTINGS_PATH, exc_info=True
        )
        return {}
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError:
        logger.warning(
            "Unable to parse %s; proceeding with defaults.", SETTINGS_PATH, exc_info=True
        )
        return {}
    return data if isinstance(data, dict) else {}


def _get_db_url() -> str:
    """Build PostgreSQL connection URL from settings and environment variables."""
    settings = _load_settings()
    db_settings = settings.get("database", {})
    
    # Get values from environment or use defaults from settings
    host = os.getenv(db_settings.get("host_env", "DB_HOST")) or db_settings.get("host", "localhost")
    port = os.getenv(db_settings.get("port_env", "DB_PORT")) or db_settings.get("port", "5432")
    user = os.getenv(db_settings.get("user_env", "DB_USER")) or db_settings.get("user", "iqbts_user")
    password = os.getenv(db_settings.get("password_env", "DB_PASSWORD")) or db_settings.get("password", "iqbts_password")
    name = os.getenv(db_settings.get("name_env", "DB_NAME")) or db_settings.get("name", "iqbts_db")
    
    # Construct connection URL
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    logger.info("Database URL configured: postgresql://%s:***@%s:%s/%s", user, host, port, name)
    return db_url


def get_engine():
    """Create and return SQLAlchemy engine for PostgreSQL."""
    db_url = _get_db_url()
    try:
        engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Test connections before using them
            poolclass=NullPool,  # Use for development; consider QueuePool for production
        )
        return engine
    except Exception as e:
        logger.error("Failed to create database engine: %s", str(e))
        raise


def get_session():
    """Create and return a database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables initialized")


def test_connection() -> bool:
    """Test the database connection."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return False
