"""Script para encontrar mercados abiertos y crear bot automáticamente."""

import requests
import sys
import json
from datetime import datetime

def find_and_create_bot(email, password):
    """Encuentra mercados abiertos y crea un bot."""
    
    base_url = "http://localhost:5000"
    
    # 1. Login
    print("🔐 Iniciando sesión...")
    login_response = requests.post(f"{base_url}/login", json={
        "email": email,
        "password": password
    })
    
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.text}")
        return
    
    token = login_response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Sesión iniciada\n")
    
    # 2. Obtener activos abiertos
    print("🔍 Buscando mercados abiertos...")
    actives_response = requests.get(f"{base_url}/open-actives", headers=headers)
    
    if actives_response.status_code != 200:
        print(f"❌ Error obteniendo activos: {actives_response.text}")
        return
    
    data = actives_response.json()
    actives = data.get("actives", [])
    
    print(f"\n📊 Encontrados {len(actives)} mercados")
    print(f"Fuente de datos: {data.get('data_source', 'unknown')}")
    
    if data.get('data_source') == 'fallback':
        print("\n⚠️  ADVERTENCIA: No hay datos en vivo de IQ Option")
        print("Posibles razones:")
        print("  - Es fin de semana (mercados cerrados)")
        print("  - Hora actual: " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        print("  - Los mercados forex operan Lun-Vie 00:00-21:00 UTC")
        print("\nMostrando activos comunes que USUALMENTE están disponibles:\n")
    
    # 3. Mostrar activos disponibles
    if not actives:
        print("❌ No hay activos disponibles en este momento")
        return
    
    print("\n📋 Activos disponibles:")
    print("-" * 70)
    for i, active in enumerate(actives[:10], 1):
        binary = "✅" if active.get("binary_enabled") else "❌"
        turbo = "✅" if active.get("turbo_enabled") else "❌"
        recommended = "⭐" if active.get("recommended") else "  "
        print(f"{recommended} {i}. {active['active_id']:10} | Binary: {binary} | Turbo: {turbo}")
    print("-" * 70)
    
    # 4. Seleccionar activo recomendado
    recommended_actives = [a for a in actives if a.get("recommended")]
    if not recommended_actives:
        recommended_actives = actives[:5]
    
    selected = recommended_actives[0]
    active_id = selected["active_id"]
    
    print(f"\n🎯 Probando mercado: {active_id}")
    
    # 5. Verificar si el mercado está realmente abierto
    check_response = requests.get(f"{base_url}/check-market/{active_id}", headers=headers)
    
    if check_response.status_code == 200:
        market_data = check_response.json()
        print(f"\nEstado del mercado {active_id}:")
        print(f"  Binary: {'Abierto ✅' if market_data.get('binary_enabled') else 'Cerrado ❌'}")
        print(f"  Turbo: {'Abierto ✅' if market_data.get('turbo_enabled') else 'Cerrado ❌'}")
        
        if not market_data.get('binary_enabled') and not market_data.get('turbo_enabled'):
            print(f"\n⚠️  {active_id} está cerrado en este momento")
            print("\nIntentando con otros activos...")
            
            for alt_active in recommended_actives[1:4]:
                alt_id = alt_active["active_id"]
                print(f"\n🔄 Probando {alt_id}...")
                alt_check = requests.get(f"{base_url}/check-market/{alt_id}", headers=headers)
                
                if alt_check.status_code == 200:
                    alt_data = alt_check.json()
                    if alt_data.get('binary_enabled') or alt_data.get('turbo_enabled'):
                        active_id = alt_id
                        print(f"✅ {alt_id} está abierto!")
                        break
            else:
                print("\n❌ NINGÚN mercado está abierto en este momento")
                print("\nVerifica:")
                print("  1. Día de la semana (no opera fines de semana)")
                print("  2. Hora actual (forex: Lun-Vie 00:00-21:00 UTC)")
                print("  3. Tipo de cuenta (PRACTICE vs REAL)")
                return
    
    # 6. Crear bot con configuración conservadora
    print(f"\n🤖 Creando bot para {active_id}...")
    
    bot_config = {
        "name": f"{active_id} RSI Bot",
        "active_id": active_id,
        "strategy": "rsi",
        "initial_amount": 1.0,  # Monto bajo para pruebas
        "max_amount": 5.0,
        "duration": 5,  # 5 minutos (turbo)
        "account_type": "PRACTICE",
        "max_trades_per_day": 10,
        "stop_loss": 20.0,
        "stop_gain": 30.0,
        "config_json": json.dumps({
            "rsi_period": 14,
            "oversold_level": 30,
            "overbought_level": 70,
            "position_size": 1.0
        })
    }
    
    create_response = requests.post(
        f"{base_url}/bot/create",
        headers=headers,
        json=bot_config
    )
    
    if create_response.status_code != 201:
        print(f"❌ Error creando bot: {create_response.text}")
        return
    
    bot = create_response.json()["bot"]
    bot_id = bot["id"]
    print(f"✅ Bot creado con ID: {bot_id}")
    
    # 7. Iniciar bot
    print(f"\n🚀 Iniciando bot...")
    start_response = requests.post(
        f"{base_url}/bot/{bot_id}/start",
        headers=headers
    )
    
    if start_response.status_code != 200:
        print(f"❌ Error iniciando bot: {start_response.text}")
        return
    
    print("✅ Bot iniciado exitosamente!")
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"Bot ID: {bot_id}")
    print(f"Activo: {active_id}")
    print(f"Estrategia: RSI (14 periodos)")
    print(f"Monto inicial: $1.00")
    print(f"Límite de pérdida: $20.00")
    print(f"Límite de ganancia: $30.00")
    print(f"Max trades/día: 10")
    print("="*70)
    print("\n📝 Los logs del bot aparecerán en el servidor (run_prod.py)")
    print(f"\n🛑 Para detener: curl -X POST http://localhost:5000/bot/{bot_id}/stop -H 'Authorization: Bearer {token}'")
    print(f"📊 Ver señales: curl http://localhost:5000/bot/{bot_id}/signals -H 'Authorization: Bearer {token}'")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python find_open_markets.py tu_email@ejemplo.com tu_password")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    find_and_create_bot(email, password)
