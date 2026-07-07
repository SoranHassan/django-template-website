from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OTP, Address


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('mobile','first_name','last_name','email','is_active','is_staff','date_joined')
    list_filter = ('is_active','is_staff','is_superuser','date_joined')
    search_fields = ('mobile','first_name','last_name','email')
    ordering = ('-date_joined',)

    fieldsets = (
        ('اطلاعات ورود', {
            'fields': ('mobile', 'password')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name','last_name','email','avatar','bio')}),
        ('دسترسی‌ها', {
            'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('تاریخ‌ها', {
            'fields': ('date_joined',)}),)

    add_fieldsets = (
        ('ایجاد کاربر جدید', {
            'classes': ('wide',),
            'fields': ( 'mobile', 'first_name', 'last_name', 'password1', 'password2', 'is_active', 'is_staff')}),)

    readonly_fields = ('date_joined',)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ( 'mobile', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('mobile',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ( 'user', 'first_name', 'last_name', 'city', 'phone', 'is_default')
    list_filter = ('city', 'is_default')
    search_fields = ( 'user__mobile', 'first_name', 'last_name', 'city', 'phone')
    ordering = ('user',)