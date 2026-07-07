from django.test import TestCase
from django.urls import reverse

from OramShop.test_utils import make_user, make_product


class DashboardAccessTest(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)

    def test_normal_user_denied(self):
        self.client.force_login(make_user(mobile='09128888880'))
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 403)


class DashboardPagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_user(mobile='09128888881', is_staff=True)
        make_product()

    def setUp(self):
        self.client.force_login(self.staff)

    def test_all_pages_render(self):
        for name in ['index', 'users_list', 'products_list', 'product_create',
                     'categories_list', 'orders_list', 'reviews_list', 'analytics']:
            response = self.client.get(reverse(f'dashboard:{name}'))
            self.assertEqual(response.status_code, 200, f'dashboard:{name} failed')
