"""
تنظیمات مخصوص اجرای تست‌ها — بدون نیاز به .env، پستگرس یا Redis
اجرا:  python manage.py test --settings=OramShop.test_settings
"""
import os

# مقادیر پیش‌فرض برای متغیرهای محیطی اجباری (فقط برای تست)
_TEST_ENV_DEFAULTS = {
    'SECRET_KEY': 'test-secret-key-not-for-production',
    'DEBUG': 'False',
    'ALLOWED_HOSTS': 'localhost,testserver',
    'DB_NAME': 'test', 'DB_USER': 'test', 'DB_PASSWORD': 'test',
    'REDIS_URL': 'redis://localhost:6379/1',
    'CELERY_BROKER_URL': 'redis://localhost:6379/0',
    'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    'EMAIL_HOST': 'localhost', 'EMAIL_PORT': '25', 'EMAIL_USE_TLS': 'False',
    'EMAIL_HOST_USER': 'test@example.com', 'EMAIL_HOST_PASSWORD': 'test',
    'SMS_IR_API_KEY': 'test', 'SMS_IR_LINE_NUMBER': '3000', 'SMS_IR_TEMPLATE_ID': '1',
    'ZARINPAL_MERCHANT_ID': 'test',
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

from OramShop.settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# در محیط تست لازم نیست
AXES_ENABLED = False
SECURE_SSL_REDIRECT = False

# هش سریع‌تر برای سرعت تست‌ها
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
