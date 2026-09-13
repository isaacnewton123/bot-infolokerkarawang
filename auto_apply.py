import requests
from bs4 import BeautifulSoup
import re
import time
import os
import sys
import json
import logging
import threading
from dotenv import load_dotenv
from telegram_notifier import send_telegram_message, start_command_listener

# Muat variabel dari .env
load_dotenv()

# ================= Kofigurasi ================= #
COOKIE = {'ci_session': os.getenv('CI_SESSION')}
BASE_URL = 'https://infoloker.karawangkab.go.id'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
APPLIED_JOBS_FILE = 'applied_jobs.json'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, 'bot.log')

# Daftar endpoint DataTables server-side yang akan di-scrape
# Hanya Lowongan Umum dan Magang (sesuai permintaan user)
JOB_ENDPOINTS = [
    {
        'name': 'Lowongan Umum',
        'endpoint': '/Dashboard_pelamar/data_list_lowongan',
        'emoji': '💼'
    },
    {
        'name': 'Magang',
        'endpoint': '/Dashboard_pelamar/data_list_magang',
        'emoji': '🎓'
    },
]
# ============================================== #

# =============== Setup Logging ================ #
# Dual output: console + file (agar /log bisa baca dari file)
def setup_logging():
    """Setup logging ke console dan file sekaligus."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler (untuk /log command di Telegram)
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

log = setup_logging()
# ============================================== #

def load_applied_jobs():
    if os.path.exists(APPLIED_JOBS_FILE):
        try:
            with open(APPLIED_JOBS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_applied_job(job_id):
    jobs = load_applied_jobs()
    if job_id not in jobs:
        jobs.append(job_id)
        with open(APPLIED_JOBS_FILE, 'w') as f:
            json.dump(jobs, f)

def get_csrf_token(http_session):
    """
    Buka dashboard untuk ambil CSRF token.
    Return (csrf_token, error_msg) — error_msg None jika sukses.
    """
    try:
        req_dash = http_session.get(f"{BASE_URL}/Dashboard_pelamar", allow_redirects=True, timeout=30)
        
        # Cek status HTTP untuk deteksi web down
        if req_dash.status_code != 200:
            return None, f"Web sepertinya down (Status code: {req_dash.status_code})"
            
        # Cek error database atau maintenance dari konten HTML
        error_keywords = ['a database error occurred', '502 bad gateway', '504 gateway time-out', '503 service temporarily unavailable', 'under maintenance']
        text_lower = req_dash.text.lower()
        if any(keyword in text_lower for keyword in error_keywords) or len(req_dash.text.strip()) < 500:
            return None, "Halaman terindikasi sedang down atau maintenance"
            
        # Cek apakah kita dilempar ke halaman login (artinya session expired)
        if 'login' in req_dash.url.lower():
            if not os.path.exists("session_expired.flag"):
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "❌ <b>Session Expired</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "ci_session sudah kedaluwarsa.\n\n"
                       "<b>Langkah:</b>\n"
                       "1. Login manual di website\n"
                       "2. Ambil <code>ci_session</code> baru\n"
                       "3. Update file <code>.env</code>\n"
                       "4. Restart bot")
                send_telegram_message(msg)
                open("session_expired.flag", "w").close()
            return None, "SESSION_EXPIRED"
            
        soup = BeautifulSoup(req_dash.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'ini_csrf'})
        if not csrf_input:
            if not os.path.exists("session_expired.flag"):
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "❌ <b>Session Expired</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       "Gagal mengambil CSRF token.\n"
                       "ci_session sepertinya sudah kedaluwarsa.\n\n"
                       "Silakan perbarui cookie di <code>.env</code>.")
                send_telegram_message(msg)
                open("session_expired.flag", "w").close()
            return None, "SESSION_EXPIRED"
            
        # Jika berhasil masuk dashboard, hapus flag error
        if os.path.exists("session_expired.flag"):
            os.remove("session_expired.flag")
            
        return csrf_input['value'], None
        
    except Exception as e:
        return None, f"Error koneksi saat membuka dashboard: {e}"

def fetch_jobs_from_datatables(http_session, endpoint_url, csrf_token):
    """
    Ambil data lowongan dari endpoint DataTables server-side.
    Website InfoLoker Karawang telah diupdate — data sekarang di-load via
    DataTables server-side processing, bukan lagi dari endpoint lowongan_new.
    
    Return list of (job_id, job_title, company_name)
    """
    headers_ajax = HEADERS.copy()
    headers_ajax['X-Requested-With'] = 'XMLHttpRequest'
    
    payload = {
        'draw': '1',
        'start': '0',
        'length': '200',  # Ambil banyak sekaligus
        'ini_csrf': csrf_token
    }
    
    try:
        req = http_session.post(f"{BASE_URL}{endpoint_url}", data=payload, headers=headers_ajax, timeout=30)
        
        # Parse JSON response dari DataTables
        try:
            json_data = req.json()
        except:
            log.info(f"    [x] Response bukan JSON valid dari {endpoint_url}")
            return []
        
        data_rows = json_data.get('data', [])
        jobs = []
        
        for row in data_rows:
            # Setiap row adalah array dengan 1 elemen berisi HTML
            html_content = row[0] if isinstance(row, list) and len(row) > 0 else str(row)
            
            # Ekstrak Job ID dari URL: Lowongan_draft/detail_lowongan/{job_id}
            id_match = re.search(r'Lowongan_draft/detail_lowongan/([^"\'&\s]+)', html_content)
            if not id_match:
                # Fallback: coba format lama detail_lowongan/{id}
                id_match = re.search(r'detail_lowongan/([^"\'&\s]+)', html_content)
            
            if not id_match:
                continue
                
            job_id = id_match.group(1)
            
            # Ekstrak judul dari <h4 class="text-primary">JUDUL</h4>
            title_match = re.search(r'<h4[^>]*class=["\']text-primary["\'][^>]*>(.*?)</h4>', html_content, re.DOTALL)
            job_title = title_match.group(1).strip() if title_match else "Tanpa Judul"
            
            # Ekstrak nama perusahaan dari <p class="text-dark"> pertama setelah h4
            company_match = re.search(r'</h4>\s*(?:\\n\s*)*<p[^>]*class=["\']text-dark["\'][^>]*>(.*?)</p>', html_content, re.DOTALL)
            company = company_match.group(1).strip() if company_match else ""
            
            jobs.append((job_id, job_title, company))
        
        return jobs
        
    except Exception as e:
        log.info(f"    [x] Error saat query {endpoint_url}: {e}")
        return []

def run_bot(http_session):
    log.info("Memulai pengecekan lowongan...")
    applied_list = load_applied_jobs()
    
    # 1. Ambil CSRF token dari dashboard
    csrf_token, error = get_csrf_token(http_session)
    
    if error:
        if error == "SESSION_EXPIRED":
            log.info("[x] Bot dilempar ke halaman Login. Session kedaluwarsa!")
            time.sleep(10)
            return False  # Hentikan loop
        else:
            log.info(f"[x] {error}. Akan mencoba lagi nanti.")
            return True  # Coba lagi nanti
    
    # 2. Scrape semua kategori lowongan dari endpoint DataTables baru
    all_jobs = []  # List of (job_id, job_title, company, category_name, category_emoji)
    
    for ep in JOB_ENDPOINTS:
        log.info(f"Mengambil data {ep['name']}...")
        jobs = fetch_jobs_from_datatables(http_session, ep['endpoint'], csrf_token)
        log.info(f"  → {len(jobs)} lowongan ditemukan")
        
        for job_id, job_title, company in jobs:
            all_jobs.append((job_id, job_title, company, ep['name'], ep['emoji']))
    
    total = len(all_jobs)
    log.info(f"Total: {total} lowongan dari semua kategori.")
    
    if total == 0:
        log.info("Tidak ada lowongan di halaman.")
        return True

    # 3. Jika applied_jobs masih kosong (bot baru pertama kali dijalankan),
    # simpan semua lowongan saat ini sebagai "Lowongan Lama" tanpa di-apply.
    # Bot hanya akan apply lowongan yang BENAR-BENAR BARU muncul setelahnya.
    if len(applied_list) == 0:
        log.info("Inisialisasi awal — menyimpan semua lowongan saat ini sebagai 'Lowongan Lama'...")
        for job_id, _, _, _, _ in all_jobs:
            save_applied_job(job_id)
        log.info(f"  → {total} lowongan lama disimpan. Bot sekarang hanya menunggu lowongan baru.")
        
        msg = ("━━━━━━━━━━━━━━━━━━━━\n"
               "📊 <b>Inisialisasi Selesai</b>\n"
               "━━━━━━━━━━━━━━━━━━━━\n\n"
               f"Ditemukan <b>{total}</b> lowongan yang sudah ada.\n"
               "Semua ditandai sebagai <i>lowongan lama</i>.\n\n"
               "✅ Bot sekarang siap mendeteksi dan\n"
               "melamar lowongan <b>baru</b> secara otomatis!")
        send_telegram_message(msg)
        return True

    # 4. Filter & Apply hanya untuk lowongan baru
    new_count = 0
    success_count = 0
    fail_count = 0
    
    for job_id, job_title, company, category, emoji in all_jobs:
        if job_id in applied_list:
            # Lowongan sudah ada di database, lewati
            continue
            
        new_count += 1
        company_info = f" — {company}" if company else ""
        log.info(f"LOWONGAN BARU [{category}]: {job_title}{company_info}")
        log.info(f"  → Melamar...")
        apply_url = f"{BASE_URL}/apply/{job_id}"
        
        try:
            req_apply = http_session.get(apply_url, allow_redirects=True, timeout=30)
            
            # Cari pesan SweetAlert dari flashdata
            flash_messages = re.findall(r'Swal\.fire\("([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\)', req_apply.text)
            
            is_success = False
            error_reason = ""
            
            for judul, pesan, tipe in flash_messages:
                if 'Gagal mengupload file' in pesan: # Abaikan script hardcoded di halaman
                    continue
                if tipe == 'success':
                    is_success = True
                elif tipe in ['warning', 'error']:
                    error_reason = f"{judul} - {pesan}"
                    break # Ambil error pertama yang relevan
            
            if is_success or req_apply.url.endswith('/History_lamaran'):
                success_count += 1
                log.info(f"  ✅ Berhasil melamar: {job_title}")
                save_applied_job(job_id)
                
                # Kirim notifikasi Telegram
                company_line = f"\n🏢 <b>Perusahaan:</b> {company}" if company else ""
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "✅ <b>Berhasil Melamar!</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"{emoji} <b>Kategori:</b> {category}\n"
                       f"📌 <b>Posisi:</b> {job_title}"
                       f"{company_line}\n\n"
                       "Semoga lekas dipanggil wawancara! 🙏")
                send_telegram_message(msg)
                
            elif error_reason:
                fail_count += 1
                log.info(f"  ❌ Gagal: {error_reason}")
                # Tetap save ke applied_jobs agar tidak di-loop terus menerus
                save_applied_job(job_id)
                
                # Kirim notifikasi gagal ke Telegram
                company_line = f"\n🏢 <b>Perusahaan:</b> {company}" if company else ""
                msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                       "❌ <b>Gagal Melamar</b>\n"
                       "━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"{emoji} <b>Kategori:</b> {category}\n"
                       f"📌 <b>Posisi:</b> {job_title}"
                       f"{company_line}\n"
                       f"⚠️ <b>Alasan:</b> {error_reason}")
                send_telegram_message(msg)
                
            else:
                fail_count += 1
                log.info(f"  ❌ Gagal tanpa pesan jelas (HTTP {req_apply.status_code})")
                # Save saja supaya tidak ngeloop terus menerus
                save_applied_job(job_id)
                
            # Jeda agar tidak dianggap spam / ddos
            time.sleep(3)
            
        except Exception as e:
            fail_count += 1
            log.info(f"  ❌ Error: {e}")
            msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                   "⚠️ <b>Error Sistem</b>\n"
                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                   f"Gagal melamar: <b>{job_title}</b>\n"
                   f"Error: <code>{e}</code>")
            send_telegram_message(msg)
    
    if new_count == 0:
        log.info("Tidak ada lowongan baru.")
    else:
        log.info(f"Selesai — {new_count} lowongan baru diproses ({success_count} berhasil, {fail_count} gagal)")
            
    return True

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("BOT AUTO-APPLY INFOLOKER KARAWANG")
    log.info("Platform: Termux | Kategori: Umum + Magang")
    log.info("=" * 50)
    
    startup_msg = ("━━━━━━━━━━━━━━━━━━━━\n"
                   "🤖 <b>Bot Aktif!</b>\n"
                   "━━━━━━━━━━━━━━━━━━━━\n\n"
                   "Bot Auto-Apply InfoLoker Karawang\n"
                   "sedang berjalan dan siap memantau\n"
                   "lowongan pekerjaan baru.\n\n"
                   "<b>Kategori yang dipantau:</b>\n"
                   "• 💼 Lowongan Umum\n"
                   "• 🎓 Magang\n\n"
                   "<b>Platform:</b> Termux\n"
                   "<b>Interval:</b> Setiap 5 menit\n\n"
                   "<i>Ketik /help untuk daftar perintah.</i>")
    send_telegram_message(startup_msg)
    
    INTERVAL_MENIT = 5
    
    # Inisialisasi HTTP Session secara global
    # Ini sangat penting agar jika server CodeIgniter me-regenerate (memperbarui) ID ci_session, 
    # bot otomatis menyimpan dan menggunakan cookie yang baru.
    global_session = requests.Session()
    global_session.headers.update(HEADERS)
    # Set cookie secara eksplisit dengan domain agar tidak bentrok dengan cookie baru dari server
    global_session.cookies.set('ci_session', COOKIE['ci_session'], domain='infoloker.karawangkab.go.id')
    
    # Jalankan Telegram Listener di background
    threading.Thread(target=start_command_listener, daemon=True).start()
    
    while True:
        if os.path.exists("stop.flag"):
            # Jika ada perintah /stop dari telegram, bot akan idle/tidur
            time.sleep(10)
            continue
            
        status_ok = run_bot(global_session)
        if not status_ok:
            log.info("Bot dihentikan karena session expired atau error kritikal.")
            break
            
        log.info(f"Menunggu {INTERVAL_MENIT} menit sebelum cek lagi...")
        time.sleep(INTERVAL_MENIT * 60)
