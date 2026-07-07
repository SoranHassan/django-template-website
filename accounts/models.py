from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    mobile = models.CharField(max_length=11, unique=True, verbose_name='شماره موبایل')
    first_name = models.CharField(max_length=50,blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=50,blank=True, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    avatar = models.ImageField(upload_to='avatars/',blank=True, null=True, verbose_name='تصویر پروفایل')
    bio = models.TextField(blank=True, verbose_name='درباره من')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_staff = models.BooleanField(default=False, verbose_name='کارمند')
    date_joined = models.DateTimeField(default=timezone.now,verbose_name='تاریخ عضویت')

    objects = CustomUserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.mobile

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.mobile


class OTP(models.Model):
    mobile = models.CharField(max_length=11, verbose_name='شماره موبایل')
    code = models.CharField(max_length=6, verbose_name='کد تأیید')
    created_at = models.DateTimeField(auto_now_add=True,verbose_name='زمان ایجاد')
    expires_at = models.DateTimeField(verbose_name='زمان انقضا')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')

    class Meta:
        verbose_name = 'کد تأیید'
        verbose_name_plural = 'کدهای تأیید'

    def __str__(self):
        return f'{self.mobile} - {self.code}'

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses', verbose_name='کاربر')
    first_name = models.CharField(max_length=50, verbose_name='نام')
    last_name = models.CharField(max_length=50, verbose_name='نام خانوادگی')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    phone = models.CharField(max_length=11, verbose_name='تلفن')
    address1 = models.CharField(max_length=255, verbose_name='آدرس ۱')
    address2 = models.CharField(max_length=255, blank=True, verbose_name='آدرس ۲')
    city = models.CharField(max_length=100, verbose_name='شهر')
    zip = models.CharField(max_length=10, verbose_name='کد پستی')
    is_default = models.BooleanField(default=False,verbose_name='آدرس پیش‌فرض')

    class Meta:
        verbose_name = 'آدرس'
        verbose_name_plural = 'آدرس‌ها'

    def __str__(self):
        return f'{self.user.mobile} - {self.city}'
