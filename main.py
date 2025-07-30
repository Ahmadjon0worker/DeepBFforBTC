import os
import time
import threading
import requests
from flask import Flask, jsonify, render_template_string
from mnemonic import Mnemonic
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TG_TOKEN", "8361927125:AAENYSNmtaLkqO61bOPnQ6yNQcYlqLLLQ-g")
CHAT_ID = os.getenv("TG_CHAT_ID", "7521446360")

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

API_ENDPOINTS = [
    {"name": "Blockstream.info", "url": "https://blockstream.info/api/address/{}/utxo", "type": "utxo", "status": "active", "errors": 0, "last_error": None},
    {"name": "Mempool.space", "url": "https://mempool.space/api/address/{}/utxo", "type": "utxo", "status": "active", "errors": 0, "last_error": None},
    {"name": "Blockchain.info", "url": "https://blockchain.info/q/addressbalance/{}", "type": "balance", "status": "active", "errors": 0, "last_error": None},
    {"name": "BlockCypher", "url": "https://api.blockcypher.com/v1/btc/main/addrs/{}/balance", "type": "balance", "status": "active", "errors": 0, "last_error": None},
    {"name": "BitPay Insight", "url": "https://insight.bitpay.com/api/addr/{}/balance", "type": "balance", "status": "active", "errors": 0, "last_error": None}
]

current_api_index = 0
api_stats = {"total_requests": 0, "successful_requests": 0, "failed_requests": 0, "api_switches": 0}

def send_telegram(msg):
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
        if not res.ok:
            print(f"Telegram error: {res.text}")
    except Exception as e:
        print(f"Telegramga yuborishda xatolik: {e}")

def check_balance_btc_optimized(address):
    global current_api_index, api_stats
    api_stats["total_requests"] += 1
    for _ in range(len(API_ENDPOINTS)):
        api = API_ENDPOINTS[current_api_index]
        try:
            url = api["url"].format(address)
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                if api["type"] == "utxo":
                    utxos = res.json()
                    balance = sum(utxo['value'] for utxo in utxos) / 1e8
                elif api["type"] == "balance":
                    if "blockchain.info" in url:
                        balance = int(res.text) / 1e8
                    elif "blockcypher.com" in url:
                        balance = res.json().get('balance', 0) / 1e8
                    elif "insight.bitpay.com" in url:
                        balance = float(res.text)
                    else:
                        balance = 0
                api["errors"] = 0
                api["status"] = "active"
                api_stats["successful_requests"] += 1
                return balance
            else:
                raise Exception(f"HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            api["errors"] += 1
            api["last_error"] = str(e)[:100]
            api["status"] = "error" if api["errors"] > 3 else "warning"
            api_stats["failed_requests"] += 1
            current_api_index = (current_api_index + 1) % len(API_ENDPOINTS)
            api_stats["api_switches"] += 1
    return 0

def check_batch_balances(addresses):
    results = []
    for address in addresses:
        balance = check_balance_btc_optimized(address)
        results.append(balance)
        time.sleep(0.1)
    return results

def generate_btc_address(mnemonic):
    try:
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
        bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        return bip44.PublicKey().ToAddress()
    except Exception as e:
        print(f"Address yaratishda xatolik: {e}")
        return None

def update_performance():
    elapsed = time.time() - status["start_time"]
    if elapsed > 0:
        status["per_second"] = status["checked"] / elapsed
        status["success_rate"] = (status["found"] / status["checked"] * 100) if status["checked"] > 0 else 0.0

def start_scanning():
    send_telegram("Skanning boshlandi")
    mnemo = Mnemonic("english")
    while status["running"]:
        try:
            batch_mnemonics = []
            batch_addresses = []
            for _ in range(status["batch_size"]):
                phrase = mnemo.generate(strength=128)
                addr = generate_btc_address(phrase)
                if addr:
                    batch_mnemonics.append(phrase)
                    batch_addresses.append(addr)
            if batch_addresses:
                balances = check_batch_balances(batch_addresses)
                for mnemonic, address, balance in zip(batch_mnemonics, batch_addresses, balances):
                    status["checked"] += 1
                    status["last_addresses"].append({"address": address, "balance": balance, "time": datetime.now().strftime("%H:%M:%S")})
                    if len(status["last_addresses"]) > 20:
                        status["last_addresses"].pop(0)
                    if balance > 0:
                        status["found"] += 1
                        send_telegram(f"TOPILDI!\nMnemonic: {mnemonic}\nAddress: {address}\nBalance: {balance} BTC")
                update_performance()
                time.sleep(0.1)
            else:
                time.sleep(1)
        except Exception as e:
            print(f"Xatolik: {e}")
            time.sleep(1)

@app.route("/")
def dashboard():
    return render_template_string("<h1>Dashboard placeholder</h1>")

@app.route("/api/stats")
def api_stats_endpoint():
    uptime = time.time() - status["start_time"]
    return jsonify({
        **status,
        "uptime": uptime,
        "api_stats": api_stats,
        "current_api": API_ENDPOINTS[current_api_index]["name"],
        "api_endpoints": API_ENDPOINTS
    })

@app.route("/stop")
def stop():
    status["running"] = False
    send_telegram("Skanner to'xtatildi")
    return "<h2>To'xtatildi!</h2><a href='/'>Dashboard ga qaytish</a>"

@app.route("/config/<int:batch_size>")
def config_batch(batch_size):
    if 1 <= batch_size <= 50:
        status["batch_size"] = batch_size
        return jsonify({"message": f"Batch size {batch_size} ga o'zgartirildi", "batch_size": batch_size})
    return jsonify({"error": "Batch size 1-50 orasida bo'lishi kerak"}), 400

if __name__ == "__main__":
    try:
        threading.Thread(target=start_scanning, daemon=True).start()
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        status["running"] = False
        print("Dastur to'xtatildi.")
