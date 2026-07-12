from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


class NewsletterSubscribeView(View):
    """ثبت ایمیل در خبرنامه (از فرم فوتر/صفحه اصلی، با AJAX)"""

    def post(self, request):
        from .models import NewsletterSubscriber
        email = (request.POST.get('email') or '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'ایمیل معتبر وارد کنید.'}, status=400)
        obj, created = NewsletterSubscriber.objects.get_or_create(email=email)
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