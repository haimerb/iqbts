# Bot de Trading para IQ Option

Sistema de trading automatizado con múltiples estrategias para IQ Option.

## 🚀 Inicio Rápido

### 1. Instalar dependencias
```sh
pipenv install --dev
```

### 2. Configurar base de datos
```sh
pipenv run python create_active_options_table.py
```

### 3. Iniciar el servidor (Terminal 1)
```sh
pipenv run python run_prod.py
```

### 4. Iniciar un bot (Terminal 2)
```sh
pipenv run python quick_start_bot.py tu_email@ejemplo.com tu_password
```

**¡Eso es todo!** El bot se iniciará y verás los logs en la Terminal 1.

## 📖 Documentación Completa

- [Guía del Bot de Trading](docs/TRADING_BOT.md) - Documentación detallada
- [FAQ y Solución de Problemas](docs/FAQ.md) - Errores comunes y soluciones
- [Configuración de Base de Datos](docs/DATABASE_SETUP.md)
- [Arquitectura](docs/arquitectura.md)

## 🎯 Estrategias Disponibles

- **RSI**: Relative Strength Index (sobrecompra/sobreventa)
- **SMA Cross**: Cruces de medias móviles
- **Martingale**: Con seguimiento de tendencia

## 🔧 Desarrollo

### Ejecutar tests
```sh
pipenv run test
```

### Ejecutar linter
```sh
pipenv run lint
```

## ⚠️ Advertencia

Este bot es para uso educativo. Siempre usa la cuenta PRACTICE primero. Las opciones binarias son de alto riesgo.
