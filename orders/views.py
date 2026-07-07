import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.urls import reverse
from .pdf import generate_invoice_response
from cart.models import CartItem
from cart.views import _get_or_create_cart
from accounts.models import Address
from accounts.tasks import send_order_status_sms
from catalog.models import ProductVariant
from .models import Order, OrderItem, Coupon, CouponUsage
from .zarinpal import request_payment, verify_payment

logger = logging.getLogger('oramshop')


def _decrease_stock(order):
    """کسر موجودی واریانت‌ها بعد از پرداخت موفق"""
    for item in order.items.select_related('variant'):
        ProductVariant.objects.filter(pk=item.variant_id).update(
            stock=Greatest(F('stock') - item.quantity, 0))


def _finalize_paid_order(order):
    """کارهای پس از پرداخت موفق: کسر موجودی، مصرف کوپن و خالی کردن آیتم‌های خریداری‌شده از سبد"""
    _decrease_stock(order)

    if order.coupon_id:
        Coupon.objects.filter(pk=order.coupon_id).update(used_count=F('used_count') + 1)
        CouponUsage.objects.get_or_create(coupon_id=order.coupon_id, user=order.user, order=order)

    CartItem.objects.filter(
        cart__user=order.user,
        variant_id__in=order.items.values_list('variant_id', flat=True)).delete()


class ApplyCouponView(LoginRequiredMixin, View):
    def post(self, request):
        code = request.POST.get('code', '').strip().upper()

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'کد تخفیف معتبر نیست'})

        is_valid, message = coupon.is_valid()
        if not is_valid:
            return JsonResponse({'status': 'error', 'message': message})

        user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()

        if user_usage_count >= coupon.max_uses_per_user:
            return JsonResponse({
                'status': 'error',
                'message': 'شما قبلاً از این کد تخفیف استفاده کرده‌اید'})

        cart = _get_or_create_cart(request)

        if cart.subtotal < coupon.min_order_amount:
            return JsonResponse({
                'status': 'error',
                'message': f'حداقل مبلغ سفارش برای استفاده از این کد {coupon.min_order_amount} تومان است'})

        request.session['coupon_id'] = coupon.pk
        discount = coupon.calculate_discount(cart.subtotal)

        return JsonResponse({
            'status': 'ok',
            'message': 'کد تخفیف اعمال شد',
            'discount': str(discount),
            'final_total': str(cart.subtotal - discount + cart.tax)})


class RemoveCouponView(LoginRequiredMixin, View):
    def post(self, request):
        request.session.pop('coupon_id', None)
        return JsonResponse({'status': 'ok'})


def _get_session_coupon(request, cart):
    """کوپن ذخیره‌شده در سشن را برمی‌گرداند: (coupon, discount_amount)"""
    coupon = None
    discount_amount = 0
    coupon_id = request.session.get('coupon_id')

    if coupon_id:
        try:
            coupon = Coupon.objects.get(pk=coupon_id)
            is_valid, _ = coupon.is_valid()
            if is_valid:
                discount_amount = coupon.calculate_discount(cart.subtotal)
        except Coupon.DoesNotExist:
            coupon = None
            request.session.pop('coupon_id', None)

    return coupon, discount_amount


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product', 'variant__size', 'variant__color').prefetch_related('variant__product__images')

        if not items.exists():
            return redirect('cart:cart')

        addresses = request.user.addresses.all()
        coupon, discount_amount = _get_session_coupon(request, cart)

        return render(request, 'orders/checkout.html', {
            'cart': items,
            'subtotal': cart.subtotal,
            'tax': cart.tax,
            'discount_amount': discount_amount,
            'total': cart.subtotal + cart.tax - discount_amount,
            'addresses': addresses,
            'coupon': coupon,})

    def post(self, request):
        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product')

        if not items.exists():
            return redirect('cart:cart')

        # چک موجودی قبل از ثبت سفارش
        for item in items:
            if item.quantity > item.variant.stock:
                return render(request, 'orders/checkout.html', {
                    'error': f'موجودی «{item.variant.product.name}» کافی نیست (موجودی فعلی: {item.variant.stock})'
                })

        address_id = request.POST.get('address_id')
        address = get_object_or_404(Address, pk=address_id, user=request.user)
        coupon, discount_amount = _get_session_coupon(request, cart)

        order = Order.objects.create(user=request.user, address=address, coupon=coupon, total_price=cart.subtotal,
                                        discount_amount=discount_amount, tax=cart.tax, status='pending')

        for item in items:
            OrderItem.objects.create(order=order, variant=item.variant, quantity=item.quantity, price=item.variant.final_price)

        # کوپن به سفارش وصل شد؛ مصرف آن (used_count و CouponUsage) بعد از پرداخت موفق ثبت می‌شود
        if coupon:
            request.session.pop('coupon_id', None)

        # سبد خرید تا پرداخت موفق دست‌نخورده می‌ماند تا در صورت انصراف از دست نرود
        callback_url = request.build_absolute_uri(reverse('orders:verify_payment', kwargs={'pk': order.pk}))
        result = request_payment(
            amount=order.final_total,
            description=f'پرداخت سفارش #{order.pk}',
            callback_url=callback_url,
            mobile=request.user.mobile,
            email=request.user.email or None)

        if result['status'] == 'ok':
            order.zarinpal_authority = result['authority']
            order.save()
            logger.info('order %s created by %s, redirected to gateway (authority=%s)',
                        order.pk, request.user.mobile, result['authority'])
            return redirect(result['payment_url'])
        else:
            order.status = 'cancelled'
            order.save()
            logger.error('payment request failed for order %s: %s', order.pk, result['message'])
            return render(request, 'orders/checkout.html', {
                'error': f"خطا در اتصال به درگاه پرداخت: {result['message']}"
            })


class VerifyPaymentView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        authority = request.GET.get('Authority')
        status = request.GET.get('Status')

        # جلوگیری از پردازش دوباره: اگر سفارش قبلاً پرداخت یا لغو شده، دست نزن
        if order.status in ('paid', 'processing', 'shipped', 'delivered'):
            return redirect('orders:complete_order', pk=order.pk)
        if order.status != 'pending':
            return render(request, 'orders/payment-failed.html', {'order': order, 'error': 'این سفارش قبلاً بسته شده است'})

        if status == 'OK' and authority == order.zarinpal_authority:
            result = verify_payment(amount=order.final_total, authority=authority)

            if result['status'] == 'ok':
                order.status = 'paid'
                order.zarinpal_ref_id = str(result['ref_id'])
                order.save()

                _finalize_paid_order(order)
                logger.info('order %s paid successfully (ref_id=%s)', order.pk, order.zarinpal_ref_id)
                send_order_status_sms.delay(request.user.mobile,order.pk,'paid')
                return redirect('orders:complete_order', pk=order.pk)
            else:
                logger.warning('payment verification failed for order %s: %s', order.pk, result['message'])
                return render(request, 'orders/payment-failed.html', {'order': order,'error': result['message']})
        else:
            order.status = 'cancelled'
            order.save()
            logger.info('payment cancelled by user for order %s', order.pk)
            return render(request, 'orders/payment-failed.html', {'order': order, 'error': 'پرداخت لغو شد یا با خطا مواجه شد'})


class CompleteOrderView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        return render(request, 'orders/complete.html', {'order': order})




class InvoiceDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)

        if order.status not in ('paid', 'processing', 'shipped', 'delivered'):
            return redirect('orders:complete_order', pk=pk)
        return generate_invoice_response(order, request)