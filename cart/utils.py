from .models import Cart, CartItem


def merge_guest_cart(user, old_session_key):
    """
    بعد از ورود، سبد خرید مهمان (مبتنی بر سشن) به سبد کاربر منتقل می‌شود.
    باید قبل از login() کلید سشن قدیمی گرفته شده باشد چون login کلید را عوض می‌کند.
    """
    if not old_session_key:
        return

    guest_cart = Cart.objects.filter(session_key=old_session_key, user__isnull=True).first()
    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    for item in guest_cart.items.select_related('variant'):
        existing = CartItem.objects.filter(cart=user_cart, variant=item.variant).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, item.variant.stock)
            existing.save()
        else:
            CartItem.objects.create(cart=user_cart, variant=item.variant,
                                    quantity=min(item.quantity, item.variant.stock))

    guest_cart.delete()
