#!/usr/bin/env python3
"""Test database connection and initialize tables."""

from src.servicios.database import test_connection, init_db

if __name__ == "__main__":
    print("Probando conexión a PostgreSQL...")
    if test_connection():
        print("✓ Conexión exitosa!")
        print("\nInicializando tablas...")
        init_db()
        print("✓ Tablas creadas correctamente!")
    else:
        print("✗ Conexión fallida")
        exit(1)
