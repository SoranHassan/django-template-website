from cart.models import Cart
from reviews.models import Review
from orders.models import Order

def announcements_context(request):
    from .models import Announcement
    return {'announcements': Announcement.objects.filter(is_active=True)}

def cart_context(request):
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                return {'cart_count': 0}
            cart = Cart.objects.filter(session_key=session_key).first()

        if cart:
            return {'cart_count': cart.total_items}
    except Exception:
        pass

    return {'cart_count': 0}

def wishlist_context(request):
    """Wishlist items in pages"""
    wishlist = request.session.get('wishlist', [])
    return {'wishlist': wishlist, 'wishlist_count': len(wishlist), 'wishlist_subtotal': sum(float(item.get('price', 0)) for item in wishlist)}

def dashboard_context(request):
    """آمار داشبورد برای نمایش در navbar"""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    pending_orders_count = Order.objects.filter(status='pending').count()
    pending_reviews_count = Review.objects.filter(is_approved=False).count()

    return {'pending_orders_count': pending_orders_count,'pending_reviews_count': pending_reviews_count}