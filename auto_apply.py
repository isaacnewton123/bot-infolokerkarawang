import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
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

def run_bot(http_session):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Memulai pengecekan lowongan...")
    applied_list = load_applied_jobs()
    
    # 1. Buka dashboard untuk ambil CSRF
    try:
        req_dash = http_session.get(f"{BASE_URL}/Dashboard_pelamar", allow_redirects=True, timeout=30)
        
        # Cek status HTTP untuk deteksi web down
        if req_dash.status_code != 200:
            print(f"[x] Web sepertinya down (Status code: {req_dash.status_code}). Akan mencoba lagi nanti.")
            return True
            
        # Cek error database atau maintenance dari konten HTML
        error_keywords = ['a database error occurred', '502 bad gateway', '504 gateway time-out', '503 service temporarily unavailable', 'under maintenance']
        text_lower = req_dash.text.lower()
        if any(keyword in text_lower for keyword in error_keywords) or len(req_dash.text.strip()) < 500:
            print("[x] Halaman terindikasi sedang down atau maintenance. Menunggu...")
            return True
            
        # Cek apakah kita dilempar ke halaman login (artinya session expired)
        if 'login' in req_dash.url.lower():
            print("[x] Bot dilempar ke halaman Login. Session kedaluwarsa!")
            if not os.path.exists("session_expired.flag"):
                send_telegram_message("❌ <b>Bot Terhenti (Session Expired)</b>\n\nci_session Anda sudah kedaluwarsa karena bot dialihkan ke halaman Login. Silakan login manual, ambil `ci_session` baru, lalu perbarui di script.")
                open("session_expired.flag", "w").close()
            time.sleep(10) # Tunda sedikit agar jika menggunakan PM2/auto-restart tidak ngeloop terlalu cepat
            return False # Hentikan loop
            
        soup = BeautifulSoup(req_dash.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'ini_csrf'})
        if not csrf_input:
            print("[x] Gagal mengambil CSRF Token. Session mungkin kedaluwarsa.")
            if not os.path.exists("session_expired.flag"):
                send_telegram_message("❌ <b>Bot Gagal Berjalan (Session Expired)</b>\n\nci_session Anda sepertinya sudah kedaluwarsa. Silakan perbarui cookie di script `auto_apply.py`.")
                open("session_expired.flag", "w").close()
            time.sleep(10) # Tunda sedikit agar PM2 tidak spam
            return False # Return false untuk menghentikan loop
            
        csrf_token = csrf_input['value']
        
        # Jika berhasil masuk dashboard, hapus flag error agar notif berfungsi normal lagi nantinya
        if os.path.exists("session_expired.flag"):
            os.remove("session_expired.flag")
    except Exception as e:
        print(f"[x] Error koneksi saat membuka dashboard: {e}")
        # Tidak mengirim notif telegram agar tidak spam saat server sedang down / gangguan jaringan
        return True # Return true agar tetap mencoba lagi di interval berikutnya
        
    # 2. Ambil data lowongan dari DataTables
    payload = {
        'draw': '1',
        'start': '0',
        'length': '100',
        'ini_csrf': csrf_token
    }
    
    headers_ajax = HEADERS.copy()
    headers_ajax['X-Requested-With'] = 'XMLHttpRequest'
    
    try:
        req_jobs = http_session.post(f"{BASE_URL}/Dashboard_pelamar/lowongan_new", data=payload, headers=headers_ajax)
        
        # Ekstrak ID dan Judul dari elemen HTML pada respons DataTables
        links = re.findall(r'<a target="_blank" href="[^"]*?detail_lowongan/([^"]+)">(.*?)</a>', req_jobs.text, re.DOTALL)
        
        new_jobs = []
        for job_id, inner_html in links:
            m_title = re.search(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', inner_html)
            title = m_title.group(1).strip() if m_title else "Tanpa Judul"
            new_jobs.append((job_id, title))
        
        print(f"[*] Ditemukan {len(new_jobs)} lowongan di halaman.")
    except Exception as e:
        print(f"[x] Error saat menarik lowongan: {e}")
        # Tidak mengirim notif telegram agar tidak spam
        return True
    
    if len(new_jobs) == 0:
        print("[-] Tidak ada lowongan di halaman.")
        return True

    # Jika list applied_jobs masih kosong (bot baru pertama kali dijalankan), 
    # kita anggap lowongan yang ada saat ini sebagai "Lowongan Lama" dan langsung kita simpan tanpa dilamar.
    if len(applied_list) == 0:
        print("[*] Inisialisasi awal. Memasukkan semua lowongan saat ini ke daftar abaikan (Lowongan Lama)...")
        for job_id, _ in new_jobs:
            save_applied_job(job_id)
        print("[*] Selesai. Bot sekarang hanya akan menunggu lowongan yang benar-benar baru.")
        return True
        
    # 4. Filter & Apply hanya untuk lowongan baru
    for job_id, job_title in new_jobs:
        if job_id in applied_list:
            # Lowongan sudah ada di database, lewati secara diam-diam untuk mengurangi spam log
            continue
            
        print(f"\n[!] LOWONGAN BARU DITEMUKAN: {job_title}")
        print(f"[*] Melamar pekerjaan...")
        apply_url = f"{BASE_URL}/apply/{job_id}"
        
        try:
            req_apply = http_session.get(apply_url, allow_redirects=True)
            
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
                print(f"[+] Berhasil mengirim lamaran untuk '{job_title}'!")
                save_applied_job(job_id)
                
                # Kirim notifikasi Telegram
                msg = f"✅ <b>BERHASIL MELAMAR!</b>\n\n<b>Posisi:</b> {job_title}\n<b>ID:</b> <code>{job_id}</code>\n\nSemoga lekas dipanggil wawancara! 🙏"
                send_telegram_message(msg)
                
            elif error_reason:
                print(f"[x] Gagal apply: {error_reason} - {job_title}")
                # Tetap save ke applied_jobs agar tidak di-loop terus menerus (diabaikan ke depannya)
                save_applied_job(job_id)
                
                # Kirim notifikasi gagal ke Telegram
                msg = f"❌ <b>GAGAL MELAMAR</b>\n\n<b>Posisi:</b> {job_title}\n<b>Alasan:</b> {error_reason}\n\nSilakan lengkapi berkas di akun Anda."
                send_telegram_message(msg)
                
            else:
                print(f"[x] Gagal apply tanpa pesan jelas. Status Code: {req_apply.status_code}")
                # Save saja supaya tidak ngeloop terus menerus
                save_applied_job(job_id)
                
            # Jeda agar tidak dianggap spam / ddos
            time.sleep(3)
            
        except Exception as e:
            print(f"[x] Error saat apply: {e}")
            send_telegram_message(f"⚠️ <b>Peringatan:</b> Terjadi error sistem saat bot mencoba melamar pekerjaan {job_title}.\n\nError: {e}")
            
    return True

if __name__ == "__main__":
    print("====================================================")
    print("BOT AUTO-APPLY INFOLOKER KARAWANG SEDANG BERJALAN...")
    print("====================================================")
    send_telegram_message("🤖 <b>Bot Auto-Apply InfoLoker Karawang Aktif!</b>\n\nBot akan berjalan terus-menerus dan memantau lowongan pekerjaan baru. Anda akan mendapat notifikasi jika ada lamaran yang terkirim.")
    
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
            print("[!] Bot dihentikan karena session expired atau error kritikal.")
            break
            
        print(f"[*] Menunggu {INTERVAL_MENIT} menit sebelum mengecek lagi...")
        time.sleep(INTERVAL_MENIT * 60)
