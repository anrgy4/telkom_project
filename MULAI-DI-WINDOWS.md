# Menjalankan Rantai di laptop Windows

## 1. Pasang kebutuhan sekali saja

- Pasang **Python 3.12** dari https://www.python.org/downloads/release/python-31210/. Saat instalasi, centang **Add python.exe to PATH**. Gunakan installer resmi yang sesuai arsitektur Windows Anda.
- Pasang **Ollama untuk Windows** dari https://ollama.com/download/windows, lalu buka aplikasinya. Ollama diperlukan untuk analisis AI; melihat contoh diagram tidak memerlukannya.

Gunakan koneksi internet saat pemasangan pertama. Siapkan beberapa GB ruang kosong untuk dependensi, browser Chromium dan model sekitar 2 GB. Model 3B berjalan di CPU; durasi analisis bergantung pada kemampuan laptop. RAM 8 GB atau lebih disarankan, dengan kapasitas tambahan membantu proses analisis panjang.

## 2. Ekstrak paket

Klik kanan `Rantai-Windows.zip` → **Extract All / Ekstrak Semua**. Buka folder `Rantai-Windows` hasil ekstraksi. Jangan menjalankan file langsung dari dalam ZIP.

## 3. Buka aplikasi

Klik dua kali **`1-JALANKAN-APLIKASI.bat`**.

Pertama kali, aplikasi memasang dependensi Python dan Chromium melalui internet. Tunggu sampai selesai. Browser kemudian terbuka otomatis. Biarkan jendela terminal tetap terbuka selama aplikasi digunakan. Tutup aplikasi dengan **Ctrl+C** pada jendela itu.

Tidak perlu mengetik perintah atau mengaktifkan virtual environment secara manual. Pada penggunaan berikutnya cukup klik file yang sama.

Jika browser tidak terbuka otomatis, buka Chrome/Edge dan ketik `localhost:8000` pada bilah alamat setelah terminal menampilkan “Aplikasi siap”.

## 4. Aktifkan AI sekali saja

Biarkan Ollama aktif. Klik dua kali **`2-SIAPKAN-AI-SEKALI.bat`** dan tunggu unduhan model `qwen2.5:3b` sekitar 2 GB selesai. File ini tidak mengunduh ulang jika model sudah tersedia.

Setelah selesai, kembali ke Rantai. Pilih **Panduan → Periksa kembali model**. Kemudian pilih perusahaan dan klik **Riset & buat analisis**.

## Mencocokkan produk Telkom Solution dan IndiBiz

Snapshot 72 produk/halaman solusi resmi sudah disertakan dalam paket, sehingga tidak perlu mengisinya satu per satu. Buka **Peluang solusi** untuk melihat kandidat, alasan dan tautan produk. Pilih **Solusi** pada diagram untuk melihat nama produknya di rantai aktivitas.

Untuk membaca data terbaru, buka **Katalog resmi → Perbarui katalog resmi**. Tunggu beberapa menit sampai selesai. Produk maintenance/coming soon tidak masuk rekomendasi otomatis. Kandidat yang serupa dengan existing diberi label untuk konfirmasi, bukan ditawarkan otomatis sebagai layanan baru. Pencocokan dengan kerangka contoh tetap hipotesis; riset perusahaan dan LLM memberi analisis yang lebih spesifik setelah keduanya berjalan.

## Jika ingin mencoba diagram dulu

Pilih perusahaan, lalu klik **Lihat kerangka tanpa riset**. Ini bisa dilakukan sebelum model AI siap. Hasil tersebut tetap kerangka hipotesis, bukan riset Google/LLM.

Versi tanpa instalasi juga disertakan di `outputs/Rantai-Buka-Langsung.html`. Buka file itu langsung di browser untuk melihat contoh; file tersebut tidak menjalankan riset atau AI.

## Jika ada masalah

- **Python belum ditemukan:** pastikan Python **3.12** terpasang, lalu buka ulang file `.bat`. Tidak perlu mengubah Execution Policy PowerShell.
- **Unduhan dependensi/Chromium gagal:** periksa internet dan jalankan file pertama lagi. Jangan menonaktifkan verifikasi sertifikat. Pada jaringan kantor, minta admin menyiapkan trust CA/proxy yang benar jika diperlukan.
- **Ollama belum aktif:** buka Ollama dari Start Menu, lalu jalankan file kedua lagi.
- **Model belum siap:** tunggu unduhan pada file kedua selesai, lalu periksa model dari Panduan.
- **Port 8000 dipakai aplikasi lain:** tutup aplikasi yang menggunakan port itu, lalu buka file pertama lagi.
- **Google meminta CAPTCHA:** aplikasi menghentikan riset. Tunggu akses Google pulih lalu coba kembali; aplikasi tidak melewati CAPTCHA. Koneksi laptop dapat berbeda dari jaringan cloud, sehingga akses Google tetap perlu diuji.
- **Analisis lama:** model berjalan di laptop sendiri dan dapat memerlukan beberapa menit.

Tidak memerlukan API key Google/LLM. Data layanan dan catatan pelanggan diproses oleh Ollama pada laptop; nama perusahaan dan segmen dipakai untuk pencarian Google. Hasil AI harus tetap ditinjau, terutama identitas perusahaan dan hipotesis kebutuhan.

Paket ini sudah diperiksa isinya dan kode Python launcher diuji di cloud Linux. File `.bat` belum dijalankan pada mesin Windows sungguhan; jika ada kegagalan, simpan teks error yang terlihat dan lanjutkan diagnosis tanpa mengirim kredensial.
