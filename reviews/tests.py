from django.test import TestCase
from django.urls import reverse

from OramShop.test_utils import make_user, make_product
from .models import Review


class ReviewTest(TestCase):
    def setUp(self):
        self.user = make_user(mobile='09129999990')
        self.product, _ = make_product()
        self.url = reverse('reviews:add', kwargs={'slug': self.product.slug})

    def test_login_required(self):
        response = self.client.post(self.url, {'rating': 5, 'body': 'خوب'})
        self.assertEqual(response.status_code, 302)

    def test_create_review_pending_approval(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'rating': 5, 'body': 'عالی بود'})
        self.assertEqual(response.status_code, 200)
        review = Review.objects.get()
        self.assertFalse(review.is_approved)

    def test_duplicate_review_rejected(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'rating': 5, 'body': 'عالی'})
        response = self.client.post(self.url, {'rating': 1, 'body': 'دوباره'})
        self.assertEqual(response.status_code, 400)

    def test_missing_body_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'rating': 5})
        self.assertEqual(response.status_code, 400)

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'rating': 'abc', 'body': 'متن'})
        self.assertEqual(response.status_code, 400)
