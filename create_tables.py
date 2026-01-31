#!/usr/bin/env python3
"""Create all database tables."""

from src.servicios.database import get_engine
from src.servicios.models import Base, User, TradingSession, Trade

engine = get_engine()

print("Creando tablas...")
Base.metadata.create_all(engine)
print("✓ Tablas creadas exitosamente!")

# Verificar
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()

print("\nTablas en la base de datos:")
for table in tables:
    print(f"  ✓ {table}")
    columns = inspector.get_columns(table)
    for col in columns:
        print(f"    - {col['name']}: {col['type']}")
