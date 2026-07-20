# 🛡️ راهنمای رفع خطاها و مقابله با حمله‌ها — OramShop

این فایل دو بخش دارد:

* **بخش ۱ — خطاهای رایج سایت:** هر خطایی که ممکن است پیش بیاید، علتش و راه‌حلش.
* **بخش ۲ — حمله‌ها و دفاع:** انواع حمله به سایت، نشانه‌ها، و روش دفع هرکدام.

> مسیر پروژه `/srv/oramshop`، کاربر اجرا `www-data`، دامنه `oramshop.ir`.

---

# بخش ۱ — خطاهای رایج سایت و رفع آن‌ها

## 🔴 اولین کارها هنگام هر خرابی (چک‌لیست سریع)

```bash
systemctl status oramshop oramshop-celery nginx postgresql redis-server
journalctl -u oramshop -n 80 --no-pager
tail -n 80 /var/log/nginx/error.log
df -h                 # دیسک پر است؟
free -h               # رم تمام شده؟
```
۹۰٪ مشکلات با همین پنج دستور مشخص می‌شود.

---

## خطای ۵۰۰ (Internal Server Error)

**یعنی:** کد سایت هنگام اجرا خطا داده.

```bash
journalctl -u oramshop -n 100 --no-pager      # متن دقیق خطا اینجاست
```
علت‌های رایج:
| نشانه در لاگ | علت | راه‌حل |
|---|---|---|
| `OperationalError: could not connect` | دیتابیس خاموش است | `systemctl restart postgresql` |
| `ProgrammingError: relation ... does not exist` | مایگریشن اجرا نشده | `migrate` بزن (پایین) |
| `ModuleNotFoundError` | بستهٔ پایتون نصب نشده | `pip install -r requirements.txt` |
| `redis ... Connection refused` | Redis خاموش | `systemctl restart redis-server` |

```bash
cd /srv/oramshop
sudo -u www-data /srv/oramshop/.venv/bin/python manage.py migrate
systemctl restart oramshop oramshop-celery
```

---

## خطای ۵۰۲ / ۵۰۴ (Bad Gateway / Gateway Timeout)

**یعنی:** nginx هست ولی Gunicorn جواب نمی‌دهد.

```bash
systemctl status oramshop           # احتمالاً failed یا خاموش است
systemctl restart oramshop
journalctl -u oramshop -n 50 --no-pager
```
اگر مدام کرش می‌کند، معمولاً خطای پایتون در استارت‌آپ است؛ متنش را در لاگ ببین.

---

## خطای ۴۰۳ (Forbidden)

**علت‌های ممکن:**
* دسترسی فایل‌ها اشتباه است → `chown -R www-data:www-data /srv/oramshop`
* IP کاربر توسط سیستم ضدنفوذ (django-axes) قفل شده → [بخش brute-force](#۲-حملهٔ-brute-force-امتحان-رمز)
* قانون nginx یا فایروال → `tail /var/log/nginx/error.log`

---

## خطای ۴۰۴ (صفحه پیدا نشد)

اگر **همه‌چیز** ۴۰۴ می‌دهد (نه فقط یک صفحه)، معمولاً فایل‌های استاتیک/مسیر اشتباه است:
```bash
sudo -u www-data /srv/oramshop/.venv/bin/python manage.py collectstatic --noinput
systemctl reload nginx
```
سایت صفحهٔ ۴۰۴ سفارشی فارسی دارد؛ اگر آن را می‌بینی یعنی مشکلی نیست، فقط آدرس اشتباه است.

---

## CSS/تصاویر لود نمی‌شوند (سایت بی‌قواره)

```bash
sudo -u www-data /srv/oramshop/.venv/bin/python manage.py collectstatic --noinput
systemctl reload nginx
```
اگر بعد از آپدیت، استایل قدیمی می‌ماند: مقدار `ASSET_VERSION` در تنظیمات را یک عدد
جلو ببر (کش مرورگر با `?v=NN` تازه می‌شود) و مرورگر را `Ctrl+Shift+R` بزن.

---

## پیامک ارسال نمی‌شود

۱. **اول پنل داشبورد ➜ «لاگ پیامک‌ها» را ببین.** آنجا وضعیت هر ارسال و خطای فارسی
   sms.ir نوشته شده. رایج‌ترین‌ها:
   | پیام | معنی و رفع |
   |---|---|
   | «قالب یافت نشد» (۱۱۳) | `SMS_IR_TEMPLATE_ID` در `.env` اشتباه است |
   | «اعتبار کافی نیست» (۱۰۳) | حساب sms.ir شارژ ندارد |
   | «کلید API نامعتبر» (۴۰۱) | `SMS_IR_API_KEY` اشتباه است |
   | «ارتباط با sms.ir برقرار نشد» | سرور به اینترنت بیرون وصل نیست / فایروال |

۲. اگر لاگ می‌گوید «موفق» ولی پیامک نرسید ➜ مشکل سمت **اپراتور مخابرات** است، نه سایت.
   برای OTP از **خط خدماتی** استفاده کن که تأخیر ندارد.

۳. بعد از تغییر کلیدها در `.env`:
```bash
systemctl restart oramshop oramshop-celery      # هر دو، حتماً!
```

---

## پرداخت کار نمی‌کند

```bash
journalctl -u oramshop -n 100 --no-pager | grep -i payment
```
* کلید `ZARINPAL_MERCHANT_ID` را در `.env` چک کن.
* سایت باید HTTPS باشد و درگاه به `oramshop.ir` برگردد (callback).
* حالت تست/واقعی زرین‌پال را با درگاه یکی کن.

---

## دیسک پر شده («No space left on device»)

```bash
df -h
du -sh /srv/oramshop/* /var/log/* | sort -rh | head    # مقصر را پیدا کن
journalctl --vacuum-time=7d           # لاگ‌های قدیمی‌تر از ۷ روز را پاک کن
find /srv/oramshop -name "*.pyc" -delete
```
معمولاً مقصر: لاگ‌های حجیم یا بکاپ‌های قدیمی در `/srv/backups`.

---

## دیتابیس: «permission denied for schema public»
```bash
sudo -u postgres psql -d oramshop -c "ALTER SCHEMA public OWNER TO oramshop; GRANT ALL ON SCHEMA public TO oramshop;"
```

---

## سایت کند شده

```bash
top                        # کدام پردازش CPU/رم را خورده؟
free -h                    # رم پر است؟
ss -s                      # تعداد اتصال‌ها
```
* اگر رم پر است، تعداد worker های Gunicorn را کم کن.
* اگر یک IP خاص هزاران درخواست می‌زند ➜ [حملهٔ DDoS](#۱-حملهٔ-ddos-سیل-درخواست).

---

# بخش ۲ — حمله‌ها و روش دفاع

> این پروژه از قبل چند لایهٔ دفاعی دارد: HTTPS اجباری، هدرهای امنیتی، محافظت CSRF،
> ORM (ضدِ SQL Injection)، قالب‌های خودکار escape (ضدِ XSS)، محدودیت نرخ روی OTP و
> API، و سیستم قفل ورود (django-axes). این بخش می‌گوید هر حمله چطور شناسایی و تقویت شود.

---

## ۱. حملهٔ DDoS (سیل درخواست)

**نشانه:** سایت کند/قطع، بار CPU بالا، هزاران درخواست از چند IP.

**تشخیص — پرتکرارترین IPها در لاگ nginx:**
```bash
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
```

**دفاع فوری — مسدودکردن IP مهاجم:**
```bash
ufw deny from 1.2.3.4        # مسدودکردن یک IP
```

**دفاع پایدار:**
* در nginx محدودیت نرخ فعال کن (نمونه در `DEPLOY.md`):
  ```nginx
  limit_req_zone $binary_remote_addr zone=oramshop:10m rate=10r/s;
  # داخل location:
  limit_req zone=oramshop burst=20 nodelay;
  ```
* برای حملهٔ حجیم، از سرویس ابری مثل **Cloudflare** (پلن رایگان) جلوی دامنه استفاده کن؛
  خودش بیشتر ترافیک مخرب را جذب می‌کند.
* نصب **fail2ban** برای مسدودسازی خودکار (پایین).

---

## ۲. حملهٔ Brute-Force (امتحان رمز)

**نشانه:** تلاش‌های پیاپی ناموفق ورود از یک IP.

**دفاع موجود:** سایت از **django-axes** استفاده می‌کند. بعد از ۵ تلاش ناموفق، همان **IP**
(نه کل کاربرها) قفل می‌شود. IP واقعی از هدر `X-Real-IP` که nginx می‌گذارد خوانده می‌شود
(قابل جعل نیست).

**مدیریت:**
```bash
cd /srv/oramshop
PY=/srv/oramshop/.venv/bin/python
# دیدن قفل‌شده‌ها
sudo -u www-data $PY manage.py axes_list_attempts
# باز کردن یک IP که اشتباه قفل شده
sudo -u www-data $PY manage.py axes_reset_ip 1.2.3.4
# ریست کامل
sudo -u www-data $PY manage.py axes_reset
```
سخت‌گیرتر کردن: در `.env` مقدار `DJANGO_AXES_FAILURE_LIMIT` را کم کن (مثلاً ۳) و
`DJANGO_AXES_COOLOFF_TIME` (ساعت) را زیاد کن، بعد ری‌استارت.

---

## ۳. SQL Injection (تزریق کوئری)

**دفاع موجود:** کل سایت با Django ORM کار می‌کند که پارامترها را امن می‌کند. تا وقتی
کسی کوئری خام (`raw()` / رشتهٔ SQL دستی) ننویسد، این حمله بی‌اثر است.

**قانون طلایی:** هیچ‌وقت ورودی کاربر را مستقیم داخل رشتهٔ SQL نگذار. همیشه ORM یا
پارامتر (`%s`) استفاده کن.

---

## ۴. XSS (تزریق اسکریپت)

**دفاع موجود:** قالب‌های Django به‌صورت خودکار HTML را escape می‌کنند.

**قانون:** از `|safe` یا `mark_safe` فقط روی محتوایی استفاده کن که خودت ساخته‌ای، نه
روی ورودی کاربر (نظر، نام، آدرس). ورودی کاربر هیچ‌وقت `|safe` نشود.

---

## ۵. CSRF (جعل درخواست)

**دفاع موجود:** میدل‌ور CSRF فعال است و همهٔ فرم‌ها `{% csrf_token %}` دارند.

اگر خطای «CSRF verification failed» گرفتی، معمولاً یعنی دامنه در `CSRF_TRUSTED_ORIGINS`
(در `.env` / تنظیمات) نیست:
```
CSRF_TRUSTED_ORIGINS=https://oramshop.ir,https://www.oramshop.ir
```

---

## ۶. سوءاستفاده از OTP / API

**دفاع موجود:**
* ارسال OTP محدودیت نرخ دارد (نمی‌شود پیامکی اسپم کرد).
* API عمومی سایت با کلید `X-API-Key` محافظت می‌شود و هر IP سقف ۱۲۰ درخواست در دقیقه دارد.

اگر کسی کلید API را لو داده یا سوءاستفاده شد، کلید را عوض کن: در پنل داشبورد
(«تنظیمات») یا `.env` (`BOT_API_KEY`) کلید جدید بگذار و ری‌استارت کن.

---

## ۷. لو رفتن فایل‌های حساس

**قانون:** فایل `.env` را هیچ‌وقت در گیت commit نکن (در `.gitignore` هست) و دسترسی‌اش
را محدود کن:
```bash
chmod 600 /srv/oramshop/.env
```
`DEBUG` در محیط واقعی حتماً `False` باشد، وگرنه جزئیات خطاها و تنظیمات لو می‌رود:
```
DEBUG=False
```

---

## نصب fail2ban (مسدودسازی خودکار مهاجم)

fail2ban لاگ‌ها را می‌خواند و IPهایی که رفتار مشکوک دارند را خودکار در فایروال بلاک می‌کند.

```bash
apt install fail2ban -y
systemctl enable --now fail2ban
```
یک فیلتر ساده برای nginx (فایل `/etc/fail2ban/jail.local`):
```ini
[sshd]
enabled = true

[nginx-limit-req]
enabled  = true
filter   = nginx-limit-req
port     = http,https
logpath  = /var/log/nginx/error.log
maxretry = 10
findtime = 60
bantime  = 3600
```
```bash
systemctl restart fail2ban
fail2ban-client status                # وضعیت
fail2ban-client status sshd           # قربانیان یک jail
fail2ban-client set sshd unbanip 1.2.3.4   # آزادکردن IP
```

---

## چک‌لیست امنیتی دوره‌ای (ماهانه)

- [ ] `apt update && apt upgrade -y` (وصله‌های امنیتی)
- [ ] بکاپ دیتابیس تست شود (که واقعاً باز می‌شود)
- [ ] `DEBUG=False` و کلیدها فقط در `.env`
- [ ] گواهی SSL معتبر است (`curl -I https://oramshop.ir`)
- [ ] لاگ‌ها را برای IP یا الگوی مشکوک مرور کن
- [ ] رمز `root` و کاربرها قوی باشد؛ ورود با کلید SSH فعال
- [ ] فقط پورت‌های لازم در `ufw` باز باشد (۲۲، ۸۰، ۴۴۳)

---

## در لحظهٔ حمله چه کنم؟ (خلاصهٔ اضطراری)

```bash
# ۱. مهاجم را پیدا کن
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head

# ۲. بلاکش کن
ufw deny from <IP>

# ۳. اگر سایت زیر بار است، موقتاً محدودتر کن یا Cloudflare را روشن کن

# ۴. لاگ بگیر برای بررسی بعدی
cp /var/log/nginx/access.log /srv/backups/incident-$(date +%F).log

# ۵. بعد از آرام‌شدن، رمزها و کلیدها را عوض کن
```

📌 برای دستورات پایهٔ سرور، فایل **`LINUX-SERVER.md`** را ببین.
