from django.http import HttpResponse
from django.shortcuts import render


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


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