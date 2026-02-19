# Bot de Trading para IQ Option

Este proyecto incluye un bot de trading automatizado para opciones binarias en IQ Option.

## 🤖 Características del Bot

- **Múltiples estrategias de trading**:
  - SMA Crossover (Cruce de medias móviles)
  - Martingale con seguimiento de tendencia
  - RSI (Relative Strength Index)

- **Gestión de riesgo**:
  - Stop Loss configurable
  - Stop Gain configurable
  - Límite de operaciones diarias
  - Monto máximo por operación

- **Modos de cuenta**:
  - PRACTICE (cuenta demo)
  - REAL (cuenta real)

- **Monitoreo completo**:
  - Registro de todas las señales
  - Historial de operaciones
  - Estadísticas en tiempo real

## 📋 Requisitos

```bash
# Instalar dependencias
pip install -r requirements.txt

# O con pipenv
pipenv install
```

## 🗄️ Configuración de Base de Datos

```bash
# Crear las tablas necesarias
python create_active_options_table.py
```

## 🚀 Uso del Bot

### 1. Via API (Recomendado)

#### Paso 1: Iniciar el servidor
```bash
python run_prod.py
```

#### Paso 2: Login en IQ Option
```bash
POST /login
{
  "username": "tu_email@ejemplo.com",
  "password": "tu_password"
}
```

Respuesta:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJh...",
  "message": "Login successful"
}
```

#### Paso 3: Crear un bot
```bash
POST /bot/create
Authorization: Bearer <tu_token>

{
  "name": "Mi Bot EUR/USD",
  "active_id": "EURUSD",
  "strategy": "sma_cross",
  "initial_amount": 1.0,
  "max_amount": 50.0,
  "duration": 1,
  "stop_loss": 20.0,
  "stop_gain": 50.0,
  "max_trades_per_day": 10,
  "account_type": "PRACTICE",
  "strategy_config": {
    "fast_period": 5,
    "slow_period": 20
  }
}
```

#### Paso 4: Iniciar el bot
```bash
POST /bot/<bot_id>/start
Authorization: Bearer <tu_token>
```

#### Paso 5: Monitorear el bot
```bash
# Ver señales y estadísticas
GET /bot/<bot_id>/signals
Authorization: Bearer <tu_token>

# Ver configuración del bot
GET /bot/<bot_id>
Authorization: Bearer <tu_token>
```

#### Paso 6: Detener el bot
```bash
POST /bot/<bot_id>/stop
Authorization: Bearer <tu_token>
```

### 2. Via Script Standalone

```bash
python run_bot.py <bot_id> <iq_email> <iq_password>
```

Ejemplo:
```bash
python run_bot.py 1 user@example.com mypassword123
```

## 📊 Endpoints API Disponibles

### Gestión de Bots
- `POST /bot/create` - Crear nuevo bot
- `GET /bot/list` - Listar todos los bots
- `GET /bot/<bot_id>` - Ver detalles de un bot
- `POST /bot/<bot_id>/start` - Iniciar bot
- `POST /bot/<bot_id>/stop` - Detener bot
- `DELETE /bot/<bot_id>/delete` - Eliminar bot
- `GET /bot/<bot_id>/signals` - Ver señales y estadísticas
- `GET /bot/strategies` - Listar estrategias disponibles

### IQ Option
- `POST /login` - Autenticarse en IQ Option
- `POST /logout` - Cerrar sesión
- `GET /balance` - Ver balance de cuenta
- `GET /all-actives-opcode` - Ver activos disponibles

## 🎯 Estrategias Disponibles

### 1. SMA Crossover (`sma_cross`)
Genera señales cuando las medias móviles se cruzan.

**Configuración:**
```json
{
  "fast_period": 5,
  "slow_period": 20
}
```

**Señales:**
- CALL: Cuando la MA rápida cruza por encima de la lenta
- PUT: Cuando la MA rápida cruza por debajo de la lenta

### 2. Martingale (`martingale`)
Estrategia de seguimiento de tendencia con gestión de capital Martingale.

**Configuración:**
```json
{
  "multiplier": 2.2,
  "reset_on_win": true
}
```

**Gestión de capital:**
- Después de ganar: Vuelve al monto inicial
- Después de perder: Multiplica el monto por el multiplicador

### 3. RSI (`rsi`)
Genera señales basadas en niveles de sobrecompra/sobreventa del RSI.

**Configuración:**
```json
{
  "period": 14,
  "oversold": 30,
  "overbought": 70
}
```

**Señales:**
- CALL: Cuando RSI sale de zona de sobreventa
- PUT: Cuando RSI sale de zona de sobrecompra

## ⚙️ Configuración del Bot

### Parámetros principales:

- **name**: Nombre descriptivo del bot
- **active_id**: Par de divisas o activo (ej: "EURUSD", "GBPUSD")
- **strategy**: Estrategia a usar ("sma_cross", "martingale", "rsi")
- **initial_amount**: Monto inicial por operación
- **max_amount**: Monto máximo permitido por operación
- **duration**: Duración de cada operación en minutos (1-5)
- **stop_loss**: Pérdida máxima diaria (opcional)
- **stop_gain**: Ganancia objetivo diaria (opcional)
- **max_trades_per_day**: Límite de operaciones por día
- **account_type**: "PRACTICE" o "REAL"
- **strategy_config**: Configuración específica de la estrategia (opcional)

## 📈 Ejemplo Completo

```bash
# 1. Iniciar servidor
python run_prod.py

# 2. Login (en otra terminal)
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tu_email@ejemplo.com","password":"tu_password"}'

# 3. Crear bot
curl -X POST http://localhost:5000/bot/create \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bot RSI EURUSD",
    "active_id": "EURUSD",
    "strategy": "rsi",
    "initial_amount": 2.0,
    "max_amount": 20.0,
    "duration": 1,
    "stop_loss": 10.0,
    "stop_gain": 20.0,
    "max_trades_per_day": 15,
    "account_type": "PRACTICE",
    "strategy_config": {
      "period": 14,
      "oversold": 30,
      "overbought": 70
    }
  }'

# 4. Iniciar bot (supongamos que el bot_id es 1)
curl -X POST http://localhost:5000/bot/1/start \
  -H "Authorization: Bearer <TOKEN>"

# 5. Ver señales
curl -X GET http://localhost:5000/bot/1/signals \
  -H "Authorization: Bearer <TOKEN>"

# 6. Detener bot
curl -X POST http://localhost:5000/bot/1/stop \
  -H "Authorization: Bearer <TOKEN>"
```

## ⚠️ Advertencias Importantes

1. **Siempre usa la cuenta PRACTICE primero** para probar estrategias
2. **Las opciones binarias son de alto riesgo** - solo invierte lo que puedas perder
3. **Monitorea el bot regularmente** - revisa las señales y resultados
4. **Ajusta los límites** de stop loss y max_trades_per_day apropiadamente
5. **Ninguna estrategia garantiza ganancias** - el mercado es impredecible

## 🔍 Monitoreo y Logs

Los logs del bot incluyen:
- Señales detectadas con razón y confianza
- Operaciones ejecutadas
- Resultados de cada operación (ganancia/pérdida)
- Errores y advertencias

Revisa los logs en tiempo real para monitorear el comportamiento del bot.

## 🛠️ Desarrollo

### Crear una nueva estrategia:

1. Edita `src/servicios/trading_strategies.py`
2. Crea una clase que herede de `TradingStrategy`
3. Implementa los métodos `analyze()` y `get_next_amount()`
4. Registra la estrategia en el diccionario `STRATEGIES`

Ejemplo:
```python
class MiEstrategia(TradingStrategy):
    def analyze(self, candles, current_price):
        # Tu lógica de análisis
        if condicion_compra:
            return TradingSignal(
                signal_type="call",
                confidence=0.8,
                reason="Mi razón",
                timestamp=datetime.utcnow()
            )
        return None
    
    def get_next_amount(self, last_result, current_amount, initial_amount, max_amount):
        # Tu lógica de gestión de capital
        return initial_amount

# Registrar
STRATEGIES["mi_estrategia"] = MiEstrategia
```

## 📝 Base de Datos

El bot utiliza PostgreSQL con las siguientes tablas:
- `trading_bots`: Configuración de los bots
- `trading_signals`: Señales generadas y resultados
- `active_options`: Activos disponibles
- `users`: Usuarios del sistema
- `trading_sessions`: Sesiones de trading

## 🤝 Soporte

Para problemas o preguntas:
1. Revisa los logs del bot
2. Verifica la configuración de la base de datos
3. Asegúrate de tener una sesión activa en IQ Option
4. Revisa que el activo esté disponible para trading

## 📜 Licencia

Este proyecto es para uso educativo. Usa bajo tu propio riesgo.
