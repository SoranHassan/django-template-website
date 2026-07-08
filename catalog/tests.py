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
    """همه تمپلیت‌ها باید بدون خطای سینتکس لود شوند.
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
