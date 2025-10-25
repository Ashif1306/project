from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class District(models.Model):
    """
    Model untuk kecamatan di Makassar dengan tarif pengiriman.
    Origin: Universitas Negeri Makassar (UNM), Jl. AP Pettarani
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Kecamatan")

    # Tarif Reguler (2-3 hari)
    reg_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Tarif Reguler (Rp)",
        help_text="Estimasi 2-3 hari kerja"
    )

    # Tarif Express (1 hari)
    exp_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Tarif Express (Rp)",
        help_text="Estimasi 1 hari kerja"
    )

    # Estimasi waktu pengiriman
    eta_reg = models.CharField(
        max_length=50,
        default="2-3 hari kerja",
        verbose_name="ETA Reguler"
    )
    eta_exp = models.CharField(
        max_length=50,
        default="1 hari kerja",
        verbose_name="ETA Express"
    )

    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kecamatan"
        verbose_name_plural = "Kecamatan"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Address(models.Model):
    """
    Model untuk alamat pengiriman pelanggan dengan dukungan RajaOngkir API
    """
    # Validator nomor HP Indonesia
    phone_validator = RegexValidator(
        regex=r'^(\+62|62|0)[0-9]{9,12}$',
        message="Nomor telepon harus berformat Indonesia (contoh: 08123456789 atau +628123456789)"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name="Pengguna"
    )
    full_name = models.CharField(max_length=120, verbose_name="Nama Lengkap")
    phone = models.CharField(
        max_length=30,
        validators=[phone_validator],
        verbose_name="Nomor Telepon"
    )
    address_line = models.CharField(max_length=255, blank=True, verbose_name="Alamat/Jalan")

    # === FIELD UNTUK RAJAONGKIR API ===
    # Wajib untuk ongkir: simpan ID kecamatan tujuan (nanti dipakai ke API)
    destination_subdistrict_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID Kecamatan Tujuan",
        help_text="ID kecamatan tujuan (RajaOngkir)."
    )

    # Opsional untuk tampilan/validasi
    subdistrict_name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Kecamatan",
        help_text="ex: Panakkukang"
    )
    city_name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Kota",
        help_text="ex: Makassar"
    )
    province_name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Provinsi",
        help_text="Set 'Sulawesi Selatan' saat simpan"
    )
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Kode Pos")

    # === BACKWARD COMPATIBILITY ===
    # Untuk data lama yang masih menggunakan District lokal
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Kecamatan (Lokal)",
        help_text="Legacy field - gunakan destination_subdistrict_id untuk RajaOngkir"
    )
    street = models.TextField(blank=True, verbose_name="Alamat/Jalan (Legacy)")

    is_default = models.BooleanField(default=False, verbose_name="Alamat Utama")
    is_primary = models.BooleanField(default=True, verbose_name="Alamat Primary")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alamat"
        verbose_name_plural = "Alamat"
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]

    def __str__(self):
        location = self.subdistrict_name or (self.district.name if self.district else 'N/A')
        return f"{self.full_name} — {location}"

    def save(self, *args, **kwargs):
        """
        Pastikan hanya ada satu alamat default/primary per user
        """
        if self.is_default:
            # Set semua alamat user lain jadi non-default
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        if self.is_primary:
            # Set semua alamat user lain jadi non-primary
            Address.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class Shipment(models.Model):
    """
    Model untuk data pengiriman di setiap order
    """
    SERVICE_CHOICES = [
        ('REG', 'Reguler'),
        ('EXP', 'Express'),
    ]

    order = models.OneToOneField(
        'core.Order',  # Relasi ke Order model yang sudah ada
        on_delete=models.CASCADE,
        related_name='shipment',
        verbose_name="Pesanan"
    )

    # Data alamat (snapshot saat order dibuat)
    full_name = models.CharField(max_length=200, verbose_name="Nama Penerima")
    phone = models.CharField(max_length=20, verbose_name="Telepon")
    street = models.TextField(verbose_name="Alamat")
    district_name = models.CharField(max_length=100, verbose_name="Kecamatan")
    postal_code = models.CharField(max_length=10, verbose_name="Kode Pos")

    # Service dan biaya (snapshot saat order)
    service = models.CharField(
        max_length=3,
        choices=SERVICE_CHOICES,
        verbose_name="Layanan Pengiriman"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Biaya Pengiriman"
    )
    eta = models.CharField(max_length=50, verbose_name="Estimasi Pengiriman")

    # Tracking
    tracking_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Nomor Resi"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pengiriman"
        verbose_name_plural = "Pengiriman"
        ordering = ['-created_at']

    def __str__(self):
        return f"Pengiriman #{self.order.order_number} - {self.get_service_display()}"

    def get_service_label(self):
        """Return label untuk display"""
        return self.get_service_display()
