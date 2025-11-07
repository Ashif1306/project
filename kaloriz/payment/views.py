"""Views for handling Midtrans Snap payments."""
import json
import logging
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from catalog.models import DiscountCode
from core.models import Order
from core.views import _get_active_cart, _prepare_selected_cart_items
from core.services.orders import create_order_from_checkout, restore_order_stock
from shipping.models import Address

logger = logging.getLogger(__name__)

try:  # pragma: no cover - defensive import check
    import midtransclient
except ImportError:  # pragma: no cover - handled at runtime
    midtransclient = None


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _to_int_amount(value: Decimal) -> int:
    return int(_to_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _build_midtrans_client():
    if midtransclient is None:
        raise RuntimeError("midtransclient library is not installed")
    if not settings.MIDTRANS_SERVER_KEY:
        raise RuntimeError("MIDTRANS_SERVER_KEY tidak dikonfigurasi")

    return midtransclient.Snap(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER_KEY,
        client_key=settings.MIDTRANS_CLIENT_KEY,
    )


def _calculate_discount(
    subtotal: Decimal,
    shipping_cost: Decimal,
    shipping_method: str,
    discount_session: dict | None,
) -> tuple[Decimal, str]:
    discount_session = discount_session or {}
    discount_code = discount_session.get("code")

    if not discount_code:
        return Decimal("0"), ""

    discount_obj = DiscountCode.objects.filter(code__iexact=discount_code).first()
    if not discount_obj:
        return Decimal("0"), ""

    if not discount_obj.is_valid():
        return Decimal("0"), ""

    if not discount_obj.is_shipping_allowed(shipping_method):
        return Decimal("0"), ""

    grand_total = subtotal + shipping_cost
    if grand_total < discount_obj.get_min_spend():
        return Decimal("0"), ""

    discount_amount = discount_obj.calculate_discount(grand_total)
    if discount_amount > grand_total:
        discount_amount = grand_total

    return discount_amount, discount_obj.code.upper()


def _build_item_details(selected_items, shipping_cost: Decimal, discount_amount: Decimal, discount_code: str):
    details = []
    for item in selected_items:
        price = _to_int_amount(item.product.get_display_price())
        details.append(
            {
                "id": str(item.product.id),
                "price": price,
                "quantity": int(item.quantity),
                "name": item.product.name[:50],
            }
        )

    if shipping_cost > 0:
        details.append(
            {
                "id": "SHIPPING",
                "price": _to_int_amount(shipping_cost),
                "quantity": 1,
                "name": "Ongkos Kirim",
            }
        )

    if discount_amount > 0:
        details.append(
            {
                "id": "DISCOUNT",
                "price": -_to_int_amount(discount_amount),
                "quantity": 1,
                "name": f"Diskon {discount_code}".strip(),
            }
        )

    return details


def _build_customer_details(shipping_address: Address, user) -> dict:
    email = user.email or "customer@example.com"
    first_name = shipping_address.full_name or (user.get_full_name() or user.username)

    address_payload = {
        "first_name": first_name,
        "last_name": "",
        "email": email,
        "phone": shipping_address.phone,
        "address": shipping_address.get_full_address(),
        "city": shipping_address.city,
        "postal_code": shipping_address.postal_code,
        "country_code": "IDN",
    }

    return {
        "first_name": first_name,
        "last_name": "",
        "email": email,
        "phone": shipping_address.phone,
        "billing_address": address_payload,
        "shipping_address": address_payload,
    }


@csrf_exempt
@login_required
@require_POST
def payment_create_snap_token(request):
    """Create a Midtrans Snap transaction token."""
    try:
        client_payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        client_payload = {}

    try:
        snap_client = _build_midtrans_client()
    except RuntimeError as exc:
        logger.exception("Midtrans configuration error: %s", exc)
        return JsonResponse({"message": str(exc)}, status=500)

    try:
        cart = _get_active_cart(request)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Cart lookup failed: %s", exc)
        return JsonResponse({"message": "Keranjang tidak ditemukan."}, status=400)

    selected_items_qs = cart.items.filter(is_selected=True).select_related("product")
    if not selected_items_qs.exists():
        return JsonResponse({"message": "Tidak ada item yang dipilih untuk pembayaran."}, status=400)

    checkout_data = request.session.get("checkout", {})
    address_id = checkout_data.get("address_id")
    shipping_address = (
        Address.objects.filter(id=address_id, user=request.user, is_deleted=False)
        .select_related("district")
        .first()
    )

    if not shipping_address:
        return JsonResponse({"message": "Alamat pengiriman tidak ditemukan."}, status=400)

    shipping_cost = _to_decimal(checkout_data.get("shipping_cost"))
    subtotal = _to_decimal(cart.get_selected_total())

    discount_amount, discount_code = _calculate_discount(
        subtotal,
        shipping_cost,
        checkout_data.get("shipping_method"),
        request.session.get("discount"),
    )

    total = subtotal + shipping_cost - discount_amount
    if total < 0:
        total = Decimal("0")

    # Validate client-provided totals if available
    client_total_value = client_payload.get("total")
    if client_total_value is not None:
        client_total = _to_decimal(client_total_value)
        if client_total != total:
            logger.warning(
                "Client total %s does not match server total %s",
                client_total,
                total,
            )

    selected_items, selected_quantities = _prepare_selected_cart_items(selected_items_qs)
    if not selected_items:
        return JsonResponse({"message": "Tidak ada item yang dipilih untuk pembayaran."}, status=400)

    for item in selected_items:
        quantity = selected_quantities.get(item.pk, item.quantity)
        if item.product.stock < quantity:
            return JsonResponse(
                {"message": f"Stok {item.product.name} tidak mencukupi."},
                status=400,
            )

    item_details = _build_item_details(selected_items, shipping_cost, discount_amount, discount_code or "")

    order_id = f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    service_code = str(checkout_data.get("shipping_method") or "").upper()
    service_label = "Express" if service_code == "EXP" else "Reguler"
    district_name = getattr(getattr(shipping_address, "district", None), "name", "")
    eta = checkout_data.get("eta")
    notes = checkout_data.get("notes", "")

    transaction_payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": _to_int_amount(total),
        },
        "item_details": item_details,
        "customer_details": _build_customer_details(shipping_address, request.user),
        "credit_card": {"secure": True},
        "callbacks": {
            "finish": request.build_absolute_uri("/payment/finish/"),
        },
    }

    token = None
    order = None
    try:
        with transaction.atomic():
            order = create_order_from_checkout(
                user=request.user,
                cart=cart,
                selected_items=selected_items,
                selected_quantities=selected_quantities,
                order_number=order_id,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                total=total,
                shipping_full_name=shipping_address.full_name,
                shipping_email=request.user.email,
                shipping_phone=shipping_address.phone,
                shipping_address_text=shipping_address.get_full_address(),
                shipping_city=shipping_address.city,
                shipping_postal_code=shipping_address.postal_code,
                courier_service=service_code,
                district_name=district_name,
                eta=eta,
                notes=notes,
                shipping_address_obj=shipping_address,
                shipping_service_name=service_label,
            )
            snap_response = snap_client.create_transaction(transaction_payload)
            token = snap_response.get("token")
            if not token:
                raise RuntimeError("Token Snap tidak tersedia.")
    except RuntimeError as exc:  # Token missing or business rule failure
        logger.exception("Failed to create Midtrans Snap transaction: %s", exc)
        return JsonResponse({"message": str(exc)}, status=500)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to create order or Snap transaction: %s", exc)
        return JsonResponse({"message": "Gagal membuat Snap Token."}, status=500)

    request.session["midtrans_order_id"] = order.order_number
    request.session.pop("checkout", None)
    request.session.pop("discount", None)
    request.session.modified = True

    return JsonResponse({"token": token, "order_id": order.order_number})


@csrf_exempt
@login_required
@require_POST
def payment_finish(request):
    """Receive payment result callbacks from the frontend and update order status."""
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "Payload tidak valid."}, status=400)

    result = payload.get("result") or payload
    order_id = result.get("order_id")
    transaction_status = result.get("transaction_status") or result.get("status")

    if not order_id:
        return JsonResponse({"message": "Order ID tidak ditemukan."}, status=400)

    order = Order.objects.filter(order_number=order_id).first()
    if order and transaction_status:
        success_states = {"capture", "settlement"}
        pending_states = {"pending"}
        failure_states = {"deny", "cancel", "expire", "failure"}

        if transaction_status in success_states and order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])
        elif transaction_status in pending_states and order.status != "pending":
            order.status = "pending"
            order.save(update_fields=["status"])
        elif transaction_status in failure_states and order.status != "cancelled":
            with transaction.atomic():
                restore_order_stock(order)
                order.status = "cancelled"
                order.save(update_fields=["status"])

    request.session["midtrans_last_result"] = result
    request.session.modified = True

    response_payload = {"message": "Status pembayaran diterima.", "order_id": order_id}
    if order:
        response_payload["status"] = order.status

    return JsonResponse(response_payload)
