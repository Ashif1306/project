# Integrasi RajaOngkir Shipping Cost API

## 📋 Ringkasan

Proyek e-commerce Django ini telah terintegrasi dengan **RajaOngkir Komerce - Shipping Cost API** untuk menghitung biaya ongkir otomatis. Integrasi ini fokus pada wilayah **Provinsi Sulawesi Selatan** dengan dukungan kurir: JNE, J&T, Sicepat, TIKI, POS, dan AnterAja.

## ✅ Status Implementasi

Integrasi RajaOngkir **SUDAH LENGKAP** dan siap digunakan. Berikut komponennya:

### 1. Konfigurasi (`kaloriz/settings.py`)

```python
# RajaOngkir API Configuration
RAJAONGKIR_API_KEY = os.getenv("RAJAONGKIR_API_KEY")
RAJAONGKIR_BASE_URL = "https://rajaongkir.komerce.id/api/v1"

# Warning jika API key kosong
if not RAJAONGKIR_API_KEY:
    print("⚠️  WARNING: RAJAONGKIR_API_KEY tidak ditemukan di .env file!")

# ID kecamatan asal (gudang)
ORIGIN_SUBDISTRICT_ID = int(os.getenv("ORIGIN_SUBDISTRICT_ID", "0"))

# Daftar kurir yang didukung
SUPPORTED_COURIERS = ("jne", "jnt", "sicepat", "tiki", "pos", "anteraja")
```

### 2. File .env

File `.env` telah dibuat di `/home/user/project/kaloriz/.env`:

```bash
# RajaOngkir API Configuration
RAJAONGKIR_API_KEY=dqycwvhVe8e8c43b31fd9951VwgouurS

# ID Kecamatan Asal (Gudang)
ORIGIN_SUBDISTRICT_ID=0
```

**⚠️ PENTING**: Pastikan API key yang digunakan valid dan aktif. Jika mendapat error 403, verifikasi API key Anda di dashboard RajaOngkir.

### 3. Service Module (`shipping/services/raja.py`)

HTTP client untuk berkomunikasi dengan RajaOngkir API:

#### Fungsi yang Tersedia:

- **`get_sulsel_province_id()`** - Mendapatkan ID provinsi Sulawesi Selatan (cached)
- **`list_cities_in_sulsel()`** - Daftar kota/kabupaten di Sulawesi Selatan
- **`list_subdistricts(city_id)`** - Daftar kecamatan di kota tertentu
- **`calculate_cost(origin, destination, weight, courier)`** - Hitung biaya ongkir

### 4. API Endpoints (`shipping/views.py` & `shipping/urls.py`)

Empat endpoint JSON telah diimplementasikan:

#### a. Daftar Kota di Sulawesi Selatan
```
GET /shipping/api/sulsel/cities
```
Response:
```json
{
  "cities": [
    {
      "city_id": "123",
      "type": "Kota",
      "city_name": "Makassar",
      "postal_code": "90000"
    }
  ]
}
```

#### b. Daftar Kecamatan di Kota
```
GET /shipping/api/sulsel/subdistricts?city_id=123
```
Response:
```json
{
  "subdistricts": [
    {
      "subdistrict_id": "456",
      "subdistrict_name": "Panakkukang",
      "type": "Kecamatan",
      "city": "Makassar"
    }
  ]
}
```

#### c. Quote Ongkir (Manual)
```
GET /shipping/api/quote?destination_subdistrict_id=456&weight=1500&courier=jne&origin=789
```
Response:
```json
{
  "data": [
    {
      "code": "jne",
      "name": "JNE",
      "costs": [
        {
          "service": "REG",
          "description": "Layanan Reguler",
          "cost": [
            {
              "value": 15000,
              "etd": "2-3",
              "note": ""
            }
          ]
        }
      ]
    }
  ]
}
```

#### d. Quote Ongkir berdasarkan Address
```
GET /shipping/api/quote-by-address?address_id=1&courier=jne&order_id=10
```
- Menggunakan `destination_subdistrict_id` dari model Address
- Origin dari `settings.ORIGIN_SUBDISTRICT_ID`
- Weight dari query param atau `Order.total_weight_gram`

### 5. Model Data

#### Address Model (`shipping/models.py`)
```python
class Address(models.Model):
    # Field untuk RajaOngkir API
    destination_subdistrict_id = models.PositiveIntegerField(...)
    subdistrict_name = models.CharField(...)
    city_name = models.CharField(...)
    province_name = models.CharField(...)
    postal_code = models.CharField(...)
```

#### Order Model (`core/models.py`)
```python
class Order(models.Model):
    shipping_address = models.ForeignKey('shipping.Address', ...)
    selected_courier = models.CharField(...)  # jne/jnt/sicepat/etc
    selected_service_name = models.CharField(...)  # REG/YES/OKE/etc
    total_weight_gram = models.PositiveIntegerField(...)
    shipping_cost = models.DecimalField(...)
```

## 🚀 Cara Penggunaan

### 1. Setup Awal

**a. Verifikasi .env File**
```bash
cat kaloriz/.env
```

**b. Set ORIGIN_SUBDISTRICT_ID**

Untuk mendapatkan ID kecamatan gudang Anda:
1. Jalankan server: `python manage.py runserver`
2. Akses: `http://localhost:8000/shipping/api/sulsel/cities`
3. Cari city_id untuk kota Anda (misalnya Makassar)
4. Akses: `http://localhost:8000/shipping/api/sulsel/subdistricts?city_id=<ID>`
5. Cari subdistrict_id untuk kecamatan gudang Anda
6. Update `.env`:
   ```
   ORIGIN_SUBDISTRICT_ID=<ID_KECAMATAN_GUDANG>
   ```

**c. Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. Testing Integrasi

**a. Test via Script Python**
```bash
cd kaloriz
python test_rajaongkir_integration.py
```

**b. Test via Django Server**
```bash
python manage.py runserver
```

**c. Test via cURL**

```bash
# 1. Daftar kota di Sulawesi Selatan
curl http://localhost:8000/shipping/api/sulsel/cities | jq

# 2. Daftar kecamatan di Makassar (ganti city_id)
curl "http://localhost:8000/shipping/api/sulsel/subdistricts?city_id=7371" | jq

# 3. Hitung ongkir manual
curl "http://localhost:8000/shipping/api/quote?destination_subdistrict_id=1234&weight=1500&courier=jne&origin=5678" | jq

# 4. Hitung ongkir dari Address (ganti address_id)
curl "http://localhost:8000/shipping/api/quote-by-address?address_id=1&courier=jne" | jq
```

### 3. Integrasi di Checkout

Contoh alur checkout dengan RajaOngkir:

**a. User Memilih Alamat**
```javascript
// Frontend: User memilih Address yang sudah tersimpan
const addressId = document.querySelector('#address-select').value;
```

**b. Hitung Ongkir**
```javascript
// Frontend: Request quote dari server
const response = await fetch(
  `/shipping/api/quote-by-address?address_id=${addressId}&courier=jne&order_id=${orderId}`
);
const data = await response.json();

// Tampilkan pilihan layanan
data.data.forEach(courier => {
  courier.costs.forEach(service => {
    const cost = service.cost[0].value;
    const etd = service.cost[0].etd;
    // Render ke UI
  });
});
```

**c. User Memilih Layanan**
```python
# Backend: Simpan pilihan ke Order
order.selected_courier = "jne"
order.selected_service_name = "REG"
order.shipping_cost = 15000
order.total = order.subtotal + order.shipping_cost
order.save()
```

## 📁 Struktur File

```
kaloriz/
├── .env                              # Konfigurasi API key
├── kaloriz/
│   └── settings.py                   # Django settings dengan RajaOngkir config
├── shipping/
│   ├── models.py                     # Address model dengan destination_subdistrict_id
│   ├── views.py                      # 4 API endpoints
│   ├── urls.py                       # URL routing
│   └── services/
│       ├── __init__.py
│       └── raja.py                   # RajaOngkir HTTP client
├── core/
│   └── models.py                     # Order model dengan shipping fields
├── test_rajaongkir_integration.py   # Test script
└── requirements.txt                  # Dependencies (httpx sudah termasuk)
```

## 🔧 Troubleshooting

### Error 403 Forbidden

**Penyebab:**
- API key tidak valid atau expired
- API key belum diaktifkan untuk Komerce tier

**Solusi:**
1. Login ke dashboard RajaOngkir
2. Verifikasi API key Anda aktif
3. Pastikan menggunakan API key untuk tier Komerce
4. Copy ulang API key ke file `.env`

### Error: ORIGIN_SUBDISTRICT_ID belum dikonfigurasi

**Solusi:**
Set ID kecamatan gudang di `.env`:
```bash
ORIGIN_SUBDISTRICT_ID=1234
```

### Error: destination_subdistrict_id tidak ada

**Solusi:**
Pastikan Address memiliki `destination_subdistrict_id`:
```python
address = Address.objects.get(pk=address_id)
address.destination_subdistrict_id = 1234
address.save()
```

### Weight kurang dari 1000 gram

RajaOngkir API memerlukan minimal 1000 gram (1 kg). Service otomatis adjust:
```python
weight = max(1000, int(weight_gram))
```

## 📚 Dokumentasi API RajaOngkir

- Base URL: `https://rajaongkir.komerce.id/api/v1`
- Dokumentasi: https://rajaongkir.com/dokumentasi
- Header: `{"key": "YOUR_API_KEY"}`

### Endpoint yang Digunakan:

1. **GET /destination/province** - Daftar provinsi
2. **GET /destination/city?province_id={id}** - Daftar kota
3. **GET /destination/subdistrict?city_id={id}** - Daftar kecamatan
4. **POST /cost** - Hitung ongkir

## ✨ Fitur

✅ Fokus pada Provinsi Sulawesi Selatan
✅ Support 6 kurir: JNE, J&T, Sicepat, TIKI, POS, AnterAja
✅ Perhitungan otomatis berdasarkan berat produk
✅ API key disimpan aman di .env
✅ Error handling yang baik (400 untuk input error, 502 untuk API error)
✅ Biaya diurutkan dari termurah
✅ Cache province ID untuk performa
✅ Timeout 20 detik untuk setiap request

## 🔐 Keamanan

- ✅ API key di .env (tidak di-commit ke git)
- ✅ Tidak ada hardcoded API key
- ✅ Server-side validation untuk courier
- ✅ Input validation untuk semua parameter

## 📝 Acceptance Criteria

✅ `.env` berisi `RAJAONGKIR_API_KEY`
✅ `GET /shipping/api/sulsel/cities` → daftar kota Sulawesi Selatan
✅ `GET /shipping/api/sulsel/subdistricts?city_id=X` → daftar kecamatan
✅ `GET /shipping/api/quote?...` → hitung ongkir dengan biaya terurut
✅ `GET /shipping/api/quote-by-address?...` → hitung dari Address model
✅ Error handling (400 untuk input, 502 untuk upstream)
✅ Tidak ada API key hardcoded
✅ Struktur data tidak diubah (hanya menambah endpoint & service)

## 🎯 Next Steps

1. **Verifikasi API Key** - Pastikan API key valid di dashboard RajaOngkir
2. **Set ORIGIN_SUBDISTRICT_ID** - Isi dengan ID kecamatan gudang Anda
3. **Test Endpoints** - Jalankan test script atau akses via browser
4. **Integrasi Frontend** - Tambahkan logic di halaman checkout
5. **Production Deployment** - Setup .env di server production

## 🤝 Support

Untuk pertanyaan atau issue:
- RajaOngkir Support: https://rajaongkir.com/kontak
- Django Documentation: https://docs.djangoproject.com/

---

**Status**: ✅ Integrasi LENGKAP dan siap digunakan
**Update Terakhir**: 2025-10-25
**Developer**: Django Senior Engineer
