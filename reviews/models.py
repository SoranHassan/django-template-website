from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
from catalog.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='محصول')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews', verbose_name='کاربر')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)], verbose_name='امتیاز')
    title = models.CharField(max_length=100, blank=True, verbose_name='عنوان')
    body = models.TextField(verbose_name='متن نظر')
    is_approved = models.BooleanField(default=False, verbose_name='تأیید شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ('-created_at',)
        unique_together = ('product', 'user')

    def __str__(self):
        return f'{self.user.mobile} - {self.product.name} - {self.rating}★'