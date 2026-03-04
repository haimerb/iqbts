"""Trading strategies adapted for Binance crypto trading."""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import ta  # Technical Analysis library

logger = logging.getLogger(__name__)


class BinanceSignal:
    """Trading signal for Binance."""
    
    def __init__(self, signal_type: str, confidence: float, reason: str, 
                 stop_loss: Optional[float] = None, take_profit: Optional[float] = None):
        """
        Initialize signal.
        
        Args:
            signal_type: "BUY" or "SELL"
            confidence: Signal confidence (0-1)
            reason: Human-readable reason for signal
            stop_loss: Suggested stop loss price
            take_profit: Suggested take profit price
        """
        self.signal_type = signal_type.upper()
        self.confidence = confidence
        self.reason = reason
        self.stop_loss = stop_loss
        self.take_profit = take_profit


class BinanceStrategy(ABC):
    """Abstract base class for Binance trading strategies."""
    
    @abstractmethod
    def analyze(self, candles: List[Dict[str, Any]], current_price: float) -> Optional[BinanceSignal]:
        """
        Analyze market data and generate trading signal.
        
        Args:
            candles: List of candle dicts with OHLCV data
            current_price: Current market price
        
        Returns:
            BinanceSignal or None if no signal
        """
        pass
    
    @abstractmethod
    def get_position_size(self, balance: float, risk_percent: float = 2.0) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            balance: Available balance in USDT
            risk_percent: Percentage of balance to risk (default 2%)
        
        Returns:
            Position size in USDT
        """
        pass


class BinanceRSIStrategy(BinanceStrategy):
    """RSI-based strategy for crypto trading."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize RSI strategy.
        
        Config parameters:
            - rsi_period: RSI calculation period (default: 14)
            - oversold_level: Oversold threshold (default: 30)
            - overbought_level: Overbought threshold (default: 70)
            - position_size_percent: Position size as % of balance (default: 5.0)
            - stop_loss_percent: Stop loss % (default: 3.0)
            - take_profit_percent: Take profit % (default: 6.0)
        """
        self.rsi_period = config.get('rsi_period', 14)
        self.oversold_level = config.get('oversold_level', 30)
        self.overbought_level = config.get('overbought_level', 70)
        self.position_size_percent = config.get('position_size_percent', 5.0)
        self.stop_loss_percent = config.get('stop_loss_percent', 3.0)
        self.take_profit_percent = config.get('take_profit_percent', 6.0)
        
        logger.info(f"Initialized RSI strategy: period={self.rsi_period}, "
                   f"oversold={self.oversold_level}, overbought={self.overbought_level}")
    
    def analyze(self, candles: List[Dict[str, Any]], current_price: float) -> Optional[BinanceSignal]:
        """Analyze with RSI indicator."""
        if len(candles) < self.rsi_period + 1:
            logger.warning(f"Not enough candles for RSI calculation: {len(candles)} < {self.rsi_period + 1}")
            return None
        
        try:
            # Extract close prices
            closes = [c['close'] for c in candles]
            
            # Calculate RSI using ta library
            import pandas as pd
            df = pd.DataFrame({'close': closes})
            rsi = ta.momentum.RSIIndicator(df['close'], window=self.rsi_period).rsi()
            current_rsi = rsi.iloc[-1]
            
            logger.info(f"Current RSI: {current_rsi:.2f}")
            
            # Generate signals
            if current_rsi < self.oversold_level:
                # Oversold - BUY signal
                confidence = (self.oversold_level - current_rsi) / self.oversold_level
                stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                take_profit = current_price * (1 + self.take_profit_percent / 100)
                
                return BinanceSignal(
                    signal_type="BUY",
                    confidence=min(confidence, 1.0),
                    reason=f"RSI oversold: {current_rsi:.2f} < {self.oversold_level}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            elif current_rsi > self.overbought_level:
                # Overbought - SELL signal
                confidence = (current_rsi - self.overbought_level) / (100 - self.overbought_level)
                stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                return BinanceSignal(
                    signal_type="SELL",
                    confidence=min(confidence, 1.0),
                    reason=f"RSI overbought: {current_rsi:.2f} > {self.overbought_level}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}", exc_info=True)
            return None
    
    def get_position_size(self, balance: float, risk_percent: float = 2.0) -> float:
        """Calculate position size."""
        return balance * (self.position_size_percent / 100)


class BinanceMACDStrategy(BinanceStrategy):
    """MACD-based strategy for trend following."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MACD strategy.
        
        Config parameters:
            - fast_period: Fast EMA period (default: 12)
            - slow_period: Slow EMA period (default: 26)
            - signal_period: Signal line period (default: 9)
            - position_size_percent: Position size (default: 5.0)
            - stop_loss_percent: Stop loss % (default: 2.5)
            - take_profit_percent: Take profit % (default: 5.0)
        """
        self.fast_period = config.get('fast_period', 12)
        self.slow_period = config.get('slow_period', 26)
        self.signal_period = config.get('signal_period', 9)
        self.position_size_percent = config.get('position_size_percent', 5.0)
        self.stop_loss_percent = config.get('stop_loss_percent', 2.5)
        self.take_profit_percent = config.get('take_profit_percent', 5.0)
        
        logger.info(f"Initialized MACD strategy: {self.fast_period}/{self.slow_period}/{self.signal_period}")
    
    def analyze(self, candles: List[Dict[str, Any]], current_price: float) -> Optional[BinanceSignal]:
        """Analyze with MACD indicator."""
        min_candles = self.slow_period + self.signal_period + 1
        if len(candles) < min_candles:
            logger.warning(f"Not enough candles for MACD: {len(candles)} < {min_candles}")
            return None
        
        try:
            import pandas as pd
            closes = [c['close'] for c in candles]
            df = pd.DataFrame({'close': closes})
            
            # Calculate MACD
            macd_indicator = ta.trend.MACD(
                df['close'],
                window_fast=self.fast_period,
                window_slow=self.slow_period,
                window_sign=self.signal_period
            )
            
            macd_line = macd_indicator.macd()
            signal_line = macd_indicator.macd_signal()
            histogram = macd_indicator.macd_diff()
            
            # Get last two values to detect crossovers
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_hist = histogram.iloc[-1]
            
            prev_macd = macd_line.iloc[-2]
            prev_signal = signal_line.iloc[-2]
            prev_hist = histogram.iloc[-2]
            
            logger.info(f"MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, Hist: {current_hist:.4f}")
            
            # Bullish crossover: MACD crosses above signal
            if prev_macd < prev_signal and current_macd > current_signal:
                confidence = min(abs(current_hist) / current_price * 100, 1.0)
                stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                take_profit = current_price * (1 + self.take_profit_percent / 100)
                
                return BinanceSignal(
                    signal_type="BUY",
                    confidence=confidence,
                    reason=f"MACD bullish crossover (histogram: {current_hist:.4f})",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            # Bearish crossover: MACD crosses below signal
            elif prev_macd > prev_signal and current_macd < current_signal:
                confidence = min(abs(current_hist) / current_price * 100, 1.0)
                stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                return BinanceSignal(
                    signal_type="SELL",
                    confidence=confidence,
                    reason=f"MACD bearish crossover (histogram: {current_hist:.4f})",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}", exc_info=True)
            return None
    
    def get_position_size(self, balance: float, risk_percent: float = 2.0) -> float:
        """Calculate position size."""
        return balance * (self.position_size_percent / 100)


class BinanceBollingerBandsStrategy(BinanceStrategy):
    """Bollinger Bands mean reversion strategy."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bollinger Bands strategy.
        
        Config parameters:
            - period: Moving average period (default: 20)
            - std_dev: Standard deviation multiplier (default: 2.0)
            - position_size_percent: Position size (default: 5.0)
            - stop_loss_percent: Stop loss % (default: 3.0)
            - take_profit_percent: Take profit % (default: 4.0)
        """
        self.period = config.get('period', 20)
        self.std_dev = config.get('std_dev', 2.0)
        self.position_size_percent = config.get('position_size_percent', 5.0)
        self.stop_loss_percent = config.get('stop_loss_percent', 3.0)
        self.take_profit_percent = config.get('take_profit_percent', 4.0)
        
        logger.info(f"Initialized Bollinger Bands strategy: period={self.period}, std_dev={self.std_dev}")
    
    def analyze(self, candles: List[Dict[str, Any]], current_price: float) -> Optional[BinanceSignal]:
        """Analyze with Bollinger Bands."""
        if len(candles) < self.period + 1:
            logger.warning(f"Not enough candles for BB: {len(candles)} < {self.period + 1}")
            return None
        
        try:
            import pandas as pd
            closes = [c['close'] for c in candles]
            df = pd.DataFrame({'close': closes})
            
            # Calculate Bollinger Bands
            bb_indicator = ta.volatility.BollingerBands(
                df['close'],
                window=self.period,
                window_dev=self.std_dev
            )
            
            upper_band = bb_indicator.bollinger_hband().iloc[-1]
            lower_band = bb_indicator.bollinger_lband().iloc[-1]
            middle_band = bb_indicator.bollinger_mavg().iloc[-1]
            
            logger.info(f"BB: Upper={upper_band:.2f}, Middle={middle_band:.2f}, Lower={lower_band:.2f}, Price={current_price:.2f}")
            
            # Price touches or breaks lower band - BUY signal (oversold)
            if current_price <= lower_band:
                distance_from_band = (lower_band - current_price) / lower_band * 100
                confidence = min(distance_from_band / 2, 1.0)  # Scale to 0-1
                stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                take_profit = middle_band  # Target middle band
                
                return BinanceSignal(
                    signal_type="BUY",
                    confidence=confidence,
                    reason=f"Price at lower BB: {current_price:.2f} <= {lower_band:.2f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            # Price touches or breaks upper band - SELL signal (overbought)
            elif current_price >= upper_band:
                distance_from_band = (current_price - upper_band) / upper_band * 100
                confidence = min(distance_from_band / 2, 1.0)
                stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                take_profit = middle_band  # Target middle band
                
                return BinanceSignal(
                    signal_type="SELL",
                    confidence=confidence,
                    reason=f"Price at upper BB: {current_price:.2f} >= {upper_band:.2f}",
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}", exc_info=True)
            return None
    
    def get_position_size(self, balance: float, risk_percent: float = 2.0) -> float:
        """Calculate position size."""
        return balance * (self.position_size_percent / 100)


def get_binance_strategy(strategy_name: str, config: Dict[str, Any]) -> Optional[BinanceStrategy]:
    """Factory function to get strategy instance by name."""
    strategies = {
        'rsi': BinanceRSIStrategy,
        'macd': BinanceMACDStrategy,
        'bollinger': BinanceBollingerBandsStrategy,
        'bollinger_bands': BinanceBollingerBandsStrategy,
        'bb': BinanceBollingerBandsStrategy
    }
    
    strategy_class = strategies.get(strategy_name.lower())
    if strategy_class:
        return strategy_class(config)
    
    logger.error(f"Unknown strategy: {strategy_name}")
    return None
