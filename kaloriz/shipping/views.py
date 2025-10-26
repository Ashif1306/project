from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import District, Address
from .forms import AddressForm


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
        tuple: (is_valid, error_message)
    """
    if not district_id:
        return False, 'Kecamatan harus dipilih'

    if service not in ['REG', 'EXP']:
        return False, 'Metode pengiriman tidak valid'

    # Check if district exists and active
    try:
        district = District.objects.get(id=district_id, is_active=True)
    except District.DoesNotExist:
        return False, 'Kecamatan tidak ditemukan'

    return True, None


# Address Management Views
@login_required
def add_address(request):
    """Add new shipping address"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # If this is set as default, unset other defaults
            if address.is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

            address.save()
            messages.success(request, 'Alamat berhasil ditambahkan.')
            return redirect(request.META.get('HTTP_REFERER', 'core:checkout'))
        else:
            messages.error(request, 'Gagal menambahkan alamat. Periksa kembali data Anda.')

    return redirect(request.META.get('HTTP_REFERER', 'core:checkout'))


@login_required
def edit_address(request, address_id):
    """Edit shipping address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)

            # If this is set as default, unset other defaults
            if updated_address.is_default:
                Address.objects.filter(user=request.user, is_default=True).exclude(id=address_id).update(is_default=False)

            updated_address.save()
            messages.success(request, 'Alamat berhasil diperbarui.')
            return redirect(request.META.get('HTTP_REFERER', 'core:profile'))
        else:
            messages.error(request, 'Gagal memperbarui alamat. Periksa kembali data Anda.')
    else:
        form = AddressForm(instance=address)

    districts = District.objects.filter(is_active=True).order_by('name')
    context = {
        'form': form,
        'address': address,
        'districts': districts,
    }
    return render(request, 'shipping/edit_address.html', context)


@login_required
def delete_address(request, address_id):
    """Delete shipping address"""
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.delete()
        messages.success(request, 'Alamat berhasil dihapus.')

    return redirect(request.META.get('HTTP_REFERER', 'core:profile'))


@login_required
def set_default_address(request, address_id):
    """Set address as default"""
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)

        # Unset other defaults
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        # Set this as default
        address.is_default = True
        address.save()

        messages.success(request, 'Alamat utama berhasil diubah.')

    return redirect(request.META.get('HTTP_REFERER', 'core:profile'))
