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


class SuperuserOnlySectionsTest(TestCase):
    """Site-critical sections must reject regular staff admins (403)."""

    SUPER_ONLY = ['hero_list', 'home_cards_list', 'announcements_list',
                  'site_settings', 'seo', 'newsletter']

    @classmethod
    def setUpTestData(cls):
        cls.staff = make_user(mobile='09127777771', is_staff=True)
        cls.boss = make_user(mobile='09127777772', is_staff=True, is_superuser=True)

    def test_staff_admin_gets_403(self):
        self.client.force_login(self.staff)
        for name in self.SUPER_ONLY:
            response = self.client.get(reverse(f'dashboard:{name}'))
            self.assertEqual(response.status_code, 403, f'dashboard:{name} not protected')

    def test_superuser_gets_200(self):
        self.client.force_login(self.boss)
        for name in self.SUPER_ONLY:
            response = self.client.get(reverse(f'dashboard:{name}'))
            self.assertEqual(response.status_code, 200, f'dashboard:{name} failed')

    def test_staff_still_reaches_daily_sections(self):
        self.client.force_login(self.staff)
        for name in ['index', 'products_list', 'orders_list', 'blog_list']:
            response = self.client.get(reverse(f'dashboard:{name}'))
            self.assertEqual(response.status_code, 200, f'dashboard:{name} failed')


class HomeCardsCrudTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.boss = make_user(mobile='09127777773', is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.boss)

    def test_create_edit_delete_card(self):
        from core.models import HomeCategoryCard
        self.client.post(reverse('dashboard:home_card_create'),
                         {'title': 'تیشرت', 'link': '/shop/?category=tshirt', 'order': 1})
        card = HomeCategoryCard.objects.get(title='تیشرت')
        self.client.post(reverse('dashboard:home_card_edit', args=[card.pk]),
                         {'title': 'هودی', 'link': card.link, 'order': 2})
        card.refresh_from_db()
        self.assertEqual(card.title, 'هودی')
        self.client.post(reverse('dashboard:home_card_delete', args=[card.pk]))
        self.assertFalse(HomeCategoryCard.objects.filter(pk=card.pk).exists())


class ReviewApproveTest(TestCase):
    """Approving a review from the panel must actually persist (was broken: GET to a POST view)."""

    @classmethod
    def setUpTestData(cls):
        from reviews.models import Review
        cls.staff = make_user(mobile='09127777774', is_staff=True)
        cls.customer = make_user(mobile='09127777775')
        cls.product, _ = make_product(slug='rev-prod')
        cls.review = Review.objects.create(product=cls.product, user=cls.customer,
                                           rating=5, body='عالی', is_approved=False)

    def test_post_toggles_approval(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('dashboard:review_approve', args=[self.review.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['is_approved'], True)
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_approved)

    def test_get_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('dashboard:review_approve', args=[self.review.pk]))
        self.assertEqual(response.status_code, 405)
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_approved)

    def test_button_uses_generated_url_and_post(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('dashboard:reviews_list'))
        self.assertContains(response, 'data-url=')
        self.assertContains(response, "method: 'POST'")
