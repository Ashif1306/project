from django.contrib import admin
from .models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    PaymentMethod,
    PaymentTransaction,
    UserProfile,
    Watchlist,
    EmailVerification,
)

admin.site.site_header = "Kaloriz Admin"
admin.site.site_title = "Kaloriz Admin"
admin.site.index_title = "Dashboard"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'display_order', 'updated_at']
    list_editable = ['is_active', 'display_order']
    search_fields = ['name', 'slug', 'description']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        (
            'Informasi Utama',
            {
                'fields': (
                    'name',
                    'slug',
                    'tagline',
                    'description',
                    'additional_info',
                )
            },
        ),
        (
            'Tampilan',
            {
                'fields': (
                    'logo',
                    'button_label',
                    'display_order',
                    'is_active',
                )
            },
        ),
        (
            'Metadata',
            {
                'classes': ('collapse',),
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at', 'get_total_items']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at']

    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_price', 'quantity', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'full_name', 'status', 'total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__username', 'full_name', 'email', 'phone']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informasi Pesanan', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Informasi Pengiriman', {
            'fields': ('full_name', 'email', 'phone', 'address', 'city', 'postal_code')
        }),
        ('Total', {
            'fields': ('subtotal', 'shipping_cost', 'total')
        }),
        ('Catatan', {
            'fields': ('notes',)
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'gender', 'birth_date', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    list_filter = ['gender', 'created_at']


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used', 'ip_address']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'code']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'order',
        'payment_method',
        'transaction_status',
        'gross_amount',
        'payment_type',
        'created_at',
    ]
    list_filter = ['transaction_status', 'fraud_status', 'payment_type', 'created_at']
    search_fields = [
        'transaction_id',
        'order__order_number',
        'order__user__username',
        'order__email',
    ]
    readonly_fields = [
        'transaction_id',
        'snap_token',
        'payment_type',
        'transaction_status',
        'fraud_status',
        'status_code',
        'signature_key',
        'response_midtrans',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        (
            'Informasi Transaksi',
            {
                'fields': (
                    'order',
                    'payment_method',
                    'transaction_id',
                    'snap_token',
                    'gross_amount',
                )
            },
        ),
        (
            'Status Pembayaran',
            {
                'fields': (
                    'transaction_status',
                    'fraud_status',
                    'payment_type',
                    'status_code',
                )
            },
        ),
        (
            'Verifikasi',
            {
                'classes': ('collapse',),
                'fields': ('signature_key',),
            },
        ),
        (
            'Response Midtrans',
            {
                'classes': ('collapse',),
                'fields': ('response_midtrans',),
            },
        ),
        (
            'Timestamp',
            {
                'fields': ('created_at', 'updated_at'),
            },
        ),
    )

    def has_add_permission(self, request):
        # Prevent manual creation of payment transactions
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of payment transactions
        return False
