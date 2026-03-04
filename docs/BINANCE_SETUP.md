# Guía de Instalación - Binance Bot

Esta guía te ayudará a configurar el nuevo sistema de trading para Binance.

## 📦 Paso 1: Instalar Dependencias

### Actualizar Pipfile

El archivo `requirements.txt` ya incluye las nuevas dependencias:
- `python-binance==1.0.19` - Cliente oficial de Binance
- `ta==0.11.0` - Librería de análisis técnico (indicadores)

### Instalar con pipenv

```bash
pipenv install
```

O si prefieres pip:

```bash
pip install -r requirements.txt
```

## 🗄️ Paso 2: Crear Tablas de Base de Datos

```bash
python create_binance_tables.py
```

Esto creará 4 nuevas tablas:
- `binance_api_keys` - Almacena credenciales de Binance
- `binance_bots` - Configuraciones de bots
- `binance_trades` - Historial de trades
- `binance_positions` - Posiciones abiertas

## 🔑 Paso 3: Obtener Credenciales de Binance Testnet

### ¿Por qué Testnet?

**NUNCA uses la API de producción sin probar primero.** Testnet usa dinero falso.

### Obtener API Key

1. Ve a [Binance Testnet](https://testnet.binance.vision/)
2. Click en "Login with GitHub"
3. Autoriza la aplicación
4. En el dashboard, click "Generate HMAC_SHA256 Key"
5. Copia y guarda:
   - **API Key**: `B8xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Secret Key**: `Y7xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**⚠️ IMPORTANTE**: Nunca compartas estas keys. Si las expones, regeneralas inmediatamente.

## 🚀 Paso 4: Iniciar el Sistema

### Terminal 1: Servidor

```bash
python run_prod.py
```

Deberías ver:
```
INFO - Binance endpoints loaded successfully
INFO - Servidor iniciando en http://127.0.0.1:5000
```

### Terminal 2: Quick Start

```bash
python quick_start_binance.py tu_email tu_password TU_API_KEY TU_API_SECRET
```

Ejemplo real:
```bash
python quick_start_binance.py user@example.com mypass123 B8abc123def456 Y7xyz789uvw012
```

## ✅ Verificar Instalación

### 1. Verificar que el servidor cargó Binance

En los logs del servidor deberías ver:
```
INFO - Binance endpoints loaded successfully
```

### 2. Listar estrategias disponibles

```bash
curl http://localhost:5000/binance/strategies
```

Debería devolver:
```json
{
  "count": 3,
  "strategies": [
    {"name": "rsi", "display_name": "RSI (Relative Strength Index)"},
    {"name": "macd", "display_name": "MACD Crossover"},
    {"name": "bollinger", "display_name": "Bollinger Bands"}
  ]
}
```

### 3. Verificar tablas creadas

En PostgreSQL:
```sql
\dt binance*
```

Deberías ver:
```
 binance_api_keys
 binance_bots
 binance_positions
 binance_trades
```

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'binance'"

**Solución**:
```bash
pipenv install python-binance
# o
pip install python-binance==1.0.19
```

### Error: "ModuleNotFoundError: No module named 'ta'"

**Solución**:
```bash
pipenv install ta
# o
pip install ta==0.11.0
```

### Error: "Binance endpoints not loaded"

Esto es solo una advertencia si las dependencias no están instaladas. El servidor IQ Option seguirá funcionando.

**Para habilitar Binance**:
1. Instala dependencias: `pipenv install`
2. Reinicia el servidor
3. Deberías ver "Binance endpoints loaded successfully"

### Error: "Invalid API key"

- ✅ Verifica que estés usando keys de **Testnet**, no producción
- ✅ Copia las keys sin espacios adicionales
- ✅ Regenera las keys si es necesario

### Error: "Connection error"

- ✅ Verifica tu conexión a internet
- ✅ Testnet puede estar en mantenimiento (verifica status.binance.com)
- ✅ Prueba más tarde

## 📊 Próximos Pasos

Una vez instalado:

1. **Lee la documentación completa**: [docs/BINANCE_BOT.md](../docs/BINANCE_BOT.md)
2. **Crea tu primer bot**: `POST /binance/bot/create`
3. **Monitorea trades**: `GET /binance/bot/{id}/trades`
4. **Ajusta estrategias**: Modifica parámetros según resultados

## 🎓 Recursos de Aprendizaje

### Binance API
- [Documentación oficial](https://binance-docs.github.io/apidocs/spot/en/)
- [python-binance docs](https://python-binance.readthedocs.io/)

### Análisis Técnico
- [technical-analysis library](https://technical-analysis-library-in-python.readthedocs.io/)
- [TradingView indicators](https://www.tradingview.com/scripts/)

### Trading  
- [Investopedia](https://www.investopedia.com/cryptocurrency-4427699)
- [Binance Academy](https://academy.binance.com/)

## ⚠️ Recordatorios Finales

1. **SIEMPRE usa Testnet primero** (al menos 1 mes)
2. **NO inviertas más de lo que puedes perder**
3. **Habilita 2FA** en tu cuenta de Binance
4. **Usa restricciones de IP** para tus API keys
5. **NO des permisos de withdrawal** a las API keys de trading

---

¿Listo? Ejecuta:
```bash
python quick_start_binance.py tu_email tu_password TU_API_KEY TU_SECRET
```

**Happy Trading! 🚀**
