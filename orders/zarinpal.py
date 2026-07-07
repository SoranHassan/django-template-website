import requests
from django.conf import settings


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
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': int(amount) * 10,  # تبدیل تومان به ریال
        'description': description,
        'callback_url': callback_url}

    if mobile:
        data['metadata'] = {'mobile': mobile}
    if email:
        data.setdefault('metadata', {})['email'] = email

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()

        if result['data']['code'] == 100:
            authority = result['data']['authority']
            payment_url = get_payment_gateway_url(authority)
            return {
                'status': 'ok',
                'authority': authority,
                'payment_url': payment_url}
        else:
            return {
                'status': 'error',
                'message': f"کد خطا: {result['data']['code']}"}
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'message': str(e)}


def verify_payment(amount, authority):
    """تأیید پرداخت"""
    url = get_api_url() + 'verify.json'
    data = {
        'merchant_id': settings.ZARINPAL_MERCHANT_ID,
        'amount': int(amount) * 10,
        'authority': authority,}

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()

        if result['data']['code'] in (100, 101):
            return {
                'status': 'ok',
                'ref_id': result['data']['ref_id'],
                'already_verified': result['data']['code'] == 101}
        else:
            return {
                'status': 'error',
                'message': f"کد خطا: {result['data']['code']}"}
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'message': str(e)}