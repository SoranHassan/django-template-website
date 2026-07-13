from django.test import TestCase
from django.urls import reverse

from OramShop.test_utils import make_user, make_product
from .models import Review


class ReviewTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09129999990')
        self.product, _ = make_product()
        self.url = reverse('reviews:add', kwargs={'slug': self.product.slug})

    def ajax_post(self, data):
        # The site's JS always submits with the AJAX header
        return self.client.post(self.url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_login_required(self):
        response = self.client.post(self.url, {'rating': 5, 'body': 'خوب'})
        self.assertEqual(response.status_code, 302)

    def test_create_review_pending_approval(self):
        self.client.force_login(self.user)
        response = self.ajax_post({'rating': 5, 'body': 'عالی بود'})
        self.assertEqual(response.status_code, 200)
        review = Review.objects.get()
        self.assertFalse(review.is_approved)

    def test_duplicate_review_rejected(self):
        self.client.force_login(self.user)
        self.ajax_post({'rating': 5, 'body': 'عالی'})
        response = self.ajax_post({'rating': 1, 'body': 'دوباره'})
        self.assertEqual(response.status_code, 400)

    def test_missing_body_rejected(self):
        self.client.force_login(self.user)
        response = self.ajax_post({'rating': 5})
        self.assertEqual(response.status_code, 400)

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.user)
        response = self.ajax_post({'rating': 'abc', 'body': 'متن'})
        self.assertEqual(response.status_code, 400)


class ReviewSubmitResponseTest(TestCase):
    """AJAX gets JSON; a plain browser POST is redirected back to the product (no raw JSON page)."""

    @classmethod
    def setUpTestData(cls):
        from OramShop.test_utils import make_user, make_product
        cls.user = make_user(mobile='09126660001')
        cls.product, _ = make_product(slug='review-resp')

    def test_ajax_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('reviews:add', args=[self.product.slug]),
                                    {'rating': 5, 'body': 'خوب'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['status'], 'ok')

    def test_plain_post_redirects_to_product(self):
        from reviews.models import Review
        self.client.force_login(self.user)
        Review.objects.filter(product=self.product).delete()
        response = self.client.post(reverse('reviews:add', args=[self.product.slug]),
                                    {'rating': 4, 'body': 'باز هم خوب'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.product.get_absolute_url())
        self.assertTrue(Review.objects.filter(product=self.product).exists())

    def test_dialog_partial_on_product_page(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'osDialog')
        self.assertContains(response, 'os-dialog-overlay')
