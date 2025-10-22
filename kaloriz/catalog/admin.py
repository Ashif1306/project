from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'available', 'created_at']
    list_filter = ['available', 'category', 'created_at']
    list_editable = ['price', 'discount_price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Harga & Stok', {
            'fields': ('price', 'discount_price', 'stock', 'available')
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )
