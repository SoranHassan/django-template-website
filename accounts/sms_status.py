"""Persian names for sms.ir API status codes + a small logging helper.

sms.ir returns a numeric ``status`` field in every JSON response. We translate
the common ones to Persian so the dashboard SMS log reads like plain language
instead of raw numbers.
"""

# Common sms.ir v1 status codes (verify + bulk). 1 == success.
SMS_IR_STATUS_FA = {
    1: 'ارسال موفق',
    0: 'خطای نامشخص',
    10: 'کاربر مورد نظر فعال نیست',
    11: 'ارسال نشده',
    12: 'اطلاعات کاربر کامل نیست',
    20: 'متن حاوی کلمه فیلترشده است',
    21: 'خط ارسال‌کننده معتبر نیست',
    103: 'اعتبار کافی نیست',
    104: 'خط ارسال‌کننده فعال نیست',
    105: 'حداکثر تعداد گیرندگان رعایت نشده',
    106: 'لیست موبایل‌ها خالی است',
    107: 'متن پیامک خالی است',
    108: 'خط ارسال‌کننده یافت نشد',
    109: 'زمان‌بندی ارسال نامعتبر است',
    110: 'مقادیر پارامترها خالی است',
    111: 'تعداد پارامترها با متغیرهای قالب همخوانی ندارد',
    112: 'نام پارامتر با متغیرهای قالب همخوانی ندارد',
    113: 'قالب یافت نشد',
    114: 'شناسه قالب نامعتبر است',
    115: 'شماره موبایل در لیست سیاه است',
    116: 'کد پارامتر تکراری است',
    401: 'کلید API نامعتبر است',
    403: 'دسترسی غیرمجاز',
    429: 'تعداد درخواست‌ها بیش از حد مجاز است',
    500: 'خطای داخلی سرور sms.ir',
}


def status_text_fa(code):
    """Return the Persian text for an sms.ir status code (or a generic fallback)."""
    try:
        code = int(code)
    except (TypeError, ValueError):
        return 'پاسخ نامشخص'
    return SMS_IR_STATUS_FA.get(code, f'کد پاسخ ناشناخته ({code})')


def log_sms(kind, mobile, *, ok, code=None, message=''):
    """Persist one SmsLog row. Never raises (logging must not break sending)."""
    try:
        from .models import SmsLog
        SmsLog.objects.create(
            kind=kind, mobile=str(mobile or '')[:20],
            status='ok' if ok else 'error',
            code=code if isinstance(code, int) else None,
            message=(message or '')[:300])
    except Exception:
        pass


def fetch_credit():
    """Live remaining SMS credit from sms.ir. Returns (credit, error_fa)."""
    import requests
    from django.conf import settings
    try:
        r = requests.get('https://api.sms.ir/v1/credit',
                         headers={'x-api-key': settings.SMS_IR_API_KEY,
                                  'Accept': 'application/json'}, timeout=8)
        body = r.json()
        if body.get('status') == 1:
            return body.get('data'), None
        return None, status_text_fa(body.get('status'))
    except Exception:
        # Keep the tile readable — no raw stack trace / proxy dump on screen.
        return None, 'ارتباط با sms.ir برقرار نشد'
