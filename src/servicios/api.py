"""Simple Flask API that authenticates against IQ Option via iqoptionapi."""

from __future__ import annotations

import datetime
import logging
import os
import secrets
from functools import wraps
from pathlib import Path
from typing import Any, Dict

import bcrypt
import jwt
import yaml  # type: ignore[import-not-found]
from flask import Flask, jsonify, request

from src.servicios.iqoption_auth import authenticate

from src.servicios.database import get_session
from src.servicios.models import User
from src.servicios.models import TradingSession
from src.servicios.models import ActiveOption
from src.servicios.models import TradingBot, TradingSignal, BotStatus, SignalStatus
from src.servicios.trading_bot_service import TradingBotService
from src.servicios.trading_strategies import STRATEGIES
import json

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
DEFAULT_SECRET_ENV = "IQBTS_SECRET_KEY"


def _load_settings() -> Dict[str, Any]:
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


def _resolve_secret_key(settings: Dict[str, Any]) -> str:
    flask_settings = settings.get("flask") or {}
    env_name = flask_settings.get("secret_key_env")
    if env_name:
        secret = os.getenv(env_name)
        if secret:
            return secret

    secret = flask_settings.get("secret_key")
    if secret:
        return str(secret)

    secret = os.getenv(DEFAULT_SECRET_ENV)
    if secret:
        return secret

    generated = secrets.token_hex(32)
    logger.warning(
        "Generated ad-hoc Flask secret key. Configure %s or update config/settings.yaml.",
        env_name or DEFAULT_SECRET_ENV,
    )
    return generated


def _shutdown_client(client: Any) -> None:
    for attr in ("close", "disconnect"):
        method = getattr(client, attr, None)
        if callable(method):
            try:
                method()
            except Exception:
                logger.debug("Failed to invoke %s on IQ Option client", attr, exc_info=True)
            finally:
                break


SETTINGS = _load_settings()

app = Flask(__name__)
app.config["SECRET_KEY"] = _resolve_secret_key(SETTINGS)

_active_sessions: Dict[str, Any] = {}
_active_bots: Dict[int, TradingBotService] = {}  # bot_id -> TradingBotService


def _generate_token(username: str) -> str:
    payload = {
        "username": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        if token.startswith("Bearer "):
            token = token[7:]

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = data["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    session = get_session()
    user = session.query(User).filter_by(email=username).first()

    # Encode password for bcrypt
    password_bytes = password.encode('utf-8')

    if user is None:
        # New user: hash password and store
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Authenticate with IQ Option before creating user
        auth_result = authenticate(username, password)
        if not auth_result.success:
            logger.warning(
                "IQ Option authentication failed for new user %s: %s", username, auth_result.reason
            )
            return (
                jsonify(
                    {
                        "message": "Invalid IQ Option credentials",
                        "reason": auth_result.reason,
                    }
                ),
                401,
            )

        new_user = User(email=username, password_hash=password_hash.decode('utf-8'))
        session.add(new_user)
        session.commit()
        
        logger.info("New user %s created and stored in the database.", username)
        
        # Set user to new_user to continue with session creation
        user = new_user

    else:
        # Existing user: check password
        password_is_valid = False
        try:
            # Check against bcrypt hash
            password_is_valid = bcrypt.checkpw(password_bytes, user.password_hash.encode('utf-8'))
        except ValueError:
            # This may be a legacy plaintext password
            logger.warning("ValueError checking password for %s. Attempting legacy password upgrade.", username)
            if user.password_hash == password:
                logger.info("Legacy password matches for %s. Upgrading to bcrypt hash.", username)
                salt = bcrypt.gensalt()
                new_hash = bcrypt.hashpw(password_bytes, salt)
                user.password_hash = new_hash.decode('utf-8')
                session.commit()
                password_is_valid = True

        if not password_is_valid:
            logger.warning("Invalid password for user %s", username)
            return jsonify({"message": "Invalid credentials"}), 401
        
        if not user.is_active:
            logger.warning("User %s is inactive. Login denied.", username)
            return jsonify({"message": "User is inactive. Login denied."}), 423
        
        # Authenticate with IQ Option
        auth_result = authenticate(username, password)
        if not auth_result.success:
            logger.warning(
                "IQ Option authentication failed for existing user %s: %s", username, auth_result.reason
            )
            return (
                jsonify(
                    {
                        "message": "Invalid IQ Option credentials",
                        "reason": auth_result.reason,
                    }
                ),
                401,
            )

    # Manage IQ Option client session
    existing_client = _active_sessions.get(username)
    if existing_client is not None:
        _shutdown_client(existing_client)

    if auth_result.client is not None:
        _active_sessions[username] = auth_result.client

    token = _generate_token(username)

    # Manage database trading session
    old_tradingsession = session.query(TradingSession).filter_by(user_id=user.id, is_active=True).first()
    if old_tradingsession:
        old_tradingsession.is_active = False
        session.commit()
        logger.info("Deactivated old trading session for user %s.", username)

    new_tradingsession = TradingSession(
        user_id=user.id,
        token=token
    )
    session.add(new_tradingsession)
    session.commit()
    
    session.close()

    return jsonify({"token": token, "message": "Login successful"}), 200


@app.route("/logout", methods=["POST"])
@token_required
def logout(current_user):
    client = _active_sessions.pop(current_user, None)
    if client is not None:
        _shutdown_client(client)

    return (
        jsonify(
            {
                "message": "Logout successful",
                "session_cleared": client is not None,
            }
        ),
        200,
    )


@app.route("/protected", methods=["GET"])
@token_required
def protected_route(current_user):
    return (
        jsonify(
            {
                "message": f"Hello {current_user}",
                "iqoption_session_active": current_user in _active_sessions,
            }
        ),
        200,
    )


@app.route("/balance", methods=["GET"])
@token_required
def get_balance(current_user):
    """Get the current balance for the authenticated user from IQ Option."""
    client = _active_sessions.get(current_user)
    
    if client is None:
        return (
            jsonify(
                {
                    "message": "IQ Option session not active",
                    "error": "No active trading session found. Please login first.",
                }
            ),
            401,
        )
    
    try:
        balance = client.get_balance()
        
        if balance is None:
            return (
                jsonify(
                    {
                        "message": "Failed to retrieve balance",
                        "error": "IQ Option API returned None",
                    }
                ),
                500,
            )
        
        logger.info("Balance retrieved for user %s: %s", current_user, balance)
        
        return (
            jsonify(
                {
                    "message": "Balance retrieved successfully",
                    "balance": balance,
                    "user": current_user,
                }
            ),
            200,
        )
    
    except Exception as e:
        logger.error("Error retrieving balance for user %s: %s", current_user, str(e))
        return (
            jsonify(
                {
                    "message": "Error retrieving balance",
                    "error": str(e),
                }
            ),
            500,
        )


@app.route("/reset-practice-balance", methods=["POST"])
@token_required
def reset_practice_balance(current_user):
    """Reset the practice balance for the authenticated user from IQ Option."""
    client = _active_sessions.get(current_user)
    
    if client is None:
        return (
            jsonify(
                {
                    "message": "IQ Option session not active",
                    "error": "No active trading session found. Please login first.",
                }
            ),
            401,
        )
    
    try:
        result = client.reset_practice_balance()
        #logger.info("AQUI")
        if result:
            logger.info("Practice balance reset successfully for user %s", current_user)
            
            return (
                jsonify(
                    {
                        "message": "Practice balance reset successfully",
                        "user": current_user,
                        "status": "success",
                    }
                ),
                200,
            )
        else:
            logger.warning("Failed to reset practice balance for user %s: API returned False", current_user)
            
            return (
                jsonify(
                    {
                        "message": "Failed to reset practice balance",
                        "error": "IQ Option API returned False",
                    }
                ),
                500,
            )
    
    except Exception as e:
        logger.error("Error resetting practice balance for user %s: %s", current_user, str(e))
        return (
            jsonify(
                {
                    "message": "Error resetting practice balance",
                    "error": str(e),
                }
            ),
            500,
        )


@app.route("/all-actives-opcode", methods=["GET"])
@token_required
def get_all_actives_opcode(current_user):
    """Get all active OPCODE from IQ Option and store them in the database."""
    client = _active_sessions.get(current_user)
    
    if client is None:
        return (
            jsonify(
                {
                    "message": "IQ Option session not active",
                    "error": "No active trading session found. Please login first.",
                }
            ),
            401,
        )
    
    try:
        actives_opcode = client.get_all_ACTIVES_OPCODE()
        
        if actives_opcode is None:
            return (
                jsonify(
                    {
                        "message": "Failed to retrieve actives OPCODE",
                        "error": "IQ Option API returned None",
                    }
                ),
                500,
            )
        
        # Store actives in database
        session = get_session()
        try:
            stored_count = 0
            updated_count = 0
            
            # actives_opcode is typically a dict with opcode as key
            for opcode, opcode_data in actives_opcode.items():
                # Check if this opcode already exists
                existing_active = session.query(ActiveOption).filter_by(opcode=str(opcode)).first()
                
                if existing_active:
                    # Update existing record
                    existing_active.is_enabled = True
                    existing_active.last_updated = datetime.datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new record
                    new_active = ActiveOption(
                        opcode=str(opcode),
                        name=str(opcode_data) if opcode_data else None,
                        is_enabled=True
                    )
                    session.add(new_active)
                    stored_count += 1
            
            session.commit()
            logger.info(
                "Actives OPCODE stored for user %s: %d new, %d updated", 
                current_user, stored_count, updated_count
            )
            
        except Exception as db_error:
            session.rollback()
            logger.error("Database error storing actives: %s", str(db_error))
            return (
                jsonify(
                    {
                        "message": "Error storing actives in database",
                        "error": str(db_error),
                        "actives_opcode": actives_opcode,
                    }
                ),
                500,
            )
        finally:
            session.close()
        
        logger.info("Actives OPCODE retrieved for user %s", current_user)
        
        return (
            jsonify(
                {
                    "message": "Actives OPCODE retrieved and stored successfully",
                    "actives_opcode": actives_opcode,
                    "user": current_user,
                    "stored": stored_count,
                    "updated": updated_count,
                }
            ),
            200,
        )
    
    except Exception as e:
        logger.error("Error retrieving actives OPCODE for user %s: %s", current_user, str(e))
        return (
            jsonify(
                {
                    "message": "Error retrieving actives OPCODE",
                    "error": str(e),
                }
            ),
            500,
        )




@app.route("/test-candles/<active_id>", methods=["GET"])
@token_required
def test_candles(current_user, active_id):
    """Test getting candles for an active - useful for debugging."""
    import time
    
    client = _active_sessions.get(current_user)
    if client is None:
        return jsonify({
            "message": "IQ Option session not active",
            "error": "Please login first"
        }), 401
    
    try:
        # Get parameters
        duration = int(request.args.get("duration", 1))  # minutes
        count = int(request.args.get("count", 10))
        
        logger.info(f"Testing candles for {active_id}, duration: {duration}m, count: {count}")
        
        # Try to get candles
        end_time = time.time()
        candles = client.get_candles(active_id, duration * 60, count, end_time)
        
        if not candles:
            return jsonify({
                "message": "No candles received",
                "active_id": active_id,
                "duration": duration,
                "count": count,
                "suggestion": "Try using all_actives_opcode endpoint to get valid active IDs"
            }), 404
        
        # Format candles
        formatted_candles = []
        for candle in candles[:5]:  # Show only first 5
            if isinstance(candle, dict):
                formatted_candles.append({
                    "open": candle.get("open"),
                    "high": candle.get("max", candle.get("high")),
                    "low": candle.get("min", candle.get("low")),
                    "close": candle.get("close"),
                    "volume": candle.get("volume", 0)
                })
            else:
                formatted_candles.append({
                    "open": getattr(candle, "open", 0),
                    "high": getattr(candle, "max", getattr(candle, "high", 0)),
                    "low": getattr(candle, "min", getattr(candle, "low", 0)),
                    "close": getattr(candle, "close", 0),
                    "volume": getattr(candle, "volume", 0)
                })
        
        # Get current price from last candle
        last_candle = candles[-1]
        if isinstance(last_candle, dict):
            current_price = last_candle.get("close", 0)
        else:
            current_price = getattr(last_candle, "close", 0)
        
        return jsonify({
            "message": "Candles retrieved successfully",
            "active_id": active_id,
            "total_candles": len(candles),
            "current_price": current_price,
            "sample_candles": formatted_candles
        }), 200
    
    except Exception as e:
        logger.error(f"Error testing candles for {active_id}: {e}", exc_info=True)
        return jsonify({
            "message": "Error retrieving candles",
            "active_id": active_id,
            "error": str(e)
        }), 500


@app.route("/check-market/<active_id>", methods=["GET"])
@token_required
def check_market(current_user, active_id):
    """Check if a market is open and available for trading."""
    client = _active_sessions.get(current_user)
    if client is None:
        return jsonify({
            "message": "IQ Option session not active",
            "error": "Please login first"
        }), 401
    
    try:
        # Get all opened actives
        all_actives = None
        try:
            all_actives = client.get_all_open_time()
        except Exception as e:
            logger.warning(f"Error getting open time data: {e}")
        
        # Check if our active is in the list
        is_open = False
        binary_available = False
        turbo_available = False
        
        if all_actives and active_id in all_actives:
            active_info = all_actives[active_id]
            if isinstance(active_info, dict):
                binary_available = active_info.get("binary", {}).get("enabled", False)
                turbo_available = active_info.get("turbo", {}).get("enabled", False)
                is_open = binary_available or turbo_available
        
        # Get current balance
        balance = 0.0
        try:
            balance = client.get_balance()
        except Exception as e:
            logger.warning(f"Error getting balance: {e}")
        
        # Get account type
        account_type = "UNKNOWN"
        try:
            account_type = client.get_balance_mode()
        except Exception as e:
            logger.warning(f"Error getting account type: {e}")
        
        return jsonify({
            "message": "Market status retrieved",
            "active_id": active_id,
            "is_open": is_open,
            "binary_available": binary_available,
            "turbo_available": turbo_available,
            "account_type": account_type,
            "balance": balance,
            "recommendation": "Use 'turbo' for 1-5 minute trades" if turbo_available else "Binary not available right now"
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking market {active_id}: {e}", exc_info=True)
        return jsonify({
            "message": "Error checking market",
            "active_id": active_id,
            "error": str(e)
        }), 500


@app.route("/open-actives", methods=["GET"])
@token_required
def get_open_actives(current_user):
    """Get all currently open actives for trading."""
    client = _active_sessions.get(current_user)
    if client is None:
        return jsonify({
            "message": "IQ Option session not active",
            "error": "Please login first"
        }), 401
    
    # Common actives that are usually available during market hours
    common_actives = [
        {"active_id": "EURUSD", "binary_enabled": True, "turbo_enabled": True, "recommended": True},
        {"active_id": "GBPUSD", "binary_enabled": True, "turbo_enabled": True, "recommended": True},
        {"active_id": "USDJPY", "binary_enabled": True, "turbo_enabled": True, "recommended": True},
        {"active_id": "AUDUSD", "binary_enabled": True, "turbo_enabled": True, "recommended": True},
        {"active_id": "EURJPY", "binary_enabled": True, "turbo_enabled": True, "recommended": True},
        {"active_id": "USDCAD", "binary_enabled": True, "turbo_enabled": True, "recommended": False},
        {"active_id": "EURGBP", "binary_enabled": True, "turbo_enabled": True, "recommended": False},
        {"active_id": "AUDJPY", "binary_enabled": True, "turbo_enabled": True, "recommended": False},
        {"active_id": "NZDUSD", "binary_enabled": True, "turbo_enabled": True, "recommended": False},
    ]
    
    try:
        all_actives = None
        try:
            # Try to get live data
            logger.info("Attempting to get live market data...")
            all_actives = client.get_all_open_time()
            logger.info(f"get_all_open_time returned: {type(all_actives)}, length: {len(all_actives) if all_actives else 0}")
        except Exception as e:
            logger.warning(f"Error getting all open time: {e}")
        
        if not all_actives or len(all_actives) == 0:
            logger.warning("No live data available, returning common actives")
            import datetime
            now = datetime.datetime.utcnow()
            
            # Check if it's weekend (markets closed)
            is_weekend = now.weekday() >= 5  # 5=Saturday, 6=Sunday
            
            return jsonify({
                "message": "Using common actives (live data not available)",
                "count": len(common_actives),
                "actives": common_actives,
                "note": "These are common forex pairs that are usually available during market hours",
                "market_status": "Markets may be closed" if is_weekend else "Try again during market hours (Mon-Fri)",
                "current_time_utc": now.isoformat(),
                "data_source": "fallback"
            }), 200
        
        # Process live data
        open_actives = []
        for active_id, info in all_actives.items():
            if isinstance(info, dict):
                binary = info.get("binary", {})
                turbo = info.get("turbo", {})
                
                if binary.get("enabled") or turbo.get("enabled"):
                    open_actives.append({
                        "active_id": active_id,
                        "binary_enabled": binary.get("enabled", False),
                        "turbo_enabled": turbo.get("enabled", False),
                        "recommended": active_id in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY"]
                    })
        
        if len(open_actives) == 0:
            logger.warning("Live data returned empty list, using common actives")
            return jsonify({
                "message": "Using common actives (no markets currently open)",
                "count": len(common_actives),
                "actives": common_actives,
                "note": "Markets may be closed. These are common pairs usually available Mon-Fri.",
                "data_source": "fallback"
            }), 200
        
        return jsonify({
            "message": "Open actives retrieved successfully from live data",
            "count": len(open_actives),
            "actives": open_actives[:50],  # Return first 50
            "data_source": "live"
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting open actives: {e}", exc_info=True)
        return jsonify({
            "message": "Error getting live data, returning common actives",
            "count": len(common_actives),
            "actives": common_actives,
            "error": str(e),
            "data_source": "fallback"
        }), 200  # Return 200 with fallback data instead of 500


# ==================== Trading Bot Endpoints ====================

@app.route("/bot/create", methods=["POST"])
@token_required
def create_bot(current_user):
    """Create a new trading bot configuration."""
    data = request.get_json(silent=True) or {}
    
    # Get user from database
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        # Validate required fields
        required_fields = ["name", "active_id", "strategy", "initial_amount", "duration"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({"message": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Validate strategy
        if data["strategy"] not in STRATEGIES:
            return jsonify({
                "message": f"Invalid strategy. Available strategies: {', '.join(STRATEGIES.keys())}"
            }), 400
        
        # Create bot
        new_bot = TradingBot(
            user_id=user.id,
            name=data["name"],
            active_id=data["active_id"],
            strategy=data["strategy"],
            initial_amount=float(data["initial_amount"]),
            max_amount=float(data.get("max_amount", 100.0)),
            duration=int(data["duration"]),
            stop_loss=float(data["stop_loss"]) if data.get("stop_loss") else None,
            stop_gain=float(data["stop_gain"]) if data.get("stop_gain") else None,
            max_trades_per_day=int(data.get("max_trades_per_day", 10)),
            account_type=data.get("account_type", "PRACTICE").upper(),
            config_json=json.dumps(data.get("strategy_config", {})),
            status=BotStatus.STOPPED.value
        )
        
        session.add(new_bot)
        session.commit()
        
        bot_id = new_bot.id
        
        logger.info(f"Bot created: {new_bot.name} (ID: {bot_id}) for user {current_user}")
        
        return jsonify({
            "message": "Bot created successfully",
            "bot_id": bot_id,
            "bot": {
                "id": bot_id,
                "name": new_bot.name,
                "active_id": new_bot.active_id,
                "strategy": new_bot.strategy,
                "status": new_bot.status
            }
        }), 201
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating bot: {e}")
        return jsonify({"message": "Error creating bot", "error": str(e)}), 500
    finally:
        session.close()


@app.route("/bot/list", methods=["GET"])
@token_required
def list_bots(current_user):
    """List all bots for the current user."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bots = session.query(TradingBot).filter_by(user_id=user.id).all()
        
        bots_data = [{
            "id": bot.id,
            "name": bot.name,
            "active_id": bot.active_id,
            "strategy": bot.strategy,
            "status": bot.status,
            "initial_amount": bot.initial_amount,
            "max_amount": bot.max_amount,
            "duration": bot.duration,
            "account_type": bot.account_type,
            "created_at": bot.created_at.isoformat() if bot.created_at else None
        } for bot in bots]
        
        return jsonify({
            "message": "Bots retrieved successfully",
            "bots": bots_data,
            "count": len(bots_data)
        }), 200
    
    finally:
        session.close()


@app.route("/bot/<int:bot_id>", methods=["GET"])
@token_required
def get_bot(current_user, bot_id):
    """Get details of a specific bot."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bot = session.query(TradingBot).filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        strategy_config = {}
        if bot.config_json:
            try:
                strategy_config = json.loads(bot.config_json)
            except:
                pass
        
        return jsonify({
            "message": "Bot retrieved successfully",
            "bot": {
                "id": bot.id,
                "name": bot.name,
                "active_id": bot.active_id,
                "strategy": bot.strategy,
                "status": bot.status,
                "initial_amount": bot.initial_amount,
                "max_amount": bot.max_amount,
                "duration": bot.duration,
                "stop_loss": bot.stop_loss,
                "stop_gain": bot.stop_gain,
                "max_trades_per_day": bot.max_trades_per_day,
                "account_type": bot.account_type,
                "strategy_config": strategy_config,
                "created_at": bot.created_at.isoformat() if bot.created_at else None,
                "updated_at": bot.updated_at.isoformat() if bot.updated_at else None
            }
        }), 200
    
    finally:
        session.close()


@app.route("/bot/<int:bot_id>/start", methods=["POST"])
@token_required
def start_bot(current_user, bot_id):
    """Start a trading bot."""
    # Check if user has active IQ Option session
    client = _active_sessions.get(current_user)
    if client is None:
        return jsonify({
            "message": "IQ Option session not active",
            "error": "Please login first"
        }), 401
    
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bot = session.query(TradingBot).filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Check if bot is already running
        if bot_id in _active_bots:
            return jsonify({"message": "Bot is already running"}), 400
        
        # Create and start bot service
        try:
            bot_service = TradingBotService(bot_id, client)
            if bot_service.start():
                _active_bots[bot_id] = bot_service
                logger.info(f"Bot {bot_id} started by user {current_user}")
                return jsonify({
                    "message": "Bot started successfully",
                    "bot_id": bot_id,
                    "status": BotStatus.RUNNING.value
                }), 200
            else:
                return jsonify({"message": "Failed to start bot"}), 500
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return jsonify({"message": "Error starting bot", "error": str(e)}), 500
    
    finally:
        session.close()


@app.route("/bot/<int:bot_id>/stop", methods=["POST"])
@token_required
def stop_bot(current_user, bot_id):
    """Stop a trading bot."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bot = session.query(TradingBot).filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Check if bot is running
        if bot_id not in _active_bots:
            return jsonify({"message": "Bot is not running"}), 400
        
        # Stop bot service
        bot_service = _active_bots[bot_id]
        if bot_service.stop():
            del _active_bots[bot_id]
            logger.info(f"Bot {bot_id} stopped by user {current_user}")
            return jsonify({
                "message": "Bot stopped successfully",
                "bot_id": bot_id,
                "status": BotStatus.STOPPED.value
            }), 200
        else:
            return jsonify({"message": "Failed to stop bot"}), 500
    
    finally:
        session.close()


@app.route("/bot/<int:bot_id>/signals", methods=["GET"])
@token_required
def get_bot_signals(current_user, bot_id):
    """Get trading signals for a specific bot."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bot = session.query(TradingBot).filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Get query parameters
        limit = int(request.args.get("limit", 50))
        status = request.args.get("status")
        
        query = session.query(TradingSignal).filter_by(bot_id=bot_id)
        
        if status:
            query = query.filter_by(status=status.upper())
        
        signals = query.order_by(TradingSignal.created_at.desc()).limit(limit).all()
        
        signals_data = [{
            "id": signal.id,
            "active_id": signal.active_id,
            "signal_type": signal.signal_type,
            "status": signal.status,
            "amount": signal.amount,
            "duration": signal.duration,
            "entry_price": signal.entry_price,
            "exit_price": signal.exit_price,
            "profit_loss": signal.profit_loss,
            "order_id": signal.order_id,
            "created_at": signal.created_at.isoformat() if signal.created_at else None,
            "executed_at": signal.executed_at.isoformat() if signal.executed_at else None,
            "closed_at": signal.closed_at.isoformat() if signal.closed_at else None
        } for signal in signals]
        
        # Calculate statistics
        total_trades = len([s for s in signals if s.status in [SignalStatus.WON.value, SignalStatus.LOST.value]])
        won_trades = len([s for s in signals if s.status == SignalStatus.WON.value])
        lost_trades = len([s for s in signals if s.status == SignalStatus.LOST.value])
        total_pnl = sum(s.profit_loss for s in signals if s.profit_loss)
        
        return jsonify({
            "message": "Signals retrieved successfully",
            "signals": signals_data,
            "count": len(signals_data),
            "statistics": {
                "total_trades": total_trades,
                "won_trades": won_trades,
                "lost_trades": lost_trades,
                "win_rate": (won_trades / total_trades * 100) if total_trades > 0 else 0,
                "total_pnl": total_pnl
            }
        }), 200
    
    finally:
        session.close()


@app.route("/bot/<int:bot_id>/delete", methods=["DELETE"])
@token_required
def delete_bot(current_user, bot_id):
    """Delete a trading bot."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=current_user).first()
        if not user:
            return jsonify({"message": "User not found"}), 404
        
        bot = session.query(TradingBot).filter_by(id=bot_id, user_id=user.id).first()
        if not bot:
            return jsonify({"message": "Bot not found"}), 404
        
        # Check if bot is running
        if bot_id in _active_bots:
            return jsonify({"message": "Cannot delete a running bot. Stop it first."}), 400
        
        # Delete bot
        session.delete(bot)
        session.commit()
        
        logger.info(f"Bot {bot_id} deleted by user {current_user}")
        
        return jsonify({"message": "Bot deleted successfully"}), 200
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting bot: {e}")
        return jsonify({"message": "Error deleting bot", "error": str(e)}), 500
    finally:
        session.close()


@app.route("/bot/strategies", methods=["GET"])
@token_required
def list_strategies(current_user):
    """List available trading strategies."""
    strategies_info = {
        "sma_cross": {
            "name": "Simple Moving Average Crossover",
            "description": "Generates signals based on SMA crossovers",
            "config": {
                "fast_period": "Period for fast SMA (default: 5)",
                "slow_period": "Period for slow SMA (default: 20)"
            }
        },
        "martingale": {
            "name": "Martingale with Trend Following",
            "description": "Doubles bet after loss, follows simple trend",
            "config": {
                "multiplier": "Amount multiplier after loss (default: 2.2)",
                "reset_on_win": "Reset to initial amount on win (default: true)"
            }
        },
        "rsi": {
            "name": "Relative Strength Index (RSI)",
            "description": "Generates signals based on RSI overbought/oversold levels",
            "config": {
                "period": "RSI period (default: 14)",
                "oversold": "Oversold level (default: 30)",
                "overbought": "Overbought level (default: 70)"
            }
        }
    }
    
    return jsonify({
        "message": "Strategies retrieved successfully",
        "strategies": strategies_info
    }), 200


if __name__ == "__main__":
    app.run(debug=True)

