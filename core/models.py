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