#!/usr/bin/env python3
"""
Script de inicio rápido para probar el bot de trading.
Este script:
1. Hace login en IQ Option
2. Crea un bot de prueba
3. Inicia el bot
"""

import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:5000"

def main():
    if len(sys.argv) < 3:
        print("Uso: python quick_start_bot.py <iq_email> <iq_password>")
        print("\nEjemplo:")
        print("  python quick_start_bot.py tu@email.com tu_password")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    print("=" * 70)
    print("🤖 INICIO RÁPIDO DE BOT DE TRADING")
    print("=" * 70)
    
    # 1. Login
    print("\n[1/6] 🔐 Haciendo login en IQ Option...")
    try:
        response = requests.post(f"{BASE_URL}/login", json={
            "username": email,
            "password": password
        })
        
        if response.status_code != 200:
            print(f"❌ Error en login: {response.json()}")
            sys.exit(1)
        
        token = response.json()["token"]
        print(f"✅ Login exitoso")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("Asegúrate de que el servidor esté corriendo con: python run_prod.py")
        sys.exit(1)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Check open markets
    print("\n[2/5] 🌍 Verificando mercados abiertos...")
    try:
        response = requests.get(f"{BASE_URL}/open-actives", headers=headers)
        if response.status_code == 200:
            actives_data = response.json()
            open_actives = actives_data.get("actives", [])
            
            print(f"✅ Hay {actives_data['count']} activos disponibles")
            
            # Find best active
            preferred_actives = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY"]
            selected_active = None
            
            for pref in preferred_actives:
                for active in open_actives:
                    if active["active_id"] == pref and (active["binary_enabled"] or active["turbo_enabled"]):
                        selected_active = pref
                        print(f"   Usando: {pref} ✓")
                        break
                if selected_active:
                    break
            
            if not selected_active and open_actives:
                # Use the first available
                selected_active = open_actives[0]["active_id"]
                print(f"   Usando: {selected_active}")
            
            if not selected_active:
                print("❌ No hay activos disponibles para trading en este momento")
                print("Los mercados pueden estar cerrados. Intenta más tarde.")
                sys.exit(1)
        else:
            print("⚠️  No se pudo verificar mercados, usando EURUSD por defecto")
            selected_active = "EURUSD"
    except Exception as e:
        print(f"⚠️  Error verificando mercados: {e}, usando EURUSD por defecto")
        selected_active = "EURUSD"
    
    # 3. Verify selected market
    print(f"\n[3/5] 🔍 Verificando {selected_active}...")
    response = requests.get(f"{BASE_URL}/check-market/{selected_active}", headers=headers)
    if response.status_code == 200:
        market_info = response.json()
        if market_info["is_open"]:
            print(f"✅ {selected_active} está abierto para trading")
            print(f"   Balance: ${market_info['balance']:.2f}")
            print(f"   Cuenta: {market_info['account_type']}")
        else:
            print(f"⚠️  {selected_active} podría estar cerrado")
    
    # 4. Listar estrategias disponibles
    print("\n[4/5] 📊 Estrategias disponibles:")
    response = requests.get(f"{BASE_URL}/bot/strategies", headers=headers)
    strategies = response.json()["strategies"]
    for name, info in strategies.items():
        print(f"  • {name}: {info['name']}")
    
    # 5. Crear bot
    print(f"\n[5/5] 🔧 Creando bot de prueba para {selected_active}...")
    bot_config = {
        "name": f"Bot Test RSI {selected_active}",
        "active_id": selected_active,
        "strategy": "rsi",
        "initial_amount": 1.0,
        "max_amount": 10.0,
        "duration": 1,
        "stop_loss": 5.0,
        "stop_gain": 10.0,
        "max_trades_per_day": 5,
        "account_type": "PRACTICE",
        "strategy_config": {
            "period": 14,
            "oversold": 30,
            "overbought": 70
        }
    }
    
    response = requests.post(f"{BASE_URL}/bot/create", headers=headers, json=bot_config)
    
    if response.status_code != 201:
        print(f"❌ Error creando bot: {response.json()}")
        sys.exit(1)
    
    bot_id = response.json()["bot_id"]
    print(f"✅ Bot creado con ID: {bot_id}")
    print(f"   Activo: {bot_config['active_id']}")
    print(f"   Estrategia: {bot_config['strategy']}")
    print(f"   Monto inicial: ${bot_config['initial_amount']}")
    
    # 6. Iniciar bot
    print("\n[6/6] 🚀 Iniciando bot...")
    response = requests.post(f"{BASE_URL}/bot/{bot_id}/start", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error iniciando bot: {response.json()}")
        sys.exit(1)
    
    print("✅ Bot iniciado exitosamente!")
    print("\n" + "=" * 70)
    print("🎯 EL BOT ESTÁ CORRIENDO")
    print("=" * 70)
    print("\nMira la consola donde ejecutaste 'python run_prod.py' para ver los logs")
    print("\nComandos útiles:")
    print(f"  • Ver señales: curl -H 'Authorization: Bearer {token}' {BASE_URL}/bot/{bot_id}/signals")
    print(f"  • Detener bot: curl -X POST -H 'Authorization: Bearer {token}' {BASE_URL}/bot/{bot_id}/stop")
    print(f"  • Ver estado:  curl -H 'Authorization: Bearer {token}' {BASE_URL}/bot/{bot_id}")
    print("\nPresiona Ctrl+C para salir de este script (el bot seguirá corriendo)")
    
    # Monitoreo simple
    print("\n" + "-" * 70)
    print("📈 Monitoreando señales (actualiza cada 30 segundos)...")
    print("-" * 70)
    
    try:
        while True:
            time.sleep(30)
            response = requests.get(f"{BASE_URL}/bot/{bot_id}/signals?limit=5", headers=headers)
            if response.status_code == 200:
                data = response.json()
                stats = data["statistics"]
                signals = data["signals"]
                
                print(f"\n⏰ {time.strftime('%H:%M:%S')}")
                print(f"   Total operaciones: {stats['total_trades']}")
                print(f"   Ganadas: {stats['won_trades']} | Perdidas: {stats['lost_trades']}")
                print(f"   Win Rate: {stats['win_rate']:.1f}%")
                print(f"   PnL Total: ${stats['total_pnl']:.2f}")
                
                if signals:
                    print(f"   Última señal: {signals[0]['signal_type']} - {signals[0]['status']}")
    
    except KeyboardInterrupt:
        print("\n\n✋ Script de monitoreo detenido")
        print(f"El bot {bot_id} sigue corriendo en el servidor")
        print(f"Para detenerlo: curl -X POST -H 'Authorization: Bearer {token}' {BASE_URL}/bot/{bot_id}/stop")

if __name__ == "__main__":
    main()
