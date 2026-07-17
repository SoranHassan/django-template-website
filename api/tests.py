"""Tests for the JSON API v1 (Telegram bot integration)."""
from django.test import TestCase, override_settings

from catalog.models import Brand, Category, Color, Product, ProductVariant, Size

API_KEY = 'test-key-abc'


def make_product(name='Test Shirt', price=100000, **kw):
    return Product.objects.create(name=name, slug=name.lower().replace(' ', '-'),
                                  price=price, is_active=True, **kw)


@override_settings(BOT_API_KEY=API_KEY)
class ApiAuthTests(TestCase):
    def test_missing_key_returns_401(self):
        resp = self.client.get('/api/v1/products/')
        self.assertEqual(resp.status_code, 401)

    def test_wrong_key_returns_401(self):
        resp = self.client.get('/api/v1/products/', HTTP_X_API_KEY='wrong')
        self.assertEqual(resp.status_code, 401)

    def test_disabled_api_returns_503(self):
        with override_settings(BOT_API_KEY=''):
            resp = self.client.get('/api/v1/products/', HTTP_X_API_KEY='anything')
        self.assertEqual(resp.status_code, 503)

    def test_post_not_allowed(self):
        resp = self.client.post('/api/v1/products/', HTTP_X_API_KEY=API_KEY)
        self.assertEqual(resp.status_code, 405)


@override_settings(BOT_API_KEY=API_KEY)
class ApiProductTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name='Nike', slug='nike', is_active=True)
        cls.cat = Category.objects.create(name='Shirts', slug='shirts', is_active=True)
        cls.p1 = make_product('Blue Shirt', 150000, brand=cls.brand, category=cls.cat,
                              gender='men')
        cls.p2 = make_product('Red Dress', 250000, gender='women')
        inactive = make_product('Hidden Item', 90000)
        inactive.is_active = False
        inactive.save()
        size = Size.objects.create(name='XL')
        color = Color.objects.create(name='Blue', hex_code='#0000ff')
        cls.variant = ProductVariant.objects.create(
            product=cls.p1, size=size, color=color, stock=5)

    def get(self, url, **params):
        return self.client.get(url, params, HTTP_X_API_KEY=API_KEY)

    def test_product_list_returns_active_only(self):
        data = self.get('/api/v1/products/').json()
        self.assertEqual(data['count'], 2)
        names = {r['name'] for r in data['results']}
        self.assertNotIn('Hidden Item', names)

    def test_product_list_search(self):
        data = self.get('/api/v1/products/', q='blue').json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['name'], 'Blue Shirt')

    def test_product_list_filters(self):
        by_cat = self.get('/api/v1/products/', category='shirts').json()
        self.assertEqual(by_cat['count'], 1)
        by_brand = self.get('/api/v1/products/', brand='nike').json()
        self.assertEqual(by_brand['count'], 1)
        by_gender = self.get('/api/v1/products/', gender='women').json()
        self.assertEqual(by_gender['count'], 1)
        self.assertEqual(by_gender['results'][0]['name'], 'Red Dress')

    def test_product_list_pagination(self):
        data = self.get('/api/v1/products/', page_size=1, page=2).json()
        self.assertEqual(data['pages'], 2)
        self.assertEqual(data['page'], 2)
        self.assertEqual(len(data['results']), 1)

    def test_product_list_bad_page_params_fall_back(self):
        data = self.get('/api/v1/products/', page='x', page_size='y').json()
        self.assertEqual(data['page'], 1)

    def test_product_detail_includes_variants(self):
        data = self.get(f'/api/v1/products/{self.p1.pk}/').json()
        self.assertEqual(data['name'], 'Blue Shirt')
        self.assertEqual(len(data['variants']), 1)
        v = data['variants'][0]
        self.assertEqual(v['size'], 'XL')
        self.assertEqual(v['color'], 'Blue')
        self.assertEqual(v['stock'], 5)
        self.assertTrue(data['in_stock'])

    def test_product_detail_404_for_missing_or_inactive(self):
        self.assertEqual(self.get('/api/v1/products/999999/').status_code, 404)

    def test_absolute_urls_in_payload(self):
        data = self.get(f'/api/v1/products/{self.p1.pk}/').json()
        self.assertTrue(data['url'].startswith('http'))

    def test_categories_and_brands_endpoints(self):
        cats = self.get('/api/v1/categories/').json()['results']
        self.assertEqual(cats[0]['slug'], 'shirts')
        brands = self.get('/api/v1/brands/').json()['results']
        self.assertEqual(brands[0]['slug'], 'nike')


@override_settings(BOT_API_KEY=API_KEY)
class ApiRateLimitTest(TestCase):
    def test_429_after_limit(self):
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()
        with patch('api.views.RATE_LIMIT_PER_MINUTE', 3):
            codes = [self.client.get('/api/v1/categories/', HTTP_X_API_KEY=API_KEY).status_code
                     for _ in range(5)]
        self.assertEqual(codes[:3], [200, 200, 200])
        self.assertIn(429, codes[3:])


@override_settings(BOT_API_KEY=API_KEY)
class ApiWholesaleMaskTest(TestCase):
    def test_wholesale_price_is_null_in_api(self):
        p = make_product('Bulk Jacket', 900000)
        p.is_wholesale = True
        p.save()
        resp = self.client.get(f'/api/v1/products/{p.pk}/', HTTP_X_API_KEY=API_KEY).json()
        self.assertTrue(resp['is_wholesale'])
        self.assertIsNone(resp['price'])
