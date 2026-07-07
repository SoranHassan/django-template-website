import re

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import CustomUser, Address

MOBILE_RE = re.compile(r'^09\d{9}$')


def validate_mobile(value):
    if not MOBILE_RE.match(value or ''):
        raise ValidationError('شماره موبایل معتبر نیست (مثال: 09121234567)')


class LoginForm(forms.Form):
    mobile = forms.CharField(max_length=11, validators=[validate_mobile])
    password = forms.CharField()


class SignupForm(forms.Form):
    mobile = forms.CharField(max_length=11, validators=[validate_mobile])
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    password = forms.CharField()
    confirm_password = forms.CharField()

    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        if CustomUser.objects.filter(mobile=mobile).exists():
            raise ValidationError('این شماره موبایل قبلاً ثبت شده است')
        return mobile

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            raise ValidationError('رمز عبور و تکرار آن یکسان نیستند')
        if password:
            validate_password(password)
        return cleaned


class ForgotPasswordForm(forms.Form):
    mobile = forms.CharField(max_length=11, validators=[validate_mobile])


class ResetPasswordForm(forms.Form):
    password = forms.CharField()
    confirm_password = forms.CharField()

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if password and confirm and password != confirm:
            raise ValidationError('رمز عبور و تکرار آن یکسان نیستند')
        if password:
            validate_password(password)
        return cleaned


class ProfileForm(forms.Form):
    MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB

    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=False)
    bio = forms.CharField(required=False)
    avatar = forms.ImageField(required=False)

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and avatar.size > self.MAX_AVATAR_SIZE:
            raise ValidationError('حجم تصویر پروفایل نباید بیشتر از ۲ مگابایت باشد')
        return avatar


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['first_name', 'last_name', 'email', 'phone',
                  'address1', 'address2', 'city', 'zip', 'is_default']

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        validate_mobile(phone)
        return phone

    def clean_zip(self):
        zip_code = self.cleaned_data['zip']
        if not re.match(r'^\d{10}$', zip_code or ''):
            raise ValidationError('کد پستی باید ۱۰ رقم باشد')
        return zip_code


def first_error(form):
    """اولین پیام خطای فرم به صورت یک رشته — برای نمایش در تمپلیت‌های فعلی"""
    for errors in form.errors.values():
        return errors[0]
    return 'اطلاعات وارد شده معتبر نیست'
