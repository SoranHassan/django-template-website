# راهنمای کامل استقرار OramShop روی سرور اصلی

<div dir="rtl">

این راهنما شما را قدم‌به‌قدم از **خرید سرور** تا **بالا آمدن کامل سایت روی دامنه oramshop.ir** همراهی می‌کند.
هر دستوری که می‌بینید را به همان ترتیب اجرا کنید. هر جا مقداری باید عوض شود با `<...>` مشخص شده است.

---

## فهرست

1. [خرید سرور و مشخصات پیشنهادی](#۱-خرید-سرور)
2. [اتصال اولیه و امن‌سازی سرور](#۲-اتصال-اولیه-و-امنسازی-سرور)
3. [نصب پیش‌نیازها](#۳-نصب-پیشنیازها)
4. [ساخت دیتابیس PostgreSQL](#۴-ساخت-دیتابیس)
5. [انتقال کد به سرور](#۵-انتقال-کد-به-سرور)
6. [فایل env. — توضیح تک‌تک متغیرها](#۶-فایل-env)
7. [آماده‌سازی جنگو](#۷-آمادهسازی-جنگو)
8. [سرویس‌های systemd (gunicorn + celery)](#۸-سرویسهای-systemd)
9. [nginx و گواهی SSL](#۹-nginx-و-ssl)
10. [تنظیم DNS دامنه](#۱۰-dns)
11. [چک‌لیست امنیتی نهایی](#۱۱-چکلیست-امنیتی)
12. [بکاپ‌گیری خودکار](#۱۲-بکاپگیری)
13. [آپدیت‌های بعدی سایت](#۱۳-آپدیتهای-بعدی)
14. [عیب‌یابی و دستورهای پرکاربرد](#۱۴-عیبیابی)

---

## ۱. خرید سرور

### چه سروری بخرم؟

**سرور مجازی (VPS) ایرانی** بگیرید، به دو دلیل:

- زرین‌پال و SMS.ir به IP ایران راحت‌تر سرویس می‌دهند و مشکل تحریم/فیلترینگ ندارید؛
- سرعت لود سایت برای مشتری ایرانی چند برابر بهتر است (مخصوصاً در «اینترنت ملی»).

ارائه‌دهنده‌های شناخته‌شده: آروان‌کلود، پارس‌پک، ایران‌سرور، آسیاتک، لیموهاست. فرقی نمی‌کند کدام — مشخصات مهم است.

### مشخصات پیشنهادی برای شروع

| منبع | حداقل | پیشنهادی |
|---|---|---|
| CPU | 2 هسته | 4 هسته |
| RAM | 2 GB | 4 GB |
| دیسک | 25 GB SSD/NVMe | 50 GB NVMe |
| سیستم‌عامل | **Ubuntu Server 24.04 LTS** | همان |
| ترافیک ماهانه | 1 TB | نامحدود/بیشتر |

> با 4GB RAM: جنگو + PostgreSQL + Redis + Celery همه راحت روی یک سرور جا می‌شوند. بعداً که فروش زیاد شد می‌توانید ارتقا دهید — نیازی به تصمیم بزرگ الان نیست.

موقع خرید یک **IP ثابت (IPv4)** می‌گیرید — همان را برای DNS لازم دارید.

---

## ۲. اتصال اولیه و امن‌سازی سرور

بعد از خرید، پنل ارائه‌دهنده یک IP و رمز root می‌دهد.

### ۲.۱. اولین ورود

از لینوکس/مک (یا PowerShell ویندوز):

```bash
ssh root@<IP-سرور>
```

### ۲.۲. به‌روزرسانی سیستم

```bash
apt update && apt upgrade -y
reboot   # اگر کرنل آپدیت شد
```

### ۲.۳. ساخت کاربر غیر root

هیچ‌وقت با root کار نکنید:

```bash
adduser soran          # رمز قوی بدهید
usermod -aG sudo soran
```

### ۲.۴. ورود با کلید SSH به‌جای رمز (مهم‌ترین قدم امنیتی)

روی **کامپیوتر خودتان** (اگر کلید ندارید):

```bash
ssh-keygen -t ed25519
ssh-copy-id soran@<IP-سرور>
```

حالا تست کنید که `ssh soran@<IP>` بدون رمز وارد می‌شود. سپس روی سرور، ورودِ با رمز و ورودِ root را ببندید:

```bash
sudo nano /etc/ssh/sshd_config
```

این سه خط را پیدا و این‌طور کنید:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

```bash
sudo systemctl restart ssh
```

> ⚠️ قبل از بستن ترمینال، در یک ترمینال دوم تست کنید `ssh soran@<IP>` کار می‌کند — وگرنه پشت در می‌مانید!

### ۲.۵. فایروال UFW

فقط سه پورت لازم داریم:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

> PostgreSQL و Redis پورت باز به بیرون **ندارند** و نباید داشته باشند — فقط localhost.

### ۲.۶. Fail2ban (قفل خودکار IPهای مهاجم به SSH)

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

---

## ۳. نصب پیش‌نیازها

```bash
sudo apt install -y python3 python3-venv python3-pip \
                    postgresql postgresql-contrib \
                    redis-server nginx git \
                    certbot python3-certbot-nginx \
                    libpq-dev build-essential
```

بررسی که همه بالا هستند:

```bash
systemctl status postgresql redis-server nginx --no-pager | grep -E "●|Active"
```

---

## ۴. ساخت دیتابیس

```bash
sudo -u postgres psql
```

داخل psql (رمز قوی و تصادفی بگذارید و یادداشت کنید):

```sql
CREATE DATABASE oramshop;
CREATE USER oramshop WITH PASSWORD '<یک-رمز-قوی-تصادفی>';
ALTER ROLE oramshop SET client_encoding TO 'utf8';
ALTER ROLE oramshop SET default_transaction_isolation TO 'read committed';
ALTER ROLE oramshop SET timezone TO 'Asia/Tehran';
GRANT ALL PRIVILEGES ON DATABASE oramshop TO oramshop;
\c oramshop
GRANT ALL ON SCHEMA public TO oramshop;
\q
```

---

## ۵. انتقال کد به سرور

کد را در `/srv/oramshop` می‌گذاریم (سرویس‌های آماده در پوشه `deploy/` همین مسیر را انتظار دارند):

```bash
sudo mkdir -p /srv/oramshop
sudo chown soran:soran /srv/oramshop
```

### روش الف — با git (اگر مخزن دارید)

```bash
git clone <آدرس-مخزن> /srv/oramshop
```

### روش ب — با bundle (همان فایل‌هایی که تحویل گرفته‌اید)

از کامپیوتر خودتان:

```bash
scp oramshop-v30.bundle soran@<IP>:/tmp/
```

روی سرور:

```bash
git clone /tmp/oramshop-v30.bundle /srv/oramshop -b claude/project-analysis-review-wm914e
```

### محیط مجازی و پکیج‌ها

```bash
cd /srv/oramshop
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt   # شامل gunicorn هم هست
```

---

## ۶. فایل env.

```bash
cd /srv/oramshop
cp .env.example .env
nano .env
```

مقادیر production به این شکل — **تک‌تک متغیرها توضیح داده شده‌اند**:

```env
# ---------- هسته جنگو ----------
# کلید امضای کوکی‌ها و توکن‌ها. لو برود = کل سایت لو رفته.
# با این دستور بسازید و جای‌گذاری کنید:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=<خروجی-دستور-بالا>

# روی سرور اصلی همیشه False. با True جزئیات خطاها به همه نمایش داده می‌شود!
DEBUG=False

# جنگو فقط به درخواست‌هایی با این Host ها جواب می‌دهد (سد حمله Host header)
ALLOWED_HOSTS=oramshop.ir,www.oramshop.ir

# روی سرور همیشه False (True فقط برای توسعه روی لپ‌تاپ بدون Redis/Postgres است)
DEV_MODE=False

# ---------- آدرس‌های مخفی پنل‌ها ----------
# به‌جای /admin/ و /dashboard/ معروف، آدرس غیرقابل حدس بگذارید تا ربات‌ها پیدا نکنند
ADMIN_URL=panel-<چند-حرف-تصادفی>/
DASHBOARD_URL=manage-<چند-حرف-تصادفی>/

# ---------- CSRF ----------
# «فرم‌های ارسالی فقط از این دامنه‌ها معتبرند.»
# جنگو برای هر فرم (ورود، سبد خرید، پرداخت) یک توکن ضدجعل می‌گذارد و موقع دریافت،
# مبدأ (Origin) درخواست را با این لیست مقایسه می‌کند. از جنگو 4 به بعد باید
# دامنه‌ها را با https:// صریح بنویسید، وگرنه بعد از فعال شدن SSL همه فرم‌ها
# خطای CSRF verification failed می‌گیرند. همین دو مقدار کافی است:
CSRF_TRUSTED_ORIGINS=https://oramshop.ir,https://www.oramshop.ir

# ---------- PostgreSQL ----------
DB_NAME=oramshop
DB_USER=oramshop
DB_PASSWORD=<همان-رمزی-که-در-مرحله-۴-ساختید>
DB_HOST=localhost
DB_PORT=5432

# ---------- Redis / Celery ----------
# دیتابیس 1 برای کش صفحات، دیتابیس 0 برای صف تسک‌ها — جدا تا با هم قاطی نشوند
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ---------- ایمیل (خبرنامه و اعلان‌ها) ----------
# از پنل هاست/ارائه‌دهنده ایمیل بگیرید؛ اگر فعلاً ندارید خالی بگذارید
EMAIL_HOST=mail.oramshop.ir
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=info@oramshop.ir
EMAIL_HOST_PASSWORD=<رمز-ایمیل>

# ---------- SMS.ir (کد ورود و پیامک سفارش) ----------
# از پنل sms.ir → توسعه‌دهندگان → کلید API
SMS_IR_API_KEY=<کلید-واقعی>
SMS_IR_LINE_NUMBER=<شماره-خط-شما>
SMS_IR_TEMPLATE_ID=<کد-قالب-تاییدشده>

# ---------- زرین‌پال ----------
# از پنل زرین‌پال → درگاه‌های من → کد مرچنت (۳۶ کاراکتری)
ZARINPAL_MERCHANT_ID=<کد-مرچنت-واقعی>
# روی سرور اصلی حتماً False — با True پرداخت‌ها آزمایشی است و پولی جابه‌جا نمی‌شود!
ZARINPAL_SANDBOX=False

# ---------- django-axes (قفل ضد حدس رمز) ----------
# بعد از ۵ تلاش ناموفق ورود، ۱ ساعت قفل
DJANGO_AXES_FAILURE_LIMIT=5
DJANGO_AXES_COOLOFF_TIME=1

# ---------- فایل‌ها روی S3 (فعلاً لازم نیست) ----------
USE_S3=False

# ---------- گفتینو ----------
GOFTINO_ID=<کد-ویجت-از-پنل-گفتینو>

# ---------- کلید API ربات تلگرام ----------
# اگر ربات ندارید خالی بگذارید (API غیرفعال می‌شود). اگر دارید یک رشته
# تصادفی طولانی بسازید: openssl rand -hex 32
BOT_API_KEY=
```

> 🔐 سه مقدار **حیاتی**: `SECRET_KEY`، `DB_PASSWORD` و `SMS_IR_API_KEY`. این فایل هرگز در git نیست و نباید برای کسی بفرستید. دسترسی فایل را هم محدود کنید:

```bash
chmod 600 /srv/oramshop/.env
```

---

## ۷. آماده‌سازی جنگو

```bash
cd /srv/oramshop
source .venv/bin/activate

python manage.py migrate                # ساخت جدول‌ها + ثبت زمان‌بندی‌های Celery
python manage.py collectstatic --noinput  # جمع‌کردن استاتیک‌ها در staticfiles/
python manage.py createsuperuser        # حساب ادمین خودتان (موبایل + رمز قوی)
python manage.py check --deploy         # بررسی نهایی تنظیمات production
```

`check --deploy` نباید خطای قرمز بدهد (هشدارهای HSTS اگر بود، طبیعی است چون nginx جلوی کار است).

عکس‌های کارت دسته‌بندی‌ها (اگر عکس‌ها را در `media/banners/` گذاشته‌اید):

```bash
python manage.py set_home_category_images
```

### مالکیت فایل‌ها

سرویس‌ها با کاربر `www-data` اجرا می‌شوند:

```bash
sudo chown -R www-data:www-data /srv/oramshop
```

---

## ۸. سرویس‌های systemd

فایل‌های آماده در پوشه `deploy/` هست — فقط کپی و فعال کنید:

```bash
sudo cp /srv/oramshop/deploy/gunicorn.socket  /etc/systemd/system/oramshop.socket
sudo cp /srv/oramshop/deploy/gunicorn.service /etc/systemd/system/oramshop.service
sudo cp /srv/oramshop/deploy/celery.service   /etc/systemd/system/oramshop-celery.service

sudo systemctl daemon-reload
sudo systemctl enable --now oramshop.socket oramshop.service oramshop-celery.service
```

بررسی:

```bash
systemctl status oramshop oramshop-celery --no-pager | grep -E "●|Active"
```

هر دو باید `active (running)` باشند.

- **oramshop.service** = gunicorn (خود سایت)
- **oramshop-celery.service** = ورکر + beat (پیامک‌ها، پاک‌سازی OTP، لغو سفارش‌های پرداخت‌نشده — زمان‌بندی‌ها در پنل ادمین ← Periodic tasks قابل ویرایش‌اند، بدون ری‌استارت)

---

## ۹. nginx و SSL

### ۹.۱. کانفیگ nginx

فایل آماده است:

```bash
sudo cp /srv/oramshop/deploy/nginx-oramshop.conf /etc/nginx/sites-available/oramshop
sudo ln -s /etc/nginx/sites-available/oramshop /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

> نکته: این کانفیگ گواهی SSL می‌خواهد که هنوز نگرفته‌ایم، پس `nginx -t` فعلاً خطا می‌دهد — طبیعی است؛ اول DNS (مرحله ۱۰) بعد certbot.

### ۹.۲. گرفتن گواهی رایگان Let's Encrypt

**بعد از** ست شدن DNS. اگر فقط دامنه .ir دارید:

```bash
sudo certbot --nginx -d oramshop.ir -d www.oramshop.ir
sudo nginx -t && sudo systemctl reload nginx
```

اگر **هر دو دامنه .ir و .com** را دارید، هر ۴ نام در یک گواهی (اول DNS هر دو دامنه را طبق مرحله ۱۰ ست کنید):

```bash
sudo certbot --nginx -d oramshop.ir -d www.oramshop.ir -d oramshop.com -d www.oramshop.com
sudo nginx -t && sudo systemctl reload nginx
```

تمدید خودکار است؛ تستش:

```bash
sudo certbot renew --dry-run
```

این کانفیگ خودش شامل این‌هاست:
- ری‌دایرکت http → https و www → بدون www
- سرو مستقیم `/static/` و `/media/` (بدون فشار به جنگو)
- صفحه «در حال به‌روزرسانی» برای وقتی برنامه ری‌استارت می‌شود (`error_page 502-504`)

---

## ۱۰. DNS

در پنل مدیریت دامنه (nic.ir یا هر جا که oramshop.ir را ثبت کرده‌اید) این دو رکورد را بسازید:

| نوع | نام | مقدار | TTL |
|---|---|---|---|
| A | `@` | `<IP-سرور>` | 3600 |
| A | `www` | `<IP-سرور>` | 3600 |

### اگر دامنه .com هم دارید

در پنل دامنه oramshop.com هم **دقیقاً همین دو رکورد** را با همان IP بسازید.
هیچ چیز دیگری لازم نیست — کانفیگ nginx پروژه از قبل طوری نوشته شده که
oramshop.com و همه‌ی wwwها را با ری‌دایرکت دائمی (301) به آدرس اصلی
oramshop.ir بفرستد. این یعنی:

- هر کس oramshop.com را تایپ کند خودکار به oramshop.ir می‌رسد؛
- گوگل فقط یک آدرس رسمی می‌بیند و اعتبار سئو بین دو دامنه تقسیم نمی‌شود؛
- در `ALLOWED_HOSTS` و `CSRF_TRUSTED_ORIGINS` هم لازم نیست .com را اضافه کنید،
  چون ری‌دایرکت در nginx انجام می‌شود و درخواستِ .com اصلاً به جنگو نمی‌رسد.

انتشار DNS از چند دقیقه تا چند ساعت طول می‌کشد. تست:

```bash
ping oramshop.ir
ping oramshop.com   # اگر .com دارید
```

وقتی IP سرور را برگرداند، مرحله ۹.۲ (certbot) را اجرا کنید — با دو دامنه، دستور ۴نامه‌ی همان مرحله را بزنید. **حالا سایت بالاست ✅**

---

## ۱۱. چک‌لیست امنیتی

قبل از معرفی سایت، این لیست را تیک بزنید:

- [ ] `DEBUG=False` در .env
- [ ] `DEV_MODE=False` در .env
- [ ] `SECRET_KEY` تصادفی جدید (نه همان مقدار توسعه!)
- [ ] `ZARINPAL_SANDBOX=False`
- [ ] `ADMIN_URL` و `DASHBOARD_URL` غیرقابل حدس
- [ ] `CSRF_TRUSTED_ORIGINS` با https ست شده
- [ ] ورود SSH فقط با کلید (`PasswordAuthentication no`)
- [ ] `PermitRootLogin no`
- [ ] UFW فعال و فقط 22/80/443 باز
- [ ] fail2ban فعال
- [ ] `chmod 600 .env`
- [ ] رمز PostgreSQL قوی و متفاوت از بقیه رمزها
- [ ] حساب سوپریوزر جنگو رمز قوی دارد
- [ ] بکاپ خودکار فعال (مرحله ۱۲)

**چیزهایی که کد پروژه خودش هندل می‌کند** (کاری لازم نیست): HSTS، ری‌دایرکت SSL، کوکی‌های Secure، هدرهای امنیتی، قفل axes بعد از ۵ تلاش ناموفق، مخفی بودن قیمت‌های عمده، محدودیت نرخ API.

---

## ۱۲. بکاپ‌گیری

اسکریپت بکاپ شبانه از دیتابیس + عکس‌ها:

```bash
sudo mkdir -p /var/backups/oramshop
sudo nano /usr/local/bin/oramshop-backup.sh
```

محتوا:

```bash
#!/bin/bash
# پشتیبان شبانه OramShop: دیتابیس + پوشه media (نگه‌داری ۱۴ روز)
set -e
STAMP=$(date +%F)
DEST=/var/backups/oramshop
sudo -u postgres pg_dump oramshop | gzip > "$DEST/db-$STAMP.sql.gz"
tar -czf "$DEST/media-$STAMP.tar.gz" -C /srv/oramshop media
find "$DEST" -name "*.gz" -mtime +14 -delete
```

فعال‌سازی (هر شب ساعت ۳:۳۰):

```bash
sudo chmod +x /usr/local/bin/oramshop-backup.sh
echo "30 3 * * * root /usr/local/bin/oramshop-backup.sh" | sudo tee /etc/cron.d/oramshop-backup
```

> 📌 هر چند وقت یک‌بار یک نسخه از `/var/backups/oramshop/` را **بیرون از سرور** هم نگه دارید (روی کامپیوتر خودتان با `scp`). بکاپی که فقط روی همان سرور است، با سوختن سرور می‌سوزد.

بازگردانی در روز مبادا:

```bash
gunzip -c db-2026-07-18.sql.gz | sudo -u postgres psql oramshop
```

---

## ۱۳. آپدیت‌های بعدی

هر بار نسخه جدید (bundle یا commit) گرفتید:

```bash
cd /srv/oramshop
sudo -u www-data git pull /tmp/oramshop-vXX.bundle claude/project-analysis-review-wm914e
source .venv/bin/activate
pip install -r requirements.txt          # اگر پکیج جدید اضافه شده
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart oramshop oramshop-celery
```

در چند ثانیه‌ی ری‌استارت، بازدیدکننده‌ها صفحه «در حال به‌روزرسانی» را می‌بینند نه خطای خام.

---

## ۱۴. عیب‌یابی

### دیدن لاگ‌ها

```bash
sudo journalctl -u oramshop -n 50 --no-pager         # لاگ سایت (gunicorn)
sudo journalctl -u oramshop-celery -n 50 --no-pager  # لاگ تسک‌ها
sudo tail -50 /var/log/nginx/error.log               # لاگ nginx
```

### مشکلات متداول

| علامت | علت معمول | راه‌حل |
|---|---|---|
| 502 Bad Gateway | gunicorn پایین است | `sudo systemctl restart oramshop` و بعد journalctl |
| خطای CSRF در فرم‌ها | `CSRF_TRUSTED_ORIGINS` ست نشده/بدون https | مرحله ۶ را چک کنید |
| عکس‌ها/استایل لود نمی‌شود | collectstatic اجرا نشده یا مالکیت فایل‌ها | `collectstatic` + `chown -R www-data` |
| پیامک نمی‌رود | کلید SMS.ir یا اعتبار پنل | `journalctl -u oramshop-celery` را ببینید؛ خطای 401 یعنی کلید غلط |
| پرداخت خطا می‌دهد | مرچنت اشتباه یا `ZARINPAL_SANDBOX=True` مانده | .env را چک و سرویس را ری‌استارت کنید |
| DisallowedHost در لاگ | دامنه در `ALLOWED_HOSTS` نیست | دامنه را اضافه و ری‌استارت کنید |
| بعد از تغییر .env اثری نیست | سرویس‌ها env قدیمی را دارند | `sudo systemctl restart oramshop oramshop-celery` |

### دستورهای روزمره

```bash
sudo systemctl restart oramshop            # ری‌استارت سایت
sudo systemctl restart oramshop-celery     # ری‌استارت تسک‌ها
sudo systemctl reload nginx                # بارگذاری مجدد nginx
df -h                                      # فضای دیسک
free -h                                    # وضعیت RAM
```

---

## نقشه کلی (که بدانید چه چیزی کجاست)

```
اینترنت ──HTTPS──▶ nginx ──▶ gunicorn (جنگو) ──▶ PostgreSQL
                    │                    │
                    │ /static/ /media/   ├──▶ Redis (کش)
                    │ را خودش می‌دهد     │
                    │                    └──▶ Celery worker+beat
                    └─ صفحه تعمیرات وقتی برنامه پایین است   (پیامک، زمان‌بندی‌ها)
```

</div>
