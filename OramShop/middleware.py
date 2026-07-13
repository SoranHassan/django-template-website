# OramShop/middleware.py
import hashlib


class VisitTrackingMiddleware:
    """Records real site visits.

    Only storefront HTML pages (GET, 200 responses) are counted; static
    files, admin panels, AJAX requests and bots are ignored so the
    statistics stay real and noise-free.
    """

    SKIP_PREFIXES = ('/static/', '/media/', '/admin/', '/dashboard/',
                     '/cart/', '/wishlist/', '/accounts/', '/favicon')
    BOT_HINTS = ('bot', 'crawl', 'spider', 'slurp', 'bingpreview',
                 'facebookexternalhit', 'pingdom', 'headless', 'lighthouse')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._track(request, response)
        except Exception:
            # Tracking must never break page delivery
            pass
        return response

    def _track(self, request, response):
        if request.method != 'GET' or response.status_code != 200:
            return
        # HTML responses only
        ctype = response.get('Content-Type', '')
        if 'text/html' not in ctype:
            return
        path = request.path
        if any(path.startswith(p) for p in self.SKIP_PREFIXES):
            return
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        if not ua or any(h in ua for h in self.BOT_HINTS):
            return

        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key or ''

        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
            or request.META.get('REMOTE_ADDR', '')
        ip_hash = hashlib.md5(ip.encode()).hexdigest()[:16] if ip else ''

        from core.models import SiteVisit
        SiteVisit.objects.create(
            session_key=session_key,
            path=path[:255],
            user=request.user if request.user.is_authenticated else None,
            ip_hash=ip_hash,
            is_authenticated=request.user.is_authenticated,
        )


class SecurityHeadersMiddleware:
    """
    Only the headers Django does not set by itself.
    (nosniff, X-Frame-Options and HSTS are set by SecurityMiddleware and
    XFrameOptionsMiddleware with the production settings.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response
