"""Trading strategies for the bot."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Represents a trading signal."""
    signal_type: str  # "call" or "put"
    confidence: float  # 0.0 to 1.0
    reason: str
    timestamp: datetime


class TradingStrategy(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.last_signals: List[TradingSignal] = []
    
    @abstractmethod
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[TradingSignal]:
        """Analyze market data and return a trading signal if found."""
        pass
    
    @abstractmethod
    def get_next_amount(self, last_result: Optional[str], current_amount: float, initial_amount: float, max_amount: float) -> float:
        """Calculate the next trade amount based on strategy and previous result."""
        pass
    
    def get_name(self) -> str:
        """Return strategy name."""
        return self.__class__.__name__


class SimpleMovingAverageCrossStrategy(TradingStrategy):
    """Strategy based on simple moving average crossovers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.fast_period = self.config.get("fast_period", 5)
        self.slow_period = self.config.get("slow_period", 20)
    
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[TradingSignal]:
        """
        Analyze using SMA crossover.
        BUY (CALL) when fast SMA crosses above slow SMA.
        SELL (PUT) when fast SMA crosses below slow SMA.
        """
        if len(candles) < self.slow_period:
            logger.debug("Not enough candles for SMA strategy")
            return None
        
        # Calculate SMAs
        closes = [float(c.get("close", 0)) for c in candles[-self.slow_period:]]
        
        if not closes or any(c == 0 for c in closes):
            return None
        
        fast_sma = sum(closes[-self.fast_period:]) / self.fast_period
        slow_sma = sum(closes) / self.slow_period
        
        # Previous SMAs (for crossover detection)
        prev_closes = closes[:-1]
        if len(prev_closes) < self.slow_period:
            return None
            
        prev_fast_sma = sum(prev_closes[-self.fast_period:]) / self.fast_period
        prev_slow_sma = sum(prev_closes) / self.slow_period
        
        # Detect crossover
        if prev_fast_sma <= prev_slow_sma and fast_sma > slow_sma:
            # Bullish crossover
            signal = TradingSignal(
                signal_type="call",
                confidence=0.7,
                reason=f"Bullish SMA crossover (Fast: {fast_sma:.5f}, Slow: {slow_sma:.5f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
        
        elif prev_fast_sma >= prev_slow_sma and fast_sma < slow_sma:
            # Bearish crossover
            signal = TradingSignal(
                signal_type="put",
                confidence=0.7,
                reason=f"Bearish SMA crossover (Fast: {fast_sma:.5f}, Slow: {slow_sma:.5f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
        
        return None
    
    def get_next_amount(self, last_result: Optional[str], current_amount: float, initial_amount: float, max_amount: float) -> float:
        """Fixed amount strategy - always use initial amount."""
        return min(initial_amount, max_amount)


class MartingaleStrategy(TradingStrategy):
    """Martingale strategy - double bet after loss."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.multiplier = self.config.get("multiplier", 2.2)
        self.reset_on_win = self.config.get("reset_on_win", True)
    
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[TradingSignal]:
        """
        Simple trend following based on recent candles.
        Uses the last 3 candles to determine trend.
        """
        if len(candles) < 5:
            logger.debug("Not enough candles for Martingale strategy")
            return None
        
        recent_candles = candles[-5:]
        closes = [float(c.get("close", 0)) for c in recent_candles]
        
        if not closes or any(c == 0 for c in closes):
            return None
        
        # Simple trend detection
        avg_early = sum(closes[:3]) / 3
        avg_recent = sum(closes[-3:]) / 3
        
        trend_strength = abs(avg_recent - avg_early) / avg_early
        
        if trend_strength < 0.001:  # Too weak
            return None
        
        if avg_recent > avg_early:
            # Uptrend
            signal = TradingSignal(
                signal_type="call",
                confidence=min(0.6 + trend_strength * 10, 0.9),
                reason=f"Uptrend detected (strength: {trend_strength:.4f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
        else:
            # Downtrend
            signal = TradingSignal(
                signal_type="put",
                confidence=min(0.6 + trend_strength * 10, 0.9),
                reason=f"Downtrend detected (strength: {trend_strength:.4f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
    
    def get_next_amount(self, last_result: Optional[str], current_amount: float, initial_amount: float, max_amount: float) -> float:
        """
        Martingale: multiply amount after loss, reset to initial after win.
        """
        if last_result is None:
            return initial_amount
        
        if last_result == "won":
            return initial_amount
        elif last_result == "lost":
            next_amount = current_amount * self.multiplier
            return min(next_amount, max_amount)
        
        return initial_amount


class RSIStrategy(TradingStrategy):
    """Strategy based on Relative Strength Index (RSI)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.period = self.config.get("period", 14)
        self.oversold = self.config.get("oversold", 30)
        self.overbought = self.config.get("overbought", 70)
    
    def calculate_rsi(self, closes: List[float]) -> Optional[float]:
        """Calculate RSI."""
        if len(closes) < self.period + 1:
            return None
        
        # Calculate price changes
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [c if c > 0 else 0 for c in changes[-self.period:]]
        losses = [-c if c < 0 else 0 for c in changes[-self.period:]]
        
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def analyze(self, candles: List[Dict], current_price: float) -> Optional[TradingSignal]:
        """
        Analyze using RSI.
        BUY (CALL) when RSI crosses above oversold level.
        SELL (PUT) when RSI crosses below overbought level.
        """
        if len(candles) < self.period + 2:
            logger.debug("Not enough candles for RSI strategy")
            return None
        
        closes = [float(c.get("close", 0)) for c in candles]
        
        if not closes or any(c == 0 for c in closes):
            return None
        
        rsi = self.calculate_rsi(closes)
        prev_rsi = self.calculate_rsi(closes[:-1])
        
        if rsi is None or prev_rsi is None:
            return None
        
        # Oversold -> Buy signal
        if prev_rsi <= self.oversold and rsi > self.oversold:
            signal = TradingSignal(
                signal_type="call",
                confidence=0.75,
                reason=f"RSI crossed above oversold level (RSI: {rsi:.2f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
        
        # Overbought -> Sell signal
        elif prev_rsi >= self.overbought and rsi < self.overbought:
            signal = TradingSignal(
                signal_type="put",
                confidence=0.75,
                reason=f"RSI crossed below overbought level (RSI: {rsi:.2f})",
                timestamp=datetime.utcnow()
            )
            self.last_signals.append(signal)
            return signal
        
        return None
    
    def get_next_amount(self, last_result: Optional[str], current_amount: float, initial_amount: float, max_amount: float) -> float:
        """Fixed amount strategy."""
        return min(initial_amount, max_amount)


# Strategy registry
STRATEGIES = {
    "sma_cross": SimpleMovingAverageCrossStrategy,
    "martingale": MartingaleStrategy,
    "rsi": RSIStrategy,
}


def get_strategy(strategy_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[TradingStrategy]:
    """Get a trading strategy by name."""
    strategy_class = STRATEGIES.get(strategy_name.lower())
    if strategy_class:
        return strategy_class(config)
    return None
