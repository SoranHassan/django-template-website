from django.db import models
from django.urls import reverse

from accounts.models import CustomUser


class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name='اسلاگ')
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='posts', verbose_name='نویسنده')
    image = models.ImageField(upload_to='blog/', blank=True, null=True, verbose_name='تصویر شاخص')
    excerpt = models.CharField(max_length=300, blank=True, verbose_name='خلاصه')
    body = models.TextField(verbose_name='متن')
    is_published = models.BooleanField(default=True, verbose_name='منتشر شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ انتشار')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین ویرایش')

    class Meta:
        verbose_name = 'نوشته'
        verbose_name_plural = 'نوشته‌ها'
        ordering = ('-created_at',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:detail', kwargs={'slug': self.slug})
