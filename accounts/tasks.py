import logging

from celery import shared_task
from django.utils import timezone
import requests
from django.conf import settings

from .sms_status import status_text_fa, log_sms

logger = logging.getLogger('oramshop')

SMS_TIMEOUT = 10


def _post_sms(url, data, timeout=SMS_TIMEOUT):
    """POST to sms.ir and return (ok, code, message_fa, raw).

    ok is True only when the HTTP call succeeded AND sms.ir status == 1.
    message_fa is a Persian, human-readable result (delivery status or error).
    """
    headers = {'Content-Type': 'application/json', 'x-api-key': settings.SMS_IR_API_KEY}
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return False, None, f'خطای ارتباط با sms.ir: {e}', None
    try:
        body = resp.json()
    except ValueError:
        body = {}
    code = body.get('status')
    message_fa = status_text_fa(code) if code is not None else f'خطای HTTP {resp.status_code}'
    ok = (resp.status_code == 200 and code == 1)
    return ok, (code if isinstance(code, int) else None), message_fa, body


@shared_task
def send_otp_sms(mobile, code):
    """Send the OTP code via sms.ir (verify template)."""
    tid = settings.SMS_IR_TEMPLATE_ID
    ok, status_code, message_fa, _ = _post_sms(
        'https://api.sms.ir/v1/send/verify',
        {'mobile': mobile,
         'templateId': int(tid) if str(tid).isdigit() else tid,
         'parameters': [{'name': 'CODE', 'value': str(code)}]})
    log_sms('otp', mobile, ok=ok, code=status_code, message=message_fa)
    if ok:
        logger.info('OTP SMS sent to %s', mobile)
        return {'status': 'ok'}
    logger.error('OTP SMS failed for %s: %s', mobile, message_fa)
    return {'status': 'error', 'message': message_fa}


@shared_task
def cleanup_expired_otps():
    """Purge expired OTP codes - run by Celery Beat."""
    from .models import OTP
    deleted_count, _ = OTP.objects.filter(expires_at__lt=timezone.now()).delete()
    return f'{deleted_count} کد منقضی‌شده پاک شد'


@shared_task
def send_newsletter_sms(mobiles, text):
    """Send the newsletter SMS to a list of numbers (bulk)."""
    if not mobiles:
        return {'status': 'ok', 'count': 0}
    ok, status_code, message_fa, _ = _post_sms(
        'https://api.sms.ir/v1/send/bulk',
        {'lineNumber': settings.SMS_IR_LINE_NUMBER,
         'MessageTexts': [text] * len(mobiles),
         'Mobiles': list(mobiles)}, timeout=15)
    log_sms('newsletter', f'{len(mobiles)} شماره', ok=ok, code=status_code, message=message_fa)
    if ok:
        logger.info('newsletter SMS sent to %d mobiles', len(mobiles))
        return {'status': 'ok', 'count': len(mobiles)}
    logger.error('newsletter SMS failed: %s', message_fa)
    return {'status': 'error', 'message': message_fa}


@shared_task
def send_order_status_sms(mobile, order_id, status):
    """Notify the customer about an order status change via SMS.

    Uses the sms.ir *verify* (pattern) template in ``SMS_IR_ORDER_TEMPLATE_ID``.
    The template must contain a single ``#ORDER_ID#`` variable — the send below
    fills it with the order number. Unlike the old bulk send, this works on a
    normal (non-service) line once the template is approved.
    """
    # Kept only for the internal log so the shop owner sees which change fired;
    # the customer receives the fixed template text with the order number.
    status_labels = {
        'paid': 'پرداخت تأیید شد',
        'processing': 'در حال پردازش',
        'shipped': 'ارسال شد',
        'delivered': 'تحویل داده شد',
        'cancelled': 'لغو شد',
    }
    label = status_labels.get(status, 'به‌روزرسانی وضعیت')
    tid = settings.SMS_IR_ORDER_TEMPLATE_ID
    ok, status_code, message_fa, _ = _post_sms(
        'https://api.sms.ir/v1/send/verify',
        {'mobile': mobile,
         'templateId': int(tid) if str(tid).isdigit() else tid,
         'parameters': [{'name': 'ORDER_ID', 'value': str(order_id)}]})
    log_sms('order', mobile, ok=ok, code=status_code,
            message=f'#{order_id} ({label}) — {message_fa}')
    if ok:
        logger.info('order status SMS (%s) sent to %s for order %s', status, mobile, order_id)
        return {'status': 'ok'}
    logger.error('order status SMS failed for %s (order %s): %s', mobile, order_id, message_fa)
    return {'status': 'error', 'message': message_fa}
