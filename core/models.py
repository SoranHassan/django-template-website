from django.db import models


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
    """اسلایدهای بنر اصلی سایت — از پنل ادمین جنگو قابل مدیریت است"""

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
    """تنظیمات ظاهری سایت — از ادمین قابل تغییر بدون دیپلوی"""

    TOPBAR_CHOICES = [
        ('black', 'مشکی ساده'),
        ('charcoal', 'شارکول'),
        ('gradient-cyan', 'گرادینت مشکی → سایان'),
        ('gradient-dark', 'گرادینت سرمه‌ای تیره'),
        ('ivory', 'کرم روشن (متن تیره)'),
    ]

    home_watermark = models.CharField(max_length=60, default='ORAM SHOP',
                                      verbose_name='متن واترمارک صفحه اصلی')
    topbar_style = models.CharField(max_length=20, choices=TOPBAR_CHOICES, default='black',
                                    verbose_name='رنگ نوار اطلاعیه بالای سایت')

    class Meta:
        verbose_name = 'تنظیمات سایت'
        verbose_name_plural = 'تنظیمات سایت'

    def __str__(self):
        return 'تنظیمات سایت'

    def save(self, *args, **kwargs):
        # فقط یک ردیف تنظیمات
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomeCategoryCard(models.Model):
    """۴ کارت دسته‌بندی زیر بنر اصلی — تصویر/آیکون از پنل قابل تغییر"""

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
