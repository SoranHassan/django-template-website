from django.test import TestCase
from django.urls import reverse

from OramShop.test_utils import make_user, make_product
from .models import Cart, CartItem


class CartStockLimitTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09120000006')
        self.client.force_login(self.user)
        _, self.variant = make_product(stock=2)

    def test_cannot_add_more_than_stock(self):
        response = self.client.post(reverse('cart:add'),
                                    {'variant_id': self.variant.pk, 'quantity': 3})
        self.assertEqual(response.status_code, 400)

    def test_cannot_exceed_stock_cumulatively(self):
        ok = self.client.post(reverse('cart:add'), {'variant_id': self.variant.pk, 'quantity': 2})
        self.assertEqual(ok.status_code, 200)
        over = self.client.post(reverse('cart:add'), {'variant_id': self.variant.pk, 'quantity': 1})
        self.assertEqual(over.status_code, 400)

    def test_update_capped_to_stock(self):
        self.client.post(reverse('cart:add'), {'variant_id': self.variant.pk, 'quantity': 1})
        item = Cart.objects.get(user=self.user).items.first()
        response = self.client.post(reverse('cart:update'), {'item_id': item.pk, 'quantity': 5})
        self.assertEqual(response.status_code, 400)

    def test_invalid_quantity_returns_400_not_500(self):
        response = self.client.post(reverse('cart:add'),
                                    {'variant_id': self.variant.pk, 'quantity': 'abc'})
        self.assertEqual(response.status_code, 400)


class GuestCartTest(TestCase):
    def test_guest_can_add_to_cart(self):
        _, variant = make_product(stock=5)
        response = self.client.post(reverse('cart:add'), {'variant_id': variant.pk, 'quantity': 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_guest_cart_merged_into_user_cart_on_login(self):
        """سبد مهمان بعد از ورود نباید گم شود"""
        user = make_user(mobile='09127777777')
        _, variant = make_product(stock=5)

        self.client.post(reverse('cart:add'), {'variant_id': variant.pk, 'quantity': 2})
        self.client.post(reverse('accounts:login'),
                         {'mobile': '09127777777', 'password': 'pass12345'})

        user_cart = Cart.objects.get(user=user)
        self.assertEqual(user_cart.items.get(variant=variant).quantity, 2)
