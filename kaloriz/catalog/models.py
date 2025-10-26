from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nama Kategori")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name="Deskripsi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategori"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category_detail', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Kategori")
    name = models.CharField(max_length=200, verbose_name="Nama Produk")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(verbose_name="Deskripsi")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Harga")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Harga Diskon")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Gambar")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stok")
    available = models.BooleanField(default=True, verbose_name="Tersedia")

    # === FIELD PENGIRIMAN ===
    weight_gram = models.PositiveIntegerField(
        default=1000,
        verbose_name="Berat (gram)",
        help_text="Berat per unit (gram). Minimal 1000 gram untuk ongkir."
    )
    length_cm = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Panjang (cm)",
        help_text="Panjang (cm) – opsional"
    )
    width_cm = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Lebar (cm)",
        help_text="Lebar (cm) – opsional"
    )
    height_cm = models.PositiveIntegerField(
        default=0,
        blank=True,
        verbose_name="Tinggi (cm)",
        help_text="Tinggi (cm) – opsional"
    )
    is_fragile = models.BooleanField(
        default=False,
        verbose_name="Mudah Pecah",
        help_text="Mudah pecah (opsional)"
    )
    is_perishable = models.BooleanField(
        default=False,
        verbose_name="Mudah Rusak",
        help_text="Mudah rusak (opsional)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produk"
        verbose_name_plural = "Produk"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.slug])

    def get_display_price(self):
        """Return discount price if available, otherwise regular price"""
        return self.discount_price if self.discount_price else self.price

    def is_on_sale(self):
        """Check if product has a discount"""
        return self.discount_price is not None and self.discount_price < self.price

    def get_discount_percentage(self):
        """Calculate discount percentage"""
        if self.is_on_sale():
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0


class Testimonial(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='testimonials', verbose_name="Produk")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='testimonials', verbose_name="Pengguna")
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="Rating")
    review = models.TextField(verbose_name="Ulasan")
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True, verbose_name="Foto")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True, verbose_name="Disetujui")

    class Meta:
        verbose_name = "Testimoni"
        verbose_name_plural = "Testimoni"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class DiscountCode(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Kode")
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Nominal Diskon",
        help_text="Nilai potongan dalam rupiah",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Berlaku Sampai",
        help_text="Biarkan kosong jika tanpa batas waktu",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kode Diskon"
        verbose_name_plural = "Kode Diskon"
        ordering = ['-created_at']

    def __str__(self):
        return self.code.upper()

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expiry_date and self.expiry_date < timezone.now():
            return False
        return True
