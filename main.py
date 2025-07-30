
import os
import time
import threading
import requests
from flask import Flask, jsonify, render_template_string
from mnemonic import Mnemonic
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import json
from datetime import datetime

# Telegram sozlamalari
TELEGRAM_TOKEN = os.getenv("TG_TOKEN", "8361927125:AAENYSNmtaLkqO61bOPnQ6yNQcYlqLLLQ-g")
CHAT_ID = os.getenv("TG_CHAT_ID", "7521446360")

# Flask monitoring
app = Flask(__name__)
status = {
    "running": True, 
    "checked": 0, 
    "found": 0,
    "start_time": time.time(),
    "per_second": 0,
    "success_rate": 0.0,
    "last_addresses": [],
    "batch_size": 10
}

# API endpoints for better performance
API_ENDPOINTS = [
    {
        "name": "Blockstream.info",
        "url": "https://blockstream.info/api/address/{}/utxo",
        "type": "utxo",
        "status": "active",
        "errors": 0,
        "last_error": None
    },
    {
        "name": "Mempool.space", 
        "url": "https://mempool.space/api/address/{}/utxo",
        "type": "utxo",
        "status": "active",
        "errors": 0,
        "last_error": None
    },
    {
        "name": "Blockchain.info",
        "url": "https://blockchain.info/q/addressbalance/{}",
        "type": "balance",
        "status": "active", 
        "errors": 0,
        "last_error": None
    },
    {
        "name": "BlockCypher",
        "url": "https://api.blockcypher.com/v1/btc/main/addrs/{}/balance",
        "type": "balance",
        "status": "active",
        "errors": 0,
        "last_error": None
    },
    {
        "name": "BitPay Insight",
        "url": "https://insight.bitpay.com/api/addr/{}/balance",
        "type": "balance", 
        "status": "active",
        "errors": 0,
        "last_error": None
    }
]

current_api_index = 0
api_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "api_switches": 0
}

# Telegramga xabar yuboruvchi funksiya
def send_telegram(msg):
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
        if not res.ok:
            print(f"⚠️ Telegram error: {res.text}")
    except Exception as e:
        print(f"❌ Telegramga yuborishda xatolik: {e}")

# Enhanced API chain with error handling and logging
def check_balance_btc_optimized(address):
    global current_api_index, api_stats
    
    api_stats["total_requests"] += 1
    
    for attempt in range(len(API_ENDPOINTS)):
        current_api = API_ENDPOINTS[current_api_index]
        api_name = current_api["name"]
        api_url = current_api["url"]
        api_type = current_api["type"]
        
        try:
            url = api_url.format(address)
            res = requests.get(url, timeout=8)
            
            if res.status_code == 200:
                # Parse response based on API type
                if api_type == "utxo":
                    utxos = res.json()
                    balance = sum(utxo['value'] for utxo in utxos) / 1e8
                elif api_type == "balance":
                    if "blockchain.info" in api_url:
                        balance = int(res.text) / 1e8
                    elif "blockcypher.com" in api_url:
                        data = res.json()
                        balance = data.get('balance', 0) / 1e8
                    elif "insight.bitpay.com" in api_url:
                        balance = float(res.text)
                    else:
                        balance = 0
                
                # Success - reset error count
                current_api["errors"] = 0
                current_api["status"] = "active"
                api_stats["successful_requests"] += 1
                
                print(f"✅ {api_name}: {address} → {balance} BTC")
                return balance
                
            else:
                raise Exception(f"HTTP {res.status_code}: {res.text[:100]}")
                
        except Exception as e:
            # Log error
            error_msg = str(e)[:100]
            current_api["errors"] += 1
            current_api["last_error"] = error_msg
            current_api["status"] = "error" if current_api["errors"] > 3 else "warning"
            
            api_stats["failed_requests"] += 1
            
            print(f"❌ {api_name} xatolik: {error_msg}")
            
            # Switch to next API
            old_index = current_api_index
            current_api_index = (current_api_index + 1) % len(API_ENDPOINTS)
            
            if old_index != current_api_index:
                api_stats["api_switches"] += 1
                next_api = API_ENDPOINTS[current_api_index]
                print(f"🔄 API almashtirildi: {api_name} → {next_api['name']}")
            
            continue
            
    print(f"💥 Barcha APIlar ishlamadi: {address}")
    return 0

# Enhanced batch balance checker with API chain
def check_batch_balances(addresses):
    """Bir vaqtda bir nechta addressni tekshirish"""
    results = []
    
    # Try batch APIs first
    batch_apis = [
        {
            "name": "BlockCypher Batch",
            "url": "https://api.blockcypher.com/v1/btc/main/addrs/{}/balance",
            "separator": ";"
        }
    ]
    
    for batch_api in batch_apis:
        try:
            addresses_str = batch_api["separator"].join(addresses)
            batch_url = batch_api["url"].replace("{}", addresses_str)
            
            res = requests.get(batch_url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                
                if isinstance(data, list):
                    for item in data:
                        balance = item.get('balance', 0) / 1e8
                        results.append(balance)
                else:
                    balance = data.get('balance', 0) / 1e8
                    results.append(balance)
                
                print(f"✅ Batch API {batch_api['name']}: {len(results)} addresses processed")
                return results
                
        except Exception as e:
            print(f"❌ Batch API {batch_api['name']} xatolik: {e}")
            continue
    
    # Fallback to individual API chain
    print("🔄 Individual API chain ga o'tilmoqda...")
    for address in addresses:
        balance = check_balance_btc_optimized(address)
        results.append(balance)
        time.sleep(0.1)  # Rate limiting
        
    return results

# Mnemonic dan Bitcoin address yaratish
def generate_btc_address(mnemonic):
    try:
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
        bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0)
        address = bip44_addr_ctx.PublicKey().ToAddress()
        return address
    except Exception as e:
        print(f"❗ Address yaratishda xatolik: {e}")
        return None

# Performance calculator
def update_performance():
    elapsed_time = time.time() - status["start_time"]
    if elapsed_time > 0:
        status["per_second"] = status["checked"] / elapsed_time
        status["success_rate"] = (status["found"] / status["checked"] * 100) if status["checked"] > 0 else 0.0

# Optimized scanner with batch processing
def start_scanning():
    send_telegram("✅ Optimized skanning boshlandi.")
    mnemo = Mnemonic("english")
    
    while status["running"]:
        try:
            # Batch yaratish
            batch_mnemonics = []
            batch_addresses = []
            
            for _ in range(status["batch_size"]):
                seed_phrase = mnemo.generate(strength=128)
                address = generate_btc_address(seed_phrase)
                if address:
                    batch_mnemonics.append(seed_phrase)
                    batch_addresses.append(address)
            
            if batch_addresses:
                # Batch balanslarni tekshirish
                balances = check_batch_balances(batch_addresses)
                
                for i, (mnemonic, address, balance) in enumerate(zip(batch_mnemonics, batch_addresses, balances)):
                    status["checked"] += 1
                    
                    # Last addresses list update
                    status["last_addresses"].append({
                        "address": address,
                        "balance": balance,
                        "time": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    # Keep only last 20 addresses
                    if len(status["last_addresses"]) > 20:
                        status["last_addresses"].pop(0)
                    
                    if balance > 0:
                        status["found"] += 1
                        message = (
                            f"💸 TOPILDI!\n\n"
                            f"🧠 Mnemonic: {mnemonic}\n"
                            f"🏦 Address: {address}\n"
                            f"💰 Balance: {balance} BTC\n"
                            f"📊 #{status['checked']} ta tekshirilgan"
                        )
                        send_telegram(message)
                        print(f"🎉 TOPILDI: {address} → {balance} BTC")
                    else:
                        print(f"🔍 {status['checked']}: {address} → 0 BTC")
                
                # Performance update
                update_performance()
                time.sleep(0.1)
            else:
                time.sleep(1)
                
        except Exception as e:
            print(f"❗ Xatolik: {e}")
            time.sleep(1)

# Real-time dashboard template
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🔍 BTC Scanner Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            border-radius: 15px; 
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-value { font-size: 2.5em; font-weight: bold; margin: 10px 0; }
        .stat-label { font-size: 0.9em; opacity: 0.8; }
        .progress-bar { 
            width: 100%; 
            height: 8px; 
            background: rgba(255,255,255,0.2); 
            border-radius: 4px; 
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill { 
            height: 100%; 
            background: linear-gradient(90deg, #00ff88, #00cc6a); 
            transition: width 0.3s ease;
        }
        .recent-addresses { 
            background: rgba(255,255,255,0.1); 
            padding: 20px; 
            border-radius: 15px; 
            backdrop-filter: blur(10px);
        }
        .address-item { 
            display: flex; 
            justify-content: space-between; 
            padding: 8px 0; 
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-family: monospace;
            font-size: 0.9em;
        }
        .success { color: #00ff88; }
        .zero { color: #ff6b6b; }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        .btn {
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            margin: 0 10px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .btn.stop { background: rgba(255,107,107,0.6); }
        .status-running { color: #00ff88; }
        .status-stopped { color: #ff6b6b; }
    </style>
    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('checked').textContent = data.checked.toLocaleString();
                    document.getElementById('found').textContent = data.found;
                    document.getElementById('per_second').textContent = data.per_second.toFixed(2);
                    document.getElementById('success_rate').textContent = data.success_rate.toFixed(6) + '%';
                    document.getElementById('uptime').textContent = formatTime(data.uptime);
                    document.getElementById('batch_size').textContent = data.batch_size;
                    
                    const status = document.getElementById('status');
                    status.textContent = data.running ? '✅ RUNNING' : '⛔ STOPPED';
                    status.className = data.running ? 'status-running' : 'status-stopped';
                    
                    // Update API stats
                    if (data.api_stats) {
                        document.getElementById('current_api').textContent = data.current_api || '-';
                        document.getElementById('api_switches').textContent = data.api_stats.api_switches || 0;
                        document.getElementById('successful_requests').textContent = data.api_stats.successful_requests || 0;
                        document.getElementById('failed_requests').textContent = data.api_stats.failed_requests || 0;
                    }
                    
                    // Update API status
                    if (data.api_endpoints) {
                        const apiStatusDiv = document.getElementById('api-status');
                        apiStatusDiv.innerHTML = data.api_endpoints.map(api => {
                            const statusColor = api.status === 'active' ? '#00ff88' : 
                                              api.status === 'warning' ? '#ffeb3b' : '#ff6b6b';
                            return `<div class="address-item">
                                <span>${api.name}</span>
                                <span style="color: ${statusColor};">${api.status.toUpperCase()}</span>
                                <span>Errors: ${api.errors}</span>
                            </div>`;
                        }).join('');
                    }
                    
                    // Update recent addresses
                    const recentDiv = document.getElementById('recent-addresses');
                    recentDiv.innerHTML = data.last_addresses.map(addr => 
                        `<div class="address-item">
                            <span>${addr.address}</span>
                            <span class="${addr.balance > 0 ? 'success' : 'zero'}">${addr.balance} BTC</span>
                            <span>${addr.time}</span>
                        </div>`
                    ).join('');
                });
        }
        
        function formatTime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            return `${hours}h ${minutes}m ${secs}s`;
        }
        
        setInterval(updateStats, 2000);
        updateStats();
    </script>
</head>
<body>
    <div class="container">
        <h1>🔍 Bitcoin Wallet Scanner Dashboard</h1>
        
        <div class="controls">
            <span id="status" class="status-running">✅ RUNNING</span>
            <button class="btn stop" onclick="window.location.href='/stop'">🛑 Stop Scanner</button>
            <button class="btn" onclick="updateStats()">🔄 Refresh</button>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Tekshirilgan Walletlar</div>
                <div class="stat-value" id="checked">0</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Topilgan Walletlar</div>
                <div class="stat-value" id="found">0</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Tezlik (wallet/sekund)</div>
                <div class="stat-value" id="per_second">0.00</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Muvaffaqiyat Foizi</div>
                <div class="stat-value" id="success_rate">0.000000%</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Ishlash Vaqti</div>
                <div class="stat-value" id="uptime">0h 0m 0s</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Batch Size</div>
                <div class="stat-value" id="batch_size">10</div>
            </div>
        </div>
        
        <div class="recent-addresses">
            <h3>📊 So'nggi Tekshirilgan Addresslar</h3>
            <div id="recent-addresses">
                <!-- Real-time data will be loaded here -->
            </div>
        </div>
        
        <div class="recent-addresses" style="margin-top: 20px;">
            <h3>🔌 API Holati va Statistika</h3>
            <div class="stats" style="margin: 20px 0;">
                <div class="stat-card">
                    <div class="stat-label">Joriy API</div>
                    <div class="stat-value" id="current_api" style="font-size: 1.5em;">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">API Almashtirishlar</div>
                    <div class="stat-value" id="api_switches">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Muvaffaqiyatli So'rovlar</div>
                    <div class="stat-value" id="successful_requests">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Xatoli So'rovlar</div>
                    <div class="stat-value" id="failed_requests">0</div>
                </div>
            </div>
            <div id="api-status">
                <!-- API status will be loaded here -->
            </div>
        </div>
    </div>
</body>
</html>
'''

# Flask routes
@app.route("/")
def dashboard():
    return DASHBOARD_TEMPLATE

@app.route("/api/stats")
def api_stats_endpoint():
    uptime = time.time() - status["start_time"]
    return jsonify({
        "running": status["running"],
        "checked": status["checked"],
        "found": status["found"],
        "per_second": status["per_second"],
        "success_rate": status["success_rate"],
        "uptime": uptime,
        "batch_size": status["batch_size"],
        "last_addresses": status["last_addresses"],
        "api_stats": api_stats,
        "current_api": API_ENDPOINTS[current_api_index]["name"],
        "api_endpoints": API_ENDPOINTS
    })

@app.route("/stop")
def stop():
    status["running"] = False
    send_telegram("🛑 Optimized skanning to'xtatildi.")
    return "<h2>✅ To'xtatildi!</h2><a href='/'>Dashboard ga qaytish</a>"

@app.route("/config/<int:batch_size>")
def config_batch(batch_size):
    if 1 <= batch_size <= 50:
        status["batch_size"] = batch_size
        return jsonify({"message": f"Batch size {batch_size} ga o'zgartirildi", "batch_size": batch_size})
    return jsonify({"error": "Batch size 1-50 orasida bo'lishi kerak"}), 400

# Dasturni ishga tushirish
if __name__ == "__main__":
    try:
        # Scanner threadini ishga tushirish
        scanner_thread = threading.Thread(target=start_scanning, daemon=True)
        scanner_thread.start()
        
        # Flask serverni ishga tushirish
        print("🚀 Optimized BTC Scanner ishga tushmoqda...")
        print("📊 Dashboard: http://localhost:5000")
        app.run(host="0.0.0.0", port=5000, debug=False)
        
    except KeyboardInterrupt:
        status["running"] = False
        print("📴 Dastur to'xtatildi.")
