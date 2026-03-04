"""Binance trading bot service with automated trading logic."""

from __future__ import annotations

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from threading import Thread, Event

from src.servicios.database import get_session
from src.servicios.models import (
    BinanceBot, BinanceTrade, BinancePosition, BinanceApiKey,
    BotStatus, BinanceOrderSide
)
from src.servicios.binance_client import BinanceClientWrapper
from src.servicios.binance_strategies import get_binance_strategy, BinanceStrategy

logger = logging.getLogger(__name__)


class BinanceBotService:
    """Service for managing Binance trading bot operations."""
    
    def __init__(self, bot_id: int):
        """
        Initialize Binance bot service.
        
        Args:
            bot_id: Database ID of the bot configuration
        """
        self.bot_id = bot_id
        self.bot_config: Optional[BinanceBot] = None
        self.client: Optional[BinanceClientWrapper] = None
        self.strategy: Optional[BinanceStrategy] = None
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.is_running = False
        self.current_position: Optional[Dict[str, Any]] = None
        
        # Load bot configuration and initialize client
        self._load_config()
    
    def _load_config(self):
        """Load bot configuration and initialize Binance client."""
        session = get_session()
        try:
            # Load bot config
            self.bot_config = session.query(BinanceBot).filter_by(id=self.bot_id).first()
            if not self.bot_config:
                raise ValueError(f"Bot with ID {self.bot_id} not found")
            
            # Load API key
            api_key_obj = session.query(BinanceApiKey).filter_by(
                id=self.bot_config.api_key_id,
                is_active=True
            ).first()
            
            if not api_key_obj:
                raise ValueError(f"API key {self.bot_config.api_key_id} not found or inactive")
            
            # Initialize Binance client
            self.client = BinanceClientWrapper(
                api_key=api_key_obj.api_key,
                api_secret=api_key_obj.api_secret,
                testnet=api_key_obj.is_testnet
            )
            
            # Test connection
            if not self.client.test_connection():
                raise ValueError("Failed to connect to Binance API")
            
            logger.info(f"Bot will trade {self.bot_config.symbol} on {self.bot_config.market_type}")
            
            # Load strategy
            strategy_config = {}
            if self.bot_config.config_json:
                try:
                    strategy_config = json.loads(self.bot_config.config_json)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse bot config JSON")
            
            self.strategy = get_binance_strategy(self.bot_config.strategy, strategy_config)
            if not self.strategy:
                raise ValueError(f"Unknown strategy: {self.bot_config.strategy}")
            
            logger.info(f"Loaded bot config: {self.bot_config.name} with strategy {self.bot_config.strategy}")
        finally:
            session.close()
    
    def start(self) -> bool:
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
        
        logger.info(f"Binance bot {self.bot_id} started")
        return True
    
    def stop(self) -> bool:
        """Stop the trading bot."""
        if not self.is_running:
            logger.warning("Bot is not running")
            return False
        
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        
        self.is_running = False
        self._update_bot_status(BotStatus.STOPPED.value)
        
        logger.info(f"Binance bot {self.bot_id} stopped")
        return True
    
    def _update_bot_status(self, status: str):
        """Update bot status in database."""
        session = get_session()
        try:
            bot = session.query(BinanceBot).filter_by(id=self.bot_id).first()
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
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check max trades per day
        today_trades = session.query(BinanceTrade).filter(
            BinanceTrade.bot_id == self.bot_id,
            BinanceTrade.created_at >= today_start,
            BinanceTrade.status.in_(['executed', 'filled', 'closed'])
        ).count()
        
        if today_trades >= self.bot_config.max_trades_per_day:
            logger.info(f"Bot {self.bot_id} reached max trades per day: {today_trades}")
            return False
        
        # Check daily loss limit
        if self.bot_config.max_daily_loss:
            trades = session.query(BinanceTrade).filter(
                BinanceTrade.bot_id == self.bot_id,
                BinanceTrade.created_at >= today_start,
                BinanceTrade.profit_loss.isnot(None)
            ).all()
            
            total_pnl = sum(t.profit_loss for t in trades if t.profit_loss)
            
            if total_pnl <= -abs(self.bot_config.max_daily_loss):
                logger.info(f"Bot {self.bot_id} hit daily loss limit: {total_pnl:.2f} USDT")
                return False
        
        # Check daily gain limit
        if self.bot_config.max_daily_gain:
            trades = session.query(BinanceTrade).filter(
                BinanceTrade.bot_id == self.bot_id,
                BinanceTrade.created_at >= today_start,
                BinanceTrade.profit_loss.isnot(None)
            ).all()
            
            total_pnl = sum(t.profit_loss for t in trades if t.profit_loss)
            
            if total_pnl >= self.bot_config.max_daily_gain:
                logger.info(f"Bot {self.bot_id} hit daily gain limit: {total_pnl:.2f} USDT")
                return False
        
        return True
    
    def _get_current_position(self, session) -> Optional[Dict[str, Any]]:
        """Get current open position if any."""
        # For spot trading, check if we have base asset
        if self.bot_config.market_type == "spot":
            # Extract base asset from symbol (e.g., "BTC" from "BTCUSDT")
            base_asset = self.bot_config.symbol.replace("USDT", "").replace("BUSD", "")
            balance = self.client.get_account_balance(base_asset)
            
            if balance > 0:
                current_price = self.client.get_symbol_price(self.bot_config.symbol)
                return {
                    'type': 'spot',
                    'asset': base_asset,
                    'quantity': balance,
                    'current_price': current_price,
                    'value': balance * current_price if current_price else 0
                }
        
        # For futures, check open positions (would need futures API integration)
        # This is a simplified version for spot trading
        return None
    
    def _execute_buy(self, amount_usdt: float, signal: Any, session) -> Optional[int]:
        """Execute a buy order."""
        try:
            logger.info(f"Executing BUY order for {self.bot_config.symbol}")
            logger.info(f"Amount: {amount_usdt:.2f} USDT")
            logger.info(f"Reason: {signal.reason}")
            
            # Create market buy order
            order = self.client.create_market_buy_order(
                symbol=self.bot_config.symbol,
                quote_quantity=amount_usdt
            )
            
            if not order:
                logger.error("Failed to execute buy order")
                return None
            
            # Save trade to database
            trade = BinanceTrade(
                bot_id=self.bot_id,
                symbol=self.bot_config.symbol,
                order_side=BinanceOrderSide.BUY.value,
                order_type='market',
                status='executed',
                quote_quantity=amount_usdt,
                entry_price=float(order.get('fills', [{}])[0].get('price', 0)) if order.get('fills') else None,
                order_id=str(order['orderId']),
                client_order_id=order.get('clientOrderId'),
                executed_at=datetime.utcnow()
            )
            
            # Calculate quantity and commission
            if order.get('fills'):
                total_qty = sum(float(fill['qty']) for fill in order['fills'])
                total_commission = sum(float(fill['commission']) for fill in order['fills'])
                trade.quantity = total_qty
                trade.commission = total_commission
                trade.commission_asset = order['fills'][0].get('commissionAsset', 'USDT')
            
            session.add(trade)
            session.commit()
            
            logger.info(f"✅ BUY order executed: Order ID {order['orderId']}")
            logger.info(f"   Quantity: {trade.quantity if trade.quantity else 'N/A'}")
            logger.info(f"   Price: {trade.entry_price if trade.entry_price else 'N/A'}")
            
            return trade.id
        
        except Exception as e:
            logger.error(f"Error executing buy order: {e}", exc_info=True)
            return None
    
    def _execute_sell(self, quantity: float, signal: Any, session, entry_trade_id: Optional[int] = None) -> Optional[int]:
        """Execute a sell order."""
        try:
            logger.info(f"Executing SELL order for {self.bot_config.symbol}")
            logger.info(f"Quantity: {quantity}")
            logger.info(f"Reason: {signal.reason}")
            
            # Create market sell order
            order = self.client.create_market_sell_order(
                symbol=self.bot_config.symbol,
                quantity=quantity
            )
            
            if not order:
                logger.error("Failed to execute sell order")
                return None
            
            # Calculate average price and proceeds
            avg_price = None
            proceeds = 0
            if order.get('fills'):
                total_qty = sum(float(fill['qty']) for fill in order['fills'])
                total_proceeds = sum(float(fill['price']) * float(fill['qty']) for fill in order['fills'])
                avg_price = total_proceeds / total_qty if total_qty > 0 else None
                proceeds = total_proceeds
            
            # Save trade to database
            trade = BinanceTrade(
                bot_id=self.bot_id,
                symbol=self.bot_config.symbol,
                order_side=BinanceOrderSide.SELL.value,
                order_type='market',
                status='executed',
                quantity=quantity,
                quote_quantity=proceeds,
                exit_price=avg_price,
                order_id=str(order['orderId']),
                client_order_id=order.get('clientOrderId'),
                executed_at=datetime.utcnow()
            )
            
            # Calculate commission
            if order.get('fills'):
                total_commission = sum(float(fill['commission']) for fill in order['fills'])
                trade.commission = total_commission
                trade.commission_asset = order['fills'][0].get('commissionAsset', 'USDT')
            
            # Calculate P&L if we have entry trade
            if entry_trade_id:
                entry_trade = session.query(BinanceTrade).filter_by(id=entry_trade_id).first()
                if entry_trade and entry_trade.entry_price and avg_price:
                    # P&L = (sell_price - buy_price) * quantity - commissions
                    pnl = (avg_price - entry_trade.entry_price) * quantity
                    pnl -= (trade.commission or 0)
                    if entry_trade.commission:
                        # Convert entry commission to USDT if needed
                        pnl -= entry_trade.commission if entry_trade.commission_asset == 'USDT' else 0
                    
                    trade.profit_loss = pnl
                    trade.profit_loss_percent = (pnl / entry_trade.quote_quantity * 100) if entry_trade.quote_quantity else None
                    
                    logger.info(f"   P&L: {pnl:.2f} USDT ({trade.profit_loss_percent:.2f}%)")
            
            session.add(trade)
            session.commit()
            
            logger.info(f"✅ SELL order executed: Order ID {order['orderId']}")
            logger.info(f"   Price: {avg_price if avg_price else 'N/A'}")
            logger.info(f"   Proceeds: {proceeds:.2f} USDT")
            
            return trade.id
        
        except Exception as e:
            logger.error(f"Error executing sell order: {e}", exc_info=True)
            return None
    
    def _run(self):
        """Main bot loop."""
        logger.info(f"Binance bot {self.bot_id} main loop started")
        logger.info(f"Trading: {self.bot_config.symbol} ({self.bot_config.market_type})")
        logger.info(f"Strategy: {self.bot_config.strategy}")
        
        if not self.bot_config or not self.strategy or not self.client:
            logger.error("Bot configuration, strategy or client not loaded")
            self._update_bot_status(BotStatus.ERROR.value)
            return
        
        iteration = 0
        last_buy_trade_id = None
        
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
                    
                    # Check current position
                    position = self._get_current_position(session)
                    
                    # Get market data
                    logger.info(f"Fetching market data for {self.bot_config.symbol}...")
                    # Use appropriate timeframe based on strategy
                    interval = "5m"  # 5-minute candles
                    candles = self.client.get_klines(
                        symbol=self.bot_config.symbol,
                        interval=interval,
                        limit=100
                    )
                    
                    if not candles:
                        logger.warning("No candles received, waiting 30 seconds...")
                        time.sleep(30)
                        continue
                    
                    logger.info(f"Successfully retrieved {len(candles)} candles")
                    
                    # Get current price
                    current_price = self.client.get_symbol_price(self.bot_config.symbol)
                    if not current_price:
                        logger.warning("Could not get current price, waiting 30 seconds...")
                        time.sleep(30)
                        continue
                    
                    logger.info(f"Current price: {current_price:.2f} USDT")
                    
                    # Analyze with strategy
                    logger.info(f"Analyzing market with {self.bot_config.strategy} strategy...")
                    signal = self.strategy.analyze(candles, current_price)
                    
                    if signal:
                        logger.info(f"🎯 Signal detected: {signal.signal_type} - {signal.reason} (confidence: {signal.confidence:.2f})")
                        
                        if signal.signal_type == "BUY" and not position:
                            # We don't have a position, buy
                            usdt_balance = self.client.get_account_balance("USDT")
                            logger.info(f"USDT Balance: {usdt_balance:.2f}")
                            
                            # Calculate position size
                            position_size = self.strategy.get_position_size(usdt_balance)
                            position_size = min(position_size, self.bot_config.max_amount)
                            position_size = max(position_size, self.bot_config.initial_amount)
                            
                            if usdt_balance < position_size:
                                logger.warning(f"Insufficient balance: {usdt_balance:.2f} < {position_size:.2f}")
                            else:
                                trade_id = self._execute_buy(position_size, signal, session)
                                if trade_id:
                                    last_buy_trade_id = trade_id
                                    # Wait a bit before next analysis
                                    time.sleep(10)
                        
                        elif signal.signal_type == "SELL" and position:
                            # We have a position, sell it
                            trade_id = self._execute_sell(
                                position['quantity'],
                                signal,
                                session,
                                entry_trade_id=last_buy_trade_id
                            )
                            if trade_id:
                                last_buy_trade_id = None  # Reset after selling
                                time.sleep(10)
                        
                        else:
                            if signal.signal_type == "BUY" and position:
                                logger.info("BUY signal but already have position, ignoring")
                            elif signal.signal_type == "SELL" and not position:
                                logger.info("SELL signal but no position to sell, ignoring")
                    else:
                        logger.info("No signal detected, continuing to monitor...")
                    
                    # Wait before next analysis (30 seconds)
                    logger.info("Waiting 30 seconds before next analysis...")
                    for _ in range(30):
                        if self.stop_event.is_set():
                            break
                        time.sleep(1)
                
                finally:
                    session.close()
            
            except Exception as e:
                logger.error(f"Error in bot loop: {e}", exc_info=True)
                self._update_bot_status(BotStatus.ERROR.value)
                time.sleep(60)  # Wait 1 minute before retrying
        
        self._update_bot_status(BotStatus.STOPPED.value)
        logger.info(f"Binance bot {self.bot_id} main loop ended")
