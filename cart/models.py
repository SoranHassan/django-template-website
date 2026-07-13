from django.db import models
from accounts.models import CustomUser
from catalog.models import ProductVariant


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='cart', verbose_name='کاربر')
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name='کلید سشن')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید'

    def __str__(self):
        return f'{self.user or self.session_key}'

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total(self):
        # Shipping cost is added at the checkout step
        return self.subtotal


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='سبد خرید')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items', verbose_name='واریانت محصول')
    quantity = models.PositiveIntegerField(default=1,verbose_name='تعداد')

    class Meta:
        verbose_name = 'آیتم سبد خرید'
        verbose_name_plural = 'آیتم‌های سبد خرید'
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f'{self.cart} - {self.variant}'

    @property
    def total_price(self):
        from decimal import Decimal
        return self.variant.final_price * Decimal(str(self.quantity))
