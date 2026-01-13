"""Database models for the application."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from src.servicios.database import Base


class User(Base):
    """User model for storing authentication data."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class TradingSession(Base):
    """Trading session model for logging trades."""
    __tablename__ = "trading_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(500), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow)
    logout_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradingSession(id={self.id}, user_id={self.user_id})>"


class Trade(Base):
    """Trade model for logging individual trades."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    symbol = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False)  # 'call' or 'put'
    amount = Column(Float, nullable=False)
    profit_loss = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade(id={self.id}, session_id={self.session_id}, symbol='{self.symbol}')>"
