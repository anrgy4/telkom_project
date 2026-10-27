# Hasil validasi aktual — 22 Oktober 2026

**Pembaruan 27 Oktober 2026:** pencocokan katalog resmi ditambahkan dan diuji; 72 entri sumber nyata sudah dibaca dan disertakan sebagai snapshot. Total tes backend kini 51 lulus. Browser untuk katalog/produk dan alur aplikasi lulus; model/Google end-to-end tetap belum diklaim sukses. Lihat [PRODUCT_MATCHING.md](PRODUCT_MATCHING.md) untuk metode, batasan, dan hasil pengujian terbaru. Paket Windows diperbarui dan sudah diunggah ke GitHub `anrgy4/telkom_project`, branch `main`, setelah izin pengguna diberikan pada 27 Oktober 2026. Ref remote telah diverifikasi melalui Git. Tautan internal workspace sebelumnya dilaporkan tidak dapat diunduh; distribusi sekarang melalui GitHub. Pemeriksaan HTTP unduhan langsung dari cloud dibatasi proxy, sehingga keberhasilan unduh lewat browser pengguna belum diklaim.

## Yang sudah berjalan

- Python 3.12.14; virtual environment proyek; instalasi seluruh dependensi dari `requirements.lock`; `pip check` lolos. `scripts/setup.sh` dijalankan ulang dan berhasil.
- Backend FastAPI berjalan melalui `scripts/dev.sh`. Ollama CPU v0.6.8 berjalan melalui `scripts/ollama.sh`. Kedua proses yang dibuat pada sesi ini dihentikan dan dinyalakan ulang menggunakan script proyek; `scripts/start-cloud.sh` memeriksa HTTP readiness dan aman dipanggil ketika keduanya sudah berjalan.
- Arsip Ollama resmi diverifikasi terhadap SHA-256 dari rilis resmi sebelum ekstraksi: `9f9ff52b8297d6e40904f22bac09eac587a05111762bf278359621fbdb53dbb9`. Library CUDA tidak diekstrak karena workflow ini menggunakan CPU. Tidak ada TLS/checksum/signature verification yang dinonaktifkan.
- **23 tes backend/API/parser/grounding lulus** melalui `.venv/bin/python -m unittest discover -s tests -v`. Tes alur sukses riset/model menggunakan mock; hasilnya tidak membuktikan Google atau inferensi sebenarnya.
- `node --check app/static/app.js` dan pemeriksaan sintaks shell lulus.
- **Smoke test Chromium aktual lulus** untuk lima perusahaan, sembilan aktivitas, detail aktivitas/ekosistem, view solusi, tab, impor tabel multi-perusahaan, penanda input berubah, penanganan input HTML, CSV aman terhadap formula, serta ekspor SVG/JSON/CSV/PDF. Tidak ada error JavaScript. Model yang belum tersedia menghasilkan HTTP 503 dan canvas tetap berlabel contoh.
- Tampilan diuji pada desktop 1440×1080 dan ponsel 390×844. Halaman ponsel tidak melebar di luar viewport; diagram menggunakan scroll horizontal agar strukturnya tetap terbaca.
- PDF hasil cetak: satu halaman, nama `BPR BANK SURYA YUDHA` dan label diagram diperiksa dari teks PDF. SVG diverifikasi sebagai XML vektor dengan label belum diriset.
- Lima contoh SVG di `outputs/` dibuat lewat fitur ekspor aplikasi, dengan nama perusahaan dan label jelas **CONTOH KERANGKA — BELUM DIRISET**. Tidak ada yang diklaim sebagai analisis LLM atau profil publik terverifikasi.

Artefak pengujian browser lokal: `.runtime/browser/desktop.png`, `mobile.png`, `sample.svg`, `sample.json`, `sample.csv`, `sample.pdf`. Direktori runtime diabaikan Git.

## Versi contoh tanpa instalasi

Untuk pengguna yang ingin melihat/mencoba hasil tanpa terminal, disediakan `outputs/Rantai-Buka-Langsung.html` (satu file, seluruh CSS/JS/data disertakan) dan `outputs/Contoh-Diagram-5-Perusahaan.pdf`.

Dokumen HTML diuji dalam Chromium menggunakan `set_content` karena kebijakan browser cloud memblokir navigasi `file://`. Lima contoh, nama perusahaan sendiri, impor CSV, lapisan solusi, ekspor SVG, dan panduan lulus; tidak ada request jaringan atau error JavaScript. Pengujian ini memvalidasi eksekusi dokumen mandiri, bukan integrasi Google/LLM ataupun konfigurasi aplikasi default pada laptop pengguna. PDF diperiksa: tepat lima halaman, semua nama perusahaan sesuai, setiap halaman berlabel belum diriset. Versi offline secara eksplisit tidak memakai server/Google/LLM; data edit hanya bertahan di tab browser.

## Paket Windows

Paket `outputs/Rantai-Windows.zip` berisi source, dependensi yang dipin, panduan Windows, dan dua peluncur `.bat`. Folder cloud `.venv`, `.runtime`, `.cache`, metadata Git, dan file `.env` tidak ikut dikemas. Integritas arsip dan daftar berkas diverifikasi. Peluncur Python menangani pemasangan dependensi satu kali, pemasangan browser, port yang terpakai, pembukaan UI, serta penghentian server. Penyiapan AI memeriksa model yang sudah ada, mengunduh bila diperlukan, dan tidak mencetak signed URL dari kegagalan.

Enam tes launcher ditambah 23 tes aplikasi **lulus (29 total)** di Linux. Cabang pemasangan Windows, `.bat`, dan unduhan/inferensi model nyata pada laptop pengguna belum dijalankan; paket belum diklaim teruji langsung di Windows. Launcher tidak memerlukan atau menyalin konfigurasi rahasia dari cloud. Koneksi Google pada laptop pengguna perlu diuji tersendiri.

## Yang masih terblokir

1. **Scraping Google:** koneksi awal ditolak proxy, kemudian HTTP Google berhasil. HTML yang diterima hanya meminta JavaScript. Pemeriksaan Chromium normal (TLS tetap diverifikasi) menampilkan pesan Indonesia tentang lalu lintas tidak wajar/verifikasi, tanpa hasil pencarian. CAPTCHA tidak diinteraksikan atau dilewati. Belum ada kumpulan sumber Google nyata yang berhasil diperoleh. Pengguna memilih tetap scraping dan menunggu akses Google pulih; adapter API berbayar tidak digunakan. Browser renderer sudah disiapkan, dengan tes kontrak; pipeline scraping lengkap belum dapat dinyatakan lolos.
2. **Model lokal:** Ollama HTTP `/api/tags` bekerja tetapi daftar model masih kosong. Manifest `qwen2.5:3b` dapat dibaca, kemudian unduhan blob ditolak pada host `dd20bb891979d25aebc8bec07b2b3bbc.r2.cloudflarestorage.com`. Model sekitar 1,93 GB belum selesai diunduh/diverifikasi. Inferensi model lokal dan analisis lengkap Google → LLM **belum dijalankan sampai sukses**.

Keduanya merupakan blocker akses layanan eksternal, bukan kegagalan tes aplikasi yang disembunyikan. Tidak ada klaim lingkungan siap penuh.

## Konfigurasi tersimpan dan langkah berikut

Draf konfigurasi berhasil disimpan: `install_script`, `start_skill`, dan domain jaringan tambahan, dengan preset package manager tetap dipertahankan. Domain custom: `www.google.com`, `www.gstatic.com`, `registry.ollama.ai`, `ollama.com`, `api.github.com`, serta host storage model di atas. Tidak ada secret atau API key yang diminta/disimpan.

Menyimpan draf tidak membuktikan konfigurasi sudah diterapkan pada mesin, dipublikasikan, atau dipulihkan di task baru. Instruksi instalasi menyertakan tahap pull model yang masih memerlukan izin jaringan; keberhasilan keseluruhan script itu belum diklaim. Hasil instalasi Python, runtime Ollama, startup, dan pengujian lokal sudah divalidasi terpisah.

Simpan perubahan jaringan melalui pengaturan lingkungan agar host storage model diizinkan. Setelah akses itu tersedia, jalankan `.venv/bin/python scripts/pull-model.py`; periksa `llm.ready` pada `/api/health`. Setelah akses Google pulih, jalankan satu analisis nyata melalui UI dan periksa sumber, kutipan, struktur sembilan aktivitas, serta identitas perusahaan. Bila Google meminta verifikasi lagi, hentikan dan tunggu pemulihan akses. Tidak ada retry pencarian berulang sebagai pengganti izin atau penyelesaian CAPTCHA.

Pengguna dapat meninjau pengaturan tersimpan dan mempublikasikan lingkungan setelah validasi langsung yang tersisa selesai. Publikasi dan pemulihan snapshot pada task baru belum diuji. Publikasi cloud dan pengujian restore masih belum dilakukan. Source dan paket Windows kemudian diunggah ke GitHub setelah izin pengguna pada 27 Oktober 2026; ini berbeda dari publikasi lingkungan cloud.

## Perbaikan pemeriksaan startup Windows (27 Oktober 2026)

Log pengguna menunjukkan Uvicorn sudah menyala, tetapi launcher melaporkan timeout. Pemeriksaan lama mengakses `/api/health` dengan timeout 2 detik, sedangkan pemeriksaan Ollama di endpoint itu memiliki timeout 3 detik. Pemeriksaan baru memakai `/api/ready` dengan identitas aplikasi yang tetap dan tanpa akses Ollama. Status lengkap AI tetap tersedia pada `/api/health`.

52 tes lulus, termasuk regresi bahwa kesiapan UI tidak memanggil pemeriksaan model. Uji HTTP pada proses Uvicorn nyata dengan server Ollama simulasi yang sengaja merespons lebih lambat dari timeout juga lulus: UI terdeteksi siap segera, status AI melaporkan belum tersedia, dan UI tetap siap. Ini uji regresi di Linux, bukan klaim telah menjalankan launcher pada Windows pengguna. Pesan Playwright sebelum unduhan Chromium pada log pengguna bukan penyebab timeout yang diperbaiki di sini.
