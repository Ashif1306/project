#!/usr/bin/env python
"""Test script for new pages (Home with banner, About, Contact)"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaloriz.settings')
django.setup()

from django.test import Client

def test_new_pages():
    """Test all new pages"""
    client = Client()
    results = []

    print("🧪 Testing New Pages\n")
    print("="*60)

    # Test 1: Homepage (with new banner)
    print("\n1. Testing Homepage with Banner...")
    response = client.get('/')
    results.append(('Homepage with Banner', response.status_code == 200))
    if response.status_code == 200:
        content = response.content.decode()
        has_banner = 'hero-banner' in content
        has_stats = 'stats-section' in content
        results.append(('Homepage - Banner Section', has_banner))
        results.append(('Homepage - Stats Section', has_stats))
        print(f"   Status: 200 - ✓ PASS")
        print(f"   Banner Section: {'✓ Found' if has_banner else '✗ Not Found'}")
        print(f"   Stats Section: {'✓ Found' if has_stats else '✗ Not Found'}")
    else:
        print(f"   Status: {response.status_code} - ✗ FAIL")

    # Test 2: About Page
    print("\n2. Testing About Page...")
    response = client.get('/about/')
    results.append(('About Page', response.status_code == 200))
    if response.status_code == 200:
        content = response.content.decode()
        has_mission = 'Misi Kami' in content
        has_vision = 'Visi Kami' in content
        has_team = 'Tim Kami' in content
        results.append(('About - Mission Section', has_mission))
        results.append(('About - Vision Section', has_vision))
        results.append(('About - Team Section', has_team))
        print(f"   Status: 200 - ✓ PASS")
        print(f"   Mission Section: {'✓ Found' if has_mission else '✗ Not Found'}")
        print(f"   Vision Section: {'✓ Found' if has_vision else '✗ Not Found'}")
        print(f"   Team Section: {'✓ Found' if has_team else '✗ Not Found'}")
    else:
        print(f"   Status: {response.status_code} - ✗ FAIL")

    # Test 3: Contact Page
    print("\n3. Testing Contact Page...")
    response = client.get('/contact/')
    results.append(('Contact Page', response.status_code == 200))
    if response.status_code == 200:
        content = response.content.decode()
        has_form = 'contactForm' in content
        has_info = 'Informasi Kontak' in content
        has_faq = 'Pertanyaan yang Sering Diajukan' in content
        results.append(('Contact - Form', has_form))
        results.append(('Contact - Info', has_info))
        results.append(('Contact - FAQ', has_faq))
        print(f"   Status: 200 - ✓ PASS")
        print(f"   Contact Form: {'✓ Found' if has_form else '✗ Not Found'}")
        print(f"   Contact Info: {'✓ Found' if has_info else '✗ Not Found'}")
        print(f"   FAQ Section: {'✓ Found' if has_faq else '✗ Not Found'}")
    else:
        print(f"   Status: {response.status_code} - ✗ FAIL")

    # Test 4: Contact Form Submission
    print("\n4. Testing Contact Form Submission...")
    response = client.post('/contact/', {
        'name': 'Test User',
        'email': 'test@example.com',
        'phone': '081234567890',
        'subject': 'pertanyaan_produk',
        'message': 'This is a test message'
    })
    results.append(('Contact Form Submission', response.status_code in [200, 302]))
    print(f"   Status: {response.status_code} - {'✓ PASS' if response.status_code in [200, 302] else '✗ FAIL'}")

    # Test 5: Navbar Links
    print("\n5. Testing Navbar Links...")
    response = client.get('/')
    if response.status_code == 200:
        content = response.content.decode()
        has_about_link = 'catalog:about' in content
        has_contact_link = 'catalog:contact' in content
        results.append(('Navbar - About Link', has_about_link))
        results.append(('Navbar - Contact Link', has_contact_link))
        print(f"   About Link: {'✓ Found' if has_about_link else '✗ Not Found'}")
        print(f"   Contact Link: {'✓ Found' if has_contact_link else '✗ Not Found'}")

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
        print("🎉 All tests passed! New pages are working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")

    return passed == total

if __name__ == '__main__':
    try:
        success = test_new_pages()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
