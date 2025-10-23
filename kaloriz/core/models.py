from django.db import models
from django.contrib.auth.models import User
from catalog.models import Product
from decimal import Decimal

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts', verbose_name="Pengguna")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Keranjang"
        verbose_name_plural = "Keranjang"

    def __str__(self):
        return f"Keranjang - {self.user.username}"

    def get_total(self):
        """Calculate total price of all items in cart"""
        return sum(item.get_subtotal() for item in self.items.all())

    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Keranjang")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Produk")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Jumlah")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Item Keranjang"
        verbose_name_plural = "Item Keranjang"
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.get_display_price() * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu Pembayaran'),
        ('processing', 'Diproses'),
        ('shipped', 'Dikirim'),
        ('delivered', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name="Pengguna")
    order_number = models.CharField(max_length=100, unique=True, verbose_name="Nomor Pesanan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")

    # Shipping information
    full_name = models.CharField(max_length=200, verbose_name="Nama Lengkap")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Nomor Telepon")
    address = models.TextField(verbose_name="Alamat")
    city = models.CharField(max_length=100, verbose_name="Kota")
    postal_code = models.CharField(max_length=10, verbose_name="Kode Pos")

    # Order totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ongkir")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total")

    # Additional info
    notes = models.TextField(blank=True, verbose_name="Catatan")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pesanan"
        verbose_name_plural = "Pesanan"
        ordering = ['-created_at']

    def __str__(self):
        return f"Pesanan #{self.order_number}"

    def get_status_display_class(self):
        """Return CSS class for status badge"""
        status_classes = {
            'pending': 'warning',
            'processing': 'info',
            'shipped': 'primary',
            'delivered': 'success',
            'cancelled': 'danger',
        }
        return status_classes.get(self.status, 'secondary')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Pesanan")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Produk")
    product_name = models.CharField(max_length=200, verbose_name="Nama Produk")
    product_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Harga Produk")
    quantity = models.PositiveIntegerField(verbose_name="Jumlah")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")

    class Meta:
        verbose_name = "Item Pesanan"
        verbose_name_plural = "Item Pesanan"

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Laki-laki'),
        ('F', 'Perempuan'),
        ('O', 'Lainnya'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Pengguna")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Nomor Telepon")
    address = models.TextField(blank=True, verbose_name="Alamat")
    city = models.CharField(max_length=100, blank=True, verbose_name="Kota")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Kode Pos")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name="Jenis Kelamin")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tanggal Lahir")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Pengguna"
        verbose_name_plural = "Profil Pengguna"

    def __str__(self):
        return f"Profil - {self.user.username}"


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists', verbose_name="Pengguna")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='watchlisted_by', verbose_name="Produk")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Watchlist"
        verbose_name_plural = "Watchlist"
        unique_together = ['user', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
