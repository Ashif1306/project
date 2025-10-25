"""
RajaOngkir API Client Service
Modul untuk integrasi dengan RajaOngkir Komerce API v1

Fungsi:
- get_sulsel_province_id(): Mendapatkan ID provinsi Sulawesi Selatan
- list_cities_in_sulsel(): Daftar kota/kabupaten di Sulawesi Selatan
- list_subdistricts(city_id): Daftar kecamatan di kota tertentu
- calculate_cost(): Hitung biaya ongkir berdasarkan origin, destination, berat, dan kurir
"""

import httpx
from functools import lru_cache
from django.conf import settings


BASE = settings.RAJAONGKIR_BASE_URL


def _hdr():
    """Generate header untuk request ke RajaOngkir API"""
    return {"key": settings.RAJAONGKIR_API_KEY}


@lru_cache(maxsize=1)
def get_sulsel_province_id() -> int:
    """
    Mencari dan mengembalikan province_id untuk "Sulawesi Selatan".
    Di-cache agar hanya dipanggil 1x per session.

    Returns:
        int: Province ID untuk Sulawesi Selatan

    Raises:
        ValueError: Jika provinsi tidak ditemukan
        httpx.HTTPError: Jika request gagal
    """
    r = httpx.get(f"{BASE}/destination/province", headers=_hdr(), timeout=20)
    r.raise_for_status()

    data = r.json().get("data", [])
    for p in data:
        province_name = str(p.get("province_name", "")).strip().lower()
        if province_name == "sulawesi selatan":
            return int(p["province_id"])

    raise ValueError("Province 'Sulawesi Selatan' tidak ditemukan di RajaOngkir API")


def list_cities_in_sulsel():
    """
    Mendapatkan daftar semua kota/kabupaten di Sulawesi Selatan.

    Returns:
        list: List of dict dengan data kota (city_id, city_name, type, postal_code)

    Raises:
        httpx.HTTPError: Jika request gagal
    """
    province_id = get_sulsel_province_id()

    r = httpx.get(
        f"{BASE}/destination/city",
        headers=_hdr(),
        params={"province_id": province_id},
        timeout=20
    )
    r.raise_for_status()

    return r.json().get("data", [])


def list_subdistricts(city_id: int):
    """
    Mendapatkan daftar kecamatan di kota tertentu.

    Args:
        city_id (int): ID kota dari RajaOngkir

    Returns:
        list: List of dict dengan data kecamatan (subdistrict_id, subdistrict_name, type, city)

    Raises:
        httpx.HTTPError: Jika request gagal
    """
    r = httpx.get(
        f"{BASE}/destination/subdistrict",
        headers=_hdr(),
        params={"city_id": city_id},
        timeout=20
    )
    r.raise_for_status()

    return r.json().get("data", [])


def calculate_cost(
    origin_subdistrict_id: int,
    destination_subdistrict_id: int,
    weight_gram: int,
    courier: str
):
    """
    Menghitung biaya ongkir menggunakan RajaOngkir Cost API.

    Args:
        origin_subdistrict_id (int): ID kecamatan asal (gudang)
        destination_subdistrict_id (int): ID kecamatan tujuan
        weight_gram (int): Berat total dalam gram (minimum 1000 gram = 1 kg)
        courier (str): Kode kurir (jne/jnt/sicepat/tiki/pos/anteraja)

    Returns:
        dict: Response JSON dari RajaOngkir dengan struktur:
            {
                "data": [
                    {
                        "code": "jne",
                        "name": "JNE",
                        "costs": [
                            {
                                "service": "REG",
                                "description": "Layanan Reguler",
                                "cost": [{"value": 15000, "etd": "2-3", "note": ""}]
                            }
                        ]
                    }
                ]
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
        headers=_hdr(),
        data=payload,
        timeout=20
    )
    r.raise_for_status()

    return r.json()
