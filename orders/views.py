from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from .pdf import generate_invoice_response
from cart.views import _get_or_create_cart
from accounts.models import Address
from accounts.tasks import send_order_status_sms
from .models import Order, OrderItem, Coupon, CouponUsage
from .zarinpal import request_payment, verify_payment


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


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart = _get_or_create_cart(request)
        items = cart.items.select_related('variant__product', 'variant__size', 'variant__color').prefetch_related('variant__product__images')

        if not items.exists():
            return redirect('cart:cart')

        addresses = request.user.addresses.all()

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
                request.session.pop('coupon_id', None)

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
        items = cart.items.select_related('variant')

        if not items.exists():
            return redirect('cart:cart')

        address_id = request.POST.get('address_id')
        address = get_object_or_404(Address, pk=address_id, user=request.user)
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
                pass

        order = Order.objects.create(user=request.user, address=address, coupon=coupon, total_price=cart.subtotal,
                                        discount_amount=discount_amount, tax=cart.tax, status='pending')

        for item in items:
            OrderItem.objects.create(order=order, variant=item.variant, quantity=item.quantity, price=item.variant.final_price)

        if coupon:
            coupon.used_count += 1
            coupon.save()
            CouponUsage.objects.create(coupon=coupon, user=request.user, order=order)
            request.session.pop('coupon_id', None)

        cart.items.all().delete()
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
            return redirect(result['payment_url'])
        else:
            order.status = 'cancelled'
            order.save()
            return render(request, 'orders/checkout.html', {
                'error': f"خطا در اتصال به درگاه پرداخت: {result['message']}"
            })


class VerifyPaymentView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        authority = request.GET.get('Authority')
        status = request.GET.get('Status')

        if status == 'OK' and authority == order.zarinpal_authority:
            result = verify_payment(amount=order.final_total, authority=authority)

            if result['status'] == 'ok':
                order.status = 'paid'
                order.zarinpal_ref_id = str(result['ref_id'])
                order.save()

                send_order_status_sms.delay(request.user.mobile,order.pk,'paid')
                return redirect('orders:complete_order', pk=order.pk)
            else:
                return render(request, 'orders/payment-failed.html', {'order': order,'error': result['message']})
        else:
            order.status = 'cancelled'
            order.save()
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