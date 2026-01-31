"""Simple Flask API that authenticates against IQ Option via iqoptionapi."""

from __future__ import annotations

import datetime
import logging
import os
import secrets
from functools import wraps
from pathlib import Path
from typing import Any, Dict

import jwt
import yaml  # type: ignore[import-not-found]
from flask import Flask, jsonify, request

from src.servicios.iqoption_auth import authenticate

from src.servicios.database import get_session
from src.servicios.models import User
from src.servicios.models import TradingSession

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

    auth_result = authenticate(username, password)
    if not auth_result.success:
        logger.warning(
            "IQ Option authentication failed for %s: %s", username, auth_result.reason
        )
        return (
            jsonify(
                {
                    "message": "Invalid credentials",
                    "reason": auth_result.reason,
                }
            ),
            401,
        )

    existing_client = _active_sessions.get(username)
    if existing_client is not None:
        _shutdown_client(existing_client)

    if auth_result.client is not None:
        _active_sessions[username] = auth_result.client

    token = _generate_token(username)

    session = get_session()
    user = session.query(User).filter_by(email=username).first()

    if user is None:
        # create new user into database if not exists
        new_user = User(email=username, password_hash=password)
        session.add(new_user)
        session.commit()
        
        logger.warning("New user %s created and stored in the database.", username)
        
        # create new trading session in the database
        new_tradingsession = TradingSession(
            user_id=new_user.id,
            token=token
        )
        session.add(new_tradingsession)
        session.commit() 
        session.close()
        
    else:
        if user.is_active == False:
            logger.warning("User %s is inactive. Login denied.", username)
            return jsonify({"message": "User is inactive. Login denied."}), 423
        
        old_tradingsession = session.query(TradingSession).filter_by(user_id=user.id).first()
        if old_tradingsession is not None:

            logger.warning("TradingSession %s trae sesion anterior ", old_tradingsession)
            ##logger.warning("Deactivating old trading session for user %s.", username)
            old_tradingsession.is_active = False
            session.commit()

            # create new trading session in the database
            new_tradingsession = TradingSession(
                user_id=user.id,
                token=token
            )
            session.add(new_tradingsession)
            session.commit() 
            session.close()
        else:   
            logger.warning("TradingSession %s NO trae sesion anterior ", old_tradingsession)

        logger.warning("User %s already exists in the database.", username)
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




if __name__ == "__main__":
    app.run(debug=True)
