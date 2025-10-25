from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.conf import settings
from decimal import Decimal
from .models import District, Address
from .services.raja import list_cities_in_sulsel, list_subdistricts, calculate_cost


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
# RAJAONGKIR API ENDPOINTS
# ============================================

@require_GET
def api_sulsel_cities(request):
    """
    Endpoint untuk mendapatkan daftar kota/kabupaten di Sulawesi Selatan.

    GET /shipping/api/sulsel/cities

    Response:
    {
        "cities": [
            {
                "city_id": "123",
                "type": "Kota",
                "city_name": "Makassar",
                "postal_code": "90000"
            },
            ...
        ]
    }
    """
    try:
        cities = list_cities_in_sulsel()
        return JsonResponse({"cities": cities})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


@require_GET
def api_sulsel_subdistricts(request):
    """
    Endpoint untuk mendapatkan daftar kecamatan di kota tertentu.

    GET /shipping/api/sulsel/subdistricts?city_id=123

    Response:
    {
        "subdistricts": [
            {
                "subdistrict_id": "456",
                "subdistrict_name": "Panakkukang",
                "type": "Kecamatan",
                "city": "Makassar"
            },
            ...
        ]
    }
    """
    city_id = request.GET.get("city_id")
    if not city_id:
        return JsonResponse({"error": "city_id diperlukan"}, status=400)

    try:
        subdistricts = list_subdistricts(int(city_id))
        return JsonResponse({"subdistricts": subdistricts})
    except ValueError:
        return JsonResponse({"error": "city_id harus berupa angka"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


@require_GET
def quote_by_params(request):
    """
    Endpoint untuk menghitung ongkir dengan parameter manual.

    GET /shipping/api/quote?destination_subdistrict_id=123&weight=1200&courier=jne&origin=456

    Query params:
    - destination_subdistrict_id (required): ID kecamatan tujuan
    - weight (required): Berat dalam gram
    - courier (required): Kode kurir (jne/jnt/sicepat/tiki/pos/anteraja)
    - origin (optional): ID kecamatan asal, default dari settings.ORIGIN_SUBDISTRICT_ID

    Response:
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
    """
    try:
        dest = int(request.GET.get("destination_subdistrict_id", "0"))
        courier = request.GET.get("courier", "jne")
        weight = int(request.GET.get("weight", "1000"))
        origin = int(request.GET.get("origin", settings.ORIGIN_SUBDISTRICT_ID or 0))

        if not (dest and origin):
            return JsonResponse({
                "error": "origin dan destination_subdistrict_id wajib diisi"
            }, status=400)

        if courier not in settings.SUPPORTED_COURIERS:
            return JsonResponse({
                "error": f"courier tidak didukung. Pilih salah satu: {', '.join(settings.SUPPORTED_COURIERS)}"
            }, status=400)

        data = calculate_cost(origin, dest, weight, courier)

        # Sort biaya per courier (termurah dulu)
        for c in data.get("data", []):
            c["costs"] = sorted(
                c.get("costs", []),
                key=lambda x: x["cost"][0]["value"] if x.get("cost") else 0
            )

        return JsonResponse(data)

    except ValueError as e:
        return JsonResponse({"error": f"Parameter tidak valid: {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)


@require_GET
def quote_by_address(request):
    """
    Endpoint untuk menghitung ongkir berdasarkan Address yang sudah tersimpan.

    GET /shipping/api/quote-by-address?address_id=1&courier=jne&weight=1200&order_id=10

    Query params:
    - address_id (required): ID dari model Address
    - courier (required): Kode kurir (jne/jnt/sicepat/tiki/pos/anteraja)
    - weight (optional): Berat dalam gram, jika tidak disediakan akan ambil dari order_id
    - order_id (optional): ID order untuk mendapatkan total_weight_gram

    Response: sama seperti quote_by_params
    """
    address_id = request.GET.get("address_id")
    if not address_id:
        return JsonResponse({"error": "address_id diperlukan"}, status=400)

    # Get address
    address = get_object_or_404(Address, pk=address_id)
    dest = address.destination_subdistrict_id

    if not dest:
        return JsonResponse({
            "error": "Alamat belum memiliki destination_subdistrict_id"
        }, status=400)

    courier = request.GET.get("courier", "jne")
    if courier not in settings.SUPPORTED_COURIERS:
        return JsonResponse({
            "error": f"courier tidak didukung. Pilih salah satu: {', '.join(settings.SUPPORTED_COURIERS)}"
        }, status=400)

    # Tentukan weight: prioritas query param, fallback ke order
    weight = request.GET.get("weight")
    if weight:
        weight = int(weight)
    else:
        order_id = request.GET.get("order_id")
        if order_id:
            try:
                from core.models import Order
                order = Order.objects.get(pk=order_id)
                weight = int(getattr(order, "total_weight_gram", 1000) or 1000)
            except Order.DoesNotExist:
                weight = 1000
            except Exception:
                weight = 1000
        else:
            weight = 1000

    origin = settings.ORIGIN_SUBDISTRICT_ID or 0
    if not origin:
        return JsonResponse({
            "error": "ORIGIN_SUBDISTRICT_ID belum dikonfigurasi di settings"
        }, status=400)

    try:
        data = calculate_cost(origin, int(dest), int(weight), courier)

        # Sort biaya per courier (termurah dulu)
        for c in data.get("data", []):
            c["costs"] = sorted(
                c.get("costs", []),
                key=lambda x: x["cost"][0]["value"] if x.get("cost") else 0
            )

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)
