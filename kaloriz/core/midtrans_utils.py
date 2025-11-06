"""
Midtrans Payment Gateway Utility Functions
"""
import hashlib
import midtransclient
from django.conf import settings
from decimal import Decimal


def get_snap_client():
    """
    Initialize and return Midtrans Snap API client
    """
    snap = midtransclient.Snap(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER_KEY,
        client_key=settings.MIDTRANS_CLIENT_KEY
    )
    return snap


def get_core_api_client():
    """
    Initialize and return Midtrans Core API client for checking transaction status
    """
    core_api = midtransclient.CoreApi(
        is_production=settings.MIDTRANS_IS_PRODUCTION,
        server_key=settings.MIDTRANS_SERVER_KEY,
        client_key=settings.MIDTRANS_CLIENT_KEY
    )
    return core_api


def create_snap_transaction(order, payment_method=None):
    """
    Create Snap transaction and return snap token

    Args:
        order: Order object
        payment_method: PaymentMethod object (optional)

    Returns:
        dict: Response from Midtrans containing snap_token and redirect_url
    """
    snap = get_snap_client()

    # Prepare transaction details
    transaction_details = {
        'order_id': order.order_number,
        'gross_amount': int(order.total)  # Midtrans expects integer (amount in IDR)
    }

    # Prepare item details
    item_details = []
    for item in order.items.all():
        item_details.append({
            'id': str(item.product.id) if item.product else 'deleted',
            'price': int(item.product_price),
            'quantity': item.quantity,
            'name': item.product_name[:50],  # Limit to 50 chars
        })

    # Add shipping cost as item
    if order.shipping_cost > 0:
        item_details.append({
            'id': 'SHIPPING',
            'price': int(order.shipping_cost),
            'quantity': 1,
            'name': 'Biaya Pengiriman',
        })

    # Prepare customer details
    customer_details = {
        'first_name': order.full_name[:50],
        'email': order.email,
        'phone': order.phone,
        'billing_address': {
            'address': order.address[:200] if order.address else '',
            'city': order.city[:50] if order.city else '',
            'postal_code': order.postal_code[:10] if order.postal_code else '',
            'country_code': 'IDN'
        },
        'shipping_address': {
            'address': order.address[:200] if order.address else '',
            'city': order.city[:50] if order.city else '',
            'postal_code': order.postal_code[:10] if order.postal_code else '',
            'country_code': 'IDN'
        }
    }

    # Prepare full transaction data
    transaction_data = {
        'transaction_details': transaction_details,
        'item_details': item_details,
        'customer_details': customer_details,
        'enabled_payments': [
            'credit_card', 'bca_va', 'bni_va', 'bri_va',
            'permata_va', 'other_va', 'gopay', 'shopeepay',
            'qris', 'indomaret', 'alfamart'
        ],
        'callbacks': {
            'finish': f'/order/{order.order_number}/'
        }
    }

    # Create transaction
    try:
        response = snap.create_transaction(transaction_data)
        return {
            'success': True,
            'snap_token': response['token'],
            'redirect_url': response['redirect_url'],
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def verify_signature_key(order_id, status_code, gross_amount, server_key):
    """
    Verify signature key from Midtrans notification

    Args:
        order_id: Order ID / transaction ID
        status_code: Status code from notification
        gross_amount: Gross amount from notification
        server_key: Midtrans server key

    Returns:
        str: Generated signature key
    """
    signature_string = f"{order_id}{status_code}{gross_amount}{server_key}"
    signature_hash = hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
    return signature_hash


def check_transaction_status(order_id):
    """
    Check transaction status from Midtrans

    Args:
        order_id: Order ID / transaction ID

    Returns:
        dict: Transaction status response from Midtrans
    """
    core_api = get_core_api_client()

    try:
        response = core_api.transactions.status(order_id)
        return {
            'success': True,
            'data': response
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def parse_notification(notification_data):
    """
    Parse notification data from Midtrans

    Args:
        notification_data: Dict of notification data from Midtrans

    Returns:
        dict: Parsed notification data
    """
    return {
        'transaction_id': notification_data.get('order_id'),
        'transaction_status': notification_data.get('transaction_status'),
        'fraud_status': notification_data.get('fraud_status', ''),
        'payment_type': notification_data.get('payment_type', ''),
        'gross_amount': notification_data.get('gross_amount'),
        'status_code': notification_data.get('status_code', ''),
        'signature_key': notification_data.get('signature_key', ''),
    }


def is_valid_signature(notification_data):
    """
    Validate signature from Midtrans notification

    Args:
        notification_data: Dict of notification data from Midtrans

    Returns:
        bool: True if signature is valid, False otherwise
    """
    order_id = notification_data.get('order_id')
    status_code = notification_data.get('status_code')
    gross_amount = notification_data.get('gross_amount')
    signature_key = notification_data.get('signature_key')

    # Generate expected signature
    expected_signature = verify_signature_key(
        order_id,
        status_code,
        gross_amount,
        settings.MIDTRANS_SERVER_KEY
    )

    return signature_key == expected_signature
