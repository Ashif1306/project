from django.contrib import admin
from .models import Category, Product, Testimonial

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'weight_gram', 'is_fragile', 'is_perishable', 'available', 'created_at']
    list_filter = ['available', 'is_fragile', 'is_perishable', 'category', 'created_at']
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
            'fields': (
                'price', 'discount_price', 'stock', 'available',
                'weight_gram', 'length_cm', 'width_cm', 'height_cm',
                'is_fragile', 'is_perishable',
            )
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['user__username', 'product__name', 'review']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_approved']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informasi Testimoni', {
            'fields': ('product', 'user', 'rating', 'review', 'photo', 'is_approved')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at')
        }),
    )
