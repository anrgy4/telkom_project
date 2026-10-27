# Pencocokan produk resmi

Sumber yang diminta pengguna:

- https://www.telkomsolution.co.id/
- https://www.telkomsolution.co.id/produk
- https://indibiz.co.id/

Pada 27 Oktober 2026, 72 entri sumber berhasil diperoleh: enam halaman solusi Telkom Solution dan 66 produk IndiBiz. Snapshot nama, deskripsi, kutipan sumber, URL dan waktu pembacaan ada dalam `app/data/product-catalog.json`. Ini snapshot observasi, bukan jaminan bahwa seluruh penawaran tetap tersedia. Beberapa halaman berada pada rute maintenance; entri itu bisa dilihat di katalog tetapi tidak direkomendasikan otomatis. Crawl terdahulu menemukan satu halaman success story yang tidak terbaca; metadata snapshot tetap menandai status partial. Katalog lengkap seluruh bisnis Telkom tidak diklaim.

## Cara memakai

1. Jalankan aplikasi lengkap, pilih pelanggan, lalu lihat **Peluang solusi** dan **Solusi** pada diagram.
2. Kandidat produk ditampilkan bersama nama, penjelasan dari sumber, istilah yang cocok, kemungkinan overlap dengan existing, tanggal pembacaan dan tautan resmi.
3. Buka **Katalog resmi → Perbarui katalog resmi** untuk membaca ulang sumber. Proses ini dapat memerlukan beberapa menit. Tidak ada data pelanggan yang dikirim ke situs katalog.
4. Pembaruan otomatis mencocokkan ulang canvas yang sedang ditampilkan; input baru yang belum dianalisis tetap ditandai terpisah. Riset Google dan inferensi tidak diulang hanya untuk memperbarui kandidat produk.

Snapshot bawaan membuat katalog dapat dipakai setelah ekstraksi paket Windows, sebelum pembaruan jaringan pertama. Cache pembaruan berada di `.runtime/product-catalog.json` dan tidak mengubah snapshot source. Versi HTML offline hanya menyediakan snapshot untuk dibaca; pencocokan ulang data baru menggunakan aplikasi lengkap.

## Pengambilan dan bukti

`app/catalog.py` hanya menerima empat hostname resmi (varian www/non-www kedua situs) dan memvalidasi setiap redirect. Tidak membaca login, akun, checkout atau pengajuan langganan. Sitemap publik digunakan untuk menemukan halaman produk; pengambilan dibatasi 120 halaman, tiga request sekaligus, ukuran 2 MB per halaman. Redirect ke domain lain ditolak. Resolusi nama host resmi diserahkan pada proxy HTTPS yang sudah dikonfigurasi agar bekerja ketika DNS lokal cloud tidak tersedia; hostname arbitrer dan IP privat tidak dapat dimasukkan ke crawler katalog.

IndiBiz menyertakan `productDetail` dalam payload Next.js publik. Parser membaca nama produk dan deskripsi dari payload itu, bukan SEO title atau rekomendasi produk lain yang tertanam pada halaman. Halaman solusi Telkom Solution memakai judul metadata resmi bila H1 hanya berisi placeholder `Product Detail Page`. Berita, event, success story dan kategori marketplace tidak diperlakukan sebagai produk hanya karena slugnya berisi kata `produk` atau `layanan`.

Browser biasa hanya dipakai jika penemuan statis/sitemap tidak cukup. Tidak ada bypass TLS atau CAPTCHA. Pada cloud ini Chromium tidak mempercayai CA proxy yang baru dan izin penulisan trust store tidak diberikan; pengambilan katalog tetap berhasil melalui HTML, metadata, sitemap dan payload publik dengan TLS terverifikasi. Tidak ada penonaktifan validasi sertifikat.

## Cara pencocokan

- LLM lokal menerima maksimal 16 entri relevan yang tersedia pada snapshot/cache. Produk maintenance/coming soon tidak dikirim sebagai kandidat.
- Model memilih `product_ids` dari daftar tersebut. ID yang tidak ada di katalog dibuang; nama buatan model tidak otomatis menjadi produk resmi.
- Selain pilihan model, retrieval kata kunci menyediakan kandidat yang dapat dijelaskan. Fokus solusi menjadi syarat; konteks seperti kata `retail` tidak boleh mengganti kebutuhan inti `monitoring jaringan` menjadi aplikasi kasir. Aktivitas Service diprioritaskan untuk pelayanan/interaksi, sedangkan Marketing & Sales untuk promosi.
- Kemiripan kata/ID terpilih bukan bukti kebutuhan. Tidak ditampilkan persentase keyakinan atau klaim penghematan/peningkatan kinerja pelanggan tanpa bukti.
- Existing dicocokkan dari nama/kode/identifier produk. Kemungkinan satu keluarga layanan (misalnya VPN vs VPN IP, atau OCA vs varian OCA) diberi label untuk konfirmasi; bukan otomatis produk baru atau kontrak aktif.
- Sumber katalog hanya membuktikan deskripsi produk. Kutipan katalog tidak dipakai sebagai bukti kondisi perusahaan pelanggan. Google research dan bukti input tetap terpisah.

API: `GET /api/catalog`, `POST /api/catalog/refresh`, `POST /api/match`. Ekspor JSON memuat bukti katalog dan kandidat; CSV memuat nama kandidat, URL dan status. Diagram view Solusi menampilkan nama kandidat produk.

## Validasi

51 tes backend/launcher/parser/pencocokan lulus di cloud Linux. Tes mencakup nama placeholder, payload IndiBiz, sitemap, pembatasan domain, cache gagal, produk maintenance, overlap existing, ID buatan model, konteks yang tidak relevan, dan rematch API. Browser diuji dengan fixture yang jelas berlabel sintetis untuk alur kandidat, URL sumber, status existing, pembaruan katalog, ekspor CSV dan tampilan ponsel. Pengambilan 72 entri dari kedua situs merupakan pengujian langsung yang terpisah dari fixture.

Inferensi model lokal dan riset Google end-to-end belum diklaim berhasil; blocker sebelumnya tetap tercatat di `VALIDATION.md`. Peluncur Windows belum dijalankan di Windows asli.
