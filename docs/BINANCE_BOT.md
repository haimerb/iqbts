# Bot de Trading para Binance

Sistema de trading automatizado para Binance con múltiples estrategias técnicas.

## 🚀 Inicio Rápido

### 1. Instalar nuevas dependencias

```bash
pipenv install
```

Esto instalará:
- `python-binance`: Cliente oficial de Binance
- `ta`: Librería de análisis técnico

### 2. Crear tablas de base de datos para Binance

```bash
pipenv run python create_binance_tables.py
```

### 3. Obtener credenciales de Binance Testnet

1. Ve a [Binance Testnet](https://testnet.binance.vision/)
2. Inicia sesión con GitHub
3. Genera API Key y Secret
4. **IMPORTANTE**: Usa siempre testnet primero

### 4. Configurar API Key (vía API o GUI)

**Opción A: Usar la API**

```bash
curl -X POST http://localhost:5000/binance/api-key/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_TOKEN_JWT" \
  -d '{
    "name": "My Testnet Key",
    "api_key": "TU_API_KEY_AQUI",
    "api_secret": "TU_API_SECRET_AQUI",
    "is_testnet": true
  }'
```

**Respuesta:**
```json
{
  "message": "Binance API key created successfully",
  "api_key": {
    "id": 1,
    "name": "My Testnet Key",
    "is_testnet": true,
    "created_at": "2026-02-19T12:00:00"
  }
}
```

### 5. Crear un bot de trading

```bash
curl -X POST http://localhost:5000/binance/bot/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_TOKEN_JWT" \
  -d '{
    "name": "BTC RSI Bot",
    "api_key_id": 1,
    "symbol": "BTCUSDT",
    "strategy": "rsi",
    "initial_amount": 10.0,
    "max_amount": 100.0,
    "max_daily_loss": 50.0,
    "max_daily_gain": 100.0,
    "max_trades_per_day": 10,
    "config": {
      "rsi_period": 14,
      "oversold_level": 30,
      "overbought_level": 70,
      "position_size_percent": 10.0,
      "stop_loss_percent": 3.0,
      "take_profit_percent": 6.0
    }
  }'
```

### 6. Iniciar el bot

```bash
curl -X POST http://localhost:5000/binance/bot/1/start \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

---

## 📊 Estrategias Disponibles

### 1. RSI (Relative Strength Index)

**Concepto**: Compra cuando está sobrevend ido, vende cuando está sobrecomprado.

**Configuración recomendada para BTC:**
```json
{
  "rsi_period": 14,
  "oversold_level": 30,
  "overbought_level": 70,
  "position_size_percent": 10.0,
  "stop_loss_percent": 3.0,
  "take_profit_percent": 6.0
}
```

**Mejor para**: Mercados laterales (rango), criptos de alta liquidez (BTC, ETH)

---

### 2. MACD (Moving Average Convergence Divergence)

**Concepto**: Compra en cruce alcista, vende en cruce bajista.

**Configuración recomendada:**
```json
{
  "fast_period": 12,
  "slow_period": 26,
  "signal_period": 9,
  "position_size_percent": 10.0,
  "stop_loss_percent": 2.5,
  "take_profit_percent": 5.0
}
```

**Mejor para**: Mercados con tendencia clara, pares con alta volatilidad

---

### 3. Bollinger Bands

**Concepto**: Compra en banda inferior, vende en banda superior (mean reversion).

**Configuración recomendada:**
```json
{
  "period": 20,
  "std_dev": 2.0,
  "position_size_percent": 10.0,
  "stop_loss_percent": 3.0,
  "take_profit_percent": 4.0
}
```

**Mejor para**: Altcoins de baja capitalización, mercados laterales

---

## 🎯 Pares Recomendados por Estrategia

| Estrategia | Pares Recomendados | Timeframe |
|------------|-------------------|-----------|
| RSI | BTCUSDT, ETHUSDT, BNBUSDT | 5m - 15m |
| MACD | BTCUSDT, ETHUSDT (tendencia) | 15m - 1h |
| Bollinger Bands | Altcoins (ADAUSDT, DOGEUSDT) | 5m - 15m |

---

## 🔧 Endpoints API Completos

### Gestión de API Keys

#### Crear API Key
```bash
POST /binance/api-key/create
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "My Binance Key",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "is_testnet": true
}
```

#### Listar API Keys
```bash
GET /binance/api-key/list
Authorization: Bearer {token}
```

#### Ver Balance
```bash
GET /binance/api-key/{key_id}/balance
Authorization: Bearer {token}
```

---

### Gestión de Bots

#### Crear Bot
```bash
POST /binance/bot/create
```

#### Listar Bots
```bash
GET /binance/bot/list
```

#### Ver Detalles de Bot
```bash
GET /binance/bot/{bot_id}
```

#### Iniciar Bot
```bash
POST /binance/bot/{bot_id}/start
```

#### Detener Bot
```bash
POST /binance/bot/{bot_id}/stop
```

#### Ver Historial de Trades
```bash
GET /binance/bot/{bot_id}/trades?limit=50
```

**Respuesta:**
```json
{
  "message": "Trades retrieved successfully",
  "bot_name": "BTC RSI Bot",
  "count": 10,
  "statistics": {
    "total_trades": 10,
    "wins": 7,
    "losses": 3,
    "win_rate": 70.0,
    "total_pnl": 15.50
  },
  "trades": [...]
}
```

#### Eliminar Bot
```bash
DELETE /binance/bot/{bot_id}/delete
```

---

### Información General

#### Listar Estrategias Disponibles
```bash
GET /binance/strategies
```

---

## 💡 Ejemplos de Configuraciones

### Configuración Conservadora (Principiantes)
```json
{
  "name": "Conservative BTC Bot",
  "symbol": "BTCUSDT",
  "strategy": "rsi",
  "initial_amount": 10.0,
  "max_amount": 50.0,
  "max_daily_loss": 20.0,
  "max_daily_gain": 40.0,
  "max_trades_per_day": 5,
  "config": {
    "rsi_period": 14,
    "oversold_level": 25,
    "overbought_level": 75,
    "position_size_percent": 5.0,
    "stop_loss_percent": 2.0,
    "take_profit_percent": 4.0
  }
}
```

### Configuración Agresiva (Experimentados)
```json
{
  "name": "Aggressive ETH Bot",
  "symbol": "ETHUSDT",
  "strategy": "macd",
  "initial_amount": 50.0,
  "max_amount": 500.0,
  "max_daily_loss": 100.0,
  "max_daily_gain": 200.0,
  "max_trades_per_day": 20,
  "config": {
    "fast_period": 8,
    "slow_period": 21,
    "signal_period": 5,
    "position_size_percent": 15.0,
    "stop_loss_percent": 3.0,
    "take_profit_percent": 7.0
  }
}
```

### Grid Trading Simulation (Bollinger Bands)
```json
{
  "name": "Grid ADA Bot",
  "symbol": "ADAUSDT",
  "strategy": "bollinger",
  "initial_amount": 20.0,
  "max_amount": 200.0,
  "max_daily_loss": 40.0,
  "max_daily_gain": 80.0,
  "max_trades_per_day": 15,
  "config": {
    "period": 20,
    "std_dev": 2.0,
    "position_size_percent": 8.0,
    "stop_loss_percent": 2.5,
    "take_profit_percent": 3.5
  }
}
```

---

## ⚠️ Advertencias y Mejores Prácticas

### 🔴 Seguridad

1. **NUNCA** compartas tus API keys
2. **SIEMPRE** usa testnet primero (al menos 1 mes)
3. **NO** guardes API keys en código fuente
4. **USA** restricciones de IP en Binance
5. **HABILITA** solo permisos necesarios (Trading, no Withdrawal)

### 🟡 Gestión de Riesgo

1. **Comienza pequeño**: 1-5% del capital por trade
2. **Stop loss siempre**: No operes sin stop loss
3. **Max daily loss**: Establece límites diarios estrictos
4. **Diversifica**: No pongas todo en un bot/par
5. **Monitorea constantemente**: Especialmente las primeras semanas

### 🟢 Optimización

1. **Backtesting**: Prueba estrategias en datos históricos
2. **Paper trading**: Usa testnet al menos 1 mes
3. **Ajusta parámetros**: Cada par de crypto es diferente
4. **Horarios**: Evita operar durante bajos volúmenes
5. **Noticias**: Detén bots antes de eventos importantes

---

## 📈 Monitoreo y Análisis

### Ver rendimiento de un bot

```python
import requests

response = requests.get(
    "http://localhost:5000/binance/bot/1/trades?limit=100",
    headers={"Authorization": f"Bearer {token}"}
)

data = response.json()
print(f"Win Rate: {data['statistics']['win_rate']}%")
print(f"Total P&L: ${data['statistics']['total_pnl']}")
```

### Detener bot automáticamente si pierde mucho

Los límites `max_daily_loss` y `max_daily_gain` detienen el bot automáticamente.

---

## 🐛 Troubleshooting

### Error: "Invalid API key"

- Verifica que copiaste correctamente la API key y secret
- Confirma que estás usando testnet si `is_testnet: true`
- Revisa que la key tenga permisos de trading

### Error: "Insufficient balance"

- Verifica tu balance en testnet: `GET /binance/api-key/{id}/balance`
- En testnet, puedes obtener fondos gratis desde el sitio web

### Bot no abre posiciones

- Revisa los logs del servidor
- Los parámetros de estrategia pueden ser muy restrictivos
- Puede que no haya señales en el mercado actual

### Trades perdiendo consistentemente

- La estrategia puede no ser adecuada para el par/mercado actual
- Ajusta parámetros basándote en backtest
- Considera cambiar de estrategia o par

---

## 🔗 Recursos Adicionales

- [Documentación Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [Binance Testnet](https://testnet.binance.vision/)
- [Technical Analysis Library (ta)](https://technical-analysis-library-in-python.readthedocs.io/)
- [Guía de Trading Algorítmico](https://www.investopedia.com/articles/active-trading/101014/basics-algorithmic-trading-concepts-and-examples.asp)

---

## ⚖️ Disclaimer

**Este software es solo para fines educativos.**

- El trading de criptomonedas es de ALTO RIESGO
- Puedes perder todo tu capital
- No somos asesores financieros
- Usa bajo tu propio riesgo
- **SIEMPRE** prueba en testnet primero
- No inviertas más de lo que puedes permitirte perder

---

## 📞 Soporte

Si encuentras bugs o tienes sugerencias:
1. Revisa la sección Troubleshooting
2. Verifica los logs del servidor
3. Consulta la documentación de Binance API
4. Reporta issues con logs completos

**¡Happy Trading! 🚀📈**
