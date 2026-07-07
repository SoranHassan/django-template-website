from django.test import TestCase


class SecurityTest(TestCase):
    def test_security_headers(self):
        response = self.client.get('/')
        self.assertEqual(response['Referrer-Policy'], 'strict-origin-when-cross-origin')
        self.assertIn('geolocation', response['Permissions-Policy'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_custom_404(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)


class DjangoDefaultPagesEnglishTest(TestCase):
    def test_admin_login_is_english(self):
        """صفحات پیش‌فرض جنگو (ادمین) باید انگلیسی باشند"""
        response = self.client.get('/admin/login/?next=/admin/')
        self.assertContains(response, 'Log in')
