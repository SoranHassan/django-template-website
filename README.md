# OramShop 🛍️

فروشگاه اینترنتی پوشاک و اکسسوری ساخته‌شده با **Django** — شامل کاتالوگ محصولات با واریانت (سایز/رنگ)، سبد خرید، پرداخت زرین‌پال، احراز هویت با OTP پیامکی، کد تخفیف، پنل مدیریت اختصاصی و فاکتور PDF.

## امکانات

- 🔐 ورود/ثبت‌نام با شماره موبایل و کد یکبارمصرف (SMS.ir) + محافظت brute-force با django-axes
- 🛒 سبد خرید مهمان و کاربر (با ادغام خودکار بعد از ورود) و کنترل موجودی
- 💳 پرداخت آنلاین زرین‌پال با تأیید امن و کسر موجودی بعد از پرداخت موفق
- 🎟️ کد تخفیف درصدی/مبلغ ثابت با سقف استفاده کلی و per-user
- 📊 داشبورد مدیریت: محصولات، سفارش‌ها، کاربران، نظرات و گزارش فروش
- 📄 فاکتور PDF (WeasyPrint)، پیامک وضعیت سفارش، پاک‌سازی خودکار OTP (Celery)
- 🔎 سئو: sitemap.xml، robots.txt، متاتگ‌های OG و Schema.org روی صفحات محصول

## پیش‌نیازها

- Python 3.11+
- PostgreSQL
- Redis (برای کش، سشن و صف Celery)

## راه‌اندازی

```bash
# 1) دریافت کد و ساخت محیط مجازی
git clone https://github.com/SoranHassan/django-template-website.git
cd django-template-website
python -m venv venv && source venv/bin/activate

# 2) نصب وابستگی‌ها
pip install -r requirements.txt

# 3) تنظیمات محیطی
cp .env.example .env
# مقادیر .env را ویرایش کنید (دیتابیس، Redis، کلیدها)

# 4) دیتابیس
python manage.py migrate
python manage.py createsuperuser

# 5) اجرا
python manage.py runserver
```

### Celery (در ترمینال‌های جدا)

```bash
celery -A OramShop worker -l info
celery -A OramShop beat -l info
```

## تست‌ها

تست‌ها بدون نیاز به PostgreSQL و Redis و فایل `.env` اجرا می‌شوند:

```bash
python manage.py test --settings=OramShop.test_settings
```

## ساختار پروژه

| اپ | مسئولیت |
|---|---|
| `accounts` | کاربر سفارشی (موبایل‌محور)، OTP، پروفایل، آدرس‌ها |
| `catalog` | برند، دسته‌بندی، محصول، واریانت، جدول سایز |
| `cart` | سبد خرید مهمان/کاربر |
| `orders` | سفارش، کوپن، پرداخت زرین‌پال، فاکتور PDF |
| `reviews` | نظرات با تأیید ادمین |
| `dashboard` | پنل مدیریت فروشگاه (staff) |
| `core` | تمپلیت‌های پایه، context processor ها، صفحه 404 |

## لاگ‌ها

در پوشه `logs/` (چرخشی، حداکثر ۵×۵MB):

- `error.log` — خطاهای برنامه
- `security.log` — رخدادهای امنیتی (CSRF، تلاش‌های ورود ناموفق axes)
- `app.log` — رخدادهای کسب‌وکار (پرداخت‌ها، سفارش‌ها، OTP)

## نکات production

- `DEBUG=False` و `ZARINPAL_SANDBOX=False` را در `.env` تنظیم کنید
- `ALLOWED_HOSTS` و `CSRF_TRUSTED_ORIGINS` را با دامنه واقعی پر کنید
- با `DEBUG=False`، ریدایرکت HTTPS و HSTS و کوکی‌های امن خودکار فعال می‌شوند
- `python manage.py collectstatic` را اجرا کنید (یا `USE_S3=True` با تنظیمات MinIO/S3)
