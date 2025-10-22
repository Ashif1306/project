#!/usr/bin/env python
"""
Simple test script to verify all endpoints are working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaloriz.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from catalog.models import Product, Category
from core.models import Cart, CartItem

def test_endpoints():
    """Test all major endpoints"""
    client = Client()
    results = []

    print("🧪 Testing E-Commerce Endpoints\n")
    print("="*60)

    # Test 1: Homepage
    print("\n1. Testing Homepage...")
    response = client.get('/')
    results.append(('Homepage', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 2: Product List
    print("\n2. Testing Product List...")
    response = client.get('/products/')
    results.append(('Product List', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 3: Product Detail
    print("\n3. Testing Product Detail...")
    product = Product.objects.first()
    if product:
        response = client.get(f'/product/{product.slug}/')
        results.append(('Product Detail', response.status_code == 200))
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
        print(f"   Product: {product.name}")
    else:
        results.append(('Product Detail', False))
        print("   ✗ FAIL - No products found")

    # Test 4: Category Detail
    print("\n4. Testing Category Detail...")
    category = Category.objects.first()
    if category:
        response = client.get(f'/category/{category.slug}/')
        results.append(('Category Detail', response.status_code == 200))
        print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")
        print(f"   Category: {category.name}")
    else:
        results.append(('Category Detail', False))
        print("   ✗ FAIL - No categories found")

    # Test 5: Search
    print("\n5. Testing Search...")
    response = client.get('/search/?q=laptop')
    results.append(('Search', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 6: Login Page
    print("\n6. Testing Login Page...")
    response = client.get('/login/')
    results.append(('Login Page', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 7: Register Page
    print("\n7. Testing Register Page...")
    response = client.get('/register/')
    results.append(('Register Page', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 8: Cart (requires login - should redirect)
    print("\n8. Testing Cart (Guest - should redirect)...")
    response = client.get('/cart/')
    results.append(('Cart Redirect', response.status_code == 302))
    print(f"   Status: {response.status_code} - {'✓ PASS (redirected to login)' if response.status_code == 302 else '✗ FAIL'}")

    # Test 9: Create test user and login
    print("\n9. Testing User Registration & Login...")
    username = 'testuser_auto'
    password = 'testpass123'

    # Check if user exists, if yes delete it
    User.objects.filter(username=username).delete()

    # Register
    response = client.post('/register/', {
        'username': username,
        'password1': password,
        'password2': password
    })

    if response.status_code == 302:  # Redirect after successful registration
        print("   ✓ Registration successful")
        results.append(('User Registration', True))

        # Test login
        login_success = client.login(username=username, password=password)
        results.append(('User Login', login_success))
        print(f"   Login: {'✓ PASS' if login_success else '✗ FAIL'}")
    else:
        results.append(('User Registration', False))
        results.append(('User Login', False))
        print("   ✗ Registration failed")

    # Test 10: Cart (logged in)
    print("\n10. Testing Cart (Logged In)...")
    response = client.get('/cart/')
    results.append(('Cart Logged In', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 11: Add to cart
    print("\n11. Testing Add to Cart...")
    if product:
        response = client.post(f'/cart/add/{product.id}/', {'quantity': 1})
        results.append(('Add to Cart', response.status_code == 302))
        print(f"   Status: {response.status_code} - {'✓ PASS (redirected)' if response.status_code == 302 else '✗ FAIL'}")
    else:
        results.append(('Add to Cart', False))
        print("   ✗ FAIL - No product available")

    # Test 12: Profile
    print("\n12. Testing User Profile...")
    response = client.get('/profile/')
    results.append(('User Profile', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 13: Orders
    print("\n13. Testing Orders Page...")
    response = client.get('/orders/')
    results.append(('Orders Page', response.status_code == 200))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code == 200 else '✗ FAIL'}")

    # Test 14: Admin (should be accessible)
    print("\n14. Testing Admin Page...")
    response = client.get('/admin/')
    results.append(('Admin Page', response.status_code in [200, 302]))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code in [200, 302] else '✗ FAIL'}")

    # Print Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {test_name}")

    print("="*60)
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All tests passed! Application is working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")

    return passed == total

if __name__ == '__main__':
    try:
        success = test_endpoints()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
