"""Views for handling payment integrations (Midtrans, DOKU)."""

import json
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse
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

try:  # pragma: no cover - optional dependency for DOKU integration
    import requests
except ImportError:  # pragma: no cover - handled gracefully at runtime
    requests = None


class CheckoutPreparationError(Exception):
    """Raised when checkout data cannot be prepared for payment processing."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@dataclass
class PreparedCheckout:
    """Container for validated checkout information used by payment providers."""

    cart: Any
    selected_items: list
    selected_quantities: dict
    shipping_address: Address
    subtotal: Decimal
    shipping_cost: Decimal
    discount_amount: Decimal
    discount_code: str
    total: Decimal
    shipping_method: str | None
    service_code: str
    service_label: str
    district_name: str
    eta: str | None
    notes: str
    checkout_data: dict


def _prepare_checkout(
    request,
    *,
    require_payment_slug: str | None = None,
) -> PreparedCheckout:
    """Validate checkout session data and return normalized payment payload."""

    try:
        cart = _get_active_cart(request)
    except Exception as exc:  # pylint: disable=broad-except
        raise CheckoutPreparationError("Keranjang tidak ditemukan.", status=400) from exc

    selected_items_qs = cart.items.filter(is_selected=True).select_related("product")
    if not selected_items_qs.exists():
        raise CheckoutPreparationError(
            "Tidak ada item yang dipilih untuk pembayaran.", status=400
        )

    checkout_data = request.session.get("checkout", {}) or {}
    payment_slug = (checkout_data.get("payment_method") or "").strip().lower()
    if require_payment_slug and payment_slug != (require_payment_slug or "").lower():
        raise CheckoutPreparationError(
            "Metode pembayaran ini tidak tersedia untuk kanal yang dipilih.",
            status=400,
        )

    address_id = checkout_data.get("address_id")
    shipping_address = (
        Address.objects.filter(id=address_id, user=request.user, is_deleted=False)
        .select_related("district")
        .first()
    )
    if not shipping_address:
        raise CheckoutPreparationError("Alamat pengiriman tidak ditemukan.", status=400)

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

    selected_items, selected_quantities = _prepare_selected_cart_items(selected_items_qs)
    if not selected_items:
        raise CheckoutPreparationError(
            "Tidak ada item yang dipilih untuk pembayaran.", status=400
        )

    for item in selected_items:
        quantity = selected_quantities.get(item.pk, item.quantity)
        if item.product.stock < quantity:
            raise CheckoutPreparationError(
                f"Stok {item.product.name} tidak mencukupi.",
                status=400,
            )

    service_code = str(checkout_data.get("shipping_method") or "").upper()
    service_label = "Express" if service_code == "EXP" else "Reguler"
    district_name = getattr(getattr(shipping_address, "district", None), "name", "")

    return PreparedCheckout(
        cart=cart,
        selected_items=selected_items,
        selected_quantities=selected_quantities,
        shipping_address=shipping_address,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount_amount=discount_amount,
        discount_code=discount_code,
        total=total,
        shipping_method=checkout_data.get("shipping_method"),
        service_code=service_code,
        service_label=service_label,
        district_name=district_name,
        eta=checkout_data.get("eta"),
        notes=checkout_data.get("notes", ""),
        checkout_data=checkout_data,
    )


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


def _format_decimal_str(value: Decimal) -> str:
    """Return a string representation with 2 decimal places for API consumption."""

    decimal_value = _to_decimal(value).quantize(Decimal("0.01"))
    return f"{decimal_value:.2f}"


def _build_doku_line_items(prepared: PreparedCheckout) -> list[dict]:
    """Build DOKU line items payload based on the checkout selection."""

    items: list[dict] = []
    for item in prepared.selected_items:
        quantity = int(prepared.selected_quantities.get(item.pk, item.quantity))
        if quantity <= 0:
            continue
        price = _format_decimal_str(item.product.get_display_price())
        items.append(
            {
                "name": item.product.name[:80],
                "price": price,
                "quantity": quantity,
                "sku": str(item.product.id),
            }
        )

    if prepared.shipping_cost > 0:
        items.append(
            {
                "name": "Ongkos Kirim",
                "price": _format_decimal_str(prepared.shipping_cost),
                "quantity": 1,
                "sku": "SHIPPING",
            }
        )

    return items


def _build_doku_customer_details(shipping_address: Address, user) -> dict:
    """Construct customer payload for DOKU payment requests."""

    email = user.email or "customer@example.com"
    full_name = shipping_address.full_name or (user.get_full_name() or user.username)

    return {
        "id": str(user.id or shipping_address.id),
        "name": full_name,
        "email": email,
        "phone": shipping_address.phone,
        "address": shipping_address.get_full_address(),
        "country": "ID",
        "postal_code": shipping_address.postal_code,
        "city": shipping_address.city,
    }


def _get_doku_base_url() -> str:
    return "https://api.doku.com" if settings.DOKU_IS_PRODUCTION else "https://api-sandbox.doku.com"


def _obtain_doku_access_token() -> str:
    if requests is None:
        raise RuntimeError("Library requests tidak tersedia untuk integrasi DOKU.")

    client_id = getattr(settings, "DOKU_CLIENT_ID", "")
    client_secret = getattr(settings, "DOKU_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise RuntimeError("DOKU_CLIENT_ID dan DOKU_CLIENT_SECRET harus dikonfigurasi.")

    token_url = f"{_get_doku_base_url().rstrip('/')}/oauth/token"

    try:
        response = requests.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=15,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failures
        raise RuntimeError("Tidak dapat menghubungi DOKU untuk mendapatkan token.") from exc

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected payloads
        raise RuntimeError("Respon token DOKU tidak valid.") from exc

    if response.status_code >= 400:
        message = (
            payload.get("message")
            or payload.get("error_description")
            or payload.get("error")
            or "Gagal mendapatkan token DOKU."
        )
        raise RuntimeError(str(message))

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Access token DOKU tidak ditemukan.")

    return token


def _create_doku_payment(access_token: str, payload: dict) -> dict:
    payment_url = f"{_get_doku_base_url().rstrip('/')}/checkout/v1/payment"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(payment_url, json=payload, headers=headers, timeout=20)
    except requests.RequestException as exc:  # pragma: no cover - network failures
        raise RuntimeError("Tidak dapat menghubungi DOKU untuk membuat pembayaran.") from exc

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected payloads
        raise RuntimeError("Respon DOKU tidak valid.") from exc

    if response.status_code >= 400:
        message = (
            data.get("message")
            or data.get("error_description")
            or data.get("error")
            or "Gagal membuat pembayaran DOKU."
        )
        raise RuntimeError(str(message))

    return data


def _extract_doku_redirect_url(response_data: dict) -> str | None:
    if not isinstance(response_data, dict):
        return None

    candidates: list[str | None] = [
        response_data.get("redirect_url"),
        response_data.get("payment_url"),
        response_data.get("checkout_url"),
    ]

    nested_response = response_data.get("response")
    if isinstance(nested_response, dict):
        candidates.extend(
            [
                nested_response.get("redirect_url"),
                nested_response.get("payment_url"),
                nested_response.get("checkout_url"),
            ]
        )

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate

    return None


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

    midtrans_slug = getattr(settings, "MIDTRANS_PAYMENT_METHOD_SLUG", "midtrans")
    try:
        prepared = _prepare_checkout(request, require_payment_slug=midtrans_slug)
    except CheckoutPreparationError as exc:
        message = str(exc)
        if "Metode pembayaran ini tidak tersedia" in message:
            logger.warning(
                "Attempt to create Midtrans token with unsupported payment method: %s",
                (request.session.get("checkout", {}).get("payment_method") or ""),
            )
            return JsonResponse(
                {"message": "Metode pembayaran ini tidak menggunakan Midtrans."},
                status=400,
            )
        logger.exception("Failed to prepare checkout for Midtrans: %s", exc)
        return JsonResponse({"message": message}, status=getattr(exc, "status", 400))

    total = prepared.total

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

    item_details = _build_item_details(
        prepared.selected_items,
        prepared.shipping_cost,
        prepared.discount_amount,
        prepared.discount_code or "",
    )
    order_id = f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    transaction_payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": _to_int_amount(total),
        },
        "item_details": item_details,
        "customer_details": _build_customer_details(prepared.shipping_address, request.user),
        "credit_card": {"secure": True},
        "callbacks": {
            "finish": request.build_absolute_uri(reverse("payment:finish")),
        },
    }

    token = None
    order = None
    try:
        with transaction.atomic():
            order = create_order_from_checkout(
                user=request.user,
                cart=prepared.cart,
                selected_items=prepared.selected_items,
                selected_quantities=prepared.selected_quantities,
                order_number=order_id,
                subtotal=prepared.subtotal,
                shipping_cost=prepared.shipping_cost,
                total=total,
                shipping_full_name=prepared.shipping_address.full_name,
                shipping_email=request.user.email,
                shipping_phone=prepared.shipping_address.phone,
                shipping_address_text=prepared.shipping_address.get_full_address(),
                shipping_city=prepared.shipping_address.city,
                shipping_postal_code=prepared.shipping_address.postal_code,
                courier_service=prepared.service_code,
                district_name=prepared.district_name,
                eta=prepared.eta,
                notes=prepared.notes,
                shipping_address_obj=prepared.shipping_address,
                shipping_service_name=prepared.service_label,
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
def payment_create_doku_payment(request):
    """Create a DOKU checkout session and return redirect URL."""

    try:
        client_payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        client_payload = {}

    doku_slug = getattr(settings, "DOKU_PAYMENT_METHOD_SLUG", "doku")

    try:
        prepared = _prepare_checkout(request, require_payment_slug=doku_slug)
    except CheckoutPreparationError as exc:
        message = str(exc)
        if "Metode pembayaran ini tidak tersedia" in message:
            return JsonResponse(
                {"message": "Metode pembayaran ini tidak menggunakan DOKU."},
                status=400,
            )
        logger.exception("Failed to prepare checkout for DOKU: %s", exc)
        return JsonResponse({"message": message}, status=getattr(exc, "status", 400))

    if requests is None:
        logger.error("Library requests tidak terpasang untuk integrasi DOKU")
        return JsonResponse(
            {"message": "Library requests wajib terpasang untuk integrasi DOKU."},
            status=500,
        )

    total = prepared.total
    client_total_value = client_payload.get("total")
    if client_total_value is not None:
        client_total = _to_decimal(client_total_value)
        if client_total != total:
            logger.warning(
                "Client total %s does not match server total %s (DOKU)",
                client_total,
                total,
            )

    try:
        access_token = _obtain_doku_access_token()
    except RuntimeError as exc:
        logger.exception("Failed to obtain DOKU access token: %s", exc)
        return JsonResponse({"message": str(exc)}, status=500)

    order_id = f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    line_items = _build_doku_line_items(prepared)
    currency = getattr(settings, "DOKU_CURRENCY", "IDR") or "IDR"
    payment_due_minutes = int(getattr(settings, "DOKU_PAYMENT_EXPIRE_MINUTES", 60) or 60)
    order_list_url = request.build_absolute_uri(reverse("core:order_list"))

    payment_payload = {
        "order": {
            "amount": _format_decimal_str(total),
            "invoice_number": order_id,
            "currency": currency,
            "line_items": line_items,
            "callback_url": order_list_url,
            "return_url": order_list_url,
            "failed_url": order_list_url,
            "auto_redirect": True,
        },
        "payment": {
            "payment_due_date": payment_due_minutes,
        },
        "customer": _build_doku_customer_details(prepared.shipping_address, request.user),
        "additional_info": {
            "notes": prepared.notes,
            "shipping_service": prepared.service_label,
            "shipping_method": prepared.service_code,
        },
    }

    merchant_code = getattr(settings, "DOKU_MERCHANT_CODE", "")
    if merchant_code:
        payment_payload["merchant"] = {"code": merchant_code}

    doku_response: dict | None = None
    redirect_url: str | None = None
    order = None

    try:
        with transaction.atomic():
            order = create_order_from_checkout(
                user=request.user,
                cart=prepared.cart,
                selected_items=prepared.selected_items,
                selected_quantities=prepared.selected_quantities,
                order_number=order_id,
                subtotal=prepared.subtotal,
                shipping_cost=prepared.shipping_cost,
                total=total,
                shipping_full_name=prepared.shipping_address.full_name,
                shipping_email=request.user.email,
                shipping_phone=prepared.shipping_address.phone,
                shipping_address_text=prepared.shipping_address.get_full_address(),
                shipping_city=prepared.shipping_address.city,
                shipping_postal_code=prepared.shipping_address.postal_code,
                courier_service=prepared.service_code,
                district_name=prepared.district_name,
                eta=prepared.eta,
                notes=prepared.notes,
                shipping_address_obj=prepared.shipping_address,
                shipping_service_name=prepared.service_label,
            )

            doku_response = _create_doku_payment(access_token, payment_payload)
            redirect_url = _extract_doku_redirect_url(doku_response)
            if not redirect_url:
                raise RuntimeError("URL pembayaran DOKU tidak ditemukan.")
    except RuntimeError as exc:
        logger.exception("Failed to create DOKU payment: %s", exc)
        return JsonResponse({"message": str(exc)}, status=500)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to create DOKU order or payment: %s", exc)
        return JsonResponse({"message": "Gagal membuat pembayaran DOKU."}, status=500)

    request.session["doku_order_id"] = order.order_number
    request.session["doku_last_response"] = doku_response
    request.session.pop("checkout", None)
    request.session.pop("discount", None)
    request.session.modified = True

    return JsonResponse({"redirect_url": redirect_url, "order_id": order.order_number})


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
