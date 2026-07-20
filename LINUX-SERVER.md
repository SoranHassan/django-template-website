# 🐧 آموزش کامل دستورات سرور لینوکس — راهنمای OramShop

این فایل یک مرجع کامل و کاربردی برای مدیریت سرور لینوکسی سایت است. همه‌چیز از
اتصال اولیه تا نگهداری روزمره، با مثال‌های واقعیِ همین پروژه.

> در تمام مثال‌ها فرض شده کاربر شما `root` یا یک کاربر با دسترسی `sudo` است و
> مسیر پروژه `/srv/oramshop` و کاربر اجراکننده `www-data` است.

---

## فهرست

1. [اتصال به سرور (SSH)](#1-اتصال-به-سرور-ssh)
2. [انتقال فایل (scp / rsync / sftp)](#2-انتقال-فایل-scp--rsync--sftp)
3. [حرکت بین پوشه‌ها و مدیریت فایل](#3-حرکت-بین-پوشه‌ها-و-مدیریت-فایل)
4. [مشاهده و ویرایش فایل](#4-مشاهده-و-ویرایش-فایل)
5. [دسترسی‌ها و مالکیت (permissions)](#5-دسترسی‌ها-و-مالکیت-permissions)
6. [کاربران و sudo](#6-کاربران-و-sudo)
7. [مدیریت سرویس‌ها (systemctl)](#7-مدیریت-سرویس‌ها-systemctl)
8. [مشاهده لاگ‌ها (journalctl / tail)](#8-مشاهده-لاگ‌ها-journalctl--tail)
9. [پردازش‌ها و منابع (top / ps / kill)](#9-پردازش‌ها-و-منابع-top--ps--kill)
10. [دیسک و حافظه](#10-دیسک-و-حافظه)
11. [شبکه و پورت‌ها](#11-شبکه-و-پورت‌ها)
12. [فایروال (ufw)](#12-فایروال-ufw)
13. [بسته‌ها و آپدیت (apt)](#13-بسته‌ها-و-آپدیت-apt)
14. [جست‌وجو (find / grep)](#14-جستوجو-find--grep)
15. [فشرده‌سازی و بکاپ (tar / gzip)](#15-فشردهسازی-و-بکاپ-tar--gzip)
16. [کران‌جاب (زمان‌بندی کارها)](#16-کرانجاب-زمانبندی-کارها)
17. [دستورات مخصوص همین پروژه](#17-دستورات-مخصوص-همین-پروژه)
18. [میان‌بُرها و ترفندها](#18-میانبُرها-و-ترفندها)

---

## ۱. اتصال به سرور (SSH)

SSH ابزار اصلی اتصال امن به سرور از راه دور است.

```bash
# اتصال ساده (پورت پیش‌فرض ۲۲)
ssh root@62.220.123.56

# اتصال با پورت دلخواه
ssh -p 2222 root@62.220.123.56

# اتصال با کلید خصوصی (به‌جای رمز)
ssh -i ~/.ssh/id_ed25519 root@62.220.123.56
```

### ساخت کلید SSH (امن‌تر از رمز)
```bash
# روی لپ‌تاپ خودت این را بزن
ssh-keygen -t ed25519 -C "my-laptop"

# کلید عمومی را روی سرور نصب کن
ssh-copy-id root@62.220.123.56
```
بعد از این کار دیگر لازم نیست رمز بزنی.

### اگر SSH وصل نشد («Connection closed»)
معمولاً به‌خاطر نبودن پوشه یا کلیدهای میزبان است. روی خودِ سرور (از کنسول پنل هاست):
```bash
mkdir -p /run/sshd
ssh-keygen -A            # ساخت کلیدهای میزبان
systemctl restart ssh
sshd -t                  # تست پیکربندی؛ نباید خطایی بدهد
```

---

## ۲. انتقال فایل (scp / rsync / sftp)

### scp — کپی امن فایل بین لپ‌تاپ و سرور
`scp` مخفف Secure Copy است؛ درست مثل `cp` ولی از روی شبکه و امن.

```bash
# از لپ‌تاپ  ➜  سرور (آپلود)
scp report.pdf root@62.220.123.56:/srv/oramshop/

# از سرور  ➜  لپ‌تاپ (دانلود)
scp root@62.220.123.56:/srv/oramshop/db.sqlite3 ./

# یک پوشهٔ کامل (با -r)
scp -r ./media root@62.220.123.56:/srv/oramshop/

# با پورت خاص (حرف P بزرگ در scp)
scp -P 2222 file.zip root@62.220.123.56:/tmp/
```

### rsync — همگام‌سازی هوشمند (فقط تغییرات را می‌فرستد)
برای فایل‌های حجیم و بکاپ خیلی بهتر از scp است.
```bash
# همگام‌سازی پوشهٔ media (فقط چیزهایی که عوض شده‌اند)
rsync -avz ./media/ root@62.220.123.56:/srv/oramshop/media/

# -a آرشیو (حفظ مجوزها) | -v نمایش | -z فشرده | --delete حذف فایل‌های اضافه
rsync -avz --delete ./static/ root@62.220.123.56:/srv/oramshop/static/
```

### sftp — مرور تعاملی فایل‌ها
```bash
sftp root@62.220.123.56
# داخلش: ls, cd, get file, put file, bye
```

---

## ۳. حرکت بین پوشه‌ها و مدیریت فایل

```bash
pwd                 # نمایش مسیر فعلی (کجا هستم؟)
ls                  # فهرست فایل‌ها
ls -lah             # فهرست کامل + سایز خوانا + فایل‌های مخفی
cd /srv/oramshop    # رفتن به مسیر
cd ..               # یک پوشه بالاتر
cd ~                # پوشهٔ خانگی
cd -                # برگشت به پوشهٔ قبلی

mkdir backups             # ساخت پوشه
mkdir -p a/b/c            # ساخت زنجیرهٔ پوشه‌ها
touch notes.txt           # ساخت فایل خالی
cp a.txt b.txt            # کپی
cp -r dir1 dir2           # کپی پوشه
mv old.txt new.txt        # تغییر نام / جابه‌جایی
rm file.txt               # حذف فایل
rm -r folder              # حذف پوشه
rm -rf folder             # حذف اجباری (⚠️ خطرناک، برگشت‌ناپذیر)
```

> ⚠️ `rm -rf /` کل سرور را پاک می‌کند. هیچ‌وقت با مسیر اشتباه اجرا نکن.

---

## ۴. مشاهده و ویرایش فایل

```bash
cat file.txt              # نمایش کل فایل
less file.txt             # نمایش صفحه‌به‌صفحه (q برای خروج)
head -n 20 file.txt       # ۲۰ خط اول
tail -n 50 file.txt       # ۵۰ خط آخر
tail -f logfile           # دنبال‌کردن زندهٔ لاگ (Ctrl+C برای خروج)
wc -l file.txt            # شمارش خطوط
```

### ویرایش با nano (ساده‌ترین ویرایشگر)
```bash
nano .env
# Ctrl+O ذخیره | Enter تأیید | Ctrl+X خروج
```

### ویرایش با vim (حرفه‌ای)
```bash
vim config.py
# i  = حالت نوشتن | Esc = خروج از حالت نوشتن
# :w = ذخیره | :q = خروج | :wq = ذخیره و خروج | :q! = خروج بدون ذخیره
```

---

## ۵. دسترسی‌ها و مالکیت (permissions)

هر فایل سه گروه دسترسی دارد: **مالک (u)**، **گروه (g)**، **بقیه (o)** —
هرکدام با سه مجوز: خواندن `r`(۴)، نوشتن `w`(۲)، اجرا `x`(۱).

```bash
ls -l file.sh
# -rwxr-xr--  یعنی مالک همه‌کاره، گروه خواندن+اجرا، بقیه فقط خواندن

chmod 644 file.txt        # مالک rw، بقیه r  (فایل‌های معمولی)
chmod 755 script.sh       # مالک rwx، بقیه rx (اسکریپت‌ها/پوشه‌ها)
chmod +x deploy.sh        # اجرایی‌کردن
chmod 600 .env            # فقط مالک بخواند/بنویسد (فایل‌های محرمانه)

chown www-data:www-data file      # تغییر مالک و گروه
chown -R www-data:www-data /srv/oramshop   # کل پوشه (بازگشتی)
```

> در این پروژه همهٔ فایل‌های داخل `/srv/oramshop` باید مالک `www-data` باشند تا
> Gunicorn بتواند بخواند و بنویسد.

---

## ۶. کاربران و sudo

```bash
whoami                    # من چه کاربری هستم؟
sudo command              # اجرای دستور با دسترسی مدیر
sudo -u www-data command  # اجرا به‌جای کاربر دیگر
su - username             # تعویض کاربر

adduser sara              # ساخت کاربر جدید
usermod -aG sudo sara     # دادن دسترسی sudo
passwd                    # تغییر رمز خودم
```

---

## ۷. مدیریت سرویس‌ها (systemctl)

سرویس‌ها برنامه‌هایی هستند که در پس‌زمینه اجرا می‌شوند (وب‌سرور، دیتابیس، ...).

```bash
systemctl status oramshop        # وضعیت سرویس
systemctl start oramshop         # روشن‌کردن
systemctl stop oramshop          # خاموش‌کردن
systemctl restart oramshop       # ری‌استارت
systemctl reload nginx           # بارگذاری مجدد پیکربندی (بدون قطعی)
systemctl enable oramshop        # اجرای خودکار هنگام بوت
systemctl disable oramshop       # لغو اجرای خودکار

systemctl list-units --type=service   # فهرست همهٔ سرویس‌ها
```

### سرویس‌های همین پروژه
| سرویس | کارش |
|-------|------|
| `oramshop` | وب‌سرور Gunicorn (خود سایت) |
| `oramshop-celery` | صف کارهای پس‌زمینه (پیامک، ایمیل) |
| `nginx` | دروازهٔ ورودی و SSL |
| `postgresql` | دیتابیس |
| `redis-server` | صف و کش |

> 🔴 **نکتهٔ مهم:** بعد از هر تغییر در `.env` باید **هم** `oramshop` و **هم**
> `oramshop-celery` را ری‌استارت کنی، چون هر دو `.env` را می‌خوانند:
> ```bash
> systemctl restart oramshop oramshop-celery
> ```

---

## ۸. مشاهده لاگ‌ها (journalctl / tail)

```bash
journalctl -u oramshop -n 100          # ۱۰۰ خط آخر لاگ سرویس
journalctl -u oramshop -f              # دنبال‌کردن زنده (مثل tail -f)
journalctl -u oramshop --since "10 min ago"
journalctl -u oramshop -p err          # فقط خطاها
journalctl --since today               # کل لاگ‌های امروز

# لاگ‌های nginx
tail -f /var/log/nginx/access.log      # هر بازدید
tail -f /var/log/nginx/error.log       # خطاها
```

---

## ۹. پردازش‌ها و منابع (top / ps / kill)

```bash
top                       # نمایش زندهٔ مصرف CPU/RAM (q برای خروج)
htop                      # نسخهٔ رنگی و بهتر (اگر نصب بود)
ps aux                    # فهرست همهٔ پردازش‌ها
ps aux | grep gunicorn    # فقط پردازش‌های gunicorn

kill 1234                 # بستن پردازش با شمارهٔ ۱۲۳۴
kill -9 1234              # بستن اجباری
pkill -f runserver        # بستن با نام
```

---

## ۱۰. دیسک و حافظه

```bash
df -h                     # فضای دیسک هر پارتیشن (خوانا)
du -sh /srv/oramshop      # حجم یک پوشه
du -sh * | sort -rh | head    # سنگین‌ترین پوشه‌ها
free -h                   # مصرف RAM
```

> اگر دیسک پر شد، معمولاً مقصر: لاگ‌های حجیم، بکاپ‌های قدیمی، کش. با دستور بالا
> پیدایشان کن و پاک کن.

---

## ۱۱. شبکه و پورت‌ها

```bash
ip a                      # آدرس‌های IP سرور
ping google.com           # تست اتصال (Ctrl+C توقف)
curl -I https://oramshop.ir     # تست یک آدرس (فقط هدرها)
ss -tulpn                 # پورت‌های باز و برنامهٔ هرکدام
ss -tulpn | grep :443     # چه چیزی روی پورت ۴۴۳ گوش می‌دهد؟
```

---

## ۱۲. فایروال (ufw)

```bash
ufw status                # وضعیت فایروال
ufw enable                # فعال‌سازی
ufw allow 22/tcp          # اجازهٔ SSH
ufw allow 80,443/tcp      # اجازهٔ وب
ufw deny 3306             # مسدودکردن یک پورت
ufw delete allow 8000     # حذف یک قانون
ufw status numbered       # قوانین با شماره
```

> 🔴 قبل از `ufw enable` حتماً پورت SSH (۲۲) را allow کن، وگرنه خودت را بیرون
> می‌اندازی.

---

## ۱۳. بسته‌ها و آپدیت (apt)

```bash
apt update                # به‌روزرسانی فهرست بسته‌ها
apt upgrade               # نصب آپدیت‌ها
apt update && apt upgrade -y   # هر دو با هم

apt install nginx         # نصب یک بسته
apt remove nginx          # حذف
apt search libreoffice    # جست‌وجو
dpkg -l | grep python     # بسته‌های نصب‌شده
```

---

## ۱۴. جست‌وجو (find / grep)

```bash
# find: پیدا کردن فایل بر اساس نام/نوع
find /srv/oramshop -name "*.log"          # همهٔ فایل‌های لاگ
find . -type f -size +100M                # فایل‌های بزرگ‌تر از ۱۰۰ مگ
find . -name "*.pyc" -delete              # حذف فایل‌های کش پایتون

# grep: جست‌وجوی متن داخل فایل‌ها
grep "ERROR" app.log                      # خطوط شامل ERROR
grep -r "SECRET_KEY" .                    # جست‌وجوی بازگشتی در پوشه
grep -i "timeout" log.txt                 # بدون حساسیت به بزرگی حروف
grep -n "def send" views.py               # با شمارهٔ خط
```

---

## ۱۵. فشرده‌سازی و بکاپ (tar / gzip)

```bash
# ساخت آرشیو فشرده از یک پوشه
tar -czf media-backup.tar.gz media/
#  c=ساخت  z=فشرده(gzip)  f=فایل خروجی

# باز کردن آرشیو
tar -xzf media-backup.tar.gz
#  x=استخراج

# دیدن محتوای آرشیو بدون باز کردن
tar -tzf media-backup.tar.gz

# فشرده‌سازی یک فایل تنها
gzip bigfile.sql          # می‌شود bigfile.sql.gz
gunzip bigfile.sql.gz     # باز کردن
```

### بکاپ دیتابیس PostgreSQL
```bash
# گرفتن بکاپ
sudo -u postgres pg_dump oramshop | gzip > db-$(date +%F).sql.gz

# بازگرداندن
gunzip -c db-2026-07-20.sql.gz | sudo -u postgres psql oramshop
```

---

## ۱۶. کران‌جاب (زمان‌بندی کارها)

```bash
crontab -e                # ویرایش کران‌جاب‌های کاربر فعلی
crontab -l                # نمایش

# قالب:  دقیقه ساعت روز ماه روزهفته  دستور
# مثال: هر شب ساعت ۲ بامداد بکاپ بگیر
0 2 * * * sudo -u postgres pg_dump oramshop | gzip > /srv/backups/db-$(date +\%F).sql.gz
```

---

## ۱۷. دستورات مخصوص همین پروژه

همهٔ دستورات Django باید با کاربر `www-data` و پایتونِ محیط مجازی اجرا شوند:

```bash
cd /srv/oramshop
PY=/srv/oramshop/.venv/bin/python

# اجرای هر دستور مدیریتی
sudo -u www-data $PY manage.py migrate
sudo -u www-data $PY manage.py collectstatic --noinput
sudo -u www-data $PY manage.py createsuperuser
sudo -u www-data $PY manage.py shell

# بعد از دریافت کد جدید (باندل یا git)
sudo -u www-data git -C /srv/oramshop pull
sudo -u www-data $PY manage.py migrate
sudo -u www-data $PY manage.py collectstatic --noinput
systemctl restart oramshop oramshop-celery
```

> اگر git خطای «dubious ownership» داد:
> ```bash
> sudo git config --system --add safe.directory /srv/oramshop
> ```

### ویرایش کلیدهای محرمانه (.env)
```bash
cd /srv/oramshop
sudo -u www-data nano .env
# کلیدها را بگذار، ذخیره کن (Ctrl+O, Ctrl+X)، بعد:
systemctl restart oramshop oramshop-celery
```

---

## ۱۸. میان‌بُرها و ترفندها

```bash
Ctrl + C        # توقف دستور در حال اجرا
Ctrl + R        # جست‌وجو در تاریخچهٔ دستورات
Ctrl + L        # پاک‌کردن صفحه (مثل clear)
Ctrl + A / E    # رفتن به اول / آخر خط
!!              # تکرار آخرین دستور
sudo !!         # تکرار آخرین دستور با sudo
history         # فهرست دستورات قبلی
clear           # پاک‌کردن صفحه

command1 && command2     # اجرای دومی فقط اگر اولی موفق شد
command1 ; command2      # اجرای پشت‌سرهم بدون شرط
command &                # اجرا در پس‌زمینه
nohup command &          # اجرا در پس‌زمینه، مقاوم به قطع ترمینال
```

### سه دستور طلایی که همیشه اول بزن وقتی سایت مشکل دارد
```bash
systemctl status oramshop            # سرویس بالاست؟
journalctl -u oramshop -n 50         # آخرین خطاها چیست؟
df -h                                # دیسک پر نشده؟
```

---

📌 برای عیب‌یابی خطاها و مقابله با حمله‌ها، فایل **`SECURITY-INCIDENTS.md`** را ببین.
