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
