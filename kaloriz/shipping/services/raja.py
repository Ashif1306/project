"""
RajaOngkir API Client untuk Shipping Cost Calculation

Endpoint yang digunakan:
- GET /destination/province - Daftar provinsi
- GET /destination/city - Daftar kota/kabupaten
- GET /destination/subdistrict - Daftar kecamatan
- POST /cost - Perhitungan biaya ongkir

Dokumentasi: https://rajaongkir.komerce.id/documentation
"""

import httpx
from functools import lru_cache
from django.conf import settings


BASE = settings.RAJAONGKIR_BASE_URL


def _headers():
    """Return headers dengan API key untuk RajaOngkir"""
    return {"key": settings.RAJAONGKIR_API_KEY}


@lru_cache(maxsize=1)
def get_sulsel_province_id() -> int:
    """
    Mendapatkan province_id untuk Sulawesi Selatan.

    Hasil di-cache karena province_id tidak akan berubah.

    Returns:
        int: province_id untuk Sulawesi Selatan

    Raises:
        httpx.HTTPError: Jika request gagal
        ValueError: Jika provinsi tidak ditemukan
    """
    r = httpx.get(
        f"{BASE}/destination/province",
        headers=_headers(),
        timeout=20
    )
    r.raise_for_status()

    data = r.json()
    provinces = data.get("data", [])

    for province in provinces:
        province_name = str(province.get("province_name", "")).strip().lower()
        if province_name == "sulawesi selatan":
            return int(province["province_id"])

    raise ValueError("Province 'Sulawesi Selatan' tidak ditemukan di RajaOngkir API")


def list_cities_in_sulsel():
    """
    Mendapatkan daftar kota/kabupaten di Sulawesi Selatan.

    Returns:
        list: Daftar kota/kabupaten dalam format:
            [
                {
                    "city_id": "xxx",
                    "province_id": "xxx",
                    "province": "Sulawesi Selatan",
                    "type": "Kabupaten/Kota",
                    "city_name": "xxx",
                    "postal_code": "xxx"
                },
                ...
            ]

    Raises:
        httpx.HTTPError: Jika request gagal
        ValueError: Jika province_id tidak ditemukan
    """
    province_id = get_sulsel_province_id()

    r = httpx.get(
        f"{BASE}/destination/city",
        headers=_headers(),
        params={"province_id": province_id},
        timeout=20
    )
    r.raise_for_status()

    data = r.json()
    return data.get("data", [])


def list_subdistricts(city_id: int):
    """
    Mendapatkan daftar kecamatan untuk kota tertentu.

    Args:
        city_id: ID kota/kabupaten dari RajaOngkir

    Returns:
        list: Daftar kecamatan dalam format:
            [
                {
                    "subdistrict_id": "xxx",
                    "province_id": "xxx",
                    "province": "Sulawesi Selatan",
                    "city_id": "xxx",
                    "city": "xxx",
                    "type": "Kabupaten/Kota",
                    "subdistrict_name": "xxx"
                },
                ...
            ]

    Raises:
        httpx.HTTPError: Jika request gagal
    """
    r = httpx.get(
        f"{BASE}/destination/subdistrict",
        headers=_headers(),
        params={"city_id": city_id},
        timeout=20
    )
    r.raise_for_status()

    data = r.json()
    return data.get("data", [])


def calculate_cost(
    origin_subdistrict_id: int,
    destination_subdistrict_id: int,
    weight_gram: int,
    courier: str
):
    """
    Menghitung biaya pengiriman dari origin ke destination.

    Args:
        origin_subdistrict_id: ID kecamatan asal (gudang)
        destination_subdistrict_id: ID kecamatan tujuan (pelanggan)
        weight_gram: Berat paket dalam gram (minimal 1000 gram = 1 kg)
        courier: Kode kurir (jne, jnt, sicepat, tiki, pos, anteraja)

    Returns:
        dict: Response dari RajaOngkir API dalam format:
            {
                "status": {
                    "code": 200,
                    "description": "OK"
                },
                "data": {
                    "origin": {...},
                    "destination": {...},
                    "results": [
                        {
                            "code": "jne",
                            "name": "JNE",
                            "costs": [
                                {
                                    "service": "REG",
                                    "description": "Reguler",
                                    "cost": [
                                        {
                                            "value": 15000,
                                            "etd": "2-3",
                                            "note": ""
                                        }
                                    ]
                                },
                                ...
                            ]
                        }
                    ]
                }
            }

    Raises:
        httpx.HTTPError: Jika request gagal
    """
    # Pastikan weight minimal 1000 gram (1 kg)
    weight = max(1000, int(weight_gram))

    payload = {
        "origin": origin_subdistrict_id,
        "destination": destination_subdistrict_id,
        "weight": weight,
        "courier": courier,
    }

    r = httpx.post(
        f"{BASE}/cost",
        headers=_headers(),
        data=payload,
        timeout=20
    )
    r.raise_for_status()

    return r.json()
