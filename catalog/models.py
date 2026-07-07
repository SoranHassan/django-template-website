from django.db import models


class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام برند')
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name='اسلاگ')
    logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name='لوگو')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام دسته‌بندی')
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name='اسلاگ')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='دسته‌بندی والد')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='تصویر')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=10, verbose_name='سایز')

    class Meta:
        verbose_name = 'سایز'
        verbose_name_plural = 'سایزها'

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=50, verbose_name='نام رنگ')
    hex_code = models.CharField(max_length=7, verbose_name='کد رنگ', help_text='مثال: #FF5733')

    class Meta:
        verbose_name = 'رنگ'
        verbose_name_plural = 'رنگ‌ها'

    def __str__(self):
        return f'{self.name} ({self.hex_code})'


class Product(models.Model):
    GENDER_CHOICES = [
        ('men', 'مردانه'),
        ('women', 'زنانه'),
        ('kids', 'بچگانه'),
        ('unisex', 'همه')]

    CATEGORY_TYPE_CHOICES = [
        ('top', 'بالاتنه'),
        ('bottom', 'پایین‌تنه')]

    name = models.CharField(max_length=200, verbose_name='نام محصول')
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name='اسلاگ')
    brand = models.ForeignKey(Brand,on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='برند')
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True,related_name='products',verbose_name='دسته‌بندی')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unisex', verbose_name='جنسیت')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت')
    original_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name='قیمت قبل از تخفیف')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    sku = models.CharField(max_length=50, blank=True, null=True, default=None, verbose_name='کد محصول (SKU)') # unique=True must be Add
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPE_CHOICES, blank=True, verbose_name='نوع اندام')

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(
                (self.original_price - self.price) / self.original_price * 100)
        return 0

    @property
    def main_image(self):
        image = self.images.filter(is_main=True).first()
        return image or self.images.first()


class SizeChart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='size_charts', verbose_name='محصول')
    size = models.ForeignKey(Size,on_delete=models.CASCADE, related_name='charts', verbose_name='سایز')

    # TOP BODY
    shoulder = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='عرض شانه (cm)')
    sleeve = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='طول آستین (cm)')
    chest = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='عرض سینه (cm)')
    length_top = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='قد (cm)')

    # BOTTOM BODY
    waist = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='عرض کمر (cm)')
    hip = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='عرض ران (cm)')
    crotch = models.DecimalField(max_digits=5, decimal_places=1,null=True, blank=True,verbose_name='فاق (cm)')
    length_bottom = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='قد (cm)')

    class Meta:
        verbose_name = 'جدول سایزبندی'
        verbose_name_plural = 'جداول سایزبندی'
        unique_together = ('product', 'size')

    def __str__(self):
        return f'{self.product.name} - {self.size.name}'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='محصول')
    image = models.ImageField(upload_to='products/', verbose_name='تصویر')
    is_main = models.BooleanField(default=False, verbose_name='تصویر اصلی')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'
        ordering = ('order',)

    def __str__(self):
        return f'{self.product.name} - تصویر {self.order}'


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name='محصول')
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='سایز')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='رنگ')
    stock = models.PositiveIntegerField(default=0, verbose_name='موجودی')
    price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name='قیمت اختصاصی')

    class Meta:
        verbose_name = 'واریانت محصول'
        verbose_name_plural = 'واریانت‌های محصول'
        unique_together = ('product', 'size', 'color')

    def __str__(self):
        return f'{self.product.name} - {self.size} - {self.color}'

    @property
    def final_price(self):
        return self.price if self.price else self.product.price

    @property
    def is_available(self):
        return self.stock > 0