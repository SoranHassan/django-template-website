from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from catalog.models import ProductVariant
from .models import Cart, CartItem


def _get_or_create_cart(request):
    """ Modal Function for Create Cart """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key)
    return cart


class CartView(View):
    def get(self, request):
        # Local import to avoid a circular import with orders
        from orders.views import _get_session_coupon

        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product', 'variant__size', 'variant__color').prefetch_related('variant__product__images')
        coupon, discount_amount = _get_session_coupon(request, cart)

        return render(request, 'cart/cart.html', {
            'cart': items,
            'subtotal': cart.subtotal,
            'coupon': coupon,
            'discount_amount': discount_amount,
            'total': cart.subtotal - discount_amount,})


def _parse_quantity(value, default=1):
    """Safely parse the quantity input; None means invalid."""
    try:
        quantity = int(value if value is not None else default)
    except (TypeError, ValueError):
        return None
    return quantity if 0 <= quantity <= 100 else None


class CartAddView(View):
    def post(self, request):
        variant_id = request.POST.get('variant_id')
        quantity = _parse_quantity(request.POST.get('quantity', 1))
        if not quantity:
            return JsonResponse({'status': 'error', 'message': 'تعداد نامعتبر است'}, status=400)
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        # Wholesale products: only approved wholesale customers may buy
        if variant.product.is_wholesale and not (
                request.user.is_authenticated and request.user.is_wholesale):
            return JsonResponse({
                'status': 'error',
                'message': 'خرید محصولات عمده فقط برای مشتریان عمدهٔ تأییدشده امکان‌پذیر است'
            }, status=403)

        if not variant.is_available:
            return JsonResponse({
                'status': 'error',
                'message': 'این محصول موجود نیست'}, status=400)

        cart = _get_or_create_cart(request)

        # Requested quantity (plus what is already in the cart) must not exceed stock
        existing = CartItem.objects.filter(cart=cart, variant=variant).first()
        current_quantity = existing.quantity if existing else 0
        if current_quantity + quantity > variant.stock:
            return JsonResponse({
                'status': 'error',
                'message': f'موجودی کافی نیست (موجودی فعلی: {variant.stock})'}, status=400)

        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={'quantity': quantity})

        if not created:
            item.quantity += quantity
            item.save()

        return JsonResponse({
            'status': 'ok',
            'message': 'محصول به سبد خرید اضافه شد',
            'count': cart.total_items
        })


class CartRemoveView(View):
    def post(self, request):
        item_id = request.POST.get('item_id')
        cart = _get_or_create_cart(request)

        try:
            item = CartItem.objects.get(pk=item_id, cart=cart)
            item.delete()
        except CartItem.DoesNotExist:
            pass

        return JsonResponse({
            'status': 'ok',
            'count': cart.total_items,
            'subtotal': str(cart.subtotal),
            'total': str(cart.total),
        })


class CartUpdateView(View):
    def post(self, request):
        item_id = request.POST.get('item_id')
        quantity = _parse_quantity(request.POST.get('quantity', 1))
        if quantity is None:
            return JsonResponse({'status': 'error', 'message': 'تعداد نامعتبر است'}, status=400)
        cart = _get_or_create_cart(request)
        item = get_object_or_404(CartItem,pk=item_id,cart=cart)

        if quantity > 0:
            if quantity > item.variant.stock:
                return JsonResponse({
                    'status': 'error',
                    'message': f'موجودی کافی نیست (موجودی فعلی: {item.variant.stock})'}, status=400)
            item.quantity = quantity
            item.save()
        else:
            item.delete()

        return JsonResponse({
            'status': 'ok',
            'count': cart.total_items,
            'subtotal': str(cart.subtotal),
            'total': str(cart.total),
        })


class CartDrawerView(View):
    """Cart drawer HTML for live refresh after add/remove."""

    def get(self, request):
        from orders.views import _get_session_coupon  # noqa: F401 (import compatibility)
        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product', 'variant__size', 'variant__color').prefetch_related('variant__product__images')
        return render(request, 'cart/_drawer_content.html', {
            'nav_cart_items': items,
            'nav_cart_total': cart.subtotal,
        })
