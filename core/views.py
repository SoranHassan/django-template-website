from django.http import HttpResponse
from django.shortcuts import render


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /dashboard/',
        'Disallow: /cart/',
        'Disallow: /orders/',
        'Disallow: /accounts/',
        'Allow: /',
        '',
        f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')