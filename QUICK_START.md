# Quick Start - Testing Aplikasi E-Commerce

## ✅ Server Sudah Berjalan!

Server development Django sudah aktif di:
**http://127.0.0.1:8000/**

## 🚀 Mulai Testing (5 Menit)

### Step 1: Buka Homepage
```
URL: http://127.0.0.1:8000/
```
Anda akan melihat:
- Homepage dengan banner
- 8 produk unggulan
- 5 kategori produk

### Step 2: Browse Produk
```
URL: http://127.0.0.1:8000/products/
```
Coba:
- Filter berdasarkan kategori
- Filter harga (min/max)
- Sorting (harga terendah/tertinggi)
- Klik salah satu produk untuk detail

### Step 3: Register Akun
```
URL: http://127.0.0.1:8000/register/
```
Buat akun test:
- Username: `demouser`
- Password: `demo12345`
- Confirm: `demo12345`

### Step 4: Belanja
1. Klik salah satu produk
2. Pilih jumlah (quantity)
3. Klik "Tambah ke Keranjang"
4. Tambahkan 2-3 produk lagi

### Step 5: Checkout
```
URL: http://127.0.0.1:8000/cart/
```
1. Review keranjang Anda
2. Klik "Checkout"
3. Isi form pengiriman:
   ```
   Nama: Test User
   Email: test@example.com
   Phone: 081234567890
   Alamat: Jl. Test No. 123
   Kota: Jakarta
   Kode Pos: 12345
   ```
4. Klik "Buat Pesanan"

### Step 6: Lihat Pesanan
```
URL: http://127.0.0.1:8000/orders/
```
- Lihat daftar pesanan Anda
- Klik detail untuk melihat informasi lengkap

### Step 7: Admin Panel
```
URL: http://127.0.0.1:8000/admin/
```
Login dengan:
- Username: `admin`
- Password: `admin123`

Di admin panel, coba:
- Lihat semua pesanan
- Update status pesanan
- Tambah produk baru
- Edit produk existing

## 📊 Data Sample yang Tersedia

### Kategori (5):
1. Elektronik
2. Fashion
3. Makanan & Minuman
4. Buku
5. Olahraga

### Produk (12):
- Smartphone Android X1 - Rp 3.000.000 (diskon dari 3.500.000)
- Laptop Gaming Pro - Rp 13.500.000 (diskon dari 15.000.000)
- Wireless Earbuds - Rp 750.000
- Kaos Cotton Premium - Rp 120.000 (diskon dari 150.000)
- Jaket Hoodie - Rp 350.000
- Sepatu Sneakers - Rp 380.000 (diskon dari 450.000)
- Kopi Arabica Premium - Rp 120.000
- Madu Murni - Rp 75.000 (diskon dari 85.000)
- Buku Pemrograman Python - Rp 180.000
- Novel Best Seller - Rp 80.000 (diskon dari 95.000)
- Matras Yoga - Rp 200.000
- Dumbbell Set - Rp 300.000 (diskon dari 350.000)

## 🔥 Fitur yang Bisa Dicoba

### Untuk User:
- ✅ Browse & search produk
- ✅ Filter kategori & harga
- ✅ Tambah ke keranjang
- ✅ Update quantity di cart
- ✅ Checkout & buat pesanan
- ✅ Lihat riwayat pesanan
- ✅ Update profil & alamat

### Untuk Admin:
- ✅ CRUD produk
- ✅ CRUD kategori
- ✅ Update status pesanan
- ✅ Lihat detail pesanan
- ✅ Manajemen user

## ⚡ Quick Commands

### Jalankan Server (jika belum)
```bash
cd kaloriz
python manage.py runserver
```

### Stop Server
```bash
# Tekan CTRL+C di terminal server
```

### Reset Database (jika perlu)
```bash
rm db.sqlite3
rm catalog/migrations/0001_initial.py
rm core/migrations/0001_initial.py
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python populate_data.py
```

### Lihat Log Server
```bash
tail -f /tmp/django_server.log
```

## 🐛 Troubleshooting

### Port sudah digunakan?
```bash
python manage.py runserver 8001
```
Lalu akses: http://127.0.0.1:8001/

### Static files tidak load?
```bash
python manage.py collectstatic --noinput
```

### Error saat migrasi?
```bash
python manage.py makemigrations
python manage.py migrate
```

## 📸 Screenshot Testing

Ketika testing, perhatikan:
- ✅ Navbar responsive
- ✅ Badge diskon tampil
- ✅ Harga tercoret untuk produk diskon
- ✅ Stok produk tampil
- ✅ Notifikasi muncul saat aksi (tambah cart, dll)
- ✅ Form validation bekerja
- ✅ Messages hilang otomatis atau bisa di-close

## 🎯 Test Scenarios

### Scenario 1: Happy Path
1. Register → Login
2. Browse → Pilih produk
3. Tambah ke cart
4. Checkout → Isi form
5. Buat pesanan → Sukses
6. Lihat detail pesanan

### Scenario 2: Cart Management
1. Tambah 3 produk
2. Update quantity salah satu
3. Hapus 1 produk
4. Lanjut checkout

### Scenario 3: Admin Flow
1. Login admin
2. Tambah kategori baru
3. Tambah produk ke kategori
4. Cek di website (logout admin)
5. Produk tampil di kategori tersebut

## 💡 Tips Testing

1. **Buka 2 Browser:**
   - Browser 1: User view
   - Browser 2: Admin view
   - Test update di admin, refresh di user view

2. **Test Responsive:**
   - F12 → Toggle device toolbar
   - Test di mobile, tablet, desktop

3. **Test Edge Cases:**
   - Keranjang kosong → checkout
   - Quantity > stok
   - Form tidak lengkap

4. **Performance:**
   - Cek loading time
   - Cek query database (di admin debug toolbar jika installed)

## ✨ Next Steps

Setelah testing dasar, Anda bisa:
1. Customize desain (edit templates & CSS)
2. Tambah payment gateway
3. Tambah email notifications
4. Tambah review & rating produk
5. Tambah wishlist
6. Deploy ke production

---

**Selamat Testing! 🎉**

Jika ada pertanyaan atau menemukan bug, silakan laporkan.
