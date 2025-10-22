#!/usr/bin/env python
"""Populate database with sample data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaloriz.settings')
django.setup()

from catalog.models import Category, Product
from decimal import Decimal

# Create categories
categories_data = [
    {'name': 'Elektronik', 'description': 'Produk elektronik dan gadget'},
    {'name': 'Fashion', 'description': 'Pakaian dan aksesoris'},
    {'name': 'Makanan & Minuman', 'description': 'Produk makanan dan minuman'},
    {'name': 'Buku', 'description': 'Buku dan alat tulis'},
    {'name': 'Olahraga', 'description': 'Perlengkapan olahraga'},
]

print("Creating categories...")
for cat_data in categories_data:
    category, created = Category.objects.get_or_create(
        name=cat_data['name'],
        defaults={'description': cat_data['description']}
    )
    if created:
        print(f"  ✓ Created: {category.name}")
    else:
        print(f"  - Already exists: {category.name}")

# Create products
products_data = [
    # Elektronik
    {'category': 'Elektronik', 'name': 'Smartphone Android X1', 'description': 'Smartphone dengan kamera 48MP dan RAM 8GB', 'price': '3500000', 'discount_price': '3000000', 'stock': 15},
    {'category': 'Elektronik', 'name': 'Laptop Gaming Pro', 'description': 'Laptop gaming dengan GPU RTX dan SSD 512GB', 'price': '15000000', 'discount_price': '13500000', 'stock': 8},
    {'category': 'Elektronik', 'name': 'Wireless Earbuds', 'description': 'Earbuds wireless dengan noise cancelling', 'price': '750000', 'stock': 25},

    # Fashion
    {'category': 'Fashion', 'name': 'Kaos Cotton Premium', 'description': 'Kaos berbahan cotton 100% nyaman dipakai', 'price': '150000', 'discount_price': '120000', 'stock': 50},
    {'category': 'Fashion', 'name': 'Jaket Hoodie', 'description': 'Jaket hoodie hangat untuk segala aktivitas', 'price': '350000', 'stock': 30},
    {'category': 'Fashion', 'name': 'Sepatu Sneakers', 'description': 'Sepatu sneakers casual dan nyaman', 'price': '450000', 'discount_price': '380000', 'stock': 20},

    # Makanan & Minuman
    {'category': 'Makanan & Minuman', 'name': 'Kopi Arabica Premium 250g', 'description': 'Kopi arabica pilihan dari pegunungan', 'price': '120000', 'stock': 40},
    {'category': 'Makanan & Minuman', 'name': 'Madu Murni 500ml', 'description': 'Madu murni asli tanpa campuran', 'price': '85000', 'discount_price': '75000', 'stock': 35},

    # Buku
    {'category': 'Buku', 'name': 'Buku Pemrograman Python', 'description': 'Panduan lengkap belajar Python dari dasar', 'price': '180000', 'stock': 25},
    {'category': 'Buku', 'name': 'Novel Best Seller', 'description': 'Novel terlaris tahun ini', 'price': '95000', 'discount_price': '80000', 'stock': 45},

    # Olahraga
    {'category': 'Olahraga', 'name': 'Matras Yoga', 'description': 'Matras yoga anti slip dengan tas pembawa', 'price': '200000', 'stock': 18},
    {'category': 'Olahraga', 'name': 'Dumbbell Set 5kg', 'description': 'Set dumbbell untuk home workout', 'price': '350000', 'discount_price': '300000', 'stock': 12},
]

print("\nCreating products...")
for prod_data in products_data:
    category = Category.objects.get(name=prod_data['category'])

    # Check if product already exists
    if Product.objects.filter(name=prod_data['name']).exists():
        print(f"  - Already exists: {prod_data['name']}")
        continue

    product = Product.objects.create(
        category=category,
        name=prod_data['name'],
        description=prod_data['description'],
        price=Decimal(prod_data['price']),
        discount_price=Decimal(prod_data['discount_price']) if 'discount_price' in prod_data else None,
        stock=prod_data['stock'],
        available=True
    )
    print(f"  ✓ Created: {product.name} - Rp {product.price}")

print("\n✓ Database populated successfully!")
print(f"\nTotal Categories: {Category.objects.count()}")
print(f"Total Products: {Product.objects.count()}")
