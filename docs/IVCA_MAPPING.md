# Pemetaan materi dan data pengguna

Materi: `[Share] ToT SME Assistant - IVCA DAY 3 (1).pdf`, 53 halaman. Nomor di bawah adalah nomor halaman PDF; beberapa slide memiliki nomor cetak berbeda. PDF tidak didistribusikan ulang di repository.

| Halaman PDF | Penerapan |
| --- | --- |
| 2, 5–7 | Tujuan memahami bisnis, pengumpulan data → analisis aktivitas → mapping aktivitas/proyek |
| 8–10, 26 | Porter: 4 support dan 5 primary activities; ekosistem dan margin |
| 12–18 | Definisi dan contoh setiap aktivitas |
| 21–22, 24–25 | Aktivitas hospitality dan solusi terpisah; pemisahan view Aktivitas/Solusi |
| 35–36 | Ekosistem perbankan dan solusi; label Prospect/Win membutuhkan data |
| 38–44 | Contoh sektor F&B, hotel, pariwisata; bukan fakta perusahaan contoh pengguna |
| 46–50 | Aktivitas → deskripsi → solusi; diterapkan pada peluang dan discovery |

**Support activities**: Firm Infrastructure; HR Management; Tech Development; Procurement.

**Primary activities**: Inbound Logistics; Operations; Outbound Logistics; Marketing & Sales; Service.

**Ekosistem**: Supporting Industry kiri; Complementary Institution atas; Related Industry bawah; Customer kanan; Margin pada sisi core. Margin adalah konsep nilai tambah, bukan angka laba perusahaan.

## Lima screenshot

Urutan screenshot pada pesan berbeda dari urutan daftar kutipan. Pemetaan berdasarkan `STANDARD_NAME` dan segmen yang diberikan pengguna:

| Screenshot | STANDARD_NAME persis | Segmen yang dipakai | Catatan |
| --- | --- | --- | --- |
| 1 | KOPONTRES SIDOGIRI | Retail / IndiBiz Ruko | Label brand Basmallah dari pengguna; ejaan dan relasi entitas perlu konfirmasi |
| 2 | UNSIQ WONOSOBO | Perguruan tinggi / IndiBiz Education | Cloud, Collocation, Inkubasi, OCA, Others, Wifi disimpan sesuai hierarki gambar |
| 3 | PT ASHAVIN PANDAWA MEDIKA INDONESIA | Kesehatan / IndiBiz Health | Segmen rumah sakit dari pengguna; fasilitas/identitas belum diverifikasi |
| 4 | BPR BANK SURYA YUDHA | BPR / IndiBiz Finance | Existing: ASTINet, OCA (GROUP4 Inkubasi), VPN |
| 5 | KOSPIN JASA | Koperasi / IndiBiz Finance | Existing: ASTINet, VPN |

Input tidak memiliki nominal, kuantitas cabang, periode kontrak, kontak, ataupun evidence status Win. Aplikasi tidak mengisi atribut tersebut dengan tebakan. `RBT` dengan DESC2 antivirus dipertahankan persis; tidak dinormalisasi menjadi produk antivirus tanpa konfirmasi.

Kerangka awal sektor pada `app/domain.py` merupakan hipotesis generik yang disusun dari pendekatan materi. Model lokal harus membuat analisis spesifik berdasarkan data input dan sumber yang benar-benar tersedia; kerangka awal bukan fallback diam-diam saat riset gagal.
