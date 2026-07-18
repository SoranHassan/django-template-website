from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def error_403(request, exception=None):
    return render(request, '403.html', status=403)


def error_500(request):
    # 500.html is fully standalone (no DB/context processors) because the
    # database or cache may be the very thing that just failed
    return render(request, '500.html', status=500)


def _normalize_mobile(value):
    """Convert Persian/Arabic digits to English and normalise Iranian mobile numbers."""
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    v = (value or '').translate(trans).strip().replace(' ', '').replace('-', '')
    if v.startswith('+98'):
        v = '0' + v[3:]
    elif v.startswith('98') and len(v) == 12:
        v = '0' + v[2:]
    return v


class NewsletterSubscribeView(View):
    """Register an email or mobile number for the newsletter (footer form, AJAX)."""

    def dispatch(self, request, *args, **kwargs):
        from django.http import Http404
        from core.utils import feature_enabled
        if not feature_enabled('feature_newsletter'):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        import re
        from .models import NewsletterSubscriber
        raw = (request.POST.get('email') or request.POST.get('contact') or '').strip()

        # Detect email vs. mobile
        if '@' in raw:
            email = raw.lower()
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'message': 'ایمیل معتبر وارد کنید.'}, status=400)
            obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
        else:
            mobile = _normalize_mobile(raw)
            if not re.fullmatch(r'09\d{9}', mobile):
                return JsonResponse({'status': 'error', 'message': 'ایمیل یا شماره موبایل معتبر وارد کنید.'}, status=400)
            obj, created = NewsletterSubscriber.objects.get_or_create(mobile=mobile)

        if not created and obj.is_active:
            return JsonResponse({'status': 'ok', 'message': 'شما قبلاً عضو شده‌اید.'})
        obj.is_active = True
        obj.save()
        return JsonResponse({'status': 'ok', 'message': 'عضویت شما ثبت شد. ممنون!'})


def robots_txt(request):
    from django.conf import settings
    lines = [
        'User-agent: *',
        f'Disallow: /{settings.ADMIN_URL}',
        f'Disallow: /{settings.DASHBOARD_URL}',
        'Disallow: /cart/',
        'Disallow: /orders/',
        'Disallow: /accounts/',
        'Allow: /',
        '',
        f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')