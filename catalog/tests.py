from pathlib import Path

from django.template.loader import get_template
from django.test import TestCase
from django.urls import reverse

from OramShop.test_utils import make_product


class PublicPagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product, cls.variant = make_product()

    def test_home(self):
        response = self.client.get(reverse('catalog:index'))
        self.assertEqual(response.status_code, 200)

    def test_shop_list_and_filters(self):
        for query in ['', '?sort=price_low', '?q=تست', '?gender=men']:
            response = self.client.get(reverse('catalog:shop_style_1') + query)
            self.assertEqual(response.status_code, 200, f'shop {query} failed')

    def test_product_detail(self):
        response = self.client.get(reverse('catalog:product_detail', kwargs={'id': self.product.pk}))
        self.assertEqual(response.status_code, 200)

    def test_inactive_product_404(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(reverse('catalog:product_detail', kwargs={'id': self.product.pk}))
        self.assertEqual(response.status_code, 404)


class TemplateSyntaxTest(TestCase):
    """Every template must load without a syntax error.
    (محافظت در برابر فرمت‌کننده‌هایی که تگ‌های جنگو را می‌شکنند)"""

    def test_all_templates_parse(self):
        base_dir = Path(__file__).resolve().parent.parent
        failures = []
        for template_path in sorted(base_dir.glob('*/templates/**/*.html')):
            parts = template_path.parts
            template_name = '/'.join(parts[parts.index('templates') + 1:])
            try:
                get_template(template_name)
            except Exception as exc:
                failures.append(f'{template_name}: {exc}')
        self.assertEqual(failures, [], 'تمپلیت‌های خراب:\n' + '\n'.join(failures))


class SEOTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product, _ = make_product(slug='seo-product', name='کفش تست')

    def test_sitemap(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/shop/{self.product.pk}/')

    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sitemap:')
        self.assertContains(response, 'Disallow: /admin/')

    def test_product_page_structured_data(self):
        response = self.client.get(reverse('catalog:product_detail', kwargs={'id': self.product.pk}))
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'og:title')
        self.assertContains(response, 'rel="canonical"')

    def test_dynamic_title(self):
        response = self.client.get(reverse('catalog:product_detail', kwargs={'id': self.product.pk}))
        self.assertContains(response, '<title>خرید کفش تست | OramShop</title>', html=False)


class PriceFormattingTest(TestCase):
    def test_prices_have_thousand_separators(self):
        product, _ = make_product(price=1890000, slug='price-test', name='محصول قیمت')
        response = self.client.get(reverse('catalog:product_detail', kwargs={'id': product.pk}))
        self.assertContains(response, '1,890,000')


class ProductCardTest(TestCase):
    """Shared product card: rating badge, brand line and quick-add markup."""

    @classmethod
    def setUpTestData(cls):
        cls.product, cls.variant = make_product()

    def test_shop_uses_shared_card_with_quickadd(self):
        response = self.client.get(reverse('catalog:shop_style_1'))
        self.assertContains(response, 'os-product-card')
        self.assertContains(response, 'os-card-addbtn')
        self.assertContains(response, 'qa-variants')

    def test_card_shows_rating_when_reviewed(self):
        from OramShop.test_utils import make_user
        from reviews.models import Review
        Review.objects.create(product=self.product, user=make_user(mobile='09125550001'),
                              rating=4, body='خوب', is_approved=True)
        response = self.client.get(reverse('catalog:shop_style_1'))
        self.assertContains(response, 'os-card-rating')

    def test_card_hides_rating_without_reviews(self):
        response = self.client.get(reverse('catalog:shop_style_1'))
        self.assertNotContains(response, 'os-card-rating')


class QuickAddToCartTest(TestCase):
    """The inline size/color/qty quick-add posts straight to the cart API."""

    @classmethod
    def setUpTestData(cls):
        cls.product, cls.variant = make_product(stock=3)

    def test_add_variant_to_cart(self):
        response = self.client.post('/cart/add/', {
            'variant_id': self.variant.pk, 'quantity': 2})
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 2)

    def test_add_over_stock_fails(self):
        response = self.client.post('/cart/add/', {
            'variant_id': self.variant.pk, 'quantity': 99})
        self.assertNotEqual(response.json().get('status'), 'ok')
