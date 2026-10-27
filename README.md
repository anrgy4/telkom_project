# Rantai · IVCA Workspace

**Menjalankan aplikasi lengkap di Windows:** [unduh paket Windows](outputs/Rantai-Windows.zip), ekstrak, lalu ikuti [MULAI-DI-WINDOWS.md](MULAI-DI-WINDOWS.md). Peluncur `1-JALANKAN-APLIKASI.bat` menyiapkan dependensi dan membuka browser; `2-SIAPKAN-AI-SEKALI.bat` menyiapkan model lokal setelah Ollama dipasang. Launcher Python diuji di Linux; eksekusi `.bat` pada Windows asli belum diverifikasi.

Aplikasi berbahasa Indonesia untuk memetakan bisnis pelanggan menjadi **Ecosystem Industry Value Chain Analysis**, berdasarkan materi `[Share] ToT SME Assistant - IVCA DAY 3 (1).pdf` yang diberikan pengguna. Backend FastAPI, Chromium/Playwright untuk Google dinamis, frontend HTML/CSS/JavaScript tanpa build, dan LLM **Ollama pada mesin yang sama**.

**Pencocokan produk resmi:** kandidat dari [Telkom Solution](https://www.telkomsolution.co.id/produk) dan [IndiBiz](https://indibiz.co.id/) tersedia di diagram **Solusi**, **Peluang solusi**, dan tab **Katalog resmi**. Snapshot bawaan memuat 72 produk/halaman solusi yang benar-benar dibaca pada 27 Oktober 2026. Klik **Perbarui katalog resmi** untuk memperbarui dan mencocokkan ulang. [Metode dan validasinya](docs/PRODUCT_MATCHING.md). Kebutuhan pelanggan tetap harus dikonfirmasi; existing bukan otomatis Win.

Alur utama: nama & data layanan → pencarian Google → pembacaan sumber publik → LLM lokal → validasi struktur/bukti → diagram, peluang, dan sumber. Google hanya menerima nama perusahaan dan segmen, bukan tabel layanan atau catatan kunjungan. Tidak ada layanan LLM cloud, telemetri, penyimpanan hasil ke database, atau pengiriman email.

[Lihat lima contoh diagram](outputs/README.md) (kerangka sektor, belum diriset). [Status validasi dan blocker saat ini](docs/VALIDATION.md).

**Tanpa terminal atau instalasi:** unduh [Rantai-Buka-Langsung.html](outputs/Rantai-Buka-Langsung.html) lalu buka dengan Chrome/Edge. Pilih perusahaan dan klik **Perbarui diagram contoh**. Untuk hanya membaca hasil, tersedia [PDF kelima perusahaan](outputs/Contoh-Diagram-5-Perusahaan.pdf). Keduanya merupakan contoh kerangka yang belum diriset, bukan pengganti analisis Google dan LLM. Builder: `.venv/bin/python scripts/build-offline-demo.py`; validasi tanpa network/server: `.venv/bin/python scripts/test-offline-demo.py`.

## Menjalankan

Python 3.12 dan Linux x86_64 digunakan pada cloud ini. Dependensi Python dipin lengkap dalam `requirements.lock`.

```bash
cd /workspace/telkom_project
bash scripts/setup.sh
bash scripts/setup-ollama.sh
```

Di terminal terpisah, jalankan Ollama, unduh model, lalu nyalakan aplikasi:

```bash
# Terminal 1: runtime lokal, hanya mendengarkan loopback
bash scripts/ollama.sh

# Terminal 2: download satu kali; model disimpan di .runtime/models oleh server
.runtime/ollama/bin/ollama pull qwen2.5:3b

# Terminal 3: aplikasi, port 8000; --reload opsional untuk pengembangan
bash scripts/dev.sh
```

Pada cloud ini, `bash scripts/start-cloud.sh` dapat menyalakan ulang atau memakai kembali kedua service. Setelah jaringan untuk model tersedia, gunakan `.venv/bin/python scripts/pull-model.py` untuk mengunduh model tanpa mencetak signed URL dari pesan kegagalan.

Ollama yang sudah terpasang secara resmi juga bisa dipakai dengan `ollama serve` dan `ollama pull qwen2.5:3b`. Helper cloud mempin runtime CPU v0.6.8 dari rilis resmi GitHub dan memverifikasi SHA-256 arsip sebelum ekstraksi; model Qwen2.5 kompatibel dengan versi ini. Helper bukan pengganti kebijakan upgrade untuk deployment produksi. Model 3B membutuhkan unduhan sekitar 2 GB dan beberapa GB RAM. Runtime dapat berjalan di CPU; generasi lengkap bisa memerlukan beberapa menit. Timeout inferensi 10 menit. Empat aktivitas pendukung dan lima aktivitas utama harus lengkap agar hasil diterima.

Ollama membuat direktori kunci runtime `~/.ollama` sendiri. Pada sandbox yang membuat home read-only, berikan izin tulis hanya untuk direktori itu ketika diperlukan; jangan menyalin kunci ke repositori. `.runtime`, `.env`, `.venv`, dan cache tidak dilacak Git.

Konfigurasi server opsional:

| Variabel | Default | Kegunaan |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Nama model yang sudah diunduh; model lebih besar dapat memberi analisis lebih baik |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Dibatasi ke HTTP loopback; LLM eksternal ditolak |
| `PORT` | `8000` | Port aplikasi pada `scripts/dev.sh` |

Mode scraping ini tidak memerlukan API key Google atau LLM. Nama perusahaan dan segmen digunakan sebagai query Google HTML. Akses Google dapat dibatasi jaringan, CAPTCHA, atau perubahan markup. Permintaan yang diblokir **berhenti dengan pesan kegagalan**, tanpa bypass CAPTCHA dan tanpa mengklaim contoh sebagai hasil riset. Halaman yang meminta JavaScript dibaca menggunakan Chromium biasa melalui Playwright. Tidak ada stealth, proxy rotasi, interaksi CAPTCHA, atau API pencarian berbayar. Pengguna memilih tetap scraping dan menunggu akses Google pulih pada sesi ini.



## Menggunakan aplikasi

1. Pilih salah satu dari lima contoh atau masukkan perusahaan sendiri. Periksa segmen dan identitas perusahaan.
2. Edit `GROUP4`, `GROUP5`, dan `DESC2`; tambahkan catatan kunjungan. Excel: salin tabel dengan header atau unggah CSV/TSV. Pilih perusahaan hasil impor; sistem tidak menebak segmennya. Maksimal 1.000 baris per tabel, 150 KB, dan 80 baris layanan per analisis. XLSX dan OCR gambar belum tersedia.
3. Klik **Riset & buat analisis**. UI menunjukkan progres dan bisa membatalkan permintaan. Nama perusahaan dan segmen dikirim ke Google, maksimal lima hasil dibaca. Halaman yang gagal dibaca tetap diberi label cuplikan Google.
4. Tinjau **Peta IVCA**, lapisan **Aktivitas / Solusi**, **Peluang solusi**, dan **Data & sumber**. Klik aktivitas atau elemen ekosistem untuk detail dan kutipan.
5. Ekspor diagram SVG, analisis JSON beserta sumber/kutipan, peluang CSV, atau cetak tab aktif sebagai PDF. Ekspor memakai snapshot canvas, bukan input yang belum dianalisis.

**Lihat kerangka tanpa riset** hanya menghasilkan contoh hipotesis sektor secara deterministik, tanpa Google atau LLM. UI, JSON, nama berkas ekspor, dan diagram SVG memberi label `sample` / belum diriset. Contoh tersebut dapat dipakai meninjau layout meskipun dependensi jaringan/model belum tersedia.

## Acuan dan interpretasi

Pemetaan PDF dan contoh dijelaskan pada [docs/IVCA_MAPPING.md](docs/IVCA_MAPPING.md). Materi diperlakukan sebagai referensi analisis, bukan instruksi untuk mengeksekusi perintah.

- Diagram mengikuti empat sisi ekosistem, empat support activities, lima primary activities, dan margin pada halaman PDF 10/26. Halaman 35–36 memberi contoh perbankan dan pemetaan solusi.
- Existing berarti tercantum dalam data pengguna; bukan bukti kontrak aktif, revenue, atau status Win. Pemetaan layanan existing ke aktivitas menggunakan aturan kategori yang dapat ditinjau, bukan klaim implementasi.
- Revenue Recognition, Reverse Revenue Recognition, potongan, dan Kriteria KB tetap keterangan akuntansi, bukan layanan baru. Layanan “Others”/“Inkubasi” ambigu tidak dipetakan otomatis.
- Rekomendasi/pain point tanpa bukti adalah hipotesis. Peluang memiliki pertanyaan discovery. Aplikasi tidak menghitung wallet share tanpa angka pendapatan atau budget.
- Model harus mengutip teks sumber untuk label `public`, atau input untuk `customer`. Kutipan tidak cocok/ID tidak dikenal diturunkan menjadi `hypothesis`. Pencocokan kutipan **tidak menjamin** kebenaran, entailment, atau kecocokan badan usaha; review manusia tetap diperlukan.
- Data contoh merupakan transkripsi screenshot, bukan informasi publik terverifikasi. Nama persis dipertahankan, termasuk `KOPONTRES SIDOGIRI`; hubungan dengan brand Basmallah belum dikonfirmasi.

## Pengujian

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
node --check app/static/app.js
```

Tes meliputi lima segmen, pivot fill-down, CSV/TSV, kutipan, penolakan endpoint LLM eksternal, penolakan URL sumber privat, parser Google, API, dan alur NDJSON dengan dependensi riset/model yang di-mock. Tes kontrak dengan mock **bukan** verifikasi inferensi model atau Google sebenarnya.

Chromium sistem sudah tersedia pada mesin cloud ini. Untuk mesin lain, pasang Chromium resmi atau jalankan `.venv/bin/python -m playwright install chromium`; arahkan `CHROMIUM_PATH` bila memakai executable lain. Trust CA proxy harus terpasang pada trust store Chromium; jangan memakai opsi untuk mengabaikan kesalahan sertifikat.

Smoke test browser memakai Playwright dan Chromium yang sudah terpasang:

```bash
.venv/bin/python scripts/smoke-browser.py
```

Lihat [docs/VALIDATION.md](docs/VALIDATION.md) untuk hasil eksekusi aktual dan blocker. Tidak ada autentikasi multiuser: aplikasi ini ditujukan untuk workspace pengembangan lokal/terisolasi. Jangan publikasikan port ke internet sebagai layanan produksi tanpa autentikasi dan pembatasan request.
