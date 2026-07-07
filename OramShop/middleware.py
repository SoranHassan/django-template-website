# OramShop/middleware.py
class SecurityHeadersMiddleware:
    """
    فقط هدرهایی که جنگو خودش ست نمی‌کند.
    (nosniff ،X-Frame-Options و HSTS توسط SecurityMiddleware و
    XFrameOptionsMiddleware با تنظیمات production ست می‌شوند)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response
