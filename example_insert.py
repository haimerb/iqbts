#!/usr/bin/env python3
"""Example: How to insert data into the database."""

from src.servicios.database import get_session
from src.servicios.models import User, TradingSession, Trade

# Obtener sesión de la BD
session = get_session()

try:
    # 1. CREAR UN USUARIO
    print("1. Creando usuario...")
    new_user = User(
        email="trader@example.com",
        password_hash="hashed_password_123"
    )
    session.add(new_user)
    session.commit()
    print(f"   ✓ Usuario creado: {new_user}")
    
    # 2. CREAR UNA SESIÓN DE TRADING
    print("\n2. Creando sesión de trading...")
    trading_session = TradingSession(
        user_id=new_user.id,
        token="jwt_token_12345"
    )
    session.add(trading_session)
    session.commit()
    print(f"   ✓ Sesión creada: {trading_session}")
    
    # 3. CREAR UN TRADE
    print("\n3. Creando trade...")
    trade = Trade(
        session_id=trading_session.id,
        symbol="EURUSD",
        direction="call",
        amount=100.50,
        profit_loss=25.75
    )
    session.add(trade)
    session.commit()
    print(f"   ✓ Trade creado: {trade}")
    
    # 4. LEER DATOS
    print("\n4. Leyendo datos...")
    users = session.query(User).all()
    print(f"   ✓ Usuarios: {users}")
    
    # 5. ACTUALIZAR
    print("\n5. Actualizando usuario...")
    user = session.query(User).filter_by(email="trader@example.com").first()
    if user:
        user.is_active = False
        session.commit()
        print(f"   ✓ Usuario actualizado: {user}")
    else:
        print("   ✗ Usuario no encontrado")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    session.rollback()
finally:
    session.close()
