from django.db import models
from django.conf import settings


class SiteVisit(models.Model):
    """Real site visits - stored by the middleware (panel visit statistics)."""

    session_key = models.CharField(max_length=40, db_index=True, blank=True,
                                   verbose_name='کلید نشست')
    path = models.CharField(max_length=255, blank=True, verbose_name='مسیر')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, verbose_name='کاربر')
    ip_hash = models.CharField(max_length=32, blank=True, verbose_name='هش IP')
    is_authenticated = models.BooleanField(default=False, verbose_name='کاربر عضو')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True,
                                      verbose_name='زمان بازدید')

    class Meta:
        verbose_name = 'بازدید سایت'
        verbose_name_plural = 'بازدیدهای سایت'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['created_at', 'session_key']),
        ]

    def __str__(self):
        return f'{self.path} — {self.created_at:%Y-%m-%d %H:%M}'


class Announcement(models.Model):
    text = models.CharField(max_length=200, verbose_name='متن')
    link = models.URLField(blank=True, verbose_name='لینک')
    link_text = models.CharField(max_length=50, blank=True, verbose_name='متن لینک')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')

    class Meta:
        verbose_name = 'اطلاعیه'
        verbose_name_plural = 'اطلاعیه‌ها'
        ordering = ('order',)

    def __str__(self):
        return self.text


class HeroSlide(models.Model):
    """Main hero banner slides - manageable from the admin panel."""

    title = models.CharField(max_length=100, verbose_name='عنوان')
    subtitle = models.CharField(max_length=200, blank=True, verbose_name='زیرعنوان')
    image = models.ImageField(upload_to='hero/', verbose_name='تصویر')
    button_text = models.CharField(max_length=50, blank=True, default='خرید کنید', verbose_name='متن دکمه')
    button_link = models.CharField(max_length=200, blank=True, default='/shop/', verbose_name='لینک دکمه')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'اسلاید بنر'
        verbose_name_plural = 'اسلایدهای بنر'
        ordering = ('order',)

    def __str__(self):
        return self.title

class SiteSetting(models.Model):
    """Site appearance settings - changeable from the panel without a deploy."""

    TOPBAR_CHOICES = [
        ('black', 'مشکی ساده'),
        ('charcoal', 'شارکول (خاکستری تیره)'),
        ('navy', 'سرمه‌ای'),
        ('ivory', 'کرم روشن (متن تیره)'),
        ('gradient-cyan', 'گرادینت مشکی → سایان'),
        ('gradient-dark', 'گرادینت آبی نفتی'),
        ('gradient-purple', 'گرادینت بنفش'),
        ('gradient-sunset', 'گرادینت غروب (قرمز)'),
        ('gradient-emerald', 'گرادینت زمردی (سبز)'),
    ]

    home_watermark = models.CharField(max_length=60, default='ORAM SHOP',
                                      verbose_name='متن واترمارک صفحه اصلی')
    topbar_style = models.CharField(max_length=20, choices=TOPBAR_CHOICES, default='black',
                                    verbose_name='رنگ نوار اطلاعیه بالای سایت')

    # ---------- Footer / contact info ----------
    footer_about = models.TextField(
        blank=True, verbose_name='متن دربارهٔ فوتر',
        default='اُرام‌شاپ، فروشگاه اینترنتی پوشاک مردانه و زنانه؛ با ضمانت اصالت کالا، ارسال سریع به سراسر ایران و ۷ روز ضمانت بازگشت.')
    footer_phone = models.CharField(max_length=40, blank=True, default='۰۲۱-۰۰۰۰۰۰۰۰', verbose_name='تلفن پشتیبانی')
    footer_email = models.CharField(max_length=80, blank=True, default='info@oramshop.com', verbose_name='ایمیل')
    footer_hours = models.CharField(max_length=80, blank=True, default='شنبه تا پنجشنبه، ۹ تا ۱۸', verbose_name='ساعات کاری')
    footer_address = models.CharField(max_length=200, blank=True, verbose_name='آدرس')
    instagram_url = models.CharField(max_length=200, blank=True, verbose_name='لینک اینستاگرام')
    telegram_url = models.CharField(max_length=200, blank=True, verbose_name='لینک تلگرام')
    whatsapp_url = models.CharField(max_length=200, blank=True, verbose_name='لینک واتساپ')
    credit_text = models.CharField(max_length=120, blank=True, default='طراحی و توسعه توسط گروه ساتک کدینگ',
                                   verbose_name='متن سازندهٔ سایت')
    credit_url = models.CharField(max_length=200, blank=True, verbose_name='لینک سازنده')

    # ---------- Search rank (entered from Google Search Console) ----------
    search_rank = models.PositiveIntegerField(
        default=0, verbose_name='رتبهٔ فعلی در جستجوی گوگل',
        help_text='این عدد را از گوگل سرچ‌کنسول وارد کنید (۰ یعنی نامشخص). اگر ۱ تا ۱۰ باشد، در داشبورد آلرت داده می‌شود.')
    search_keyword = models.CharField(max_length=100, blank=True, verbose_name='کلمهٔ کلیدی رتبه')

    # ---------- Shop page banner ----------
    shop_banner = models.ImageField(upload_to='banners/', blank=True, null=True, verbose_name='بنر صفحه محصولات')
    shop_banner_title = models.CharField(max_length=100, blank=True, default='فروشگاه اُرام‌شاپ', verbose_name='عنوان بنر محصولات')
    shop_banner_subtitle = models.CharField(max_length=160, blank=True, default='جدیدترین کالکشن‌ها با بهترین قیمت', verbose_name='زیرعنوان بنر محصولات')

    # ---------- Home collection banner vectors (fall back to bundled SVGs) ----------
    men_vector = models.ImageField(upload_to='collections/', blank=True, null=True,
                                   verbose_name='وکتور کالکشن مردانه',
                                   help_text='اگر خالی باشد وکتور پیش‌فرض نمایش داده می‌شود')
    women_vector = models.ImageField(upload_to='collections/', blank=True, null=True,
                                     verbose_name='وکتور کالکشن زنانه',
                                     help_text='اگر خالی باشد وکتور پیش‌فرض نمایش داده می‌شود')

    # ---------- About-us text shown right before the footer on the home page ----------
    about_home = models.TextField(
        blank=True, verbose_name='متن دربارهٔ ما (قبل از فوتر)',
        default='اُرام‌شاپ با هدف ارائهٔ پوشاک باکیفیت مردانه و زنانه از برندهای معتبر راه‌اندازی شده است. '
                'ما با ضمانت اصالت کالا، ارسال سریع به سراسر ایران، ۷ روز ضمانت بازگشت و پشتیبانی پاسخگو '
                'تلاش می‌کنیم تجربه‌ای آرام و مطمئن از خرید آنلاین برای شما بسازیم.')

    class Meta:
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'

    def __str__(self):
        return 'تنظیمات سایت'

    def save(self, *args, **kwargs):
        # Single settings row only
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class NewsletterSubscriber(models.Model):
    """Newsletter subscribers - registered with an email or mobile number."""

    email = models.EmailField(unique=True, null=True, blank=True, verbose_name='ایمیل')
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name='موبایل')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ عضویت')

    class Meta:
        verbose_name = 'مشترک خبرنامه'
        verbose_name_plural = 'مشترکین خبرنامه'
        ordering = ('-created_at',)

    def __str__(self):
        return self.email or self.mobile or f'#{self.pk}'

    @property
    def contact(self):
        return self.email or self.mobile or ''


class NewsletterCampaign(models.Model):
    """Sent newsletter campaigns (history)."""

    subject = models.CharField(max_length=200, verbose_name='موضوع')
    body = models.TextField(verbose_name='متن')
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال')
    recipients_count = models.PositiveIntegerField(default=0, verbose_name='تعداد گیرندگان')

    class Meta:
        verbose_name = 'کمپین خبرنامه'
        verbose_name_plural = 'کمپین‌های خبرنامه'
        ordering = ('-sent_at',)

    def __str__(self):
        return self.subject


class HomeCategoryCard(models.Model):
    """The 4 category cards under the hero banner - image/icon editable from the panel."""

    title = models.CharField(max_length=50, verbose_name='عنوان')
    subtitle = models.CharField(max_length=80, blank=True, verbose_name='زیرعنوان')
    link = models.CharField(max_length=200, default='/shop/', verbose_name='لینک')
    image = models.ImageField(upload_to='home-cards/', blank=True, null=True,
                              verbose_name='تصویر (اختیاری — جای آیکون)')
    icon_class = models.CharField(max_length=50, blank=True, default='lni lni-tshirt',
                                  verbose_name='کلاس آیکون (اگر تصویر ندارید)')
    color = models.CharField(max_length=20, default='#00B8CC', verbose_name='رنگ آیکون/پس‌زمینه')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'کارت دسته‌بندی صفحه اصلی'
        verbose_name_plural = 'کارت‌های دسته‌بندی صفحه اصلی'
        ordering = ('order',)

    def __str__(self):
        return self.title
