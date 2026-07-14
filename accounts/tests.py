from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from OramShop.test_utils import make_user
from .models import CustomUser, OTP


class LoginTest(TestCase):
    def setUp(self):
        make_user(mobile='09120000001')

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'),
                                    {'mobile': '09120000001', 'password': 'pass12345'})
        self.assertRedirects(response, reverse('catalog:index'), fetch_redirect_response=False)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('accounts:login'),
                                    {'mobile': '09120000001', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['error'])

    def test_external_next_rejected(self):
        """Prevent open redirects."""
        response = self.client.post(reverse('accounts:login') + '?next=https://evil.com',
                                    {'mobile': '09120000001', 'password': 'pass12345'})
        self.assertRedirects(response, reverse('catalog:index'), fetch_redirect_response=False)

    def test_internal_next_allowed(self):
        response = self.client.post(reverse('accounts:login') + '?next=/cart/',
                                    {'mobile': '09120000001', 'password': 'pass12345'})
        self.assertRedirects(response, '/cart/', fetch_redirect_response=False)


class OTPTest(TestCase):
    def tearDown(self):
        cache.clear()

    @patch('accounts.views.send_otp_sms')
    def test_send_otp_rate_limited(self, mock_sms):
        for _ in range(5):
            ok = self.client.post(reverse('accounts:send_otp'), {'mobile': '09121111111'})
            self.assertEqual(ok.status_code, 200)
        over = self.client.post(reverse('accounts:send_otp'), {'mobile': '09121111111'})
        self.assertEqual(over.status_code, 429)

    def test_verify_otp_attempts_limited(self):
        """The 6-digit code must not be guessable with unlimited attempts."""
        OTP.objects.create(mobile='09122222222', code='123456',
                           expires_at=timezone.now() + timedelta(minutes=2))
        url = reverse('accounts:verify_otp')
        for _ in range(5):
            self.client.post(url, {'mobile': '09122222222', 'code': '000000'})
        blocked = self.client.post(url, {'mobile': '09122222222', 'code': '123456'})
        self.assertContains(blocked, 'بیش از حد مجاز')
        self.assertFalse(OTP.objects.get(mobile='09122222222').is_used)

    def test_correct_code_resets_attempts(self):
        OTP.objects.create(mobile='09123333333', code='654321',
                           expires_at=timezone.now() + timedelta(minutes=2))
        url = reverse('accounts:verify_otp')
        self.client.post(url, {'mobile': '09123333333', 'code': '000000'})
        response = self.client.post(url, {'mobile': '09123333333', 'code': '654321'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(cache.get('otp_verify_attempts:09123333333'))

    def test_expired_otp_rejected(self):
        OTP.objects.create(mobile='09124444444', code='111111',
                           expires_at=timezone.now() - timedelta(minutes=1))
        response = self.client.post(reverse('accounts:verify_otp'),
                                    {'mobile': '09124444444', 'code': '111111'})
        self.assertContains(response, 'اشتباه یا منقضی')


class SignupTest(TestCase):
    @patch('accounts.views.send_otp_sms')
    def test_signup_then_verify_creates_user(self, mock_sms):
        response = self.client.post(reverse('accounts:signup'), {
            'mobile': '09125555555', 'first_name': 'سوران', 'last_name': 'حسن',
            'password': 'pass12345', 'confirm_password': 'pass12345'})
        self.assertRedirects(response, reverse('accounts:verify_otp'), fetch_redirect_response=False)

        code = OTP.objects.get(mobile='09125555555').code
        self.client.post(reverse('accounts:verify_otp'), {'mobile': '09125555555', 'code': code})
        self.assertTrue(CustomUser.objects.filter(mobile='09125555555').exists())

    def test_password_mismatch(self):
        response = self.client.post(reverse('accounts:signup'), {
            'mobile': '09125555555', 'password': 'a12345678', 'confirm_password': 'b12345678'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OTP.objects.exists())

    def test_duplicate_mobile(self):
        make_user(mobile='09125555555')
        response = self.client.post(reverse('accounts:signup'), {
            'mobile': '09125555555', 'password': 'pass12345', 'confirm_password': 'pass12345'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OTP.objects.exists())

    def test_invalid_mobile_rejected(self):
        response = self.client.post(reverse('accounts:signup'), {
            'mobile': '12345', 'password': 'pass12345', 'confirm_password': 'pass12345'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OTP.objects.exists())


class ProfileTest(TestCase):
    def test_user_stays_logged_in_after_password_change(self):
        user = make_user(mobile='09126666666', password='oldpass123')
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:profile_info'), {
            'first_name': 'a', 'last_name': 'b', 'email': '', 'bio': '',
            'current_password': 'oldpass123', 'new_password': 'newpass123'})
        self.assertContains(response, 'موفقیت')
        check = self.client.get(reverse('accounts:profile_info'))
        self.assertEqual(check.status_code, 200)


class PasswordResetOtpFlowTest(TestCase):
    """Full OTP-based password recovery: mobile -> OTP -> new password."""

    @patch('accounts.views.send_otp_sms')
    def test_full_reset_flow(self, mock_sms):
        from OramShop.test_utils import make_user
        from accounts.models import OTP
        user = make_user(mobile='09123334444', password='OldPass123')

        # step 1: request the code
        response = self.client.post('/accounts/forgot-password/', {'mobile': '09123334444'})
        self.assertEqual(response.status_code, 302)
        otp = OTP.objects.filter(mobile='09123334444').latest('created_at')

        # step 2: verify the code
        response = self.client.post('/accounts/verify-otp/',
                                    {'mobile': '09123334444', 'code': otp.code})
        self.assertEqual(response.status_code, 302)

        # step 3: set the new password
        response = self.client.post('/accounts/reset-password/', {
            'password': 'NewSecret456', 'confirm_password': 'NewSecret456'})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewSecret456'))


class RelatedRowsOnPagesTest(TestCase):
    """Every page shows a related-products slider above the features strip."""

    def test_login_page_has_product_row(self):
        from OramShop.test_utils import make_product
        make_product(slug='row-check')
        response = self.client.get('/accounts/login/')
        self.assertContains(response, 'products-row-slider')
