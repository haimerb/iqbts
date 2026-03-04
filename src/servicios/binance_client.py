"""Binance API client wrapper with authentication."""

import logging
from typing import Optional, Dict, Any, List
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)


class BinanceClientWrapper:
    """Wrapper for Binance API client with enhanced error handling."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (True) or production (False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            # Testnet endpoints
            self.client = Client(
                api_key,
                api_secret,
                testnet=True
            )
            logger.info("Initialized Binance TESTNET client")
        else:
            # Production endpoints
            self.client = Client(api_key, api_secret)
            logger.warning("Initialized Binance PRODUCTION client - real money at risk!")
        
        self._symbol_info_cache = {}
    
    def test_connection(self) -> bool:
        """Test if API credentials are valid."""
        try:
            self.client.ping()
            account = self.client.get_account()
            logger.info(f"Connection successful. Account status: {account['accountType']}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def get_account_balance(self, asset: str = "USDT") -> float:
        """Get balance for a specific asset."""
        try:
            balance = self.client.get_asset_balance(asset=asset)
            if balance:
                return float(balance['free'])
            return 0.0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def get_all_balances(self) -> List[Dict[str, Any]]:
        """Get all non-zero balances."""
        try:
            account = self.client.get_account()
            balances = []
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    balances.append({
                        'asset': balance['asset'],
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    })
            return balances
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get trading rules and info for a symbol."""
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]
        
        try:
            exchange_info = self.client.get_symbol_info(symbol)
            self._symbol_info_cache[symbol] = exchange_info
            return exchange_info
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get candlestick data.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "1m", "5m", "15m", "1h", "4h", "1d")
            limit: Number of candles to retrieve (max 1000)
        
        Returns:
            List of candle dicts with OHLCV data
        """
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            candles = []
            for k in klines:
                candles.append({
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7]),
                    'trades': int(k[8])
                })
            
            return candles
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []
    
    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity according to symbol's LOT_SIZE filter."""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return str(quantity)
        
        # Find LOT_SIZE filter
        lot_size_filter = None
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                lot_size_filter = f
                break
        
        if lot_size_filter:
            step_size = float(lot_size_filter['stepSize'])
            # Calculate precision from step size
            precision = len(str(step_size).rstrip('0').split('.')[-1])
            
            # Round down to step size
            quantity_decimal = Decimal(str(quantity))
            step_decimal = Decimal(str(step_size))
            rounded = (quantity_decimal // step_decimal) * step_decimal
            
            return f"{rounded:.{precision}f}"
        
        return str(quantity)
    
    def create_market_buy_order(self, symbol: str, quantity: Optional[float] = None, 
                                 quote_quantity: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Create a market buy order.
        
        Args:
            symbol: Trading pair
            quantity: Amount of base asset to buy (e.g., 0.001 BTC)
            quote_quantity: Amount in quote asset to spend (e.g., 10 USDT)
        
        Returns:
            Order response dict or None on error
        """
        try:
            if quantity:
                # Buy specific amount of base asset
                formatted_qty = self._format_quantity(symbol, quantity)
                logger.info(f"Creating MARKET BUY order for {symbol}: {formatted_qty}")
                order = self.client.order_market_buy(symbol=symbol, quantity=formatted_qty)
            elif quote_quantity:
                # Buy with specific quote amount
                logger.info(f"Creating MARKET BUY order for {symbol}: {quote_quantity} USDT")
                order = self.client.order_market_buy(symbol=symbol, quoteOrderQty=quote_quantity)
            else:
                logger.error("Must specify either quantity or quote_quantity")
                return None
            
            logger.info(f"Order executed: {order['orderId']}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API error creating buy order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating buy order: {e}")
            return None
    
    def create_market_sell_order(self, symbol: str, quantity: float) -> Optional[Dict[str, Any]]:
        """Create a market sell order."""
        try:
            formatted_qty = self._format_quantity(symbol, quantity)
            logger.info(f"Creating MARKET SELL order for {symbol}: {formatted_qty}")
            order = self.client.order_market_sell(symbol=symbol, quantity=formatted_qty)
            logger.info(f"Order executed: {order['orderId']}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API error creating sell order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating sell order: {e}")
            return None
    
    def create_limit_buy_order(self, symbol: str, quantity: float, price: float) -> Optional[Dict[str, Any]]:
        """Create a limit buy order."""
        try:
            formatted_qty = self._format_quantity(symbol, quantity)
            logger.info(f"Creating LIMIT BUY order for {symbol}: {formatted_qty} @ {price}")
            order = self.client.order_limit_buy(
                symbol=symbol,
                quantity=formatted_qty,
                price=str(price)
            )
            logger.info(f"Order created: {order['orderId']}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API error creating limit buy order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating limit buy order: {e}")
            return None
    
    def create_limit_sell_order(self, symbol: str, quantity: float, price: float) -> Optional[Dict[str, Any]]:
        """Create a limit sell order."""
        try:
            formatted_qty = self._format_quantity(symbol, quantity)
            logger.info(f"Creating LIMIT SELL order for {symbol}: {formatted_qty} @ {price}")
            order = self.client.order_limit_sell(
                symbol=symbol,
                quantity=formatted_qty,
                price=str(price)
            )
            logger.info(f"Order created: {order['orderId']}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Binance API error creating limit sell order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating limit sell order: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """Cancel an open order."""
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_order(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order status."""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return order
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders."""
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()
            return orders
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    def get_24h_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24h price change statistics."""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return {
                'price': float(ticker['lastPrice']),
                'price_change': float(ticker['priceChange']),
                'price_change_percent': float(ticker['priceChangePercent']),
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'volume': float(ticker['volume']),
                'quote_volume': float(ticker['quoteVolume'])
            }
        except Exception as e:
            logger.error(f"Error getting 24h ticker: {e}")
            return None
