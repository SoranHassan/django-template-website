import logging

from celery import shared_task
from django.utils import timezone
import requests
from django.conf import settings

logger = logging.getLogger('oramshop')


@shared_task
def send_otp_sms(mobile, code):
    """ارسال OTP با sms.ir"""
    url = 'https://api.sms.ir/v1/send/verify'

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': settings.SMS_IR_API_KEY,
    }

    data = {
        'mobile': mobile,
        'templateId': settings.SMS_IR_TEMPLATE_ID,
        'parameters': [
            {
                'name': 'CODE',
                'value': code
            }
        ]
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info('OTP SMS sent to %s', mobile)
        return {'status': 'ok', 'response': response.json()}
    except requests.exceptions.RequestException as e:
        logger.error('OTP SMS failed for %s: %s', mobile, e)
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_expired_otps():
    """پاک‌سازی OTP های منقضی‌شده — اجرا با Celery Beat"""
    from .models import OTP
    deleted_count, _ = OTP.objects.filter(expires_at__lt=timezone.now()).delete()
    return f'{deleted_count} کد منقضی‌شده پاک شد'


@shared_task
def send_order_status_sms(mobile, order_id, status):
    """اطلاع‌رسانی وضعیت سفارش با پیامک"""
    status_messages = {
        'paid': 'پرداخت شما تأیید شد',
        'processing': 'سفارش شما در حال پردازش است',
        'shipped': 'سفارش شما ارسال شد',
        'delivered': 'سفارش شما تحویل داده شد',
        'cancelled': 'سفارش شما لغو شد',
    }

    message = status_messages.get(status, 'وضعیت سفارش تغییر کرد')

    url = 'https://api.sms.ir/v1/send/bulk'
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': settings.SMS_IR_API_KEY,
    }
    data = {
        'lineNumber': settings.SMS_IR_LINE_NUMBER,
        'MessageTexts': [f'سفارش #{order_id}: {message}'],
        'Mobiles': [mobile],
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info('order status SMS (%s) sent to %s for order %s', status, mobile, order_id)
        return {'status': 'ok'}
    except requests.exceptions.RequestException as e:
        logger.error('order status SMS failed for %s (order %s): %s', mobile, order_id, e)
        return {'status': 'error', 'message': str(e)}