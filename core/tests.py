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
        """Default Django pages (admin) must be English."""
        response = self.client.get('/admin/login/?next=/admin/')
        self.assertContains(response, 'Log in')


class VisitTrackingTest(TestCase):
    """Real visit statistics: the middleware must record page views."""

    def test_html_page_view_is_recorded(self):
        from core.models import SiteVisit
        self.client.get('/', HTTP_USER_AGENT='Mozilla/5.0 (X11; Linux) Chrome/126')
        self.assertEqual(SiteVisit.objects.count(), 1)
        visit = SiteVisit.objects.first()
        self.assertEqual(visit.path, '/')
        self.assertTrue(visit.session_key)

    def test_bots_and_excluded_paths_are_ignored(self):
        from core.models import SiteVisit
        self.client.get('/', HTTP_USER_AGENT='Googlebot/2.1')
        self.client.get('/robots.txt', HTTP_USER_AGENT='Mozilla/5.0 Chrome/126')
        self.client.get('/no-such-page-404/', HTTP_USER_AGENT='Mozilla/5.0 Chrome/126')
        self.assertEqual(SiteVisit.objects.count(), 0)

    def test_ajax_requests_are_ignored(self):
        from core.models import SiteVisit
        self.client.get('/', HTTP_USER_AGENT='Mozilla/5.0 Chrome/126',
                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(SiteVisit.objects.count(), 0)


class NewsletterFooterTest(TestCase):
    """The compact newsletter form lives in the footer on every page."""

    def test_footer_contains_newsletter_form(self):
        response = self.client.get('/')
        self.assertContains(response, 'footerNewsletterForm')

    def test_subscribe_with_email(self):
        from core.models import NewsletterSubscriber
        response = self.client.post('/newsletter/subscribe/', {'email': 'a@b.com'})
        self.assertEqual(response.json()['status'], 'ok')
        self.assertTrue(NewsletterSubscriber.objects.filter(email='a@b.com').exists())

    def test_subscribe_with_mobile(self):
        from core.models import NewsletterSubscriber
        response = self.client.post('/newsletter/subscribe/', {'email': '09121234567'})
        self.assertEqual(response.json()['status'], 'ok')
        self.assertTrue(NewsletterSubscriber.objects.filter(mobile='09121234567').exists())


class GoftinoWidgetTest(TestCase):
    def test_widget_absent_without_id(self):
        with self.settings(GOFTINO_ID=''):
            response = self.client.get('/')
        self.assertNotContains(response, 'goftino.com/widget')

    def test_widget_present_with_id(self):
        with self.settings(GOFTINO_ID='b5HHtR'):
            response = self.client.get('/')
        self.assertContains(response, 'goftino.com/widget')
        self.assertContains(response, 'b5HHtR')


class HomePageStructureTest(TestCase):
    def test_watermark_text_removed(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'off_title')

    def test_features_band_present(self):
        response = self.client.get('/')
        self.assertContains(response, 'os-features-band')

    def test_about_band_uses_site_settings(self):
        from core.models import SiteSetting
        s = SiteSetting.get()
        s.about_home = 'UNIQUE-ABOUT-TEXT-123'
        s.save()
        response = self.client.get('/')
        self.assertContains(response, 'UNIQUE-ABOUT-TEXT-123')


class PurgeOldVisitsTest(TestCase):
    def test_only_old_visits_are_deleted(self):
        from datetime import timedelta
        from django.utils import timezone
        from core.models import SiteVisit
        from core.tasks import purge_old_visits
        old = SiteVisit.objects.create(session_key='old', path='/')
        SiteVisit.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=120))
        SiteVisit.objects.create(session_key='new', path='/')
        deleted = purge_old_visits(days=90)
        self.assertEqual(deleted, 1)
        self.assertEqual(SiteVisit.objects.count(), 1)
        self.assertEqual(SiteVisit.objects.first().session_key, 'new')


class OptimizeImageTest(TestCase):
    def _big_jpeg(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = io.BytesIO()
        Image.effect_noise((3000, 2000), 60).convert('RGB').save(buf, format='JPEG', quality=98)
        buf.seek(0)
        return SimpleUploadedFile('big.jpg', buf.read(), content_type='image/jpeg')

    def test_large_jpeg_is_downscaled_and_compressed(self):
        from PIL import Image
        from core.utils import optimize_image
        up = self._big_jpeg()
        out = optimize_image(up)
        self.assertLess(out.size, up.size)
        img = Image.open(out)
        self.assertLessEqual(max(img.size), 1920)

    def test_svg_passes_through_untouched(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.utils import optimize_image
        svg = SimpleUploadedFile('logo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>' * 20000,
                                 content_type='image/svg+xml')
        self.assertIs(optimize_image(svg), svg)


class RuntimeConfigTest(TestCase):
    """DB value (site settings) overrides .env; empty DB falls back to .env."""

    def test_fallback_to_env(self):
        from core.utils import runtime_config
        with self.settings(GOFTINO_ID='env-id'):
            self.assertEqual(runtime_config('goftino_id_override', 'GOFTINO_ID'), 'env-id')

    def test_db_overrides_env(self):
        from core.models import SiteSetting
        from core.utils import runtime_config
        s = SiteSetting.get()
        s.goftino_id_override = 'db-id'
        s.zarinpal_merchant_id = 'db-merchant'
        s.save()
        with self.settings(GOFTINO_ID='env-id', ZARINPAL_MERCHANT_ID='env-merchant'):
            self.assertEqual(runtime_config('goftino_id_override', 'GOFTINO_ID'), 'db-id')
            self.assertEqual(runtime_config('zarinpal_merchant_id', 'ZARINPAL_MERCHANT_ID'), 'db-merchant')

    def test_zarinpal_uses_runtime_merchant(self):
        from core.models import SiteSetting
        from orders.zarinpal import get_merchant_id
        s = SiteSetting.get()
        s.zarinpal_merchant_id = 'panel-merchant-id'
        s.save()
        self.assertEqual(get_merchant_id(), 'panel-merchant-id')


class CollectionColorTest(TestCase):
    def test_custom_colors_render_on_home(self):
        from core.models import SiteSetting
        s = SiteSetting.get()
        s.men_collection_color = '#123456'
        s.women_collection_color = '#654321'
        s.save()
        response = self.client.get('/')
        self.assertContains(response, '#123456')
        self.assertContains(response, '#654321')


class PanelEditablePeriodicTasksTest(TestCase):
    """All periodic tasks are DB rows (django-celery-beat) editable from the panel."""

    def test_default_periodic_tasks_seeded(self):
        from django_celery_beat.models import PeriodicTask
        names = set(PeriodicTask.objects.values_list('task', flat=True))
        self.assertIn('accounts.tasks.cleanup_expired_otps', names)
        self.assertIn('core.tasks.purge_old_visits', names)
        self.assertIn('orders.tasks.auto_cancel_unpaid_orders', names)

    def test_no_hardcoded_beat_schedule(self):
        from django.conf import settings
        self.assertFalse(getattr(settings, 'CELERY_BEAT_SCHEDULE', {}))


class GlobalAlertTest(TestCase):
    """Panel-editable, non-dismissible site-wide alert."""

    def test_hidden_when_empty(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'os-global-alert')

    def test_shown_on_all_pages_without_close_button(self):
        from core.models import SiteSetting
        s = SiteSetting.get()
        s.global_alert = 'ارسال سفارش‌ها به دلیل تعطیلات با تأخیر انجام می‌شود'
        s.global_alert_style = 'warning'
        s.save()
        for url in ['/', '/shop/', '/accounts/login/']:
            response = self.client.get(url)
            self.assertContains(response, 'os-global-alert-warning')
            self.assertContains(response, 'با تأخیر انجام می‌شود')
            # non-dismissible: no close control inside the alert
            html = response.content.decode()
            alert = html.split('os-global-alert', 1)[1].split('</div>', 1)[0]
            self.assertNotIn('close', alert)
