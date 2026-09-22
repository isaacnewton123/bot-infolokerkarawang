import requests
import os
import re
import time
import subprocess
import sys
from dotenv import load_dotenv

# Muat variabel dari .env secara paksa (timpa yang ada di memory)
load_dotenv(override=True)

# Konfigurasi Telegram dari .env
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Path file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, 'bot.log')
ENV_FILE = os.path.join(SCRIPT_DIR, '.env')

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
            return True
        else:
            print(f"Gagal kirim notif Telegram (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"Koneksi Telegram bermasalah: {e}")
        return False

if __name__ == "__main__":
    print("Mengirim pesan uji coba ke Telegram...")
    sukses = send_telegram_message("🤖 <b>TEST BOT INFOLOKER</b>\n\nHalo bos! Bot sudah terhubung dengan Telegram Anda. Siap berburu loker!")
    if sukses:
        print("Pesan terkirim! Cek HP Anda.")
        
def get_telegram_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
        
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get("result", [])
    except:
        pass
    return []

def set_bot_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    commands = [
        {"command": "status", "description": "📊 Cek kondisi bot"},
        {"command": "log", "description": "📋 Lihat aktivitas terbaru"},
        {"command": "session", "description": "🔑 Ganti ci_session"},
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
    """Hitung uptime bot."""
    try:
        pid = os.getpid()
        stat_file = f"/proc/{pid}/stat"
        if os.path.exists(stat_file):
            boot_time = os.path.getctime(f"/proc/{pid}")
            uptime_sec = int(time.time() - boot_time)
            hari, sisa = divmod(uptime_sec, 86400)
            jam, sisa = divmod(sisa, 3600)
            menit, detik = divmod(sisa, 60)
            if hari > 0:
                return f"{hari} hari {jam} jam {menit} menit"
            elif jam > 0:
                return f"{jam} jam {menit} menit"
            elif menit > 0:
                return f"{menit} menit {detik} detik"
            else:
                return f"{detik} detik"
    except:
        pass
    return "Tidak diketahui"

def _update_env_session(new_session):
    """
    Update CI_SESSION di file .env secara langsung.
    Return True jika berhasil.
    """
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r') as f:
                content = f.read()
            
            # Replace CI_SESSION value
            if 'CI_SESSION=' in content:
                content = re.sub(r'CI_SESSION=.*', f'CI_SESSION={new_session}', content)
            else:
                content += f'\nCI_SESSION={new_session}\n'
            
            with open(ENV_FILE, 'w') as f:
                f.write(content)
            return True
        else:
            # Buat file .env baru
            with open(ENV_FILE, 'w') as f:
                f.write(f'CI_SESSION={new_session}\n')
            return True
    except Exception as e:
        print(f"Gagal update .env: {e}")
        return False

def _format_log_human(raw_lines):
    """
    Konversi log mentah ke format yang lebih enak dibaca manusia.
    """
    # Logika Log Matang (Smart Summary)
    # 1. Cari baris "Mulai cek lowongan baru..." terakhir (sebagai awal siklus)
    cycle_lines = []
    for line in reversed(raw_lines):
        line = line.strip()
        if not line:
            continue
        cycle_lines.insert(0, line)
        if "Mulai cek lowongan baru..." in line:
            break
            
    if not cycle_lines:
        return "Belum ada aktivitas di log."
        
    # Ekstrak waktu mulai siklus
    waktu_cek = "Tidak diketahui"
    m = re.search(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', cycle_lines[0])
    if m:
        waktu_cek = m.group(1)
        
    berhasil = []
    gagal = []
    total_lowongan = "0"
    status_istirahat = False
    
    for line in cycle_lines:
        clean = re.sub(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*', '', line)
        
        if "Berhasil melamar" in clean or "✅" in clean:
            berhasil.append(clean)
        elif "Gagal melamar" in clean or "❌" in clean:
            gagal.append(clean)
        elif "Total" in clean and "ditemukan" in clean:
            total_lowongan = clean
        elif "Istirahat" in clean or "Menunggu" in clean:
            status_istirahat = True
            
    # Buat format matang
    hasil_teks = []
    hasil_teks.append("━━━━━━━━━━━━━━━━━━━━")
    hasil_teks.append("📋 <b>LAPORAN TERAKHIR</b>")
    hasil_teks.append("━━━━━━━━━━━━━━━━━━━━\n")
    
    hasil_teks.append(f"🕒 <b>Waktu Cek:</b> {waktu_cek}")
    
    if len(berhasil) == 0 and len(gagal) == 0:
        hasil_teks.append(f"ℹ️ <b>Hasil:</b> Tidak ada lowongan baru.\n({total_lowongan})\n")
    else:
        hasil_teks.append(f"ℹ️ <b>Hasil:</b> {len(berhasil)} berhasil, {len(gagal)} gagal.\n")
        
    hasil_teks.append(f"✅ <b>Berhasil ({len(berhasil)}):</b>")
    if berhasil:
        for b in berhasil:
            hasil_teks.append(f"- {b}")
    else:
        hasil_teks.append("- Tidak ada")
        
    hasil_teks.append(f"\n❌ <b>Gagal ({len(gagal)}):</b>")
    if gagal:
        for g in gagal:
            hasil_teks.append(f"- {g}")
    else:
        hasil_teks.append("- Tidak ada")
        
    if status_istirahat:
        hasil_teks.append("\n⏳ <b>Status Bot:</b> Sedang istirahat, menunggu jadwal cek berikutnya.")
    else:
        hasil_teks.append("\n🔄 <b>Status Bot:</b> Sedang bekerja melakukan pengecekan...")
        
    return '\n'.join(hasil_teks)

# State: menunggu input ci_session dari user
_waiting_session = {}

def start_command_listener():
    print("Telegram listener aktif...")
    
    set_bot_commands()
    
    main_keyboard = {
        "keyboard": [
            [{"text": "/status"}, {"text": "/log"}],
            [{"text": "/session"}, {"text": "/stop"}],
            [{"text": "/start"}, {"text": "/restart"}]
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
            
            if chat_id_from != CHAT_ID:
                continue
            
            # Cek apakah sedang menunggu input ci_session
            if _waiting_session.get(chat_id_from):
                _waiting_session[chat_id_from] = False
                new_session = text.strip()
                
                # Validasi dasar (ci_session biasanya 26-40 karakter alfanumerik)
                if len(new_session) < 20 or ' ' in new_session:
                    msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                           "❌ <b>Session Tidak Valid</b>\n"
                           "━━━━━━━━━━━━━━━━━━━━\n\n"
                           "Format ci_session tidak sesuai.\n"
                           "Pastikan Anda meng-copy nilai cookie\n"
                           "yang benar dari browser.\n\n"
                           "Coba lagi dengan /session")
                    send_telegram_message(msg, reply_markup=main_keyboard)
                    continue
                
                # Update .env
                if _update_env_session(new_session):
                    msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                           "✅ <b>Session Diperbarui!</b>\n"
                           "━━━━━━━━━━━━━━━━━━━━\n\n"
                           f"Cookie baru: <code>{new_session[:8]}...{new_session[-4:]}</code>\n\n"
                           "Bot akan restart otomatis dengan\n"
                           "session yang baru. Tunggu sebentar ya...")
                    send_telegram_message(msg, reply_markup=main_keyboard)
                    time.sleep(1)
                    
                    # Beri tahu Telegram bahwa pesan sudah diproses agar tidak dikirim ulang saat restart
                    get_telegram_updates(offset)
                    
                    # Restart bot dengan session baru (kirim argumen penanda)
                    python = sys.executable
                    script = os.path.join(SCRIPT_DIR, 'auto_apply.py')
                    os.execv(python, [python, script, '--restarted_session'])
                else:
                    msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                           "❌ <b>Gagal Update</b>\n"
                           "━━━━━━━━━━━━━━━━━━━━\n\n"
                           "Tidak bisa menulis ke file .env.\n"
                           "Coba update secara manual.")
                    send_telegram_message(msg, reply_markup=main_keyboard)
                continue
                
            if text == "/help":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "📖 <b>Daftar Perintah</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "📊 /status — Cek kondisi bot\n"
                       "📋 /log — Lihat laporan matang terakhir\n"
                       "⚡ /cek — Paksa bot melamar sekarang\n"
                       "🔑 /session — Ganti cookie ci_session\n"
                       "🔄 /update — Tarik pembaruan GitHub\n"
                       "🗑️ /reset_memori — Hapus ingatan lowongan\n"
                       "⏸ /stop — Jeda pencarian\n"
                       "▶️ /start — Lanjut pencarian\n"
                       "🔁 /restart — Restart bot\n\n"
                       "<i>Gunakan menu atau ketik langsung.</i>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/status":
                uptime = _get_bot_uptime()
                is_paused = os.path.exists("stop.flag")
                status_emoji = "⏸" if is_paused else "🟢"
                status_text = "Dijeda (ketik /start)" if is_paused else "Aktif & Memantau"
                
                # Hitung jumlah lowongan yang sudah diproses
                try:
                    import json
                    with open(os.path.join(SCRIPT_DIR, 'applied_jobs.json'), 'r') as f:
                        total_tracked = len(json.load(f))
                except:
                    total_tracked = 0
                
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       f"{status_emoji} <b>Status Bot</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"<b>Kondisi:</b> {status_text}\n"
                       f"<b>Sudah jalan:</b> {uptime}\n"
                       f"<b>Lowongan dipantau:</b> {total_tracked}\n\n"
                       "<i>Bot mengecek lowongan baru\n"
                       "setiap 5 menit secara otomatis.</i>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                    
            elif text == "/log":
                try:
                    if os.path.exists(LOG_FILE):
                        with open(LOG_FILE, 'r') as f:
                            lines = f.readlines()
                        
                        # Ambil maksimal 500 baris terakhir untuk mencari siklus terakhir
                        last_lines = lines[-500:] if len(lines) > 500 else lines
                        human_log = _format_log_human(last_lines)
                        
                        if len(human_log) > 3500:
                            human_log = human_log[-3500:]
                        
                        msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                               "📋 <b>LAPORAN TERAKHIR</b>\n"
                               "━━━━━━━━━━━━━━━━━━━━\n\n"
                               f"{human_log}")
                        send_telegram_message(msg, reply_markup=main_keyboard)
                    else:
                        msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                               "📋 <b>Aktivitas</b>\n"
                               "━━━━━━━━━━━━━━━━━━━━\n\n"
                               "Belum ada file log.\n"
                               "Bot mungkin baru saja dijalankan.")
                        send_telegram_message(msg, reply_markup=main_keyboard)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal membaca log: {e}", reply_markup=main_keyboard)
                    
            elif text == "/cek":
                if os.path.exists("stop.flag"):
                    send_telegram_message("❌ <b>Bot sedang dijeda.</b>\nKetik /start dulu untuk mengaktifkan bot.", reply_markup=main_keyboard)
                else:
                    with open("force_check.flag", "w") as f:
                        f.write("1")
                    send_telegram_message("⚡ <b>Perintah Diterima!</b>\n\nBot akan segera mengabaikan waktu istirahat dan mengecek lowongan baru sekarang juga.", reply_markup=main_keyboard)
                    
            elif text == "/reset_memori":
                msg = ("⚠️ <b>PERINGATAN!</b> ⚠️\n\n"
                       "Anda akan menghapus seluruh ingatan bot tentang lowongan yang sudah pernah dicek/dilamar.\n\n"
                       "Jika dihapus, bot akan menganggap <b>semua lowongan di web saat ini adalah lowongan lama</b>, dan dia akan mulai mencari lowongan baru dari nol.\n\n"
                       "Apakah Anda yakin? Jika ya, ketik (atau salin teks ini):\n"
                       "<code>/KONFIRMASI_RESET</code>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/KONFIRMASI_RESET":
                applied_file = os.path.join(SCRIPT_DIR, 'applied_jobs.json')
                try:
                    with open(applied_file, 'w') as f:
                        f.write("[]")
                    send_telegram_message("✅ <b>Memori Berhasil Dihapus!</b>\n\nDatabase ingatan bot kini kosong (0 lowongan). Bot akan menganggap semua data di web saat ini sebagai data lawas.", reply_markup=main_keyboard)
                except Exception as e:
                    send_telegram_message(f"❌ Gagal mereset memori: {e}", reply_markup=main_keyboard)
                    
            elif text == "/session":
                _waiting_session[chat_id_from] = True
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "🔑 <b>Ganti Session</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Kirimkan cookie <code>ci_session</code> yang baru.\n\n"
                       "<b>Cara mendapatkan:</b>\n"
                       "1. Login di browser\n"
                       "2. Tekan F12 → Application → Cookies\n"
                       "3. Copy nilai <code>ci_session</code>\n"
                       "4. Paste & kirim di sini\n\n"
                       "<i>⏳ Menunggu input Anda...</i>")
                send_telegram_message(msg, reply_markup=main_keyboard)
                    
            elif text == "/stop":
                if not os.path.exists("stop.flag"):
                    open("stop.flag", "w").close()
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "⏸ <b>Bot Dijeda</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Pencarian lowongan dihentikan sementara.\n"
                       "Ketik /start untuk melanjutkan.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/start":
                if os.path.exists("stop.flag"):
                    os.remove("stop.flag")
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "▶️ <b>Bot Dilanjutkan</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Kembali berburu lowongan pekerjaan baru! 🎯")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
            elif text == "/restart":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "🔁 <b>Restart Bot</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Bot sedang di-restart...\n"
                       "Tunggu beberapa detik ya.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                time.sleep(1)
                
                # Beri tahu Telegram bahwa pesan sudah diproses
                get_telegram_updates(offset)
                
                # Restart dengan os.execv (kirim argumen penanda)
                python = sys.executable
                script = os.path.join(SCRIPT_DIR, 'auto_apply.py')
                os.execv(python, [python, script, '--restarted_manual'])
                
            elif text == "/update":
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "🔄 <b>Update Kode</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Sedang menarik update dari GitHub...")
                send_telegram_message(msg)
                try:
                    # 1. Paksa update dengan hard reset agar semua file lokal hancur & ikut GitHub 100%
                    subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, cwd=SCRIPT_DIR)
                    result = subprocess.run(["git", "reset", "--hard", "origin/main"], capture_output=True, text=True, stderr=subprocess.STDOUT, cwd=SCRIPT_DIR)
                    out = result.stdout.strip()
                    
                    if "is up to date" in out or "Already up to date" in out or "up-to-date" in out or result.returncode == 0:
                        # Cek apakah file auto_apply.py dan telegram_notifier.py valid sintaksnya
                        check_syntax_auto = subprocess.run([sys.executable, "-m", "py_compile", "auto_apply.py"], cwd=SCRIPT_DIR, capture_output=True)
                        check_syntax_tele = subprocess.run([sys.executable, "-m", "py_compile", "telegram_notifier.py"], cwd=SCRIPT_DIR, capture_output=True)
                        
                        if check_syntax_auto.returncode != 0 or check_syntax_tele.returncode != 0:
                            # Batalkan update jika error sintaks!
                            subprocess.run(["git", "reset", "--hard", "HEAD@{1}"], cwd=SCRIPT_DIR)
                            msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                                   "❌ <b>Update Dibatalkan!</b>\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Kode di GitHub mengandung Error/Cacat.\n"
                                   "Demi keselamatan, bot otomatis\n"
                                   "kembali menggunakan kode lama\n"
                                   "dan menolak untuk restart.")
                            send_telegram_message(msg, reply_markup=main_keyboard)
                        else:
                            msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                                   "✅ <b>Kode Diperbarui!</b>\n"
                                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                                   "Kode berhasil ditarik paksa dari GitHub.\n"
                                   "Bot akan restart sekarang. Jika sukses,\n"
                                   "Anda akan menerima pesan notifikasi lagi.")
                            send_telegram_message(msg, reply_markup=main_keyboard)
                            time.sleep(1)
                            
                            # Beri tahu Telegram bahwa pesan sudah diproses
                            get_telegram_updates(offset)
                            
                            python = sys.executable
                            script = os.path.join(SCRIPT_DIR, 'auto_apply.py')
                            os.execv(python, [python, script, '--restarted_update'])
                    else:
                        msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                               "❌ <b>Git Error!</b>\n"
                               "━━━━━━━━━━━━━━━━━━━━\n\n"
                               f"<pre>{out[:500]}</pre>")
                        send_telegram_message(msg, reply_markup=main_keyboard)
                        
                except Exception as e:
                    send_telegram_message(f"❌ Gagal update: {e}", reply_markup=main_keyboard)
            else:
                msg = ("Perintah tidak dikenali 🤔\n\n"
                       "Ketik /help untuk melihat daftar perintah,\n"
                       "atau gunakan tombol di bawah.")
                send_telegram_message(msg, reply_markup=main_keyboard)
                
        time.sleep(1)
