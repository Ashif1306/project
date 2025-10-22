# Panduan Testing Aplikasi E-Commerce Kaloriz

## Persiapan Testing

### 1. Pastikan Dependencies Terinstall
```bash
pip install -r requirements.txt
```

### 2. Jalankan Development Server
```bash
cd kaloriz
python manage.py runserver
```

Server akan berjalan di: **http://127.0.0.1:8000/**

## Skenario Testing

### A. Testing sebagai Guest (Pengunjung)

#### 1. Homepage
- Buka: http://127.0.0.1:8000/
- ✓ Cek tampilan homepage
- ✓ Cek produk unggulan tampil
- ✓ Cek kategori tampil
- ✓ Navbar berfungsi

#### 2. Browse Produk
- Klik menu "Produk" atau buka: http://127.0.0.1:8000/products/
- ✓ Semua produk tampil
- ✓ Filter kategori berfungsi
- ✓ Filter harga berfungsi
- ✓ Sorting berfungsi (harga, nama, terbaru)

#### 3. Detail Produk
- Klik salah satu produk
- ✓ Detail produk tampil lengkap
- ✓ Harga dan diskon tampil dengan benar
- ✓ Stok produk tampil
- ✓ Tombol "Tambah ke Keranjang" muncul (tapi harus login dulu)

#### 4. Search
- Gunakan search box di navbar
- Coba cari: "laptop", "kaos", "kopi"
- ✓ Hasil pencarian sesuai
- ✓ Jika tidak ada hasil, muncul pesan yang tepat

### B. Testing Autentikasi

#### 1. Register Akun Baru
- Klik "Register" di navbar atau buka: http://127.0.0.1:8000/register/
- Isi form:
  - Username: testuser
  - Password: testpass123
  - Confirm Password: testpass123
- ✓ Registrasi berhasil
- ✓ Auto login setelah register
- ✓ Redirect ke homepage
- ✓ Username tampil di navbar

#### 2. Logout
- Klik username di navbar → Logout
- ✓ Berhasil logout
- ✓ Kembali tampil menu Login/Register

#### 3. Login
- Klik "Login" atau buka: http://127.0.0.1:8000/login/
- Gunakan akun yang baru dibuat:
  - Username: testuser
  - Password: testpass123
- ✓ Login berhasil
- ✓ Username tampil di navbar

### C. Testing Shopping Cart (Harus Login)

#### 1. Tambah Produk ke Keranjang
- Buka detail produk
- Pilih jumlah (quantity)
- Klik "Tambah ke Keranjang"
- ✓ Muncul notifikasi sukses
- ✓ Redirect ke halaman keranjang

#### 2. Lihat Keranjang
- Buka: http://127.0.0.1:8000/cart/
- ✓ Produk yang ditambahkan tampil
- ✓ Harga dan subtotal benar
- ✓ Total dihitung dengan benar (termasuk ongkir)

#### 3. Update Quantity
- Di halaman keranjang, ubah jumlah produk
- Klik tombol centang (✓)
- ✓ Quantity berubah
- ✓ Subtotal dan total ter-update

#### 4. Hapus Item
- Klik tombol hapus (trash icon) di item keranjang
- Konfirmasi hapus
- ✓ Item terhapus dari keranjang
- ✓ Total ter-update

#### 5. Tambah Produk Lain
- Kembali ke katalog produk
- Tambahkan 2-3 produk lain
- ✓ Semua produk masuk ke keranjang

### D. Testing Checkout & Order

#### 1. Proses Checkout
- Di halaman keranjang, klik "Checkout"
- Atau buka: http://127.0.0.1:8000/checkout/
- ✓ Form pengiriman tampil
- ✓ Ringkasan pesanan tampil di sidebar

#### 2. Isi Form Pengiriman
Isi dengan data test:
```
Nama Lengkap: John Doe
Email: john@example.com
Nomor Telepon: 081234567890
Alamat: Jl. Test No. 123
Kota: Jakarta
Kode Pos: 12345
Catatan: Test order
```

#### 3. Buat Pesanan
- Klik "Buat Pesanan"
- ✓ Pesanan berhasil dibuat
- ✓ Muncul nomor pesanan
- ✓ Redirect ke detail pesanan
- ✓ Keranjang kosong

#### 4. Lihat Detail Pesanan
- ✓ Nomor pesanan tampil
- ✓ Status pesanan: "Menunggu Pembayaran"
- ✓ Item pesanan benar
- ✓ Total harga benar
- ✓ Alamat pengiriman benar

### E. Testing Order Management

#### 1. Daftar Pesanan
- Klik username → "Pesanan Saya"
- Atau buka: http://127.0.0.1:8000/orders/
- ✓ Semua pesanan tampil
- ✓ Status pesanan tampil dengan warna badge

#### 2. Detail Pesanan
- Klik "Detail" pada salah satu pesanan
- ✓ Detail lengkap tampil
- ✓ Item pesanan tampil
- ✓ Alamat pengiriman tampil

### F. Testing User Profile

#### 1. Lihat Profil
- Klik username → "Profil"
- Atau buka: http://127.0.0.1:8000/profile/
- ✓ Informasi user tampil

#### 2. Update Profil
- Isi/update alamat pengiriman:
```
Nomor Telepon: 081234567890
Alamat: Jl. Update No. 456
Kota: Bandung
Kode Pos: 40123
```
- Klik "Simpan Perubahan"
- ✓ Profil berhasil diupdate
- ✓ Data tersimpan

#### 3. Test Profil di Checkout
- Tambah produk ke keranjang lagi
- Buka checkout
- ✓ Form alamat sudah terisi otomatis dari profil

### G. Testing Admin Panel

#### 1. Login Admin
- Buka: http://127.0.0.1:8000/admin/
- Login dengan:
  - Username: admin
  - Password: admin123
- ✓ Berhasil masuk admin panel

#### 2. Manajemen Kategori
- Klik "Kategori"
- ✓ List kategori tampil
- Tambah kategori baru:
  - Nama: Peralatan Rumah
  - Deskripsi: Peralatan rumah tangga
- ✓ Kategori berhasil dibuat
- ✓ Slug auto-generate

#### 3. Manajemen Produk
- Klik "Produk"
- ✓ List produk tampil dengan filter
- Edit salah satu produk:
  - Ubah harga
  - Ubah stok
- ✓ Produk berhasil diupdate

#### 4. Tambah Produk Baru
- Klik "Add Produk"
- Isi:
  - Kategori: (pilih kategori)
  - Nama: Test Product
  - Deskripsi: Produk untuk testing
  - Harga: 100000
  - Stok: 10
  - Tersedia: ✓
- ✓ Produk berhasil dibuat
- ✓ Tampil di website

#### 5. Manajemen Pesanan
- Klik "Pesanan"
- ✓ Semua pesanan tampil
- Buka salah satu pesanan
- Update status pesanan:
  - Ubah status dari "Menunggu Pembayaran" ke "Diproses"
- ✓ Status berhasil diupdate
- Logout dari admin

#### 6. Cek Update Status di User
- Login sebagai user (testuser)
- Buka "Pesanan Saya"
- ✓ Status pesanan sudah berubah jadi "Diproses"

### H. Testing Edge Cases

#### 1. Stock Validation
- Login sebagai user
- Cari produk dengan stok rendah
- Coba tambah ke keranjang dengan quantity > stok
- ✓ Muncul error "Stok tidak mencukupi"

#### 2. Empty Cart Checkout
- Kosongkan keranjang
- Coba akses: http://127.0.0.1:8000/checkout/
- ✓ Redirect ke cart dengan pesan error

#### 3. Guest Access
- Logout
- Coba akses: http://127.0.0.1:8000/cart/
- ✓ Redirect ke login
- ✓ Setelah login, kembali ke halaman yang dituju

#### 4. Duplicate Cart Item
- Tambah produk A ke keranjang
- Tambah produk A lagi
- ✓ Quantity bertambah, bukan duplicate item

### I. Testing Responsiveness

#### 1. Mobile View
- Resize browser ke ukuran mobile (< 768px)
- ✓ Navbar collapse jadi hamburger menu
- ✓ Product cards stack vertically
- ✓ Forms tetap usable

#### 2. Tablet View
- Resize browser ke ukuran tablet (768px - 1024px)
- ✓ Layout adjust dengan baik
- ✓ 2-3 product cards per row

## Checklist Testing Lengkap

### Functionality
- [ ] Homepage loads
- [ ] Product list with filters
- [ ] Product detail
- [ ] Search functionality
- [ ] Category filtering
- [ ] User registration
- [ ] User login/logout
- [ ] Add to cart
- [ ] Update cart quantity
- [ ] Remove from cart
- [ ] Checkout process
- [ ] Order creation
- [ ] Order list
- [ ] Order detail
- [ ] User profile update
- [ ] Admin product management
- [ ] Admin order management
- [ ] Admin category management

### UI/UX
- [ ] Responsive design
- [ ] Navigation works
- [ ] Messages/notifications appear
- [ ] Forms validate properly
- [ ] Buttons have hover effects
- [ ] Images display correctly
- [ ] Price formatting correct
- [ ] Discount badges show

### Security
- [ ] Login required for cart
- [ ] Login required for checkout
- [ ] Login required for orders
- [ ] Users can only see their orders
- [ ] Admin panel protected
- [ ] CSRF protection active

### Data Integrity
- [ ] Stock updates after order
- [ ] Cart clears after order
- [ ] Prices calculated correctly
- [ ] Order totals correct
- [ ] Duplicate prevention

## Testing Tools

### Manual Testing
Gunakan browser untuk manual testing di atas.

### Browser Developer Tools
- F12 untuk buka Dev Tools
- Cek Console untuk errors
- Cek Network tab untuk API calls
- Responsive mode untuk mobile testing

### Test Different Browsers
- Chrome
- Firefox
- Safari
- Edge

## Troubleshooting

### Server tidak jalan
```bash
# Pastikan di folder yang benar
cd kaloriz

# Cek port sudah digunakan atau belum
python manage.py runserver 0.0.0.0:8001
```

### Error saat checkout
- Pastikan login
- Pastikan cart tidak kosong
- Pastikan semua field diisi

### Gambar tidak muncul
- Pastikan MEDIA_URL dan MEDIA_ROOT sudah di-setup
- Atau gunakan placeholder images

### Static files tidak load
```bash
python manage.py collectstatic
```

## Report Issues

Jika menemukan bug atau issue:
1. Catat URL yang bermasalah
2. Catat langkah untuk reproduce
3. Screenshot jika perlu
4. Catat error message dari console

---

**Happy Testing! 🧪✨**
