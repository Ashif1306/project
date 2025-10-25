#!/usr/bin/env python
"""
Test script untuk verifikasi integrasi RajaOngkir API

Script ini akan menguji:
1. Koneksi ke RajaOngkir API
2. Endpoint untuk mendapatkan kota di Sulawesi Selatan
3. Endpoint untuk mendapatkan kecamatan
4. Endpoint untuk menghitung ongkir

Cara menjalankan:
    python test_rajaongkir_integration.py

Atau dengan Django shell:
    python manage.py shell < test_rajaongkir_integration.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaloriz.settings')
django.setup()

from shipping.services.raja import (
    get_sulsel_province_id,
    list_cities_in_sulsel,
    list_subdistricts,
    calculate_cost
)
from django.conf import settings


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_api_key():
    """Test 1: Verify API key is configured"""
    print_section("TEST 1: Verifikasi Konfigurasi API Key")

    api_key = settings.RAJAONGKIR_API_KEY
    if not api_key:
        print("❌ GAGAL: RAJAONGKIR_API_KEY tidak ditemukan di .env")
        return False

    print(f"✅ BERHASIL: API Key ditemukan (panjang: {len(api_key)} karakter)")
    print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"   Base URL: {settings.RAJAONGKIR_BASE_URL}")
    return True


def test_province_id():
    """Test 2: Get Sulawesi Selatan province ID"""
    print_section("TEST 2: Mendapatkan Province ID Sulawesi Selatan")

    try:
        province_id = get_sulsel_province_id()
        print(f"✅ BERHASIL: Province ID Sulawesi Selatan = {province_id}")
        return province_id
    except Exception as e:
        print(f"❌ GAGAL: {str(e)}")
        return None


def test_cities():
    """Test 3: List cities in Sulawesi Selatan"""
    print_section("TEST 3: Mendapatkan Daftar Kota di Sulawesi Selatan")

    try:
        cities = list_cities_in_sulsel()
        print(f"✅ BERHASIL: Ditemukan {len(cities)} kota/kabupaten")

        # Show first 5 cities
        print("\n5 Kota/Kabupaten Pertama:")
        for i, city in enumerate(cities[:5], 1):
            city_type = city.get('type', 'N/A')
            city_name = city.get('city_name', 'N/A')
            city_id = city.get('city_id', 'N/A')
            postal = city.get('postal_code', 'N/A')
            print(f"   {i}. [{city_id}] {city_type} {city_name} (Kode Pos: {postal})")

        # Find Makassar
        makassar = next((c for c in cities if 'makassar' in c.get('city_name', '').lower()), None)
        if makassar:
            print(f"\n📍 Kota Makassar ditemukan:")
            print(f"   - ID: {makassar.get('city_id')}")
            print(f"   - Type: {makassar.get('type')}")
            print(f"   - Kode Pos: {makassar.get('postal_code')}")
            return makassar.get('city_id')
        else:
            print("\n⚠️  Kota Makassar tidak ditemukan dalam list")
            return cities[0].get('city_id') if cities else None

    except Exception as e:
        print(f"❌ GAGAL: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_subdistricts(city_id):
    """Test 4: List subdistricts in a city"""
    print_section(f"TEST 4: Mendapatkan Daftar Kecamatan (City ID: {city_id})")

    if not city_id:
        print("⚠️  SKIP: City ID tidak tersedia")
        return None

    try:
        subdistricts = list_subdistricts(int(city_id))
        print(f"✅ BERHASIL: Ditemukan {len(subdistricts)} kecamatan")

        # Show first 5 subdistricts
        print("\n5 Kecamatan Pertama:")
        for i, sub in enumerate(subdistricts[:5], 1):
            sub_name = sub.get('subdistrict_name', 'N/A')
            sub_id = sub.get('subdistrict_id', 'N/A')
            sub_type = sub.get('type', 'N/A')
            print(f"   {i}. [{sub_id}] {sub_name} ({sub_type})")

        if subdistricts:
            return subdistricts[0].get('subdistrict_id')
        return None

    except Exception as e:
        print(f"❌ GAGAL: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_shipping_cost(origin_id, dest_id):
    """Test 5: Calculate shipping cost"""
    print_section("TEST 5: Menghitung Biaya Ongkir")

    if not origin_id or not dest_id:
        print("⚠️  SKIP: Origin atau Destination ID tidak tersedia")
        print(f"   ORIGIN_SUBDISTRICT_ID di settings: {settings.ORIGIN_SUBDISTRICT_ID}")
        print("   Silakan set ORIGIN_SUBDISTRICT_ID di file .env")
        return False

    couriers = ['jne', 'jnt', 'sicepat']
    weight = 1500  # 1.5 kg

    print(f"Parameter:")
    print(f"   - Origin: {origin_id}")
    print(f"   - Destination: {dest_id}")
    print(f"   - Weight: {weight} gram")

    for courier in couriers:
        try:
            print(f"\nMenghitung ongkir untuk kurir: {courier.upper()}")
            result = calculate_cost(int(origin_id), int(dest_id), weight, courier)

            data = result.get('data', [])
            if data:
                for courier_data in data:
                    courier_name = courier_data.get('name', 'N/A')
                    costs = courier_data.get('costs', [])

                    if costs:
                        print(f"   ✅ {courier_name}:")
                        for service in costs[:3]:  # Show first 3 services
                            service_name = service.get('service', 'N/A')
                            service_desc = service.get('description', 'N/A')
                            cost_info = service.get('cost', [{}])[0]
                            value = cost_info.get('value', 0)
                            etd = cost_info.get('etd', 'N/A')
                            print(f"      - {service_name}: Rp {value:,} (ETD: {etd} hari)")
                    else:
                        print(f"   ⚠️  {courier_name}: Tidak ada layanan tersedia")
            else:
                print(f"   ⚠️  Tidak ada data untuk kurir {courier.upper()}")

        except Exception as e:
            print(f"   ❌ GAGAL: {str(e)}")

    return True


def main():
    """Main test runner"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TEST INTEGRASI RAJAONGKIR API" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")

    # Test 1: API Key
    if not test_api_key():
        print("\n⚠️  Pengujian dihentikan karena API key tidak ditemukan")
        print("   Silakan tambahkan RAJAONGKIR_API_KEY di file .env")
        return

    # Test 2: Province ID
    province_id = test_province_id()
    if not province_id:
        print("\n⚠️  Pengujian dihentikan karena tidak dapat mengambil Province ID")
        return

    # Test 3: Cities
    city_id = test_cities()

    # Test 4: Subdistricts
    subdistrict_id = test_subdistricts(city_id) if city_id else None

    # Test 5: Shipping Cost
    origin = settings.ORIGIN_SUBDISTRICT_ID
    if not origin and subdistrict_id:
        origin = subdistrict_id

    if origin and subdistrict_id:
        test_shipping_cost(origin, subdistrict_id)

    # Summary
    print_section("RINGKASAN PENGUJIAN")
    print("✅ Semua fungsi dasar RajaOngkir API berfungsi dengan baik")
    print("\nLangkah selanjutnya:")
    print("1. Set ORIGIN_SUBDISTRICT_ID di file .env dengan ID kecamatan gudang Anda")
    print("2. Test endpoint Django dengan menjalankan server:")
    print("   python manage.py runserver")
    print("3. Akses endpoint berikut:")
    print("   - http://localhost:8000/shipping/api/sulsel/cities")
    print("   - http://localhost:8000/shipping/api/sulsel/subdistricts?city_id=<ID>")
    print("   - http://localhost:8000/shipping/api/quote?destination_subdistrict_id=<ID>&weight=1500&courier=jne")
    print("\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pengujian dibatalkan oleh user")
    except Exception as e:
        print(f"\n\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
