#!/usr/bin/env python3
"""
Script para correr la aplicación en modo producción usando Waitress.
"""

import logging
import warnings
from waitress import serve
from src.servicios.api import app

# Configurar logging para ver todos los logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Suprimir warnings molestos de threading de iqoptionapi
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Configurar logger para suprimir errores específicos de iqoptionapi
class IQOptionThreadFilter(logging.Filter):
    def filter(self, record):
        # Filtrar mensajes de error específicos de threads de iqoptionapi
        if "KeyError: 'underlying'" in str(record.msg):
            return False
        return True

# Agregar filtro a todos los handlers
for handler in logging.root.handlers:
    handler.addFilter(IQOptionThreadFilter())

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 Bot de Trading para IQ Option")
    print("=" * 70)
    print("Servidor iniciado en http://127.0.0.1:5000")
    print("\nNOTAS:")
    print("  • Los errores 'KeyError: underlying' de iqoptionapi son normales")
    print("  • Estos errores NO afectan el funcionamiento del bot")
    print("  • Son causados por opciones digitales no disponibles")
    print("\nLos logs del bot aparecerán aquí cuando inicies un bot")
    print("-" * 70)
    serve(app, host='127.0.0.1', port=5000)