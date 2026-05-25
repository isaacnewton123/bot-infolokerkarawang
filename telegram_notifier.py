import requests
import os
from dotenv import load_dotenv

# Muat variabel dari .env
load_dotenv()

# Konfigurasi Telegram dari .env
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    """
    Mengirimkan pesan ke akun Telegram menggunakan Bot API.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
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
