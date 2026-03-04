"""Binance bot API endpoints."""

import logging
import json
from flask import request, jsonify
from datetime import datetime

from src.servicios.api import app, token_required
from src.servicios.database import get_session
from src.servicios.models import (
    BinanceBot, BinanceTrade, BinanceApiKey, BotStatus, User
)
from src.servicios.binance_client import BinanceClientWrapper
from src.servicios.binance_bot_service import BinanceBotService

logger = logging.getLogger(__name__)

# Active Binance bot instances
_active_binance_bots = {}


@app.route("/binance/api-key/create", methods=["POST"])
@token_required
def create_binance_api_key(current_user):
    """Create a new Binance API key entry."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'api_key', 'api_secret']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"Missing required field: {field}"}), 400
        
        session = get_session()
        try:
            # Test the API key first
            is_testnet = data.get('is_testnet', True)
            client = BinanceClientWrapper(
                api_key=data['api_key'],
                api_secret=data['api_secret'],
                testnet=is_testnet
            )
            
            if not client.test_connection():
                return jsonify({
                    "message": "Failed to connect with provided API credentials",
                    "error": "Invalid API key or secret"
                }), 400
            
            # Create API key entry
            api_key = BinanceApiKey(
                user_id=current_user,
                name=data['name'],
                api_key=data['api_key'],
                api_secret=data['api_secret'],  # TODO: Consider encrypting this
                is_testnet=is_testnet,
                is_active=True
            )
            
            session.add(api_key)
            session.commit()
            
            return jsonify({
                "message": "Binance API key created successfully",
                "api_key": {
                    "id": api_key.id,
                    "name": api_key.name,
                    "is_testnet": api_key.is_testnet,
                    "created_at": api_key.created_at.isoformat()
                }
            }), 201
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        return jsonify({"message": "Error creating API key", "error": str(e)}), 500


@app.route("/binance/api-key/list", methods=["GET"])
@token_required
def list_binance_api_keys(current_user):
    """List all Binance API keys for current user."""
    session = get_session()
    try:
        api_keys = session.query(BinanceApiKey).filter_by(
            user_id=current_user
        ).order_by(BinanceApiKey.created_at.desc()).all()
        
        return jsonify({
            "message": "API keys retrieved successfully",
            "count": len(api_keys),
            "api_keys": [{
                "id": k.id,
                "name": k.name,
                "is_testnet": k.is_testnet,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat()
            } for k in api_keys]
        }), 200
    
    finally:
        session.close()


@app.route("/binance/api-key/<int:key_id>/balance", methods=["GET"])
@token_required
def get_binance_balance(current_user, key_id):
    """Get Binance account balance."""
    session = get_session()
    try:
        api_key = session.query(BinanceApiKey).filter_by(
            id=key_id,
            user_id=current_user,
            is_active=True
        ).first()
        
        if not api_key:
            return jsonify({"message": "API key not found"}), 404
        
        client = BinanceClientWrapper(
            api_key=api_key.api_key,
            api_secret=api_key.api_secret,
            testnet=api_key.is_testnet
        )
        
        balances = client.get_all_balances()
        
        return jsonify({
            "message": "Balance retrieved successfully",
            "testnet": api_key.is_testnet,
            "balances": balances
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting balance: {e}", exc_info=True)
        return jsonify({"message": "Error getting balance", "error": str(e)}), 500
    finally:
        session.close()


@app.route("/binance/bot/create", methods=["POST"])
@token_required
def create_binance_bot(current_user):
    """Create a new Binance trading bot."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'api_key_id', 'symbol', 'strategy']
        for field in required_fields:
            if field not in data:
                return jsonify({"message": f"Missing required field: {field}"}), 400
        
        session = get_session()
        try:
            # Verify API key belongs to user
            api_key = session.query(BinanceApiKey).filter_by(
                id=data['api_key_id'],
                user_id=current_user,
                is_active=True
            ).first()
            
            if not api_key:
                return jsonify({"message": "API key not found or not active"}), 404
            
            # Create bot
            bot = BinanceBot(
                user_id=current_user,
                api_key_id=data['api_key_id'],
                name=data['name'],
                symbol=data['symbol'].upper(),
                market_type=data.get('market_type', 'spot'),
                strategy=data['strategy'],
                initial_amount=data.get('initial_amount', 10.0),
                max_amount=data.get('max_amount', 1000.0),
                stop_loss_percent=data.get('stop_loss_percent'),
                take_profit_percent=data.get('take_profit_percent'),
                max_daily_loss=data.get('max_daily_loss'),
                max_daily_gain=data.get('max_daily_gain'),
                max_trades_per_day=data.get('max_trades_per_day', 20),
                leverage=data.get('leverage', 1),
                config_json=json.dumps(data.get('config', {})),
                status=BotStatus.STOPPED.value
            )
            
            session.add(bot)
            session.commit()
            
            logger.info(f"Created Binance bot: {bot.name} (ID: {bot.id})")
            
            return jsonify({
                "message": "Binance bot created successfully",
                "bot": {
                    "id": bot.id,
                    "name": bot.name,
                    "symbol": bot.symbol,
                    "strategy": bot.strategy,
                    "status": bot.status,
                    "market_type": bot.market_type,
                    "created_at": bot.created_at.isoformat()
                }
            }), 201
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error creating Binance bot: {e}", exc_info=True)
        return jsonify({"message": "Error creating bot", "error": str(e)}), 500


@app.route("/binance/bot/list", methods=["GET"])
@token_required
def list_binance_bots(current_user):
    """List all Binance bots for current user."""
    session = get_session()
    try:
        bots = session.query(BinanceBot).filter_by(
            user_id=current_user
        ).order_by(BinanceBot.created_at.desc()).all()
        
        return jsonify({
            "message": "Binance bots retrieved successfully",
            "count": len(bots),
            "bots": [{
                "id": b.id,
                "name": b.name,
                "symbol": b.symbol,
                "strategy": b.strategy,
                "status": b.status,
                "market_type": b.market_type,
                "created_at": b.created_at.isoformat()
            } for b in bots]
        }), 200
    
    finally:
        session.close()


@app.route("/binance/bot/<int:bot_id>", methods=["GET"])
@token_required
def get_binance_bot(current_user, bot_id):
    """Get details of a specific Binance bot."""
    session = get_session()
    try:
        bot = session.query(BinanceBot).filter_by(
            id=bot_id,
            user_id=current_user
        ).first()
        
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Parse config JSON
        config = {}
        if bot.config_json:
            try:
                config = json.loads(bot.config_json)
            except:
                pass
        
        return jsonify({
            "message": "Bot retrieved successfully",
            "bot": {
                "id": bot.id,
                "name": bot.name,
                "status": bot.status,
                "symbol": bot.symbol,
                "market_type": bot.market_type,
                "strategy": bot.strategy,
                "initial_amount": bot.initial_amount,
                "max_amount": bot.max_amount,
                "stop_loss_percent": bot.stop_loss_percent,
                "take_profit_percent": bot.take_profit_percent,
                "max_daily_loss": bot.max_daily_loss,
                "max_daily_gain": bot.max_daily_gain,
                "max_trades_per_day": bot.max_trades_per_day,
                "leverage": bot.leverage,
                "config": config,
                "created_at": bot.created_at.isoformat(),
                "updated_at": bot.updated_at.isoformat()
            }
        }), 200
    
    finally:
        session.close()


@app.route("/binance/bot/<int:bot_id>/start", methods=["POST"])
@token_required
def start_binance_bot(current_user, bot_id):
    """Start a Binance trading bot."""
    session = get_session()
    try:
        bot = session.query(BinanceBot).filter_by(
            id=bot_id,
            user_id=current_user
        ).first()
        
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        if bot_id in _active_binance_bots:
            return jsonify({"message": "Bot is already running"}), 400
        
        # Create and start bot service
        try:
            bot_service = BinanceBotService(bot_id)
            if bot_service.start():
                _active_binance_bots[bot_id] = bot_service
                
                logger.info(f"Started Binance bot {bot_id}")
                return jsonify({
                    "message": f"Binance bot '{bot.name}' started successfully",
                    "bot_id": bot_id,
                    "status": "running"
                }), 200
            else:
                return jsonify({"message": "Failed to start bot"}), 500
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            return jsonify({"message": "Error starting bot", "error": str(e)}), 500
    
    finally:
        session.close()


@app.route("/binance/bot/<int:bot_id>/stop", methods=["POST"])
@token_required
def stop_binance_bot(current_user, bot_id):
    """Stop a running Binance bot."""
    session = get_session()
    try:
        bot = session.query(BinanceBot).filter_by(
            id=bot_id,
            user_id=current_user
        ).first()
        
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        if bot_id not in _active_binance_bots:
            return jsonify({"message": "Bot is not running"}), 400
        
        # Stop bot service
        bot_service = _active_binance_bots[bot_id]
        if bot_service.stop():
            del _active_binance_bots[bot_id]
            
            logger.info(f"Stopped Binance bot {bot_id}")
            return jsonify({
                "message": f"Binance bot '{bot.name}' stopped successfully",
                "bot_id": bot_id,
                "status": "stopped"
            }), 200
        else:
            return jsonify({"message": "Failed to stop bot"}), 500
    
    finally:
        session.close()


@app.route("/binance/bot/<int:bot_id>/trades", methods=["GET"])
@token_required
def get_binance_bot_trades(current_user, bot_id):
    """Get trade history for a Binance bot."""
    session = get_session()
    try:
        # Verify bot belongs to user
        bot = session.query(BinanceBot).filter_by(
            id=bot_id,
            user_id=current_user
        ).first()
        
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Get limit from query params
        limit = request.args.get('limit', 50, type=int)
        
        # Get trades
        trades = session.query(BinanceTrade).filter_by(
            bot_id=bot_id
        ).order_by(BinanceTrade.created_at.desc()).limit(limit).all()
        
        # Calculate statistics
        total_pnl = sum(t.profit_loss for t in trades if t.profit_loss)
        wins = sum(1 for t in trades if t.profit_loss and t.profit_loss > 0)
        losses = sum(1 for t in trades if t.profit_loss and t.profit_loss < 0)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        return jsonify({
            "message": "Trades retrieved successfully",
            "bot_name": bot.name,
            "count": len(trades),
            "statistics": {
                "total_trades": len(trades),
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2) if total_pnl else 0
            },
            "trades": [{
                "id": t.id,
                "symbol": t.symbol,
                "side": t.order_side,
                "type": t.order_type,
                "status": t.status,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "profit_loss": t.profit_loss,
                "profit_loss_percent": t.profit_loss_percent,
                "created_at": t.created_at.isoformat()
            } for t in trades]
        }), 200
    
    finally:
        session.close()


@app.route("/binance/bot/<int:bot_id>/delete", methods=["DELETE"])
@token_required
def delete_binance_bot(current_user, bot_id):
    """Delete a Binance bot."""
    session = get_session()
    try:
        bot = session.query(BinanceBot).filter_by(
            id=bot_id,
            user_id=current_user
        ).first()
        
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Stop bot if running
        if bot_id in _active_binance_bots:
            bot_service = _active_binance_bots[bot_id]
            bot_service.stop()
            del _active_binance_bots[bot_id]
        
        # Delete bot
        session.delete(bot)
        session.commit()
        
        logger.info(f"Deleted Binance bot {bot_id}")
        return jsonify({"message": f"Bot '{bot.name}' deleted successfully"}), 200
    
    finally:
        session.close()


@app.route("/binance/strategies", methods=["GET"])
@token_required
def list_binance_strategies(current_user):
    """List available Binance trading strategies."""
    strategies = [
        {
            "name": "rsi",
            "display_name": "RSI (Relative Strength Index)",
            "description": "Mean reversion strategy based on RSI oversold/overbought levels",
            "parameters": {
                "rsi_period": {"type": "int", "default": 14, "description": "RSI calculation period"},
                "oversold_level": {"type": "float", "default": 30, "description": "Oversold threshold"},
                "overbought_level": {"type": "float", "default": 70, "description": "Overbought threshold"},
                "position_size_percent": {"type": "float", "default": 5.0, "description": "Position size as % of balance"},
                "stop_loss_percent": {"type": "float", "default": 3.0, "description": "Stop loss %"},
                "take_profit_percent": {"type": "float", "default": 6.0, "description": "Take profit %"}
            }
        },
        {
            "name": "macd",
            "display_name": "MACD Crossover",
            "description": "Trend following strategy based on MACD line and signal line crossovers",
            "parameters": {
                "fast_period": {"type": "int", "default": 12, "description": "Fast EMA period"},
                "slow_period": {"type": "int", "default": 26, "description": "Slow EMA period"},
                "signal_period": {"type": "int", "default": 9, "description": "Signal line period"},
                "position_size_percent": {"type": "float", "default": 5.0, "description": "Position size %"},
                "stop_loss_percent": {"type": "float", "default": 2.5, "description": "Stop loss %"},
                "take_profit_percent": {"type": "float", "default": 5.0, "description": "Take profit %"}
            }
        },
        {
            "name": "bollinger",
            "display_name": "Bollinger Bands",
            "description": "Mean reversion when price touches upper or lower bands",
            "parameters": {
                "period": {"type": "int", "default": 20, "description": "Moving average period"},
                "std_dev": {"type": "float", "default": 2.0, "description": "Standard deviation multiplier"},
                "position_size_percent": {"type": "float", "default": 5.0, "description": "Position size %"},
                "stop_loss_percent": {"type": "float", "default": 3.0, "description": "Stop loss %"},
                "take_profit_percent": {"type": "float", "default": 4.0, "description": "Take profit %"}
            }
        }
    ]
    
    return jsonify({
        "message": "Strategies retrieved successfully",
        "count": len(strategies),
        "strategies": strategies
    }), 200
