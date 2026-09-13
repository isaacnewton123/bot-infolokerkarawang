import requests
import os
import time
import subprocess
import sys
from dotenv import load_dotenv

# Muat variabel dari .env
load_dotenv()

# Konfigurasi Telegram dari .env
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Path log file untuk Termux (bukan systemd/journalctl)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, 'bot.log')

def send_telegram_message(message, reply_markup=None):
    """
    Mengirimkan pesan ke akun Telegram menggunakan Bot API.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("[✓] Notifikasi Telegram berhasil terkirim!")
            return True
        else:
            print(f"[x] Gagal mengirim Telegram. Status: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"[x] Error koneksi Telegram: {e}")
        return False

if __name__ == "__main__":
    # Test pengiriman pesan
    print("Mencoba mengirim pesan uji coba ke Telegram Anda...")
    sukses = send_telegram_message("🤖 <b>TEST BOT INFOLOKER</b>\n\nHalo bos! Bot auto-apply sudah berhasil terhubung dengan Telegram Anda. Siap mencari kerja!")
    if sukses:
        print("Silakan cek HP Anda, pesan seharusnya sudah masuk.")
        
def get_telegram_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30} # long polling for 30 seconds
    if offset:
        params["offset"] = offset
        
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get("result", [])
    except Exception as e:
        # print(f"[x] Error getUpdates Telegram: {e}")
        pass
    return []

def set_bot_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    commands = [
        {"command": "status", "description": "📊 Cek kondisi bot"},
        {"command": "log", "description": "📋 Lihat log terbaru"},
        {"command": "stop", "description": "⏸ Jeda pencarian"},
        {"command": "start", "description": "▶️ Lanjutkan pencarian"},
        {"command": "update", "description": "🔄 Tarik update GitHub"},
        {"command": "restart", "description": "🔁 Restart bot"}
    ]
    try:
        requests.post(url, json={"commands": commands}, timeout=10)
    except:
        pass

def _get_bot_uptime():
    """Hitung uptime bot berdasarkan PID process Python saat ini."""
    try:
        pid = os.getpid()
        # Coba pakai /proc (Linux/Termux)
        stat_file = f"/proc/{pid}/stat"
        if os.path.exists(stat_file):
            boot_time = os.path.getctime(f"/proc/{pid}")
            uptime_sec = int(time.time() - boot_time)
            jam, sisa = divmod(uptime_sec, 3600)
            menit, detik = divmod(sisa, 60)
            if jam > 0:
                return f"{jam}j {menit}m {detik}d"
            elif menit > 0:
                return f"{menit}m {detik}d"
            else:
                return f"{detik} detik"
    except:
        pass
    return "N/A"

def start_command_listener():
    print("[*] Telegram Command Listener mulai berjalan...")
    
    # Daftarkan menu command bawaan Telegram
    set_bot_commands()
    
    # Buat tombol keyboard permanen
    main_keyboard = {
        "keyboard": [
            [{"text": "/status"}, {"text": "/log"}],
            [{"text": "/start"}, {"text": "/stop"}],
            [{"text": "/update"}, {"text": "/restart"}]
        ],
        "resize_keyboard": True
    }
    
    offset = None
    
    while True:
        updates = get_telegram_updates(offset)
        
        for update in updates:
            offset = update["update_id"] + 1
            
            message = update.get("message")
            if not message or "text" not in message:
                continue
                
            chat_id_from = str(message["chat"]["id"])
            text = message["text"].strip()
            
            # Verifikasi keamanan (hanya memproses dari CHAT_ID pemilik)
            if chat_id_from != CHAT_ID:
                print(f"[!] Akses ditolak dari chat id: {chat_id_from}")
                continue
                
            print(f"[Telegram] Menerima perintah: {text}")
                
            if text == "/help":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "📖 <b>Daftar Perintah</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "📊 /status — Cek kondisi bot\n"
                       "📋 /log — Lihat log aktivitas terbaru\n"
                       "⏸ /stop — Jeda pencarian loker\n"
                       "▶️ /start — Lanjutkan pencarian\n"
                       "🔄 /update — Tarik update dari GitHub\n"
                       "🔁 /restart — Restart bot\n\n"
                       "<i>Gunakan tombol di bawah untuk akses cepat.</i>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/status":
                uptime = _get_bot_uptime()
                is_paused = os.path.exists("stop.flag")
                status_emoji = "⏸" if is_paused else "🟢"
                status_text = "Dijeda" if is_paused else "Aktif"
                
                # Cek proses berjalan via ps (Termux-compatible)
                try:
                    result = subprocess.run(
                        ["ps", "aux"], capture_output=True, text=True
                    )
                    # Fallback untuk Termux yang mungkin tidak support 'aux'
                    if result.returncode != 0:
                        result = subprocess.run(
                            ["ps", "-ef"], capture_output=True, text=True
                        )
                    bot_procs = [l for l in result.stdout.splitlines() if 'auto_apply' in l and 'grep' not in l]
                    proc_count = len(bot_procs)
                except:
                    proc_count = 1  # Jika ps gagal, anggap berjalan (karena command listener aktif)
                
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       f"{status_emoji} <b>Status Bot</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"<b>Status:</b> {status_text}\n"
                       f"<b>Uptime:</b> {uptime}\n"
                       f"<b>Proses:</b> {proc_count} aktif\n"
                       f"<b>Platform:</b> Termux\n"
                       f"<b>PID:</b> <code>{os.getpid()}</code>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                    
            elif text == "/log":
                # Baca log dari file (bukan journalctl)
                try:
                    if os.path.exists(LOG_FILE):
                        with open(LOG_FILE, 'r') as f:
                            lines = f.readlines()
                        # Ambil 25 baris terakhir
                        last_lines = lines[-25:] if len(lines) > 25 else lines
                        out = ''.join(last_lines).strip()
                        if out:
                            # Potong jika terlalu panjang untuk Telegram
                            if len(out) > 3500:
                                out = out[-3500:]
                            msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                                   "📋 <b>Log Terbaru</b>\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   f"<pre>{out}</pre>")
                            send_telegram_message(msg, reply_markup=main_keyboard)
                        else:
                            send_telegram_message("📋 Log kosong.", reply_markup=main_keyboard)
                    else:
                        send_telegram_message("📋 File log belum ada. Bot mungkin baru dijalankan.", reply_markup=main_keyboard)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal membaca log: {e}", reply_markup=main_keyboard)
                    
            elif text == "/stop":
                if not os.path.exists("stop.flag"):
                    open("stop.flag", "w").close()
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "⏸ <b>Bot Dijeda</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Bot tidak akan mengecek lowongan baru sampai Anda mengirim /start.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/start":
                if os.path.exists("stop.flag"):
                    os.remove("stop.flag")
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "▶️ <b>Bot Dilanjutkan</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Kembali memantau lowongan pekerjaan baru!")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/restart":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "🔁 <b>Restart Bot</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Bot sedang di-restart...\n"
                       "Jalankan ulang secara manual di Termux jika tidak otomatis.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                os._exit(1)
                
            elif text == "/update":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "🔄 <b>Update Kode</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Sedang menarik update dari GitHub...")
                send_telegram_message(msg)
                try:
                    result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=SCRIPT_DIR)
                    out = result.stdout.strip()
                    if "Already up to date" in out:
                        send_telegram_message("✅ Kode bot sudah versi paling baru.", reply_markup=main_keyboard)
                    else:
                        msg = (f"✅ <b>Update berhasil!</b>\n\n"
                               f"<pre>{out[:500]}</pre>\n\n"
                               "Bot akan restart sekarang...")
                        send_telegram_message(msg, reply_markup=main_keyboard)
                        os._exit(1)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal update: {e}", reply_markup=main_keyboard)
            else:
                msg = ("❓ Perintah tidak dikenali.\n\n"
                       "Ketik /help untuk melihat daftar perintah,\n"
                       "atau gunakan tombol di bawah.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
        time.sleep(1)
