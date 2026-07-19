from cart.models import Cart
from reviews.models import Review
from orders.models import Order


def announcements_context(request):
    from .models import Announcement
    return {'announcements': Announcement.objects.filter(is_active=True)}


def site_settings_context(request):
    """Site appearance settings + third-party widget ids for all pages."""
    from django.conf import settings as dj_settings
    from .models import SiteSetting
    from .utils import runtime_config
    ctx = {'goftino_id': runtime_config('goftino_id_override', 'GOFTINO_ID'),
           'asset_version': getattr(dj_settings, 'ASSET_VERSION', '1')}
    try:
        ctx['site_settings'] = SiteSetting.get()
    except Exception:
        # Table does not exist before migrations have run
        ctx['site_settings'] = None
    try:
        from .models import StaticPage
        ctx['footer_pages'] = list(
            StaticPage.objects.filter(is_active=True, show_in_footer=True))
    except Exception:
        ctx['footer_pages'] = []
    return ctx


def categories_context(request):
    """Active categories for the navbar mega menu."""
    from catalog.models import Category
    return {'nav_categories': Category.objects.filter(is_active=True)}


def _get_request_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).first()
    session_key = request.session.session_key
    if not session_key:
        return None
    return Cart.objects.filter(session_key=session_key).first()


def cart_context(request):
    """Cart count and items for the navbar drawer."""
    try:
        cart = _get_request_cart(request)
        if cart:
            items = cart.items.select_related(
                'variant__product', 'variant__size', 'variant__color'
            ).prefetch_related('variant__product__images')
            return {
                'cart_count': cart.total_items,
                'nav_cart_items': items,
                'nav_cart_total': cart.subtotal,
            }
    except Exception:
        pass

    return {'cart_count': 0, 'nav_cart_items': [], 'nav_cart_total': 0}


def wishlist_context(request):
    """Wishlist items in pages"""
    wishlist = request.session.get('wishlist', [])
    return {
        'wishlist': wishlist,
        'wishlist_count': len(wishlist),
        'wishlist_ids': [str(item.get('id')) for item in wishlist],
        'wishlist_subtotal': sum(float(item.get('price', 0) or 0) for item in wishlist),
    }


def _unseen_count(request, session_key, queryset, date_field):
    """Number of new items since the admin last viewed that section.
    اگر تاکنون دیده نشده، همین حالا را مبنا می‌گیرد (بدون آلارم کاذب)."""
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    raw = request.session.get(session_key)
    if not raw:
        request.session[session_key] = timezone.now().isoformat()
        return 0
    since = parse_datetime(raw)
    if not since:
        return 0
    return queryset.filter(**{f'{date_field}__gt': since}).count()


def dashboard_context(request):
    """Dashboard notification badges - each clears after its section is viewed."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    from accounts.models import CustomUser

    # Count of 'unread' items (since the last view)
    new_orders_count = _unseen_count(request, 'seen_orders_at', Order.objects.all(), 'created_at')
    new_users_count = _unseen_count(request, 'seen_users_at', CustomUser.objects.all(), 'date_joined')
    new_reviews_count = _unseen_count(request, 'seen_reviews_at', Review.objects.filter(is_approved=False), 'created_at')

    return {
        # Notification badges (clearable)
        'new_orders_count': new_orders_count,
        'new_users_count': new_users_count,
        'new_reviews_count': new_reviews_count,
        # Actionable counts for the dashboard page (never cleared)
        'pending_orders_count': Order.objects.filter(status='pending').count(),
        'pending_reviews_count': Review.objects.filter(is_approved=False).count(),
    }
