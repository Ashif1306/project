from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.conf import settings
from decimal import Decimal
from .models import District, Address
from .services.raja import (
    list_cities_in_sulsel,
    list_subdistricts,
    calculate_cost as rajaongkir_calculate_cost
)


@require_GET
def get_districts(request):
    """
    JSON endpoint untuk mendapatkan daftar kecamatan aktif

    GET /shipping/districts/

    Response:
    {
        "success": true,
        "districts": [
            {"id": 1, "name": "Panakkukang"},
            ...
        ]
    }
    """
    try:
        districts = District.objects.filter(is_active=True).values('id', 'name')

        return JsonResponse({
            'success': True,
            'districts': list(districts)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def get_shipping_quotes(request):
    """
    JSON endpoint untuk mendapatkan tarif pengiriman berdasarkan kecamatan

    GET /shipping/quotes/?district_id=1

    Response:
    {
        "success": true,
        "quotes": [
            {
                "service": "REG",
                "label": "Reguler",
                "cost": 10000.00,
                "cost_formatted": "Rp 10.000",
                "eta": "2-3 hari kerja"
            },
            {
                "service": "EXP",
                "label": "Express",
                "cost": 18000.00,
                "cost_formatted": "Rp 18.000",
                "eta": "1 hari kerja"
            }
        ]
    }
    """
    district_id = request.GET.get('district_id')

    if not district_id:
        return JsonResponse({
            'success': False,
            'error': 'Parameter district_id diperlukan'
        }, status=400)

    try:
        district = District.objects.get(id=district_id, is_active=True)

        # Build response dengan 2 opsi: Reguler & Express
        quotes = [
            {
                'service': 'REG',
                'label': 'Reguler',
                'cost': float(district.reg_cost),
                'cost_formatted': f'Rp {district.reg_cost:,.0f}',
                'eta': district.eta_reg
            },
            {
                'service': 'EXP',
                'label': 'Express',
                'cost': float(district.exp_cost),
                'cost_formatted': f'Rp {district.exp_cost:,.0f}',
                'eta': district.eta_exp
            }
        ]

        return JsonResponse({
            'success': True,
            'district_name': district.name,
            'quotes': quotes
        })

    except District.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Kecamatan tidak ditemukan'
        }, status=404)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def calculate_shipping_cost(district_id, service, subtotal=Decimal('0')):
    """
    Helper function untuk menghitung biaya pengiriman
    Server-side validation: JANGAN PERCAYA ANGKA DARI CLIENT!

    Args:
        district_id: ID kecamatan tujuan
        service: 'REG' atau 'EXP'
        subtotal: Subtotal order untuk promo gratis ongkir

    Returns:
        tuple: (cost, eta, district_name) atau (None, None, None) jika error
    """
    try:
        # Re-lookup tarif dari database (PENTING: validasi server-side)
        district = District.objects.get(id=district_id, is_active=True)

        # Pilih tarif berdasarkan service
        if service == 'REG':
            cost = district.reg_cost
            eta = district.eta_reg
        elif service == 'EXP':
            cost = district.exp_cost
            eta = district.eta_exp
        else:
            return None, None, None

        # PROMO: Gratis ongkir jika subtotal >= 100.000
        # Uncomment baris berikut untuk mengaktifkan promo:
        # if subtotal >= Decimal('100000'):
        #     cost = Decimal('0')
        #     eta = f"{eta} (GRATIS ONGKIR!)"

        return cost, eta, district.name

    except District.DoesNotExist:
        return None, None, None
    except Exception:
        return None, None, None


def validate_shipping_data(district_id, service):
    """
    Validasi data pengiriman dari form

    Returns:
        dict: {'valid': True/False, 'error': 'message'}
    """
    if not district_id:
        return {'valid': False, 'error': 'Kecamatan harus dipilih'}

    if service not in ['REG', 'EXP']:
        return {'valid': False, 'error': 'Metode pengiriman tidak valid'}

    # Check if district exists and active
    try:
        district = District.objects.get(id=district_id, is_active=True)
    except District.DoesNotExist:
        return {'valid': False, 'error': 'Kecamatan tidak ditemukan'}

    return {'valid': True}


# ============================================
# RAJAONGKIR API ENDPOINTS (Sulawesi Selatan)
# ============================================

@require_GET
def api_sulsel_cities(request):
    """
    JSON endpoint untuk mendapatkan daftar kota/kabupaten di Sulawesi Selatan
    dari RajaOngkir API.

    GET /shipping/api/sulsel/cities

    Response:
    {
        "cities": [
            {
                "city_id": "7371",
                "province_id": "73",
                "province": "Sulawesi Selatan",
                "type": "Kota",
                "city_name": "Makassar",
                "postal_code": "90xxx"
            },
            ...
        ]
    }
    """
    try:
        cities = list_cities_in_sulsel()
        return JsonResponse({"cities": cities})

    except Exception as e:
        return JsonResponse({
            "error": f"Gagal mengambil data kota: {str(e)}"
        }, status=502)


@require_GET
def api_sulsel_subdistricts(request):
    """
    JSON endpoint untuk mendapatkan daftar kecamatan berdasarkan city_id.

    GET /shipping/api/sulsel/subdistricts?city_id=7371

    Response:
    {
        "subdistricts": [
            {
                "subdistrict_id": "7371100",
                "province_id": "73",
                "province": "Sulawesi Selatan",
                "city_id": "7371",
                "city": "Makassar",
                "type": "Kota",
                "subdistrict_name": "Panakkukang"
            },
            ...
        ]
    }
    """
    city_id = request.GET.get("city_id")

    if not city_id:
        return JsonResponse({
            "error": "Parameter city_id diperlukan"
        }, status=400)

    try:
        subdistricts = list_subdistricts(int(city_id))
        return JsonResponse({"subdistricts": subdistricts})

    except ValueError:
        return JsonResponse({
            "error": "city_id harus berupa angka"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "error": f"Gagal mengambil data kecamatan: {str(e)}"
        }, status=502)


@require_GET
def quote_by_params(request):
    """
    Hitung ongkir berdasarkan parameter langsung.

    GET /shipping/api/quote?destination_subdistrict_id=7371100&weight=1200&courier=jne&origin=7371050

    Query Parameters:
    - destination_subdistrict_id: ID kecamatan tujuan (wajib)
    - courier: Kode kurir - jne, jnt, sicepat, tiki, pos, anteraja (wajib)
    - weight: Berat dalam gram (default: 1000)
    - origin: ID kecamatan asal (default: dari ORIGIN_SUBDISTRICT_ID di settings)

    Response:
    {
        "status": {...},
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
                            "cost": [{"value": 15000, "etd": "2-3", "note": ""}]
                        },
                        ...
                    ]
                }
            ]
        }
    }
    """
    try:
        # Validasi dan ambil parameters
        dest = request.GET.get("destination_subdistrict_id")
        courier = request.GET.get("courier", "jne")
        weight = request.GET.get("weight", "1000")
        origin = request.GET.get("origin", str(settings.ORIGIN_SUBDISTRICT_ID or 0))

        # Validasi destination
        if not dest:
            return JsonResponse({
                "error": "Parameter destination_subdistrict_id wajib diisi"
            }, status=400)

        dest = int(dest)
        origin = int(origin)
        weight = int(weight)

        # Validasi origin
        if not origin:
            return JsonResponse({
                "error": "origin dan ORIGIN_SUBDISTRICT_ID belum dikonfigurasi"
            }, status=400)

        # Validasi courier
        if courier not in settings.SUPPORTED_COURIERS:
            return JsonResponse({
                "error": f"Kurir '{courier}' tidak didukung. Pilihan: {', '.join(settings.SUPPORTED_COURIERS)}"
            }, status=400)

        # Call RajaOngkir API
        data = rajaongkir_calculate_cost(origin, dest, weight, courier)

        # Sort costs by value (termurah dulu)
        if "data" in data and "results" in data["data"]:
            for courier_result in data["data"]["results"]:
                if "costs" in courier_result:
                    courier_result["costs"] = sorted(
                        courier_result.get("costs", []),
                        key=lambda x: x["cost"][0]["value"] if x.get("cost") else 0
                    )

        return JsonResponse(data)

    except ValueError as e:
        return JsonResponse({
            "error": f"Parameter tidak valid: {str(e)}"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "error": f"Gagal menghitung ongkir: {str(e)}"
        }, status=502)


@require_GET
def quote_by_address(request):
    """
    Hitung ongkir berdasarkan Address yang sudah ada di database.

    GET /shipping/api/quote-by-address?address_id=1&courier=jne&weight=1200&order_id=10

    Query Parameters:
    - address_id: ID address (wajib)
    - courier: Kode kurir - jne, jnt, sicepat, tiki, pos, anteraja (default: jne)
    - weight: Berat dalam gram (opsional, fallback ke order.total_weight_gram jika order_id ada)
    - order_id: ID order untuk ambil weight (opsional)

    Response:
    {
        "status": {...},
        "data": {
            "origin": {...},
            "destination": {...},
            "results": [...]
        }
    }
    """
    address_id = request.GET.get("address_id")

    if not address_id:
        return JsonResponse({
            "error": "Parameter address_id diperlukan"
        }, status=400)

    try:
        # Get address
        address = get_object_or_404(Address, pk=address_id)

        # Validasi destination_subdistrict_id
        dest = address.destination_subdistrict_id
        if not dest:
            return JsonResponse({
                "error": "Alamat belum memiliki destination_subdistrict_id. "
                        "Silakan lengkapi data alamat terlebih dahulu."
            }, status=400)

        # Get courier
        courier = request.GET.get("courier", "jne")
        if courier not in settings.SUPPORTED_COURIERS:
            return JsonResponse({
                "error": f"Kurir '{courier}' tidak didukung. Pilihan: {', '.join(settings.SUPPORTED_COURIERS)}"
            }, status=400)

        # Get weight - prioritas: query param > order weight > default 1000
        weight = request.GET.get("weight")
        if weight:
            weight = int(weight)
        else:
            # Try to get from order if order_id provided
            order_id = request.GET.get("order_id")
            if order_id:
                try:
                    from core.models import Order
                    order = Order.objects.get(pk=order_id)
                    weight = int(getattr(order, "total_weight_gram", 1000) or 1000)
                except Exception:
                    weight = 1000
            else:
                weight = 1000

        # Get origin
        origin = settings.ORIGIN_SUBDISTRICT_ID or 0
        if not origin:
            return JsonResponse({
                "error": "ORIGIN_SUBDISTRICT_ID belum dikonfigurasi di settings"
            }, status=400)

        # Call RajaOngkir API
        data = rajaongkir_calculate_cost(origin, int(dest), int(weight), courier)

        # Sort costs by value (termurah dulu)
        if "data" in data and "results" in data["data"]:
            for courier_result in data["data"]["results"]:
                if "costs" in courier_result:
                    courier_result["costs"] = sorted(
                        courier_result.get("costs", []),
                        key=lambda x: x["cost"][0]["value"] if x.get("cost") else 0
                    )

        return JsonResponse(data)

    except Address.DoesNotExist:
        return JsonResponse({
            "error": f"Alamat dengan ID {address_id} tidak ditemukan"
        }, status=404)

    except ValueError as e:
        return JsonResponse({
            "error": f"Parameter tidak valid: {str(e)}"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            "error": f"Gagal menghitung ongkir: {str(e)}"
        }, status=502)
