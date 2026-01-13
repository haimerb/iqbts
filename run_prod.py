#!/usr/bin/env python3
"""
Script para correr la aplicación en modo producción usando Waitress.
"""

from waitress import serve
from src.servicios.api import app

if __name__ == '__main__':
    print("Iniciando servidor de producción en http://127.0.0.1:5000")
    serve(app, host='127.0.0.1', port=5000)