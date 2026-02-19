"""Trading bot service with IQ Option integration."""

from __future__ import annotations

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from threading import Thread, Event

from src.servicios.database import get_session
from src.servicios.models import TradingBot, TradingSignal, BotStatus, SignalStatus, SignalType
from src.servicios.trading_strategies import get_strategy, TradingStrategy

logger = logging.getLogger(__name__)


class TradingBotService:
    """Service for managing trading bot operations."""
    
    def __init__(self, bot_id: int, iq_client: Any):
        """
        Initialize trading bot service.
        
        Args:
            bot_id: Database ID of the bot configuration
            iq_client: IQ Option API client instance
        """
        self.bot_id = bot_id
        self.client = iq_client
        self.bot_config: Optional[TradingBot] = None
        self.strategy: Optional[TradingStrategy] = None
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.is_running = False
        
        # Load bot configuration
        self._load_config()
    
    def _load_config(self):
        """Load bot configuration from database."""
        session = get_session()
        try:
            self.bot_config = session.query(TradingBot).filter_by(id=self.bot_id).first()
            if not self.bot_config:
                raise ValueError(f"Bot with ID {self.bot_id} not found")
            
            # Validate active_id format for IQ Option
            active_id = self.bot_config.active_id
            if not active_id:
                raise ValueError("active_id is required")
            
            # Ensure active_id is in correct format (usually just the pair name like "EURUSD")
            # IQ Option sometimes needs it without special characters
            logger.info(f"Bot will trade on: {active_id}")
            
            # Load strategy
            strategy_config = {}
            if self.bot_config.config_json:
                try:
                    strategy_config = json.loads(self.bot_config.config_json)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse bot config JSON")
            
            self.strategy = get_strategy(self.bot_config.strategy, strategy_config)
            if not self.strategy:
                raise ValueError(f"Unknown strategy: {self.bot_config.strategy}")
            
            logger.info(f"Loaded bot config: {self.bot_config.name} with strategy {self.bot_config.strategy}")
        finally:
            session.close()
    
    def start(self):
        """Start the trading bot in a separate thread."""
        if self.is_running:
            logger.warning("Bot is already running")
            return False
        
        self.stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
        self.is_running = True
        
        # Update bot status in database
        self._update_bot_status(BotStatus.RUNNING.value)
        
        logger.info(f"Trading bot {self.bot_id} started")
        return True
    
    def stop(self):
        """Stop the trading bot."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return False
        
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        
        self.is_running = False
        self._update_bot_status(BotStatus.STOPPED.value)
        
        logger.info(f"Trading bot {self.bot_id} stopped")
        return True
    
    def _update_bot_status(self, status: str):
        """Update bot status in database."""
        session = get_session()
        try:
            bot = session.query(TradingBot).filter_by(id=self.bot_id).first()
            if bot:
                bot.status = status
                bot.updated_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            logger.error(f"Error updating bot status: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _check_limits(self, session) -> bool:
        """Check if bot has reached daily limits."""
        if not self.bot_config:
            return False
        
        # Check max trades per day
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_trades = session.query(TradingSignal).filter(
            TradingSignal.bot_id == self.bot_id,
            TradingSignal.created_at >= today_start,
            TradingSignal.status.in_([SignalStatus.EXECUTED.value, SignalStatus.WON.value, SignalStatus.LOST.value])
        ).count()
        
        if today_trades >= self.bot_config.max_trades_per_day:
            logger.info(f"Bot {self.bot_id} reached max trades per day: {today_trades}")
            return False
        
        # Check stop loss
        if self.bot_config.stop_loss:
            signals = session.query(TradingSignal).filter(
                TradingSignal.bot_id == self.bot_id,
                TradingSignal.created_at >= today_start,
                TradingSignal.profit_loss.isnot(None)
            ).all()
            
            total_pnl = sum(s.profit_loss for s in signals if s.profit_loss)
            
            if total_pnl <= -abs(self.bot_config.stop_loss):
                logger.info(f"Bot {self.bot_id} hit stop loss: {total_pnl}")
                return False
        
        # Check stop gain
        if self.bot_config.stop_gain:
            signals = session.query(TradingSignal).filter(
                TradingSignal.bot_id == self.bot_id,
                TradingSignal.created_at >= today_start,
                TradingSignal.profit_loss.isnot(None)
            ).all()
            
            total_pnl = sum(s.profit_loss for s in signals if s.profit_loss)
            
            if total_pnl >= self.bot_config.stop_gain:
                logger.info(f"Bot {self.bot_id} hit stop gain: {total_pnl}")
                return False
        
        return True
    
    def _get_candles(self, active_id: str, duration: int, count: int = 100) -> List[Dict]:
        """Get historical candle data."""
        try:
            # Get candles from IQ Option API
            # duration is in minutes, API expects seconds
            end_time = time.time()
            logger.info(f"Requesting {count} candles for {active_id} (duration: {duration}m)")
            candles = self.client.get_candles(active_id, duration * 60, count, end_time)
            
            if candles and isinstance(candles, list):
                logger.info(f"Received {len(candles)} candles for {active_id}")
                # Convert to list of dicts if needed
                result = []
                for candle in candles:
                    if isinstance(candle, dict):
                        result.append(candle)
                    else:
                        # If it's an object, convert to dict
                        result.append({
                            'open': float(getattr(candle, 'open', 0)),
                            'high': float(getattr(candle, 'max', 0)),
                            'low': float(getattr(candle, 'min', 0)),
                            'close': float(getattr(candle, 'close', 0)),
                            'volume': float(getattr(candle, 'volume', 0)),
                        })
                logger.debug(f"Latest candle close: {result[-1]['close']}")
                return result
            else:
                logger.warning(f"No candles received for {active_id} or invalid format")
        except Exception as e:
            logger.error(f"Error getting candles for {active_id}: {e}", exc_info=True)
        
        return []
    
    def _is_market_open(self, active_id: str) -> bool:
        """Check if a market is currently open for trading."""
        try:
            all_actives = self.client.get_all_open_time()
            
            if not all_actives or active_id not in all_actives:
                logger.warning(f"Market {active_id} not found in active list")
                return False
            
            active_info = all_actives[active_id]
            if not isinstance(active_info, dict):
                return False
            
            binary = active_info.get("binary", {})
            turbo = active_info.get("turbo", {})
            
            binary_enabled = binary.get("enabled", False)
            turbo_enabled = turbo.get("enabled", False)
            
            is_open = binary_enabled or turbo_enabled
            
            if is_open:
                logger.info(f"✅ Market {active_id} is OPEN (Binary: {binary_enabled}, Turbo: {turbo_enabled})")
            else:
                logger.warning(f"❌ Market {active_id} is CLOSED")
            
            return is_open
        
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            # En caso de error, intentamos igual (la API rechazará si está cerrado)
            return True
    
    def _execute_trade(self, signal_type: str, amount: float, duration: int, active_id: str) -> Optional[Dict[str, Any]]:
        """Execute a trade on IQ Option."""
        try:
            # PASO 1: Verificar si el mercado está abierto
            logger.info(f"Checking if {active_id} is open...")
            if not self._is_market_open(active_id):
                logger.error(f"❌ Cannot trade: Market {active_id} is currently CLOSED or SUSPENDED")
                logger.error(f"   Please check market hours or try a different active")
                return None
            
            # Set account type (PRACTICE or REAL)
            account_type = self.bot_config.account_type if self.bot_config else "PRACTICE"
            logger.info(f"Setting account type to: {account_type}")
            self.client.change_balance(account_type)
            
            # Wait a moment for balance change
            time.sleep(1)
            
            # Verify balance
            balance = self.client.get_balance()
            logger.info(f"Current balance: ${balance}")
            
            if balance < amount:
                logger.error(f"Insufficient balance: ${balance} < ${amount}")
                return None
            
            # Log trade parameters
            logger.info(f"Executing trade:")
            logger.info(f"  Type: {signal_type.upper()}")
            logger.info(f"  Active: {active_id}")
            logger.info(f"  Amount: ${amount}")
            logger.info(f"  Duration: {duration} minute(s)")
            
            # Check which type of options are available
            all_actives = None
            try:
                all_actives = self.client.get_all_open_time()
            except Exception as e:
                logger.warning(f"Could not get market status: {e}")
                logger.info("Proceeding with trade attempt anyway...")
            
            option_type = "binary"  # default
            
            if all_actives and active_id in all_actives:
                active_info = all_actives[active_id]
                if isinstance(active_info, dict):
                    turbo_enabled = active_info.get("turbo", {}).get("enabled", False)
                    binary_enabled = active_info.get("binary", {}).get("enabled", False)
                    
                    if duration <= 5 and turbo_enabled:
                        option_type = "turbo"
                        logger.info(f"Using TURBO options (duration <= 5 min)")
                    elif binary_enabled:
                        option_type = "binary"
                        logger.info(f"Using BINARY options")
                    else:
                        logger.warning(f"⚠️  Market {active_id} may be closed")
                        logger.warning(f"   Binary enabled: {binary_enabled}")
                        logger.warning(f"   Turbo enabled: {turbo_enabled}")
                        logger.info("Attempting trade anyway - IQ Option will reject if truly closed")
            else:
                logger.info(f"Could not verify market status, attempting trade anyway...")
            
            # Buy option based on duration
            if duration <= 5:
                # For short durations (1-5 min), use buy() which typically uses turbo
                logger.info(f"Attempting to buy option (duration: {duration}m)...")
                check, order_id = self.client.buy(
                    amount,
                    active_id,
                    signal_type.lower(),
                    duration
                )
            else:
                # For longer durations, might need different method
                logger.info(f"Attempting to buy digital option...")
                check, order_id = self.client.buy_digital_spot(
                    active_id,
                    amount,
                    signal_type.lower(),
                    duration
                )
            
            logger.info(f"Buy response - check: {check}, order_id: {order_id}")
            
            if check:
                logger.info(f"✅ Trade executed successfully!")
                logger.info(f"   Order ID: {order_id}")
                return {
                    "success": True,
                    "order_id": str(order_id),
                    "signal_type": signal_type,
                    "amount": amount,
                    "active_id": active_id
                }
            else:
                error_msg = f"Trade rejected by IQ Option. Response: {order_id}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Possible reasons:")
                logger.error(f"  - Market is closed")
                logger.error(f"  - Amount too small/large")
                logger.error(f"  - Invalid active_id format")
                logger.error(f"  - Trading restrictions on account")
                
                return None
        
        except Exception as e:
            logger.error(f"❌ Exception executing trade: {e}", exc_info=True)
            return None
    
    def _check_trade_result(self, order_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """Check the result of a trade."""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if option is closed
                result = self.client.check_win_v3(order_id)
                
                if result is not None and result != 0:
                    return {
                        "result": "won" if result > 0 else "lost",
                        "profit_loss": float(result)
                    }
                
                time.sleep(5)  # Check every 5 seconds
            
            logger.warning(f"Timeout checking trade result for order {order_id}")
            return None
        
        except Exception as e:
            logger.error(f"Error checking trade result: {e}")
            return None
    
    def _run(self):
        """Main bot loop."""
        logger.info(f"Bot {self.bot_id} main loop started")
        logger.info(f"Trading on: {self.bot_config.active_id if self.bot_config else 'Unknown'}")
        logger.info(f"Strategy: {self.bot_config.strategy if self.bot_config else 'Unknown'}")
        
        if not self.bot_config or not self.strategy:
            logger.error("Bot configuration or strategy not loaded")
            self._update_bot_status(BotStatus.ERROR.value)
            return
        
        last_trade_amount = self.bot_config.initial_amount
        last_trade_result = None
        iteration = 0
        
        while not self.stop_event.is_set():
            try:
                iteration += 1
                logger.info(f"=== Bot iteration {iteration} ===")
                
                session = get_session()
                try:
                    # Check limits
                    if not self._check_limits(session):
                        logger.info(f"Bot {self.bot_id} stopped due to limits")
                        break
                    
                    # Get market data
                    logger.info(f"Fetching market data for {self.bot_config.active_id}...")
                    candles = self._get_candles(
                        self.bot_config.active_id,
                        self.bot_config.duration,
                        100
                    )
                    
                    if not candles:
                        logger.warning("No candles received, waiting 10 seconds...")
                        time.sleep(10)
                        continue
                    
                    logger.info(f"Successfully retrieved {len(candles)} candles")
                    
                    # Get current price from the last candle
                    current_price = candles[-1].get("close")
                    if not current_price or current_price <= 0:
                        logger.warning(f"Invalid current price ({current_price}), waiting 10 seconds...")
                        time.sleep(10)
                        continue
                    
                    logger.info(f"Current price: {current_price}")
                    
                    # Analyze with strategy
                    logger.info(f"Analyzing market with {self.bot_config.strategy} strategy...")
                    signal = self.strategy.analyze(candles, current_price)
                    
                    if signal:
                        logger.info(f"🎯 Signal detected: {signal.signal_type.upper()} - {signal.reason} (confidence: {signal.confidence:.2f})")
                        
                        # Calculate trade amount
                        trade_amount = self.strategy.get_next_amount(
                            last_trade_result,
                            last_trade_amount,
                            self.bot_config.initial_amount,
                            self.bot_config.max_amount
                        )
                        
                        logger.info(f"💰 Trade amount: ${trade_amount}")
                        
                        # Create signal record in database
                        db_signal = TradingSignal(
                            bot_id=self.bot_id,
                            active_id=self.bot_config.active_id,
                            signal_type=signal.signal_type.upper(),
                            status=SignalStatus.PENDING.value,
                            amount=trade_amount,
                            duration=self.bot_config.duration,
                            entry_price=current_price
                        )
                        session.add(db_signal)
                        session.commit()
                        
                        # Execute trade
                        trade_result = self._execute_trade(
                            signal.signal_type,
                            trade_amount,
                            self.bot_config.duration,
                            self.bot_config.active_id
                        )
                        
                        if trade_result:
                            # Update signal with execution info
                            db_signal.status = SignalStatus.EXECUTED.value
                            db_signal.order_id = trade_result["order_id"]
                            db_signal.executed_at = datetime.utcnow()
                            session.commit()
                            
                            last_trade_amount = trade_amount
                            
                            # Wait for trade to complete
                            wait_time = self.bot_config.duration * 60 + 30  # duration + 30 seconds buffer
                            logger.info(f"Waiting {wait_time} seconds for trade to complete...")
                            
                            for _ in range(wait_time):
                                if self.stop_event.is_set():
                                    break
                                time.sleep(1)
                            
                            # Check result
                            result = self._check_trade_result(trade_result["order_id"])
                            
                            if result:
                                db_signal.status = SignalStatus.WON.value if result["result"] == "won" else SignalStatus.LOST.value
                                db_signal.profit_loss = result["profit_loss"]
                                db_signal.closed_at = datetime.utcnow()
                                session.commit()
                                
                                last_trade_result = result["result"]
                                logger.info(f"Trade {result['result']}: PnL = {result['profit_loss']}")
                            else:
                                logger.warning("Could not determine trade result")
                        else:
                            # Trade execution failed
                            db_signal.status = SignalStatus.CANCELLED.value
                            db_signal.error_message = "Trade execution failed"
                            session.commit()
                            logger.error("❌ Trade execution failed")
                            
                            # Check if market is closed - wait longer before retrying
                            if not self._is_market_open(self.bot_config.active_id):
                                logger.warning(f"⏸️  Market {self.bot_config.active_id} is CLOSED")
                                logger.warning(f"   Bot will wait 5 minutes before checking again...")
                                logger.warning(f"   (You can stop the bot anytime with /bot/{self.bot_id}/stop)")
                                
                                # Wait 5 minutes with stop check
                                for _ in range(300):  # 5 minutes = 300 seconds
                                    if self.stop_event.is_set():
                                        break
                                    time.sleep(1)
                                continue  # Skip the normal wait time
                    else:
                        logger.info("No signal detected, continuing to monitor...")
                    
                    # Wait before next analysis
                    logger.info("Waiting 30 seconds before next analysis...")
                    time.sleep(30)  # Check for signals every 30 seconds
                
                finally:
                    session.close()
            
            except Exception as e:
                logger.error(f"Error in bot loop: {e}", exc_info=True)
                self._update_bot_status(BotStatus.ERROR.value)
                time.sleep(60)  # Wait 1 minute before retrying
        
        self._update_bot_status(BotStatus.STOPPED.value)
        logger.info(f"Bot {self.bot_id} main loop ended")
