# Kaloriz - E-Commerce Website

Website e-commerce berbasis Django dengan fitur lengkap untuk toko online.

## Fitur

### Untuk Pelanggan
- 🏠 **Homepage** dengan produk unggulan
- 🛍️ **Katalog Produk** dengan filter dan pencarian
- 🔍 **Pencarian Produk** yang responsif
- 🛒 **Keranjang Belanja** interaktif
- 💳 **Checkout** dengan validasi stok
- 📦 **Riwayat Pesanan** dan tracking status
- 👤 **Profil Pengguna** untuk manajemen data

### Untuk Admin
- 📊 **Dashboard Admin** lengkap
- 📦 **Manajemen Produk** dengan upload gambar
- 📂 **Manajemen Kategori**
- 🛒 **Manajemen Pesanan** dengan update status
- 👥 **Manajemen Pengguna**

## Teknologi

- **Backend**: Django 5.2.7
- **Database**: SQLite (development)
- **Frontend**: Bootstrap 4.6.2, Font Awesome 6.4
- **Image Processing**: Pillow

## Instalasi

### 1. Clone Repository

```bash
git clone <repository-url>
cd project
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Database

```bash
cd kaloriz
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Populate Sample Data (Optional)

```bash
python populate_data.py
```

### 6. Run Development Server

```bash
python manage.py runserver
```

Aplikasi akan berjalan di `http://127.0.0.1:8000/`

## Default Admin Account

Setelah menjalankan `populate_data.py`, Anda bisa login dengan:

- **Username**: admin
- **Password**: admin123
- **Admin URL**: http://127.0.0.1:8000/admin/

## Struktur Project

```
project/
├── kaloriz/                # Main project folder
│   ├── catalog/            # Product catalog app
│   │   ├── models.py       # Product, Category models
│   │   ├── views.py        # Catalog views
│   │   ├── urls.py         # Catalog URLs
│   │   └── admin.py        # Admin configuration
│   ├── core/               # Core functionality app
│   │   ├── models.py       # Cart, Order, UserProfile models
│   │   ├── views.py        # Cart, Checkout, Auth views
│   │   ├── urls.py         # Core URLs
│   │   └── admin.py        # Admin configuration
│   ├── templates/          # HTML templates
│   │   ├── base.html       # Base template
│   │   ├── catalog/        # Catalog templates
│   │   └── core/           # Core templates
│   ├── static/             # Static files (CSS, JS, images)
│   │   └── css/            # Stylesheets
│   └── manage.py           # Django management script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Fitur Detail

### Models

**Catalog App:**
- `Category`: Kategori produk dengan slug auto-generate
- `Product`: Produk dengan harga, diskon, stok, dan gambar

**Core App:**
- `Cart`: Keranjang belanja per user
- `CartItem`: Item dalam keranjang
- `Order`: Pesanan dengan informasi pengiriman
- `OrderItem`: Item dalam pesanan
- `UserProfile`: Profil pengguna dengan alamat

### Views & URLs

**Catalog:**
- `/` - Homepage dengan produk unggulan
- `/products/` - Daftar semua produk
- `/product/<slug>/` - Detail produk
- `/category/<slug>/` - Produk per kategori
- `/search/` - Pencarian produk

**Core:**
- `/cart/` - Keranjang belanja
- `/checkout/` - Halaman checkout
- `/orders/` - Daftar pesanan
- `/order/<order_number>/` - Detail pesanan
- `/login/` - Login
- `/register/` - Registrasi
- `/profile/` - Profil pengguna

## Development

### Create New App

```bash
python manage.py startapp app_name
```

### Make Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

### Collect Static Files (Production)

```bash
python manage.py collectstatic
```

## Deployment Notes

Untuk production:

1. Set `DEBUG = False` di `settings.py`
2. Update `SECRET_KEY` dengan key yang aman
3. Configure `ALLOWED_HOSTS`
4. Setup database production (PostgreSQL/MySQL)
5. Setup static files serving
6. Setup media files serving
7. Enable HTTPS

## License

This project is created for educational purposes.

## Contact

For questions or support, please contact the development team.
