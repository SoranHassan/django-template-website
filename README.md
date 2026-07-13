# OramShop 🛍️

An e-commerce platform for clothing and accessories built with **Django** — featuring a
product catalog with variants (size/color), guest & user carts, Zarinpal online payment,
SMS OTP authentication, coupons, a fully custom management dashboard, real visit
analytics, a JSON API for the Telegram bot, and PDF invoices.

All storefront content is Persian (RTL); the codebase, comments and docs are English.

## Features

### Storefront
- 🔐 Login/signup with a mobile number and one-time SMS code (SMS.ir) + brute-force protection (django-axes)
- 🛒 Guest and user carts (auto-merged after login) with stock control
- ⚡ Quick add-to-cart on product cards: inline size/color/quantity selection without leaving the page
- 💳 Zarinpal online payment with safe verification; stock is decremented only after a successful payment
- 🔁 Payment retry for unpaid orders; auto-cancel of unpaid orders after 30 minutes (Celery)
- 🎟️ Percentage/fixed coupons with global and per-user usage caps
- ⭐ Product reviews with approval flow; average rating shown on product cards
- 📰 Blog app with a CKEditor 5 rich-text editor (fully local, no CDN)
- 📧 Newsletter signup (email or mobile) in the footer; campaigns sent from the dashboard
- 🔎 SEO: sitemap.xml, robots.txt, OG meta tags, Schema.org product markup
- 💬 Goftino live-chat widget (enabled via the `GOFTINO_ID` env variable)
- 🌐 Every asset is self-hosted (fonts, icons, Chart.js, Cropper.js) for national-internet compatibility

### Management dashboard (no Django admin needed)
- Products with variants (size/color/stock/price), size charts (cm), image galleries
- Orders with status flow + SMS notifications + printable PDF invoice (WeasyPrint)
- Categories, brands, coupons, shipping methods, announcements, blog posts
- Home page control: hero banners, category cards, collection vectors, about text, footer info
- **Upload-time image editor**: crop / resize / rotate / flip with Cropper.js;
  banner crops are locked to the exact on-site aspect ratio (WYSIWYG)
- **Real visit analytics**: online-now, daily/monthly visits, unique visitors,
  14-day trend chart and top pages (tracked by a middleware that ignores bots/static/AJAX);
  rows older than 90 days are purged daily by a Celery task
- **Automatic image optimization**: every uploaded image is downscaled to max 1920px
  and recompressed (JPEG/PNG) before storage
- Shop page is paginated (16 products per page) and the home page data is cached
  for 5 minutes with automatic invalidation on content changes
- SEO report with an overall score and actionable suggestions
- Newsletter composer (email + SMS)
- **Permissions**: regular staff admins manage daily operations; site-critical sections
  (banners, home cards, announcements, site settings, SEO, newsletter, user toggles)
  are superuser-only.

### JSON API (Telegram bot)
Lightweight, dependency-free JSON API under `/api/v1/`, authenticated with a static
key sent as the `X-API-Key` header (configure `BOT_API_KEY` in `.env`; empty = disabled).
Rate limited to 120 requests/minute per client IP (429 on excess):

| Endpoint | Description |
|---|---|
| `GET /api/v1/products/` | Paginated list — filters: `q`, `category`, `brand`, `gender`, `page`, `page_size` (max 50) |
| `GET /api/v1/products/<id>/` | Full detail: description, images, variants (size/color/stock/price), rating |
| `GET /api/v1/categories/` | Active categories |
| `GET /api/v1/brands/` | Active brands with logos |

All URLs and images in responses are absolute, ready to be sent by a bot.

Example:
```bash
curl -H "X-API-Key: $BOT_API_KEY" "https://oramshop.ir/api/v1/products/?q=hoodie&page_size=5"
```

## Requirements

- Python 3.11+
- PostgreSQL (production) — sqlite in `DEV_MODE`
- Redis (cache, sessions, Celery broker) — in-memory in `DEV_MODE`
- WeasyPrint system deps (for PDF invoices)

## Quick start (development)

```bash
git clone <repo-url> && cd django-template-website
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# minimal dev configuration:
#   DEV_MODE=True
#   DEBUG=True
#   SECRET_KEY=<anything>
#   ALLOWED_HOSTS=127.0.0.1,localhost

python manage.py migrate
python manage.py seed_demo        # optional demo data (products, brands, reviews, ...)
python manage.py createsuperuser
python manage.py runserver
```

`DEV_MODE=True` switches to sqlite + in-memory cache + eager Celery, so no external
services are needed on a development machine.

## Running the tests

```bash
python manage.py test --settings=OramShop.test_settings
```

The suite covers accounts (OTP, open-redirect protection), cart merging and stock
limits, checkout/payment safety, coupons, dashboard permissions, visit tracking,
the newsletter, the product card/quick-add flow and the whole JSON API.

## Environment variables

See `.env.example` for the full list. Key values:

| Variable | Purpose |
|---|---|
| `DEV_MODE` | `True` = sqlite + in-memory cache + eager Celery (no external services) |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Standard Django settings |
| `ADMIN_URL`, `DASHBOARD_URL` | Hidden panel URLs (hard to guess) |
| `DB_*`, `REDIS_URL` | PostgreSQL / Redis (production) |
| `SMS_IR_API_KEY`, ... | SMS provider for OTP and order notifications |
| `ZARINPAL_*` | Payment gateway |
| `GOFTINO_ID` | Goftino live-chat widget id (empty = widget off) |
| `BOT_API_KEY` | Static key for the Telegram-bot JSON API (empty = API off) |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://oramshop.ir,https://www.oramshop.ir,https://oramshop.com,https://www.oramshop.com` |

## Production deployment notes

1. `DEBUG=False`, strong `SECRET_KEY`, PostgreSQL + Redis configured.
2. `python manage.py collectstatic` and serve `staticfiles/` + `media/` from nginx.
3. Run with gunicorn/uwsgi behind nginx; run a Celery worker + beat for SMS/cleanup tasks.
4. `python manage.py check --deploy` should be clean.

### Two domains (oramshop.ir + oramshop.com)

The standard approach is **one canonical domain + 301 redirects** at the web-server
level (redirects never even reach Django, and search engines consolidate all SEO
signals onto one domain):

1. Pick the canonical domain — for an Iranian audience `oramshop.ir` is the natural
   choice; keep `oramshop.com` as a protective/brand domain.
2. Point the DNS of **both** domains (and their `www` records) at the same server.
3. Issue TLS certificates for all four hostnames (Let's Encrypt supports multiple
   domains in one certificate).
4. nginx configuration:

```nginx
# Canonical site
server {
    listen 443 ssl;
    server_name oramshop.ir;
    # ... ssl_certificate, proxy_pass to gunicorn, static/media locations ...
}

# Everything else -> 301 to the canonical domain
server {
    listen 443 ssl;
    server_name www.oramshop.ir oramshop.com www.oramshop.com;
    return 301 https://oramshop.ir$request_uri;
}

# HTTP -> HTTPS
server {
    listen 80;
    server_name oramshop.ir www.oramshop.ir oramshop.com www.oramshop.com;
    return 301 https://oramshop.ir$request_uri;
}
```

5. Django settings (via `.env`):
   - `ALLOWED_HOSTS=oramshop.ir` (only the canonical host actually reaches Django)
   - `CSRF_TRUSTED_ORIGINS=https://oramshop.ir`
6. In Google Search Console register the canonical domain; the 301s transfer the
   ranking of the secondary domain automatically. The `<link rel="canonical">` tag
   already emitted on every page reinforces this.

## Project layout

```
OramShop/          # settings, urls, middleware (visits + security headers), celery
accounts/          # custom mobile-based user, OTP auth, addresses, wishlist
catalog/           # products, variants, categories, brands, home page
cart/              # guest/user cart with merge-on-login
orders/            # checkout, Zarinpal payment, coupons, shipping, PDF invoices
reviews/           # product reviews with approval
blog/              # blog posts (CKEditor 5)
core/              # site settings, hero slides, newsletter, visit tracking, SEO views
dashboard/         # full custom management panel
api/               # JSON API v1 for the Telegram bot
static/            # self-hosted assets (Vazirmatn, LineIcons, FA6, Chart.js, Cropper.js)
```

## License

Proprietary — built for OramShop (اُرام‌شاپ).
