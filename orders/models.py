from django.db import models
from django.utils import timezone
from accounts.models import CustomUser, Address
from catalog.models import ProductVariant, Product, Category


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'درصدی'),
        ('fixed', 'مبلغ ثابت'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='کد تخفیف')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent', verbose_name='نوع تخفیف')
    discount_value = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='مقدار تخفیف')
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='حداقل مبلغ سفارش')
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name='حداکثر مبلغ تخفیف')
    max_uses = models.PositiveIntegerField(default=0, verbose_name='حداکثر تعداد استفاده (۰ = نامحدود)')
    used_count = models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده شده')
    max_uses_per_user = models.PositiveIntegerField(default=1, verbose_name='حداکثر استفاده برای هر کاربر')
    valid_from = models.DateTimeField(verbose_name='تاریخ شروع')
    valid_until = models.DateTimeField(verbose_name='تاریخ پایان')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    applicable_categories = models.ManyToManyField(Category, blank=True, verbose_name='دسته‌بندی‌های مشمول')
    applicable_products = models.ManyToManyField(Product,blank=True, verbose_name='محصولات مشمول')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'

    def __str__(self):
        return self.code

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False, 'کد تخفیف غیرفعال است'
        if now < self.valid_from:
            return False, 'کد تخفیف هنوز فعال نشده است'
        if now > self.valid_until:
            return False, 'کد تخفیف منقضی شده است'
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False, 'ظرفیت استفاده از این کد تخفیف تمام شده است'
        return True, 'معتبر'

    def calculate_discount(self, subtotal):
        """محاسبه مقدار تخفیف"""
        if self.discount_type == 'percent':
            discount = subtotal * self.discount_value / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value
        return min(discount, subtotal)


class CouponUsage(models.Model):
    """ردیابی استفاده از کد تخفیف"""

    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages', verbose_name='کد تخفیف')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='coupon_usages', verbose_name='کاربر')
    order = models.ForeignKey('Order',on_delete=models.CASCADE, related_name='coupon_usages', verbose_name='سفارش')
    used_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ استفاده')

    class Meta:
        verbose_name = 'استفاده از کد تخفیف'
        verbose_name_plural = 'استفاده‌های کد تخفیف'

    def __str__(self):
        return f'{self.user.mobile} - {self.coupon.code}'


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('returned', 'مرجوع شده'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='orders', verbose_name='کاربر')
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True, related_name='orders', verbose_name='آدرس تحویل')
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name='کد تخفیف')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='مبلغ کل')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ تخفیف')
    tax = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مالیات')
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='هزینه ارسال')
    tracking_code = models.CharField(max_length=50, blank=True, verbose_name='کد رهگیری')
    zarinpal_authority = models.CharField(max_length=100, blank=True, verbose_name='کد پرداخت زرین‌پال')
    zarinpal_ref_id = models.CharField(max_length=100, blank=True, verbose_name='کد مرجع زرین‌پال')
    notes = models.TextField(blank=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارش‌ها'
        ordering = ('-created_at',)

    def __str__(self):
        return f'سفارش #{self.pk} - {self.user.mobile}'

    @property
    def final_total(self):
        return self.total_price - self.discount_amount + self.tax + self.shipping_cost


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='سفارش')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='order_items', verbose_name='واریانت محصول')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت در زمان خرید')

    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'

    def __str__(self):
        return f'{self.order} - {self.variant}'

    @property
    def total_price(self):
        return self.price * self.quantity