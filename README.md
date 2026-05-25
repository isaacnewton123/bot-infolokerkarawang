# Bot Auto-Apply InfoLoker Karawang 🚀

Bot Python pintar yang dirancang untuk secara otomatis berjalan di latar belakang (daemon) dan melamar pekerjaan-pekerjaan terbaru di situs web InfoLoker Karawang. Bot ini memiliki deteksi *session expired* dan mengirimkan notifikasi *error* langsung ke Telegram Anda.

## Fitur Utama
- **Auto Apply**: Langsung mendeteksi dan melamar jika ada lowongan pekerjaan baru.
- **Smart Filter**: Mengingat ID loker yang sudah dilamar, jadi tidak akan ada pengajuan ganda (*duplicate apply*).
- **Notifikasi Telegram**: Jika sesi Anda mati (*logged out*) atau ada *error*, bot akan langsung berteriak di Telegram Anda.
- **Auto-Deploy**: Setiap kali Anda memperbarui kode di GitHub, kode akan langsung ditarik dan di-restart secara otomatis di VPS (CI/CD Pipeline).

---

## 🛠️ Cara Penggunaan & Pemasangan di VPS

Karena proyek ini menggunakan sistem CI/CD GitHub Actions, **Anda tidak perlu membuat file `.env` di server VPS secara manual**. Semuanya diatur langsung dari halaman rahasia (Secrets) GitHub Anda.

### Tahap 1: Konfigurasi Repositori GitHub
1. Pastikan seluruh kode ini sudah di-*push* ke repositori GitHub pribadi Anda.
2. Di repositori GitHub Anda, buka menu **Settings** -> **Secrets and variables** -> **Actions**.
3. Tambahkan 6 (Enam) *Repository Secrets* berikut ini dengan mengklik tombol **New repository secret**:
   - `HOST` : Alamat IP VPS Anda (misal: `168.110.205.216`)
   - `USERNAME` : Nama user VPS Anda (misal: `ubuntu`)
   - `SSH_PRIVATE_KEY` : Isi dengan semua teks dari file *private key* SSH Anda.
   - `CI_SESSION` : Nilai `ci_session` Anda yang valid saat ini (didapat setelah login di browser).
   - `TELEGRAM_BOT_TOKEN` : Token Bot Telegram Anda.
   - `TELEGRAM_CHAT_ID` : ID Chat Telegram Anda.

### Tahap 2: Menyiapkan "Lahan" di VPS (Hanya Dilakukan Sekali Saja)
Masuk ke VPS Anda melalui terminal (SSH), lalu jalankan perintah berurutan ini:

```bash
# 1. Unduh kode dari GitHub (Ganti URL dengan repositori Anda)
git clone https://github.com/USERNAME/bot-infolokerkarawang.git
cd bot-infolokerkarawang

# 2. Siapkan wadah virtual environment untuk Python
sudo apt update && sudo apt install -y python3-venv
python3 -m venv .venv

# 3. Daftarkan bot agar bisa nyala sendiri otomatis setiap VPS direstart
sudo cp bot-infoloker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bot-infoloker

# 4. Beri akses tanpa password ke GitHub Actions agar bisa merestart layanan
echo "ubuntu ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart bot-infoloker, /usr/bin/systemctl daemon-reload" | sudo tee /etc/sudoers.d/github-actions-bot
```

### Tahap 3: Peluncuran Roket (Trigger CI/CD)
Setelah konfigurasi Tahap 1 dan 2 selesai, Anda tinggal melakukan salah satu dari ini:
- Perbarui sedikit file apa saja, lalu lakukan `git push`, **ATAU**
- Buka menu **Actions** di GitHub, pilih *Deploy Bot to VPS*, lalu klik *Run workflow*.

GitHub Actions akan secara otomatis masuk ke VPS Anda, menarik kode terbaru, **menyusun ulang file `.env` di VPS Anda menggunakan Secrets**, dan menghidupkan bot-nya kembali!

---

## Bagaimana Jika Sesi Kedaluwarsa Lagi?
Jika Anda mendapatkan notifikasi Telegram bahwa bot mati karena *session expired*:
1. Buka browser dan login ke web InfoLoker.
2. Ambil `ci_session` yang baru.
3. Buka GitHub Anda -> **Settings** -> **Secrets and variables** -> **Actions**.
4. Edit bagian `CI_SESSION` dan ganti dengan kode yang baru.
5. Pergi ke tab **Actions**, lalu klik **Run workflow** lagi.
6. Selesai! Bot kembali berburu 24 jam. Anda tidak perlu menyentuh terminal VPS lagi!
