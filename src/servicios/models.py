"""Database models for the application."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.servicios.database import Base


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
