import requests
from django.conf import settings

from core.utils import runtime_config


def get_merchant_id():
    """Merchant id editable from the panel (site settings), .env as fallback."""
    return runtime_config('zarinpal_merchant_id', 'ZARINPAL_MERCHANT_ID')


ZARINPAL_API_URL = 'https://api.zarinpal.com/pg/v4/payment/'
ZARINPAL_SANDBOX_URL = 'https://sandbox.zarinpal.com/pg/v4/payment/'


def get_api_url():
    if settings.ZARINPAL_SANDBOX:
        return ZARINPAL_SANDBOX_URL
    return ZARINPAL_API_URL


def get_payment_gateway_url(authority):
    if settings.ZARINPAL_SANDBOX:
        return f'https://sandbox.zarinpal.com/pg/StartPay/{authority}'
    return f'https://www.zarinpal.com/pg/StartPay/{authority}'


def request_payment(amount, description, callback_url, mobile=None, email=None):
    """
    درخواست پرداخت از زرین‌پال
    amount: مبلغ به ریال
    """
    url = get_api_url() + 'request.json'

    data = {
        'merchant_id': get_merchant_id(),
        'amount': int(amount) * 10,  # convert toman to rial
        'description': description,
        'callback_url': callback_url}

    if mobile:
        data['metadata'] = {'mobile': mobile}
    if email:
        data.setdefault('metadata', {})['email'] = email

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()

        # On error responses zarinpal sends an empty data field and a filled errors field
        result_data = result.get('data') or {}
        if isinstance(result_data, dict) and result_data.get('code') == 100:
            authority = result_data['authority']
            payment_url = get_payment_gateway_url(authority)
            return {
                'status': 'ok',
                'authority': authority,
                'payment_url': payment_url}

        errors = result.get('errors') or {}
        error_code = result_data.get('code') if isinstance(result_data, dict) else None
        message = errors.get('message') or f'کد خطا: {error_code or errors.get("code", "نامشخص")}'
        return {'status': 'error', 'message': message}
    except (requests.exceptions.RequestException, ValueError) as e:
        return {'status': 'error', 'message': str(e)}


def verify_payment(amount, authority):
    """Verify the payment."""
    url = get_api_url() + 'verify.json'
    data = {
        'merchant_id': get_merchant_id(),
        'amount': int(amount) * 10,
        'authority': authority,}

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()

        result_data = result.get('data') or {}
        if isinstance(result_data, dict) and result_data.get('code') in (100, 101):
            return {
                'status': 'ok',
                'ref_id': result_data['ref_id'],
                'already_verified': result_data['code'] == 101}

        errors = result.get('errors') or {}
        error_code = result_data.get('code') if isinstance(result_data, dict) else None
        message = errors.get('message') or f'کد خطا: {error_code or errors.get("code", "نامشخص")}'
        return {'status': 'error', 'message': message}
    except (requests.exceptions.RequestException, ValueError) as e:
        return {'status': 'error', 'message': str(e)}