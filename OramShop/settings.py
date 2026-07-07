from pathlib import Path

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent



# SECURITY
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())


# APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # third-part apps
    'django_celery_beat',
    'django_celery_results',
    'axes',
    'storages',

    # local apps
    'accounts',
    'catalog',
    'cart',
    'orders',
    'reviews',
    'dashboard',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'OramShop.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'OramShop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.cart_context',
                'core.context_processors.wishlist_context',
                'core.context_processors.dashboard_context',
                'core.context_processors.announcements_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'OramShop.wsgi.application'



# POSTGRESQL DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 60,
    }
}

# REDIS
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'TIMEOUT': 300,
    }
}

# cached_db: سرعت کش + ماندگاری در دیتابیس (با ری‌استارت Redis سشن‌ها نمی‌پرند)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'


# CELERY
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


# AUTHENTICATION
AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'catalog:index'
LOGOUT_REDIRECT_URL = 'catalog:index'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]



# DJANGO-AXES (BRUTE FORCE)
AXES_FAILURE_LIMIT = config('DJANGO_AXES_FAILURE_LIMIT', default=5, cast=int)
AXES_COOLOFF_TIME = config('DJANGO_AXES_COOLOFF_TIME', default=1, cast=int)
AXES_LOCK_OUT_AT_FAILURE = True
AXES_USER_AGENT = True
AXES_RESET_ON_SUCCESS = True



# REGION SETTINGS
# en-us: صفحات پیش‌فرض جنگو (ادمین، خطاها، پیام‌های فرم) کاملاً انگلیسی نمایش داده می‌شوند
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True


# MEDIA FILES & STATIC FILES
USE_S3 = config('USE_S3', default=False, cast=bool)

STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if USE_S3:
    # S3 / MINIO
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_S3_FILE_OVERWRITE = False

    # از Django 5.1 به بعد STATICFILES_STORAGE و DEFAULT_FILE_STORAGE حذف شده‌اند و باید STORAGES استفاده شود
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'},
        'staticfiles': {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'},
    }

    STATIC_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/static/'
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/media/'

else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

    # LOCAL STATIC
    STATIC_URL = 'static/'

    # LOCAL MEDIA
    MEDIA_URL = 'media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# EMAIL
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER')


# SMS.IR SERVICE OTP
SMS_IR_API_KEY = config('SMS_IR_API_KEY')
SMS_IR_LINE_NUMBER = config('SMS_IR_LINE_NUMBER')
SMS_IR_TEMPLATE_ID = config('SMS_IR_TEMPLATE_ID')


# ZARINPAL TERMINAL
ZARINPAL_MERCHANT_ID = config('ZARINPAL_MERCHANT_ID')
ZARINPAL_SANDBOX = config('ZARINPAL_SANDBOX', default=True, cast=bool)


# SECURITY (همه محیط‌ها)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # ۲ هفته
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# دامنه‌های مجاز برای CSRF (پشت پروکسی/دامنه اصلی)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# PRODUCTION SECURITY
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# LOGS
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        # خطاهای برنامه — چرخشی، حداکثر ۵ فایل ۵ مگابایتی
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'error.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # رخدادهای امنیتی (CSRF، لاگین ناموفق، ...)
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'security.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # رخدادهای کسب‌وکار: پرداخت، سفارش، OTP
        'app_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'simple',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'error_file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'axes': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # لاگر اختصاصی پروژه — استفاده: logging.getLogger('oramshop')
        'oramshop': {
            'handlers': ['app_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

