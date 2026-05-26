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
        {"command": "status", "description": "Mengecek kondisi bot"},
        {"command": "log", "description": "Melihat log terbaru"},
        {"command": "stop", "description": "Menjeda pencarian"},
        {"command": "start", "description": "Melanjutkan pencarian"},
        {"command": "update", "description": "Menarik update kode"},
        {"command": "restart", "description": "Restart bot"}
    ]
    try:
        requests.post(url, json={"commands": commands}, timeout=10)
    except:
        pass

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
                msg = ("🤖 <b>Daftar Perintah Bot InfoLoker:</b>\n\n"
                       "Gunakan tombol di bawah, atau ketik perintah:\n"
                       "/status - Mengecek apakah bot berjalan normal\n"
                       "/log - Melihat log/catatan aktivitas bot terakhir\n"
                       "/stop - Menghentikan sementara pencarian loker\n"
                       "/start - Melanjutkan pencarian loker\n"
                       "/restart - Memulai ulang (restart) script bot\n"
                       "/update - Menarik pembaruan kode terbaru dari GitHub")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/status":
                send_telegram_message("🔍 Mengambil status systemd...", reply_markup=main_keyboard)
                try:
                    result = subprocess.run(["systemctl", "status", "bot-infoloker", "--no-pager"], capture_output=True, text=True)
                    out = result.stdout.strip()
                    if not out:
                        out = result.stderr.strip()
                    send_telegram_message(f"🖥️ <b>Systemd Status:</b>\n<pre>{out[:3000]}</pre>", reply_markup=main_keyboard)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal mengambil status: {e}", reply_markup=main_keyboard)
                    
            elif text == "/log":
                send_telegram_message("🔍 Menarik log sistem terbaru...")
                try:
                    # Mengambil 15 baris terakhir dari log systemd
                    result = subprocess.run(["journalctl", "-u", "bot-infoloker", "-n", "15", "--no-pager"], capture_output=True, text=True)
                    out = result.stdout.strip()
                    if out:
                        send_telegram_message(f"📋 <b>Log Terbaru:</b>\n<pre>{out[-3000:]}</pre>", reply_markup=main_keyboard)
                    else:
                        send_telegram_message("📋 Log kosong atau bot tidak dijalankan via systemd.", reply_markup=main_keyboard)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal mengambil log: {e}", reply_markup=main_keyboard)
                    
            elif text == "/stop":
                if not os.path.exists("stop.flag"):
                    open("stop.flag", "w").close()
                send_telegram_message("🔴 Bot berhasil dijeda. Tidak ada pengecekan lowongan baru hingga Anda menekan /start.", reply_markup=main_keyboard)
                
            elif text == "/start":
                if os.path.exists("stop.flag"):
                    os.remove("stop.flag")
                send_telegram_message("🟢 Bot dilanjutkan! Kembali mencari lowongan pekerjaan...", reply_markup=main_keyboard)
                
            elif text == "/restart":
                send_telegram_message("🔄 Me-restart bot... (Jika pakai PM2/systemd, bot akan otomatis nyala lagi)", reply_markup=main_keyboard)
                os._exit(1)
                
            elif text == "/update":
                send_telegram_message("⏳ Sedang menarik update dari GitHub...")
                try:
                    result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
                    out = result.stdout.strip()
                    if "Already up to date" in out:
                        send_telegram_message("✅ Kode bot sudah versi paling baru.", reply_markup=main_keyboard)
                    else:
                        send_telegram_message(f"✅ Update berhasil ditarik!\n<pre>{out[:500]}</pre>\n\nBot akan otomatis restart sekarang...", reply_markup=main_keyboard)
                        os._exit(1)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal update: {e}", reply_markup=main_keyboard)
            else:
                send_telegram_message("❓ Perintah tidak dikenali. Ketik /help untuk melihat daftar perintah atau gunakan tombol di bawah.", reply_markup=main_keyboard)
                
        time.sleep(1)
