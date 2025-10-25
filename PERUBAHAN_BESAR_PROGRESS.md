# Progress Perubahan Besar Proyek E-Commerce Kaloriz

Dokumen ini mencatat progress perubahan besar yang diminta oleh user.

## ✅ SELESAI DIKERJAKAN

### 1. Hapus Integrasi RajaOngkir ✅
**Status: SELESAI 100%**

Perubahan:
- ❌ Dihapus: `shipping/services/raja.py`
- ❌ Dihapus: `test_rajaongkir_integration.py`
- ✅ Dibersihkan: Settings tidak lagi memiliki konfigurasi RajaOngkir
- ✅ Dibersihkan: `shipping/urls.py` hanya endpoint sederhana
- ✅ Dibersihkan: `shipping/views.py` hanya fungsi dasar shipping

### 2. Simplifikasi Model Address ✅
**Status: SELESAI 100%**

Model Address baru dengan field standard:
```python
class Address(models.Model):
    # Basic info
    label = models.CharField(...)           # "Rumah", "Kantor", dll
    full_name = models.CharField(...)
    phone = models.CharField(...)

    # Address details
    province = models.CharField(...)        # Default: "Sulawesi Selatan"
    city = models.CharField(...)            # Default: "Makassar"
    district = models.ForeignKey(District, ...)  # FK ke District lokal
    postal_code = models.CharField(...)
    street_name = models.CharField(...)
    detail = models.TextField(...)          # Detail tambahan

    # Map coordinates (opsional)
    latitude = models.DecimalField(...)
    longitude = models.DecimalField(...)

    # Status
    is_default = models.BooleanField(...)
```

Field yang dihapus:
- ❌ `destination_subdistrict_id` (RajaOngkir)
- ❌ `subdistrict_name` (redundant)
- ❌ `city_name` (redundant)
- ❌ `province_name` (redundant)
- ❌ `address_line` (diganti street_name + detail)
- ❌ `is_primary` (redundant, hanya pakai is_default)

### 3. Update Core Models ✅
**Status: SELESAI 100%**

#### CartItem - Checkbox Selection
```python
class CartItem(models.Model):
    cart = models.ForeignKey(...)
    product = models.ForeignKey(...)
    quantity = models.PositiveIntegerField(...)
    is_selected = models.BooleanField(default=True)  # ✨ BARU
    added_at = models.DateTimeField(...)
```

#### Cart - Methods untuk Selected Items
```python
class Cart(models.Model):
    def get_selected_total(self):
        """Calculate total of selected items only"""

    def get_selected_items_count(self):
        """Get count of selected items"""
```

#### UserProfile - Photo Upload
```python
class UserProfile(models.Model):
    user = models.OneToOneField(...)
    photo = models.ImageField(upload_to='profile_photos/', ...)  # ✨ BARU
    phone = models.CharField(...)
    address = models.TextField(...)
    city = models.CharField(...)
    postal_code = models.CharField(...)
    gender = models.CharField(...)
    birth_date = models.DateField(...)

    def get_photo_url(self):
        """Return profile photo URL or default avatar"""
```

### 4. Update Forms ✅
**Status: SELESAI 100%**

`shipping/forms.py` - AddressForm disesuaikan dengan Address model baru:
- ✅ Field sesuai dengan model Address baru
- ✅ Validasi phone number Indonesia
- ✅ Validasi kode pos Makassar (90xxx)
- ✅ Default province & city

### 5. Update Admin ✅
**Status: SELESAI 100%**

`shipping/admin.py` - AddressAdmin disesuaikan:
- ✅ list_display sesuai field baru
- ✅ list_filter sesuai field baru
- ✅ search_fields sesuai field baru
- ✅ fieldsets terorganisir dengan baik

### 6. Database Migrations ✅
**Status: SELESAI 100%**

- ✅ Migrasi baru dibuat untuk semua perubahan model
- ✅ Database baru dibuat (db.sqlite3)
- ✅ Semua migrasi berhasil dijalankan

---

## 🚧 BELUM DIKERJAKAN (Perlu Dilanjutkan)

### 1. Update Template Keranjang dengan Checkbox ⏳
**Status: BELUM MULAI**
**Priority: HIGH**

File: `templates/core/cart.html`

Yang perlu ditambahkan:
- [ ] Checkbox di setiap item keranjang
- [ ] "Select All" checkbox
- [ ] JavaScript untuk toggle selection
- [ ] Update total berdasarkan selected items
- [ ] Tombol "Hapus Terpilih" untuk bulk delete
- [ ] Tombol "Checkout" hanya untuk selected items

Contoh HTML yang perlu ditambahkan:
```html
<input type="checkbox" class="cart-item-checkbox"
       name="selected_items"
       value="{{ item.id }}"
       {% if item.is_selected %}checked{% endif %}>
```

### 2. Multi-Step Checkout (3 Steps) ⏳
**Status: BELUM MULAI**
**Priority: HIGH**

Perlu membuat 3 halaman checkout:

#### Step 1: Pilih Alamat
File: `templates/core/checkout_address.html`

Fitur:
- [ ] Progress bar (Alamat → Payment → Review)
- [ ] List alamat yang tersimpan dalam cards
- [ ] Radio button untuk pilih alamat
- [ ] Tombol "+ Tambah Alamat"
- [ ] Form tambah alamat (modal atau inline)
- [ ] Pilih kurir: Reguler vs Express
- [ ] Ringkasan pembayaran di sidebar kanan
- [ ] Tombol "Lanjutkan" ke payment

#### Step 2: Metode Pembayaran
File: `templates/core/checkout_payment.html`

Fitur:
- [ ] Progress bar (Alamat → **Payment** → Review)
- [ ] Pilihan metode pembayaran
- [ ] Ringkasan alamat terpilih
- [ ] Ringkasan biaya
- [ ] Tombol "Lanjutkan" ke review

#### Step 3: Review & Konfirmasi
File: `templates/core/checkout_review.html`

Fitur:
- [ ] Progress bar (Alamat → Payment → **Review**)
- [ ] Review semua data order
- [ ] Review alamat pengiriman
- [ ] Review metode pembayaran
- [ ] Review items & total
- [ ] Tombol "Buat Pesanan"

### 3. Update Profile Templates ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

File: `templates/core/profile.html`

Yang perlu ditambahkan:
- [ ] Display foto profil
- [ ] Form upload/change foto profil
- [ ] Preview foto sebelum upload
- [ ] Crop foto (opsional)
- [ ] Display username, nama, email, phone
- [ ] Display gender dan tanggal lahir
- [ ] Tombol "Edit Profile"

### 4. Change Password Functionality ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

Yang perlu dibuat:
- [ ] View function untuk change password di `core/views.py`
- [ ] Template `templates/core/change_password.html`
- [ ] Form validasi password lama
- [ ] Validasi password baru (minimal 8 karakter, dll)
- [ ] Konfirmasi password baru
- [ ] Success/error messages
- [ ] URL routing di `core/urls.py`

### 5. Update Product Detail Page ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

File: `templates/catalog/product_detail.html`

Perubahan layout:
- [ ] Pindahkan deskripsi produk ke BAWAH tombol "Buy It Now"
- [ ] Urutkan: Image → Title → Price → Buttons → Deskripsi
- [ ] Pastikan layout tetap rapi dan responsive

### 6. Buy It Now Direct Checkout ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

Yang perlu dibuat:
- [ ] View function `buy_now` di `core/views.py`
- [ ] Tambah produk ke session temporary (bukan cart)
- [ ] Redirect langsung ke checkout alamat
- [ ] Bypass cart page
- [ ] Handle quantity dari product detail
- [ ] Clear temporary buy_now session setelah order

### 7. Form Tambah Alamat di Checkout ⏳
**Status: BELUM MULAI**
**Priority: HIGH**

Yang perlu dibuat:
- [ ] Modal atau inline form di checkout
- [ ] Implementasi Address Map Picker
- [ ] Integrate dengan Google Maps atau Leaflet.js
- [ ] Auto-fill fields dari map click
- [ ] Geocoding untuk lat/lng → address
- [ ] Reverse geocoding untuk address → lat/lng
- [ ] Save address dan auto-select setelah create

### 8. Update Shipping Views ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

File: `core/views.py`

Yang perlu diupdate:
- [ ] `checkout()` - support multi-step flow
- [ ] `place_order()` - integrate dengan selected items only
- [ ] Add `checkout_address()` view
- [ ] Add `checkout_payment()` view
- [ ] Add `checkout_review()` view
- [ ] Add `toggle_cart_item_selection()` view
- [ ] Add `buy_now()` view

### 9. JavaScript/AJAX Functions ⏳
**Status: BELUM MULAI**
**Priority: MEDIUM**

Yang perlu dibuat:
- [ ] Cart checkbox selection toggle
- [ ] Select all / deselect all
- [ ] Update cart total (selected items only)
- [ ] Map picker integration
- [ ] Address autocomplete
- [ ] Profile photo preview
- [ ] Profile photo upload

### 10. Static Assets ⏳
**Status: BELUM MULAI**
**Priority: LOW**

Yang perlu ditambahkan:
- [ ] Default avatar image (`/static/images/default-avatar.png`)
- [ ] Map marker icons
- [ ] Loading spinners
- [ ] CSS untuk multi-step checkout progress bar
- [ ] CSS untuk address cards
- [ ] CSS untuk profile photo upload

---

## 📝 CATATAN PENTING

### Migration Strategy
✅ **SUDAH DILAKUKAN**: Database dihapus dan dibuat ulang dengan struktur baru.
- Jika ada data production, perlu migration strategy yang lebih hati-hati
- Backup database sebelum production deployment

### Breaking Changes
⚠️ **PERINGATAN**: Perubahan ini breaking changes untuk:
- Existing Address data (field structure berubah total)
- RajaOngkir integration (dihapus semua)
- Cart behavior (tambah selection feature)

### Testing Required
Setelah implementasi lengkap, perlu test:
- [ ] Cart dengan checkbox selection
- [ ] Multi-step checkout flow
- [ ] Address CRUD (Create, Read, Update, Delete)
- [ ] Profile photo upload
- [ ] Change password
- [ ] Buy It Now direct checkout
- [ ] Shipping cost calculation
- [ ] Order placement dengan selected items only

### Map Picker Implementation
Untuk Address Map Picker, ada beberapa opsi:
1. **Google Maps JavaScript API** (berbayar setelah trial)
2. **Leaflet.js + OpenStreetMap** (gratis)
3. **Mapbox** (freemium)

Rekomendasi: Gunakan **Leaflet.js** karena:
- ✅ Gratis dan open source
- ✅ Lightweight
- ✅ Easy to implement
- ✅ Support geocoding dengan plugin
- ✅ Mobile-friendly

---

## 🎯 PRIORITAS IMPLEMENTASI SELANJUTNYA

Urutan yang disarankan untuk menyelesaikan remaining work:

1. **HIGH PRIORITY - Must Have:**
   1. Update template keranjang dengan checkbox ✨
   2. Multi-step checkout (Step 1: Address) ✨
   3. Form tambah alamat di checkout ✨
   4. Update shipping views untuk new flow ✨

2. **MEDIUM PRIORITY - Should Have:**
   5. Multi-step checkout (Step 2 & 3)
   6. Update product detail page
   7. Buy It Now functionality
   8. Update profile template
   9. Change password functionality

3. **LOW PRIORITY - Nice to Have:**
   10. Map picker integration
   11. Advanced JavaScript features
   12. Static assets dan polish UI

---

## 📊 ESTIMASI WAKTU

Berdasarkan kompleksitas:
- ✅ **Sudah selesai**: ~40% dari total work
- ⏳ **Belum dikerjakan**: ~60% dari total work

Estimasi waktu untuk menyelesaikan remaining work:
- HIGH PRIORITY items: **4-6 jam**
- MEDIUM PRIORITY items: **3-4 jam**
- LOW PRIORITY items: **2-3 jam**

**Total estimasi**: **9-13 jam** untuk menyelesaikan semua

---

## 🚀 CARA MELANJUTKAN

Untuk developer yang melanjutkan:

1. **Start dengan cart template**:
   ```bash
   # Edit file ini
   nano kaloriz/templates/core/cart.html
   ```

2. **Kemudian checkout templates**:
   ```bash
   # Buat 3 file baru
   nano kaloriz/templates/core/checkout_address.html
   nano kaloriz/templates/core/checkout_payment.html
   nano kaloriz/templates/core/checkout_review.html
   ```

3. **Update views**:
   ```bash
   nano kaloriz/core/views.py
   ```

4. **Test setiap feature** setelah implementasi

5. **Commit secara incremental** per feature

---

## ✨ FITUR BARU YANG SUDAH BERFUNGSI

Meskipun UI belum diupdate, backend untuk fitur ini sudah siap:

1. ✅ **Cart Item Selection**
   - Model CartItem sudah punya field `is_selected`
   - Method `cart.get_selected_total()` tersedia
   - Method `cart.get_selected_items_count()` tersedia

2. ✅ **Profile Photo**
   - Model UserProfile sudah punya field `photo`
   - Method `profile.get_photo_url()` tersedia
   - Upload folder `profile_photos/` otomatis dibuat

3. ✅ **Simplified Address**
   - Address model sudah disederhanakan
   - Form validation sudah siap
   - Admin interface sudah sesuai

4. ✅ **Flat Rate Shipping**
   - District model sudah ada tarif REG & EXP
   - Function `calculate_shipping_cost()` sudah siap
   - Function `validate_shipping_data()` sudah siap

---

## 📞 KONTAK & SUPPORT

Jika ada pertanyaan atau kesulitan melanjutkan development:
- Cek dokumentasi Django: https://docs.djangoproject.com/
- Cek source code yang sudah dibuat (sudah ada comment)
- Model definitions di `*/models.py`
- View functions di `*/views.py`

---

**Terakhir diupdate**: 2025-10-25
**Status keseluruhan**: 40% Complete
**Next step**: Implement cart checkbox template
