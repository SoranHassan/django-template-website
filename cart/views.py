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
        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product', 'variant__size', 'variant__color').prefetch_related('variant__product__images')
        quantity_range = range(1, 11)

        return render(request, 'cart/cart.html', {
            'cart': items,
            'subtotal': cart.subtotal,
            'tax': cart.tax,
            'total': cart.total,
            'quantity_range': quantity_range,})


class CartAddView(View):
    def post(self, request):
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        if not variant.is_available:
            return JsonResponse({
                'status': 'error',
                'message': 'این محصول موجود نیست'}, status=400)

        cart = _get_or_create_cart(request)
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
            'tax': str(cart.tax),
            'total': str(cart.total),
        })


class CartUpdateView(View):
    def post(self, request):
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        cart = _get_or_create_cart(request)
        item = get_object_or_404(CartItem,pk=item_id,cart=cart)

        if quantity > 0:
            item.quantity = quantity
            item.save()
        else:
            item.delete()

        return JsonResponse({
            'status': 'ok',
            'count': cart.total_items,
            'subtotal': str(cart.subtotal),
            'tax': str(cart.tax),
            'total': str(cart.total),
        })
