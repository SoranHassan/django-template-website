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