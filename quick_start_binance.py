"""Quick start script for Binance trading bot."""

import requests
import sys
import json
from datetime import datetime

def quick_start_binance(email, password, binance_api_key, binance_api_secret):
    """Setup and start a Binance bot automatically."""
    
    base_url = "http://localhost:5000"
    
    print("="*70)
    print("🚀 BINANCE BOT QUICK START")
    print("="*70)
    print()
    
    # Step 1: Login
    print("Step 1/6: Logging in to IQBTS...")
    try:
        login_response = requests.post(f"{base_url}/login", json={
            "email": email,
            "password": password
        })
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.text}")
            return
        
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")
        print()
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return
    
    # Step 2: Add Binance API key
    print("Step 2/6: Adding Binance API credentials...")
    try:
        api_key_response = requests.post(
            f"{base_url}/binance/api-key/create",
            headers=headers,
            json={
                "name": f"Testnet Key {datetime.now().strftime('%Y-%m-%d')}",
                "api_key": binance_api_key,
                "api_secret": binance_api_secret,
                "is_testnet": True
            }
        )
        
        if api_key_response.status_code != 201:
            print(f"❌ Failed to add API key: {api_key_response.text}")
            return
        
        api_key_id = api_key_response.json()["api_key"]["id"]
        print(f"✅ API key added (ID: {api_key_id})")
        print()
    except Exception as e:
        print(f"❌ Error adding API key: {e}")
        return
    
    # Step 3: Check balance
    print("Step 3/6: Checking Binance testnet balance...")
    try:
        balance_response = requests.get(
            f"{base_url}/binance/api-key/{api_key_id}/balance",
            headers=headers
        )
        
        if balance_response.status_code == 200:
            balances = balance_response.json()["balances"]
            print("✅ Balance retrieved:")
            for b in balances[:5]:  # Show first 5
                print(f"   {b['asset']}: {b['free']:.8f} (locked: {b['locked']:.8f})")
            print()
        else:
            print(f"⚠️  Could not retrieve balance: {balance_response.text}")
            print()
    except Exception as e:
        print(f"⚠️  Error checking balance: {e}")
        print()
    
    # Step 4: Create bot
    print("Step 4/6: Creating Binance bot...")
    bot_config = {
        "name": "BTCUSDT RSI Bot",
        "api_key_id": api_key_id,
        "symbol": "BTCUSDT",
        "market_type": "spot",
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
    }
    
    try:
        create_response = requests.post(
            f"{base_url}/binance/bot/create",
            headers=headers,
            json=bot_config
        )
        
        if create_response.status_code != 201:
            print(f"❌ Failed to create bot: {create_response.text}")
            return
        
        bot = create_response.json()["bot"]
        bot_id = bot["id"]
        print(f"✅ Bot created: {bot['name']} (ID: {bot_id})")
        print(f"   Symbol: {bot['symbol']}")
        print(f"   Strategy: {bot['strategy']}")
        print()
    except Exception as e:
        print(f"❌ Error creating bot: {e}")
        return
    
    # Step 5: Get available strategies info
    print("Step 5/6: Getting strategy information...")
    try:
        strategies_response = requests.get(
            f"{base_url}/binance/strategies",
            headers=headers
        )
        
        if strategies_response.status_code == 200:
            strategies = strategies_response.json()["strategies"]
            print(f"✅ Available strategies: {len(strategies)}")
            for s in strategies:
                print(f"   - {s['name']}: {s['display_name']}")
            print()
    except Exception as e:
        print(f"⚠️  Error getting strategies: {e}")
        print()
    
    # Step 6: Start bot
    print("Step 6/6: Starting bot...")
    try:
        start_response = requests.post(
            f"{base_url}/binance/bot/{bot_id}/start",
            headers=headers
        )
        
        if start_response.status_code != 200:
            print(f"❌ Failed to start bot: {start_response.text}")
            return
        
        print("✅ Bot started successfully!")
        print()
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return
    
    # Summary
    print("="*70)
    print("📊 SETUP COMPLETE")
    print("="*70)
    print()
    print(f"Bot ID: {bot_id}")
    print(f"Bot Name: {bot['name']}")
    print(f"Symbol: {bot['symbol']}")
    print(f"Strategy: RSI (14 period)")
    print(f"Position Size: 10% of balance")
    print(f"Max Daily Loss: $50 USDT")
    print(f"Max Daily Gain: $100 USDT")
    print()
    print("📝 The bot is now running on the server (run_prod.py)")
    print()
    print("Useful commands:")
    print(f"  📊 View trades: curl {base_url}/binance/bot/{bot_id}/trades -H 'Authorization: Bearer {token}'")
    print(f"  🛑 Stop bot: curl -X POST {base_url}/binance/bot/{bot_id}/stop -H 'Authorization: Bearer {token}'")
    print(f"  💰 Check balance: curl {base_url}/binance/api-key/{api_key_id}/balance -H 'Authorization: Bearer {token}'")
    print()
    print("⚠️  IMPORTANT:")
    print("  - This is using TESTNET (fake money)")
    print("  - Monitor the bot for at least 1 week before considering real trading")
    print("  - Never invest more than you can afford to lose")
    print()
    print("="*70)
    print()
    
    # Monitor for a bit
    print("Monitoring bot for 60 seconds...")
    print("Press Ctrl+C to stop monitoring (bot will keep running)")
    print()
    
    try:
        import time
        for i in range(12):  # 60 seconds
            time.sleep(5)
            try:
                trades_response = requests.get(
                    f"{base_url}/binance/bot/{bot_id}/trades?limit=5",
                    headers=headers
                )
                
                if trades_response.status_code == 200:
                    data = trades_response.json()
                    stats = data['statistics']
                    print(f"[{i*5}s] Trades: {stats['total_trades']}, "
                          f"Wins: {stats['wins']}, "
                          f"Losses: {stats['losses']}, "
                          f"P&L: ${stats['total_pnl']:.2f}")
            except:
                pass
    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped (bot still running)")
        print(f"To stop the bot: curl -X POST {base_url}/binance/bot/{bot_id}/stop -H 'Authorization: Bearer {token}'")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python quick_start_binance.py <email> <password> <binance_api_key> <binance_api_secret>")
        print()
        print("Get Binance Testnet credentials:")
        print("  1. Go to https://testnet.binance.vision/")
        print("  2. Login with GitHub")
        print("  3. Generate API Key and Secret")
        print()
        print("Example:")
        print("  python quick_start_binance.py user@example.com password123 YOUR_API_KEY YOUR_API_SECRET")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    api_key = sys.argv[3]
    api_secret = sys.argv[4]
    
    quick_start_binance(email, password, api_key, api_secret)
