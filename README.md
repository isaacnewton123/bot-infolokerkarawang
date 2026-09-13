# 🤖 Bot Auto-Apply InfoLoker Karawang

Bot Python yang berjalan otomatis di latar belakang untuk memantau dan melamar lowongan pekerjaan terbaru di situs [InfoLoker Karawang](https://infoloker.karawangkab.go.id). Dilengkapi notifikasi Telegram real-time dan bisa dikontrol langsung dari HP.

---

## ✨ Fitur

| Fitur | Keterangan |
|-------|------------|
| 🚀 **Auto Apply** | Otomatis mendeteksi dan melamar lowongan baru |
| 📋 **Multi Kategori** | Memantau Lowongan Umum + Magang sekaligus |
| 🧠 **Smart Filter** | Mengingat lowongan yang sudah dilamar, tidak ada duplikat |
| 📱 **Kontrol Telegram** | Start, stop, cek status, lihat log — semua dari HP |
| 🔔 **Notifikasi Real-time** | Dapat notif langsung tiap kali lamaran berhasil/gagal |
| 🔐 **Deteksi Session** | Otomatis berhenti & kirim notif jika session expired |

---

## 📱 Perintah Telegram

Setelah bot aktif, Anda bisa mengontrolnya via chat Telegram:

| Perintah | Fungsi |
|----------|--------|
| `/status` | 📊 Cek kondisi bot (uptime, PID, dll) |
| `/log` | 📋 Lihat log aktivitas terbaru |
| `/stop` | ⏸ Jeda pencarian lowongan |
| `/start` | ▶️ Lanjutkan pencarian |
| `/update` | 🔄 Tarik update kode dari GitHub |
| `/restart` | 🔁 Restart bot |
| `/help` | 📖 Tampilkan daftar perintah |

---

## 🛠️ Prasyarat

Sebelum mulai, siapkan:

1. **Akun InfoLoker Karawang** — Sudah terdaftar & login di [infoloker.karawangkab.go.id](https://infoloker.karawangkab.go.id)
2. **Cookie `ci_session`** — Didapat setelah login (lihat [cara ambil ci_session](#-cara-mengambil-ci_session))
3. **Bot Telegram** — Buat via [@BotFather](https://t.me/BotFather), catat Token-nya
4. **Chat ID Telegram** — Dapatkan via [@userinfobot](https://t.me/userinfobot)

---

## 📲 Instalasi di Termux (Android)

### 1. Install Dependencies

```bash
# Update & install Python
pkg update && pkg upgrade -y
pkg install python git -y

# Clone repositori
git clone https://github.com/USERNAME/bot-infolokerkarawang.git
cd bot-infolokerkarawang

# Buat virtual environment
python -m venv .venv
source .venv/bin/activate

# Install library Python
pip install -r requirements.txt
```

### 2. Konfigurasi

Buat file `.env` di dalam folder proyek:

```bash
cat > .env << 'EOF'
CI_SESSION=ISI_COOKIE_CI_SESSION_ANDA
TELEGRAM_BOT_TOKEN=ISI_TOKEN_BOT_TELEGRAM
TELEGRAM_CHAT_ID=ISI_CHAT_ID_ANDA
EOF
```

> ⚠️ Ganti value di atas dengan data milik Anda.

### 3. Jalankan Bot

```bash
# Aktifkan virtual environment (jika belum)
source .venv/bin/activate

# Jalankan langsung
python auto_apply.py

# ATAU jalankan di background (tetap jalan walau Termux ditutup)
nohup python auto_apply.py > /dev/null 2>&1 &
```

### 4. Tips Termux

| Tips | Perintah |
|------|----------|
| Agar Termux tidak di-kill Android | Buka Pengaturan HP → Baterai → Nonaktifkan optimasi baterai untuk Termux |
| Tetap jalan saat layar mati | `pkg install termux-api && termux-wake-lock` |
| Cek bot masih jalan | `ps aux \| grep auto_apply` |
| Matikan bot manual | `pkill -f auto_apply.py` |

---

## 🖥️ Instalasi di VPS / Linux Server

### 1. Setup Awal

```bash
# Update sistem & install Python
sudo apt update && sudo apt install -y python3 python3-venv git

# Clone repositori
git clone https://github.com/USERNAME/bot-infolokerkarawang.git
cd bot-infolokerkarawang

# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install library Python
pip install -r requirements.txt
```

### 2. Konfigurasi

```bash
nano .env
```

Isi:
```
CI_SESSION=ISI_COOKIE_CI_SESSION_ANDA
TELEGRAM_BOT_TOKEN=ISI_TOKEN_BOT_TELEGRAM
TELEGRAM_CHAT_ID=ISI_CHAT_ID_ANDA
```

### 3. Jalankan dengan Screen

```bash
# Install screen
sudo apt install screen -y

# Buat session baru
screen -S infoloker

# Aktifkan venv & jalankan bot
source .venv/bin/activate
python3 auto_apply.py

# Lepas session: tekan Ctrl+A lalu D
# Kembali ke session: screen -r infoloker
```

### 4. Jalankan dengan nohup (Alternatif)

```bash
source .venv/bin/activate
nohup python3 auto_apply.py > /dev/null 2>&1 &
```

---

## 🪟 Instalasi di Windows

### 1. Install Python

- Download & install [Python](https://www.python.org/downloads/) (centang **"Add to PATH"**)

### 2. Setup Proyek

```powershell
# Clone repositori
git clone https://github.com/USERNAME/bot-infolokerkarawang.git
cd bot-infolokerkarawang

# Buat virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install library
pip install -r requirements.txt
```

### 3. Konfigurasi

Buat file `.env` di folder proyek, isi:

```
CI_SESSION=ISI_COOKIE_CI_SESSION_ANDA
TELEGRAM_BOT_TOKEN=ISI_TOKEN_BOT_TELEGRAM
TELEGRAM_CHAT_ID=ISI_CHAT_ID_ANDA
```

### 4. Jalankan

```powershell
python auto_apply.py
```

---

## 🔑 Cara Mengambil ci_session

1. Buka browser, login ke [infoloker.karawangkab.go.id](https://infoloker.karawangkab.go.id)
2. Tekan `F12` atau klik kanan → **Inspect**
3. Buka tab **Application** (Chrome) atau **Storage** (Firefox)
4. Di sidebar kiri, klik **Cookies** → pilih domain `infoloker.karawangkab.go.id`
5. Cari cookie bernama `ci_session`
6. Copy value-nya dan paste ke file `.env`

> ⚠️ Cookie `ci_session` bisa expired kapan saja. Jika bot mengirim notifikasi "Session Expired", ulangi langkah di atas dan update file `.env`, lalu restart bot.

---

## ⚙️ Cara Kerja Bot

```
Bot Aktif
  │
  ├─ Pertama kali jalan?
  │   └─ Ya → Simpan semua lowongan saat ini sebagai "Lowongan Lama"
  │          (Tidak di-apply, hanya lowongan baru setelahnya yang di-apply)
  │
  ├─ Setiap 5 menit:
  │   ├─ Buka Dashboard → Ambil CSRF token
  │   ├─ Query endpoint DataTables: Lowongan Umum + Magang
  │   ├─ Filter lowongan baru (belum pernah terdeteksi)
  │   ├─ Apply otomatis satu per satu
  │   └─ Kirim notifikasi ke Telegram (berhasil/gagal)
  │
  └─ Jika session expired → Kirim notif & berhenti
```

---

## 📁 Struktur File

```
bot-infolokerkarawang/
├── auto_apply.py          # Script utama bot
├── telegram_notifier.py   # Modul notifikasi & kontrol Telegram
├── requirements.txt       # Daftar library Python
├── .env                   # Konfigurasi (RAHASIA - jangan di-push!)
├── .gitignore             # Daftar file yang tidak di-track Git
├── applied_jobs.json      # Database lowongan yang sudah dilamar (auto)
├── bot.log                # Log aktivitas bot (auto)
└── README.md              # Dokumentasi ini
```

---

## 🔄 Update Bot

**Via Telegram:**
```
/update
```

**Via Terminal:**
```bash
cd bot-infolokerkarawang
git pull
# Restart bot
```

---

## ❓ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Bot bilang "Session Expired" | Login ulang di browser, ambil `ci_session` baru, update `.env`, restart bot |
| Lamaran gagal "Persyaratan Belum Lengkap" | Lengkapi berkas di menu **Profil → Berkas** di website InfoLoker |
| Lamaran gagal "Pendidikan tidak memenuhi" | Normal — lowongan tersebut tidak sesuai kualifikasi Anda |
| Bot tidak melamar apapun | Belum ada lowongan **baru**. Bot hanya apply yang muncul setelah pertama kali dijalankan |
| Termux di-kill Android | Nonaktifkan optimasi baterai untuk Termux & gunakan `termux-wake-lock` |
| `ModuleNotFoundError` | Pastikan virtual environment aktif: `source .venv/bin/activate` |

---

## 📝 Lisensi

Proyek ini dibuat untuk keperluan pribadi. Gunakan dengan bijak dan bertanggung jawab.
