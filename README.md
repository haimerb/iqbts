# Sistema de Trading Automatizado - IQBTS

Plataforma de trading automatizado con soporte para **IQ Option** (opciones binarias) y **Binance** (spot crypto trading).

## 🎯 Plataformas Soportadas

### 1. IQ Option
- Opciones binarias y turbo
- Forex, acciones, commodities
- Cuenta practice y real
- [Ver documentación IQ Option](docs/TRADING_BOT.md)

### 2. Binance  
- Spot trading (compra/venta directa)
- Criptomonedas (BTC, ETH, altcoins)
- Testnet y producción
- [Ver documentación Binance](docs/BINANCE_BOT.md)

---

## 🚀 Inicio Rápido

### Instalación Inicial

```sh
# 1. Instalar dependencias
pipenv install --dev

# 2. Configurar base de datos
pipenv run python create_active_options_table.py
pipenv run python create_binance_tables.py

# 3. Iniciar el servidor
pipenv run python run_prod.py
```

### Opción A: Bot para IQ Option

```sh
# En otra terminal:
pipenv run python quick_start_bot.py tu_email@iqoption.com tu_password
```

### Opción B: Bot para Binance

```sh
# Obtén credenciales en https://testnet.binance.vision/
pipenv run python quick_start_binance.py tu_email tu_password BINANCE_API_KEY BINANCE_SECRET
```

---

## 📖 Documentación Completa

### IQ Option
- [Guía del Bot de Trading IQ Option](docs/TRADING_BOT.md)
- [FAQ y Solución de Problemas](docs/FAQ.md)

### Binance
- 📘 [Guía del Bot de Trading Binance](docs/BINANCE_BOT.md)

### General
- [Configuración de Base de Datos](docs/DATABASE_SETUP.md)
- [Arquitectura del Sistema](docs/arquitectura.md)

---

## 🎯 Estrategias Disponibles

### IQ Option
- **RSI**: Relative Strength Index (sobrecompra/sobreventa)
- **SMA Cross**: Cruces de medias móviles
- **Martingale**: Con seguimiento de tendencia

### Binance
- **RSI**: Mean reversion con stop loss/take profit
- **MACD**: Trend following con cruces
- **Bollinger Bands**: Trading en bandas de volatilidad

---

## 🔧 Endpoints API

### IQ Option
```bash
POST   /login
POST   /logout
GET    /balance
POST   /bot/create
POST   /bot/{id}/start
POST   /bot/{id}/stop
GET    /bot/{id}/signals
```

### Binance
```bash
POST   /binance/api-key/create
GET    /binance/api-key/list
GET    /binance/api-key/{id}/balance
POST   /binance/bot/create
POST   /binance/bot/{id}/start
POST   /binance/bot/{id}/stop
GET    /binance/bot/{id}/trades
GET    /binance/strategies
```

[Ver documentación completa de endpoints](docs/BINANCE_BOT.md)

---

## 💡 Comparación: IQ Option vs Binance

| Característica | IQ Option | Binance |
|---------------|-----------|---------|
| **Tipo de trading** | Opciones binarias | Spot crypto |
| **Duración trades** | 1-60 minutos | Ilimitado |
| **P&L** | Fijo (~80%) | Variable |
| **Riesgo** | Todo o nada | Proporcional |
| **Activos** | Forex, acciones | Solo crypto |
| **Leverage** | No | Sí (futures) |
| **Mejor para** | Trading rápido | HODLing, swing trading |

---

## 🔧 Desarrollo

### Ejecutar tests
```sh
pipenv run test
```

### Ejecutar linter
```sh
pipenv run lint
```

### Estructura del proyecto
```
iqbts/
├── src/servicios/
│   ├── api.py                      # IQ Option endpoints
│   ├── trading_bot_service.py      # IQ Option bot logic
│   ├── binance_api_endpoints.py    # Binance endpoints
│   ├── binance_bot_service.py      # Binance bot logic
│   ├── binance_client.py           # Binance API wrapper
│   ├── binance_strategies.py       # Crypto strategies
│   ├── trading_strategies.py       # Binary options strategies
│   └── models.py                   # Database models
├── docs/
│   ├── TRADING_BOT.md              # IQ Option guide
│   ├── BINANCE_BOT.md              # Binance guide
│   └── FAQ.md                      # Troubleshooting
├── quick_start_bot.py              # IQ Option quick start
└── quick_start_binance.py          # Binance quick start
```

## ⚠️ Advertencia

Este bot es para uso educativo. Siempre usa la cuenta PRACTICE primero. Las opciones binarias son de alto riesgo.
