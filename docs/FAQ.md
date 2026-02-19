# FAQ - Preguntas Frecuentes y Solución de Problemas

## ❓ Errores Comunes

### Error: `KeyError: 'underlying'` en threads de iqoptionapi

**Qué es:**
```
Exception in thread Thread-3 (__get_digital_open):
KeyError: 'underlying'
```

**Causa:**
- Este error proviene de la librería `iqoptionapi` (no de nuestro código)
- Ocurre cuando la librería intenta obtener datos de opciones digitales que IQ Option no está devolviendo
- Es un problema interno de threads en la librería de terceros

**Solución:**
- ✅ **PUEDES IGNORAR ESTOS ERRORES** - No afectan el funcionamiento del bot
- Son molestos visualmente pero no causan problemas
- El bot seguirá funcionando normalmente
- Estos errores aparecen en stderr y no pueden ser suprimidos fácilmente

**Por qué sucede:**
- IQ Option cambió su API o no tiene opciones digitales disponibles
- La librería iqoptionapi tiene código legacy que sigue intentando acceder a estos datos
- Los threads internos siguen corriendo aunque los datos no estén disponibles

---

### Error: "No current price available"

**Causa:**
- El activo que estás intentando tradear no está devolviendo datos
- El mercado puede estar cerrado
- El formato del `active_id` puede ser incorrecto

**Solución:**
```bash
# 1. Verificar mercados abiertos
curl -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:5000/open-actives

# 2. Probar el activo específico
curl -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:5000/test-candles/EURUSD

# 3. Verificar estado del mercado
curl -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:5000/check-market/EURUSD
```

**Activos comunes y sus horarios:**
- **EURUSD**: 24/5 (Lunes a Viernes)
- **GBPUSD**: 24/5
- **USDJPY**: 24/5
- **OTC** (Over The Counter): Fines de semana y feriados

---

### Error: "Trade execution failed"

**Causas posibles:**

1. **Mercado cerrado**
   ```bash
   # Verificar estado
   curl -H "Authorization: Bearer <TOKEN>" \
     http://127.0.0.1:5000/check-market/EURUSD
   ```

2. **Balance insuficiente**
   - Verifica tu balance en la respuesta del bot
   - Ajusta `initial_amount` a un valor menor

3. **Monto inválido**
   - IQ Option tiene montos mínimos y máximos
   - Práctica: $1 - $1000 típicamente
   - Real: Varía por cuenta

4. **Active_id incorrecto**
   - Usa el formato correcto: "EURUSD", no "EUR/USD"
   - Algunos activos requieren sufijos: "EURUSD-OTC"

5. **Cuenta con restricciones**
   - Verifica que tu cuenta permita trading automático
   - Algunas cuentas tienen restricciones regionales

**Logs a revisar:**
```
Executing trade:
  Type: CALL
  Active: EURUSD
  Amount: $1.0
  Duration: 1 minute(s)
Current balance: $10000.00
Buy response - check: False, order_id: <mensaje_error>
❌ Trade rejected by IQ Option. Response: <mensaje>
```

---

### Error: "Bot is not running"

**Causa:**
Intentaste detener un bot que no está corriendo.

**Solución:**
```bash
# Ver estado de tus bots
curl -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:5000/bot/list
```

---

### Error: "IQ Option session not active"

**Causa:**
Tu sesión expiró o no has hecho login.

**Solución:**
```bash
# Login nuevamente
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tu@email.com","password":"tu_pass"}'
```

---

## 🔧 Problemas de Configuración

### El bot no genera señales

**Causas:**

1. **Estrategia muy restrictiva**
   - RSI solo genera señales en niveles extremos
   - SMA Crossover solo cuando hay cruce
   - Puede tomar tiempo ver una señal

2. **Configuración de estrategia**
   ```json
   // RSI muy restrictivo
   {
     "period": 14,
     "oversold": 20,  // Muy bajo
     "overbought": 80  // Muy alto
   }
   
   // Mejor configuración
   {
     "period": 14,
     "oversold": 30,
     "overbought": 70
   }
   ```

3. **Mercado sin volatilidad**
   - En horarios de baja actividad hay menos señales
   - Prueba durante horarios de apertura de mercados principales

**Solución:**
- Ten paciencia - puede tomar 30-60 minutos ver una señal
- Usa estrategias más agresivas para pruebas
- Revisa los logs para ver el análisis en cada iteración

---

### El bot se detiene solo

**Causas:**

1. **Stop Loss alcanzado**
   ```
   Bot hit stop loss: -5.0
   ```

2. **Stop Gain alcanzado**
   ```
   Bot hit stop gain: 10.0
   ```

3. **Límite diario de operaciones**
   ```
   Bot reached max trades per day: 10
   ```

4. **Error en la ejecución**
   - Revisa los logs para detalles
   - Estado del bot cambiará a "error"

**Solución:**
- Ajusta los límites en la configuración del bot
- Reinicia el bot después de resolver el error

---

## 💡 Mejores Prácticas

### 1. Siempre usar cuenta PRACTICE primero
```json
{
  "account_type": "PRACTICE"  // Siempre para pruebas
}
```

### 2. Configurar límites conservadores
```json
{
  "initial_amount": 1.0,      // Empezar pequeño
  "max_amount": 10.0,         // Límite conservador
  "max_trades_per_day": 5,    // Pocas operaciones
  "stop_loss": 5.0,           // Cortar pérdidas
  "stop_gain": 10.0           // Tomar ganancias
}
```

### 3. Monitorear activamente
```bash
# Ver señales cada minuto
watch -n 60 'curl -s -H "Authorization: Bearer <TOKEN>" \
  http://127.0.0.1:5000/bot/1/signals | jq'
```

### 4. Probar en días de alta liquidez
- Martes a Jueves: Mejores días
- 8:00-17:00 GMT: Horarios óptimos
- Evitar domingos y lunes temprano

### 5. Ajustar estrategias según mercado
- **Trending market**: Use SMA Crossover o Martingale
- **Ranging market**: Use RSI
- **High volatility**: Reduce trade amount

---

## 🐛 Debugging

### Ver logs detallados del bot

El bot ya incluye logs exhaustivos:
```
=== Bot iteration 1 ===
Fetching market data for EURUSD...
Requesting 100 candles for EURUSD (duration: 1m)
Received 100 candles for EURUSD
Successfully retrieved 100 candles
Current price for EURUSD: 1.178565
Analyzing market with rsi strategy...
No signal detected, continuing to monitor...
```

### Habilitar logs de iqoptionapi

Si necesitas ver más detalles de la librería:
```python
from src.servicios.iqoption_auth import authenticate

client = authenticate(
    email, 
    password, 
    enable_library_logging=True  # ← Habilitar logs
)
```

### Base de datos

Ver señales directamente en PostgreSQL:
```sql
-- Últimas 10 señales
SELECT * FROM trading_signals 
ORDER BY created_at DESC 
LIMIT 10;

-- Estadísticas de un bot
SELECT 
    status, 
    COUNT(*), 
    SUM(profit_loss) 
FROM trading_signals 
WHERE bot_id = 1 
GROUP BY status;
```

---

## 📞 Obtener Ayuda

Si después de revisar este FAQ sigues teniendo problemas:

1. **Revisa los logs** - La mayoría de problemas se explican ahí
2. **Usa los endpoints de diagnóstico** - `/check-market`, `/test-candles`
3. **Verifica tu cuenta** - Asegúrate de poder tradear manualmente
4. **Prueba con otros activos** - Algunos pueden no estar disponibles

---

## ⚠️ Recordatorios Importantes

- ❌ Nunca uses dinero real sin probar exhaustivamente en PRACTICE
- ❌ Las opciones binarias son de alto riesgo
- ❌ Ninguna estrategia garantiza ganancias
- ✅ Siempre usa stop loss y límites
- ✅ Monitorea el bot regularmente
- ✅ Comprende la estrategia que usas
