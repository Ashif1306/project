from django.contrib import admin
from .models import District, Address, Shipment


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    """
    Admin interface untuk mengelola kecamatan dan tarif pengiriman
    """
    list_display = [
        'name',
        'reg_cost_display',
        'exp_cost_display',
        'eta_reg',
        'eta_exp',
        'is_active',
        'updated_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    ordering = ['name']

    fieldsets = (
        ('Informasi Kecamatan', {
            'fields': ('name', 'is_active')
        }),
        ('Tarif Reguler', {
            'fields': ('reg_cost', 'eta_reg'),
            'description': 'Pengiriman reguler (2-3 hari kerja)'
        }),
        ('Tarif Express', {
            'fields': ('exp_cost', 'eta_exp'),
            'description': 'Pengiriman express (1 hari kerja)'
        }),
    )

    def reg_cost_display(self, obj):
        return f"Rp {obj.reg_cost:,.0f}"
    reg_cost_display.short_description = 'Tarif Reguler'

    def exp_cost_display(self, obj):
        return f"Rp {obj.exp_cost:,.0f}"
    exp_cost_display.short_description = 'Tarif Express'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """
    Admin interface untuk mengelola alamat pelanggan
    """
    list_display = [
        'full_name',
        'user',
        'phone',
        'subdistrict_name',
        'destination_subdistrict_id',
        'postal_code',
        'is_primary',
        'is_default',
        'created_at'
    ]
    list_filter = ['is_primary', 'is_default', 'province_name', 'city_name', 'created_at']
    search_fields = ['full_name', 'user__username', 'user__email', 'phone', 'address_line', 'subdistrict_name', 'city_name']
    list_select_related = ['user']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Pemilik', {
            'fields': ('user',)
        }),
        ('Identitas Penerima', {
            'fields': ('full_name', 'phone')
        }),
        ('Alamat Tujuan (RajaOngkir)', {
            'fields': (
                'address_line',
                'province_name', 'city_name', 'subdistrict_name', 'destination_subdistrict_id',
                'postal_code'
            ),
            'description': 'Field untuk integrasi RajaOngkir API'
        }),
        ('Alamat Lama (Legacy)', {
            'fields': ('street', 'district'),
            'classes': ('collapse',),
            'description': 'Field lama - untuk backward compatibility'
        }),
        ('Status', {
            'fields': ('is_primary', 'is_default')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    """
    Admin interface untuk mengelola pengiriman
    """
    list_display = [
        'order_number',
        'full_name',
        'district_name',
        'service_display',
        'cost_display',
        'eta',
        'tracking_number',
        'created_at'
    ]
    list_filter = ['service', 'created_at']
    search_fields = [
        'order__order_number',
        'full_name',
        'phone',
        'district_name',
        'tracking_number'
    ]
    list_select_related = ['order']
    readonly_fields = ['order', 'created_at', 'updated_at']

    fieldsets = (
        ('Pesanan', {
            'fields': ('order',)
        }),
        ('Alamat Pengiriman', {
            'fields': ('full_name', 'phone', 'street', 'district_name', 'postal_code')
        }),
        ('Detail Pengiriman', {
            'fields': ('service', 'cost', 'eta')
        }),
        ('Tracking', {
            'fields': ('tracking_number',)
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Nomor Pesanan'
    order_number.admin_order_field = 'order__order_number'

    def service_display(self, obj):
        return obj.get_service_display()
    service_display.short_description = 'Layanan'

    def cost_display(self, obj):
        return f"Rp {obj.cost:,.0f}"
    cost_display.short_description = 'Biaya'
