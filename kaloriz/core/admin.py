from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, UserProfile, Watchlist

admin.site.site_header = "Kaloriz Admin"
admin.site.site_title = "Kaloriz Admin"
admin.site.index_title = "Dashboard"


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
