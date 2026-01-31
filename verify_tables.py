#!/usr/bin/env python3
"""Verify database tables."""

from src.servicios.database import get_engine
from sqlalchemy import inspect

engine = get_engine()
inspector = inspect(engine)
tables = inspector.get_table_names()

print("Tablas en la base de datos:")
for table in tables:
    print(f"  ✓ {table}")
    columns = inspector.get_columns(table)
    for col in columns:
        print(f"    - {col['name']}: {col['type']}")
