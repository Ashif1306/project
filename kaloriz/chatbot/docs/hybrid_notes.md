# Asisten Kaloriz - Catatan Hybrid

## Contoh UI/UX Flow
1. **Pesan awal**: pengguna menekan tombol cepat "Lacak pesanan" atau mengetik permintaan pelacakan.
2. **Daftar pesanan**: backend mengembalikan 5 pesanan terakhir (kode, tanggal, status) dan state `STATE_AWAITING_ORDER_CHOICE` aktif.
3. **Pilih order**: pengguna mengetik atau men-tap kode pesanan dari daftar.
4. **Detail**: sistem menampilkan detail (status, item, total, alamat, resi) atau, untuk pembatalan, meminta konfirmasi jika status belum dikemas.
5. **Konfirmasi batal**: balasan "ya" membatalkan status menjadi `cancelled`/"dibatalkan"; balasan lain membatalkan proses.
6. **Kembali ke chat umum**: state dibersihkan dan chatbot siap menerima pertanyaan berikutnya.

## Tips Scaling & Caching
- **Caching intent**: cache hasil `classify_intent` per session untuk pesan berulang dalam jangka pendek guna mengurangi beban model AI.
- **Timeout AI**: gunakan timeout pendek (<=12 detik) dan fallback supaya antrean permintaan tidak menumpuk.
- **Queue & rate limit**: tambahkan antrean asinkron atau rate limiting per IP/session pada endpoint `/chatbot/` untuk mencegah spam.
- **DB indexing**: indeks kolom `user` dan `order_number` di model `Order` untuk mempercepat pencarian 5 pesanan terakhir.
- **Session trimming**: hapus `order_context` setelah selesai untuk mencegah pertumbuhan data session dan inkonsistensi state.
- **CDN untuk widget**: simpan aset widget (JS/CSS) di CDN agar pemuatan cepat pada device mobile.
