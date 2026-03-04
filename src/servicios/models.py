"""Database models for the application."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from src.servicios.database import Base
import enum


class User(Base):
    """User model for storing authentication data."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class TradingSession(Base):
    """Trading session model for logging trades."""
    __tablename__ = "trading_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    login_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    logout_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradingSession(id={self.id}, user_id={self.user_id})>"


class Trade(Base):
    """Trade model for logging individual trades."""
    __tablename__ = "trades"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # 'call' or 'put'
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    profit_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, session_id={self.session_id}, symbol='{self.symbol}')>"


class ActiveOption(Base):
    """Model for storing active options from IQ Option."""
    __tablename__ = "active_options"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opcode: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ActiveOption(id={self.id}, opcode='{self.opcode}', is_enabled={self.is_enabled})>"


class BotStatus(enum.Enum):
    """Bot status enum."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class SignalType(enum.Enum):
    """Trading signal type."""
    CALL = "call"
    PUT = "put"


class SignalStatus(enum.Enum):
    """Trading signal status."""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    WON = "won"
    LOST = "lost"


class TradingBot(Base):
    """Model for trading bot configuration."""
    __tablename__ = "trading_bots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=BotStatus.STOPPED.value, nullable=False)
    active_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "EURUSD"
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "martingale", "fibonacci"
    initial_amount: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    max_amount: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # minutes
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_gain: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    account_type: Mapped[str] = mapped_column(String(20), default="PRACTICE")  # PRACTICE or REAL
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional strategy config
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradingBot(id={self.id}, name='{self.name}', status='{self.status}')>"


class TradingSignal(Base):
    """Model for trading signals and execution results."""
    __tablename__ = "trading_signals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    active_id: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # CALL or PUT
    status: Mapped[str] = mapped_column(String(20), default=SignalStatus.PENDING.value, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<TradingSignal(id={self.id}, bot_id={self.bot_id}, signal_type='{self.signal_type}', status='{self.status}')>"


# ==================== BINANCE MODELS ====================

class BinanceOrderType(enum.Enum):
    """Binance order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LOSS_LIMIT = "stop_loss_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class BinanceOrderSide(enum.Enum):
    """Binance order side."""
    BUY = "buy"
    SELL = "sell"


class BinancePositionSide(enum.Enum):
    """Position side for futures trading."""
    LONG = "long"
    SHORT = "short"
    BOTH = "both"  # For one-way mode


class BinanceApiKey(Base):
    """Model for storing Binance API credentials."""
    __tablename__ = "binance_api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Friendly name
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    api_secret: Mapped[str] = mapped_column(String(255), nullable=False)  # Should be encrypted
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=True)  # Testnet vs production
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BinanceApiKey(id={self.id}, name='{self.name}', testnet={self.is_testnet})>"


class BinanceBot(Base):
    """Model for Binance trading bot configuration."""
    __tablename__ = "binance_bots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    api_key_id: Mapped[int] = mapped_column(Integer, nullable=False)  # References BinanceApiKey
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=BotStatus.STOPPED.value, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "BTCUSDT"
    market_type: Mapped[str] = mapped_column(String(20), default="spot")  # spot, futures, margin
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "grid", "dca", "swing"
    initial_amount: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)  # USDT
    max_amount: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    stop_loss_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g., 5.0 for 5%
    take_profit_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g., 10.0 for 10%
    max_daily_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Max loss per day in USDT
    max_daily_gain: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Max gain per day in USDT
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    leverage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)  # For futures
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional strategy config
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BinanceBot(id={self.id}, name='{self.name}', symbol='{self.symbol}', status='{self.status}')>"


class BinanceTrade(Base):
    """Model for Binance trade execution records."""
    __tablename__ = "binance_trades"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    order_side: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY or SELL
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)  # MARKET, LIMIT, etc.
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # Amount of crypto
    quote_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Amount in USDT
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # In USDT
    profit_loss_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    client_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    commission: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Trading fee
    commission_asset: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # BNB, USDT, etc.
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<BinanceTrade(id={self.id}, bot_id={self.bot_id}, symbol='{self.symbol}', side='{self.order_side}', status='{self.status}')>"


class BinancePosition(Base):
    """Model for tracking open positions (for futures/margin)."""
    __tablename__ = "binance_positions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    position_side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG or SHORT
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)  # open, closed
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, default=1)
    stop_loss_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BinancePosition(id={self.id}, symbol='{self.symbol}', side='{self.position_side}', status='{self.status}')>"


