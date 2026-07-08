from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from OramShop.test_utils import make_user, make_product
from accounts.models import Address
from cart.models import Cart, CartItem
from .models import Order, OrderItem, Coupon, CouponUsage
from .views import _decrease_stock


def make_coupon(**kwargs):
    now = timezone.now()
    defaults = dict(code='OFF10', discount_type='percent', discount_value=10,
                    valid_from=now - timedelta(days=1), valid_until=now + timedelta(days=1))
    defaults.update(kwargs)
    return Coupon.objects.create(**defaults)


class VerifyPaymentProtectionTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09120000002')
        self.client.force_login(self.user)
        _, self.variant = make_product(stock=5)
        self.order = Order.objects.create(user=self.user, total_price=1000, status='paid',
                                          zarinpal_authority='AUTH123', zarinpal_ref_id='REF1')
        OrderItem.objects.create(order=self.order, variant=self.variant, quantity=2, price=1000)

    def test_paid_order_not_cancelled_on_revisit(self):
        """باز کردن دوباره لینک بازگشت درگاه نباید سفارش پرداخت‌شده را لغو کند"""
        url = reverse('orders:verify_payment', kwargs={'pk': self.order.pk})
        response = self.client.get(url + '?Status=NOK&Authority=AUTH123')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertRedirects(response, reverse('orders:complete_order', kwargs={'pk': self.order.pk}),
                             fetch_redirect_response=False)

    @patch('orders.views.verify_payment')
    def test_paid_order_not_reverified(self, mock_verify):
        url = reverse('orders:verify_payment', kwargs={'pk': self.order.pk})
        self.client.get(url + '?Status=OK&Authority=AUTH123')
        mock_verify.assert_not_called()


class StockDecrementTest(TestCase):
    def test_decrease_stock(self):
        user = make_user(mobile='09120000003')
        _, variant = make_product(stock=5)
        order = Order.objects.create(user=user, total_price=1000, status='paid')
        OrderItem.objects.create(order=order, variant=variant, quantity=2, price=1000)
        _decrease_stock(order)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 3)

    def test_stock_never_negative(self):
        user = make_user(mobile='09120000004')
        _, variant = make_product(stock=1)
        order = Order.objects.create(user=user, total_price=1000, status='paid')
        OrderItem.objects.create(order=order, variant=variant, quantity=10, price=1000)
        _decrease_stock(order)
        variant.refresh_from_db()
        self.assertEqual(variant.stock, 0)


class CheckoutTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09120000005')
        self.client.force_login(self.user)
        _, self.variant = make_product(stock=5)
        self.address = Address.objects.create(user=self.user, first_name='a', last_name='b',
                                              phone='09120000005', address1='x', city='y', zip='1234567890')
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

    def test_checkout_blocked_when_insufficient_stock(self):
        self.variant.stock = 1
        self.variant.save()
        response = self.client.post(reverse('orders:checkout'), {'address_id': self.address.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertEqual(Order.objects.count(), 0)

    @patch('orders.views.request_payment')
    def test_cart_and_coupon_untouched_before_payment(self, mock_pay):
        mock_pay.return_value = {'status': 'ok', 'authority': 'A1', 'payment_url': '/fake-gateway/'}
        coupon = make_coupon()
        session = self.client.session
        session['coupon_id'] = coupon.pk
        session.save()

        self.client.post(reverse('orders:checkout'), {'address_id': self.address.pk})

        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 0)
        self.assertEqual(CouponUsage.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 1)

    @patch('orders.views.request_payment')
    def test_cart_preserved_on_failed_gateway(self, mock_pay):
        mock_pay.return_value = {'status': 'error', 'message': 'down'}
        self.client.post(reverse('orders:checkout'), {'address_id': self.address.pk})
        self.assertEqual(self.cart.items.count(), 1)

    @patch('orders.views.send_order_status_sms')
    @patch('orders.views.verify_payment')
    def test_coupon_consumed_and_cart_cleared_after_payment(self, mock_verify, mock_sms):
        mock_verify.return_value = {'status': 'ok', 'ref_id': 1, 'already_verified': False}
        coupon = make_coupon()
        order = Order.objects.create(user=self.user, total_price=2000, coupon=coupon,
                                     status='pending', zarinpal_authority='A1')
        OrderItem.objects.create(order=order, variant=self.variant, quantity=2, price=1000)

        url = reverse('orders:verify_payment', kwargs={'pk': order.pk})
        self.client.get(url + '?Status=OK&Authority=A1')

        order.refresh_from_db()
        coupon.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(coupon.used_count, 1)
        self.assertEqual(CouponUsage.objects.count(), 1)
        self.assertEqual(self.variant.stock, 3)
        self.assertEqual(self.cart.items.count(), 0)


class CouponTest(TestCase):
    def test_expired_coupon_invalid(self):
        coupon = make_coupon(valid_until=timezone.now() - timedelta(days=1))
        is_valid, _ = coupon.is_valid()
        self.assertFalse(is_valid)

    def test_percent_discount_capped(self):
        coupon = make_coupon(discount_value=50, max_discount_amount=100)
        self.assertEqual(coupon.calculate_discount(1000), 100)

    def test_fixed_discount_never_exceeds_subtotal(self):
        coupon = make_coupon(discount_type='fixed', discount_value=5000)
        self.assertEqual(coupon.calculate_discount(1000), 1000)


class ShippingMethodTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09120000008')
        self.client.force_login(self.user)
        _, self.variant = make_product(stock=5)
        self.address = Address.objects.create(user=self.user, first_name='a', last_name='b',
                                              phone='09120000008', address1='x', city='y', zip='1234567890')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        from .models import ShippingMethod
        self.method = ShippingMethod.objects.create(name='پست پیشتاز', price=65000)

    def test_checkout_page_shows_shipping_methods(self):
        response = self.client.get(reverse('orders:checkout'))
        self.assertContains(response, 'پست پیشتاز')
        self.assertNotContains(response, 'مالیات')

    @patch('orders.views.request_payment')
    def test_order_gets_shipping_cost(self, mock_pay):
        mock_pay.return_value = {'status': 'ok', 'authority': 'A1', 'payment_url': '/gw/'}
        self.client.post(reverse('orders:checkout'),
                         {'address_id': self.address.pk, 'shipping_method': self.method.pk})
        order = Order.objects.get()
        self.assertEqual(order.shipping_cost, 65000)
        self.assertEqual(order.final_total, order.total_price + 65000)

    @patch('orders.views.request_payment')
    def test_checkout_requires_shipping_selection(self, mock_pay):
        response = self.client.post(reverse('orders:checkout'), {'address_id': self.address.pk})
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('error', response.context)


class CouponCaseInsensitiveTest(TestCase):
    def test_lowercase_code_applies(self):
        user = make_user(mobile='09120000009')
        self.client.force_login(user)
        _, variant = make_product(stock=5)
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)
        make_coupon(code='WELCOME10')

        response = self.client.post(reverse('orders:apply_coupon'), {'code': 'welcome10'})
        self.assertEqual(response.json()['status'], 'ok')

    def test_guest_gets_json_message(self):
        response = self.client.post(reverse('orders:apply_coupon'), {'code': 'X'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')
