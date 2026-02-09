import asyncio
import threading
import logging
import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from playwright.async_api import async_playwright

# --- CONFIGURAÇÕES ---
TOKEN = "8285641434:AAFiRbk1Q3GZq3BP_6sm7COsFEtLALSa_gs"
DB_NAME = "database.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FullStackBot")

# ==========================================
# 1. DATABASE (SQLite - 0800)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bins (
            bin TEXT PRIMARY KEY,
            country TEXT,
            vendor TEXT,
            bank TEXT,
            level TEXT,
            type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_bin_local(data):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO bins (bin, country, vendor, bank, level, type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['bin'], data['country'], data['vendor'], data['bank'], data['level'], data['type']))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro DB: {e}")

# ==========================================
# 2. FLASK UI (Dark Mode 4K / Modern)
# ==========================================
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>BIN Master Dashboard</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .glow { box-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }
    </style>
</head>
<body class="p-8 font-sans">
    <div class="max-w-6xl mx-auto">
        <header class="flex justify-between items-center mb-12">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight text-blue-500">BIN_SCRAPER <span class="text-white text-sm font-mono tracking-widest">v2.0</span></h1>
                <p class="text-slate-400">Monitoramento de mineração em tempo real</p>
            </div>
            <div class="glass p-4 rounded-2xl text-center glow">
                <span class="text-3xl font-bold text-blue-400" id="count">0</span>
                <p class="text-xs uppercase tracking-widest text-slate-500">Bins no Banco</p>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12" id="latest-stats">
            </div>

        <div class="glass rounded-3xl overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead class="bg-slate-800/50">
                    <tr>
                        <th class="p-4 font-semibold text-blue-400">BIN</th>
                        <th class="p-4 font-semibold text-blue-400">PAÍS</th>
                        <th class="p-4 font-semibold text-blue-400">BANCO</th>
                        <th class="p-4 font-semibold text-blue-400">NÍVEL</th>
                        <th class="p-4 font-semibold text-blue-400">TIPO</th>
                    </tr>
                </thead>
                <tbody id="bin-table-body">
                    </tbody>
            </table>
        </div>
    </div>

    <script>
        async function updateData() {
            const res = await fetch('/api/data');
            const data = await res.json();
            document.getElementById('count').innerText = data.total;
            
            const tbody = document.getElementById('bin-table-body');
            tbody.innerHTML = data.bins.map(b => `
                <tr class="border-t border-slate-700/50 hover:bg-slate-700/30 transition">
                    <td class="p-4 font-mono text-yellow-400 font-bold">${b[0]}</td>
                    <td class="p-4 text-slate-300">${b[1]}</td>
                    <td class="p-4 text-slate-300 font-medium">${b[3]}</td>
                    <td class="p-4"><span class="bg-blue-900/40 text-blue-400 px-2 py-1 rounded-md text-xs font-bold">${b[4]}</span></td>
                    <td class="p-4 text-slate-500">${b[5]}</td>
                </tr>
            `).join('');
        }
        setInterval(updateData, 3000);
        updateData();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bins ORDER BY timestamp DESC LIMIT 15')
    rows = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM bins')
    total = cursor.fetchone()[0]
    conn.close()
    return jsonify({"bins": rows, "total": total})

# ==========================================
# 3. WORKER & BOT (Aiogram + Playwright)
# ==========================================
async def miner_task():
    """Worker minerando em background"""
    logger.info("Minerador Iniciado...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        while True:
            # Simulando lógica de varredura (Para bins.su, injetar os seletores aqui)
            try:
                current_bin = str(random.randint(400000, 599999))
                # Mock de extração (substitua pelo page.goto real se quiser o scrap ao vivo)
                data = {
                    "bin": current_bin, "country": "Brazil BR", "vendor": "VISA",
                    "bank": "NUBANK", "level": "PLATINUM", "type": "CREDIT"
                }
                save_bin_local(data)
                await asyncio.sleep(10) # Delay para evitar ban
            except Exception as e:
                logger.error(f"Erro miner: {e}")
                await asyncio.sleep(5)

async def main_async():
    init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    @dp.message(Command("bin"))
    async def cmd_bin(message: types.Message):
        bin_num = message.text.split()[-1][:6]
        conn = sqlite3.connect(DB_NAME)
        res = conn.execute('SELECT * FROM bins WHERE bin = ?', (bin_num,)).fetchone()
        conn.close()
        
        if res:
            await message.answer(f"💳 **BIN:** `{res[0]}`\n🌎 **País:** {res[1]}\n🏷️ **Bandeira:** {res[2]}\n🏦 **Banco:** {res[3]}\n🏆 **Nível:** {res[4]}\n💳 **Tipo:** {res[5]}", parse_mode="Markdown")
        else:
            await message.answer("❌ BIN não minerada ainda.")

    asyncio.create_task(miner_task())
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Roda o Flask em Thread separada
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)).start()
    # Roda o Bot/Worker
    asyncio.run(main_async())
