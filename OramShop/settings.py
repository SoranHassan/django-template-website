from pathlib import Path

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent



# SECURITY
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Lightweight development mode (e.g. on Windows): no Redis, PostgreSQL or Celery worker.
# Setting DEV_MODE=True in .env is enough - sqlite database and in-memory cache.
DEV_MODE = config('DEV_MODE', default=False, cast=bool)

# Bumped on each release: appended to the stylesheet URL so browsers never
# serve a stale cached styles.css after an update
ASSET_VERSION = '35'

# Goftino live-chat widget id (loaded in the base template when set)
GOFTINO_ID = config('GOFTINO_ID', default='')

# Static key for the JSON API used by the Telegram bot (empty = API disabled)
BOT_API_KEY = config('BOT_API_KEY', default='')

# Hidden panel URLs (changeable via .env so they cannot be guessed)

ADMIN_URL = config('ADMIN_URL', default='admin/').strip('/') + '/'
DASHBOARD_URL = config('DASHBOARD_URL', default='dashboard/').strip('/') + '/'


# APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',

    # third-part apps
    'django_celery_beat',
    'django_celery_results',
    'axes',
    'storages',
    'django_ckeditor_5',
    'rest_framework',

    # local apps
    'accounts',
    'catalog',
    'cart',
    'orders',
    'reviews',
    'dashboard',
    'core',
    'blog',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'OramShop.middleware.SecurityHeadersMiddleware',
    'OramShop.middleware.VisitTrackingMiddleware',
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
                'core.context_processors.categories_context',
                'core.context_processors.wishlist_context',
                'core.context_processors.dashboard_context',
                'core.context_processors.announcements_context',
                'core.context_processors.site_settings_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'OramShop.wsgi.application'



if DEV_MODE:
    # sqlite + in-memory cache - no external services needed
    DATABASES = {
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}
    }
    CACHES = {
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
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

    # cached_db: cache speed + database persistence (sessions survive Redis restarts)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    SESSION_CACHE_ALIAS = 'default'


# CELERY
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='memory://')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='cache+memory://')
# CELERY_EAGER=False in .env lets you run a real worker even in DEV_MODE
CELERY_EAGER = config('CELERY_EAGER', default=DEV_MODE, cast=bool)
if CELERY_EAGER:
    # No worker: tasks run immediately in the same process
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = False
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Periodic tasks live in the database (django-celery-beat) and are fully
# editable from the admin panel - see core.apps.create_default_periodic_tasks
# for the defaults seeded after migrate. Schedule changes need NO restart.


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
# The login form field is `mobile`, not the default `username`; without this
# axes records every attempt as user=None and never groups them.
AXES_USERNAME_FORM_FIELD = 'mobile'
# Behind nginx the app talks over a unix socket, so REMOTE_ADDR has no IP and
# django-ipware (used by axes by default) ignored X-Real-IP and bucketed every
# attacker under one key -> a single attacker could lock out all users. Read the
# nginx-set, un-spoofable X-Real-IP explicitly instead. See OramShop.security.
AXES_CLIENT_IP_CALLABLE = 'OramShop.security.axes_client_ip'
# Lock by IP only (the axes default). Locking by username too would let anyone
# who knows a customer's mobile number lock that account out on purpose
# (targeted denial of service), which is worse than the distributed-guess risk
# it would prevent - especially since mobile numbers are semi-guessable.
AXES_LOCKOUT_PARAMETERS = ['ip_address']


# DJANGO REST FRAMEWORK
# The public JSON API (api/ app) handles its own X-API-Key gate and rate limit,
# so DRF's default auth/permission/throttle layers are turned off here. Only the
# JSON renderer is enabled (no browsable HTML API) so bot clients always get JSON.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'UNAUTHENTICATED_USER': None,
}


# REGION SETTINGS
# en-us: default Django pages (admin, errors, form messages) are shown fully in English
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

    # Since Django 5.1 STATICFILES_STORAGE and DEFAULT_FILE_STORAGE are removed; STORAGES must be used
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
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='info@example.com')


# SMS.IR SERVICE OTP
SMS_IR_API_KEY = config('SMS_IR_API_KEY', default='')
SMS_IR_LINE_NUMBER = config('SMS_IR_LINE_NUMBER', default='')
SMS_IR_TEMPLATE_ID = config('SMS_IR_TEMPLATE_ID', default='')
# Order-status notification template (verify/pattern). Must contain an
# #ORDER_ID# variable. Overridable from .env without a code change.
SMS_IR_ORDER_TEMPLATE_ID = config('SMS_IR_ORDER_TEMPLATE_ID', default='641503')


# ZARINPAL TERMINAL
ZARINPAL_MERCHANT_ID = config('ZARINPAL_MERCHANT_ID', default='')
ZARINPAL_SANDBOX = config('ZARINPAL_SANDBOX', default=True, cast=bool)


# SECURITY (all environments)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # two weeks
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Trusted origins for CSRF (behind a proxy / main domain)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# PRODUCTION SECURITY
# DEV_MODE is excluded so DEBUG=False can be tested locally (e.g. the real
# 404 page) without being redirected to https
if not DEBUG and not DEV_MODE:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# CKEDITOR 5 (blog rich-text editor - fully local)
CKEDITOR_5_CONFIGS = {
    'default': {
        'language': 'fa',
        'toolbar': ['heading', '|', 'bold', 'italic', 'underline', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', '|',
                    'insertTable', 'undo', 'redo'],
    },
}
CKEDITOR_5_FILE_UPLOAD_PERMISSION = 'staff'


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
        # Application errors - rotating, at most five 5MB files
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'error.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # Security events (CSRF, failed logins, ...)
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'security.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # Business events: payments, orders, OTP
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
        # Project logger - usage: logging.getLogger('oramshop')
        'oramshop': {
            'handlers': ['app_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

