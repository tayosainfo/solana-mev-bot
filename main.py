
import time
import threading
from flask import Flask
from threading import Thread
import requests

# ==== Web Server Setup for Replit ====
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram MEV bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==== Telegram Bot Setup ====
BOT_TOKEN = "8116284527:AAF_X3j9sMq2gk_Lrq5AhHNhmT0UwVX37wQ"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
chat_id = None
bot_running = False
thread = None
check_interval = 30  # seconds
profit_threshold = 0.01  # 1% profit minimum to alert

def send_message(text):
    if chat_id:
        requests.get(f"{BASE_URL}/sendMessage", params={"chat_id": chat_id, "text": text})

def handle_command(command):
    global bot_running, thread
    if command == "/start":
        if not bot_running:
            bot_running = True
            thread = threading.Thread(target=trading_loop)
            thread.start()
            send_message("âœ… Bot started. Scanning for arbitrage opportunities...")
        else:
            send_message("âš ï¸ Bot is already running.")
    elif command == "/stop":
        if bot_running:
            bot_running = False
            send_message("ðŸ›‘ Bot stopped.")
        else:
            send_message("âš ï¸ Bot is not running.")

# ==== DEX APIs ====
def fetch_raydium_prices():
    try:
        url = "https://api.raydium.io/v2/sdk/liquidity/mainnet.json"
        response = requests.get(url)
        pools = response.json()
        prices = {}
        for pool in pools:
            for token in [pool["baseMint"], pool["quoteMint"]]:
                prices[token] = pool["price"]
        return prices
    except Exception as e:
        print("Error fetching Raydium prices:", e)
        return {}

def fetch_orca_prices():
    try:
        url = "https://api.orca.so/allPools"
        response = requests.get(url)
        pools = response.json()
        prices = {}
        for pool in pools:
            base = pool.get("tokenA", {}).get("mint")
            quote = pool.get("tokenB", {}).get("mint")
            price = pool.get("price") or pool.get("priceAtoB")
            if base and price:
                prices[base] = price
            if quote and price:
                prices[quote] = 1 / price if price != 0 else 0
        return prices
    except Exception as e:
        print("Error fetching Orca prices:", e)
        return {}

# ==== Arbitrage Logic ====
def find_arbitrage_opportunities():
    raydium_prices = fetch_raydium_prices()
    orca_prices = fetch_orca_prices()
    opportunities = []

    for token, ray_price in raydium_prices.items():
        orca_price = orca_prices.get(token)
        if orca_price:
            diff = orca_price - ray_price
            if diff > 0 and (diff / ray_price) >= profit_threshold:
                profit_percent = (diff / ray_price) * 100
                opportunities.append((token, ray_price, orca_price, profit_percent))
    return opportunities

# ==== Trading Loop ====
def trading_loop():
    while bot_running:
        opportunities = find_arbitrage_opportunities()
        if opportunities:
            for token, ray_price, orca_price, profit in opportunities:
                msg = (
                    f"ðŸ’° Arbitrage found for token {token}!
"
                    f"Raydium: {ray_price:.6f}
"
                    f"Orca: {orca_price:.6f}
"
                    f"Profit: {profit:.2f}%"
                )
                send_message(msg)
        else:
            send_message("ðŸ” No arbitrage opportunities found right now.")
        time.sleep(check_interval)

# ==== Telegram Polling Loop ====
def poll_messages():
    global chat_id
    last_update_id = None
    while True:
        try:
            url = f"{BASE_URL}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"
            response = requests.get(url)
            data = response.json()

            if data["ok"]:
                for result in data["result"]:
                    last_update_id = result["update_id"]
                    message = result.get("message")
                    if message:
                        chat_id = message["chat"]["id"]
                        text = message.get("text")
                        if text:
                            handle_command(text.strip())
        except Exception as e:
            print("Error polling messages:", e)
        time.sleep(3)

# ==== Start Everything ====
keep_alive()
poll_messages()
