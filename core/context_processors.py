from cart.models import Cart
from reviews.models import Review
from orders.models import Order


def announcements_context(request):
    from .models import Announcement
    return {'announcements': Announcement.objects.filter(is_active=True)}


def site_settings_context(request):
    """تنظیمات ظاهری سایت (واترمارک، رنگ تاپ‌بار) برای همه صفحات"""
    from .models import SiteSetting
    try:
        return {'site_settings': SiteSetting.get()}
    except Exception:
        # قبل از اجرای مایگریشن‌ها جدول وجود ندارد
        return {'site_settings': None}


def categories_context(request):
    """دسته‌بندی‌های فعال برای مگامنوی ناوبار"""
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
    """تعداد و آیتم‌های سبد برای ناوبار (drawer)"""
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


def dashboard_context(request):
    """آمار داشبورد برای نمایش در navbar/سایدبار (بج‌های اعلان)"""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    from django.utils import timezone
    from datetime import timedelta
    from accounts.models import CustomUser

    week_ago = timezone.now() - timedelta(days=7)
    pending_orders_count = Order.objects.filter(status='pending').count()
    pending_reviews_count = Review.objects.filter(is_approved=False).count()
    new_users_count = CustomUser.objects.filter(date_joined__gte=week_ago).count()

    return {
        'pending_orders_count': pending_orders_count,
        'pending_reviews_count': pending_reviews_count,
        'new_users_count': new_users_count,
    }
