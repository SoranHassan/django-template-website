from django.contrib import admin
from .models import Coupon, CouponUsage, Order, OrderItem


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_amount', 'used_count', 'max_uses', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)
    list_editable = ('is_active',)
    filter_horizontal = ('applicable_categories', 'applicable_products')


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'used_at')
    search_fields = ('coupon__code', 'user__mobile')
    readonly_fields = ('used_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('variant', 'quantity', 'price')
    readonly_fields = ('variant', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'discount_amount', 'final_total', 'tracking_code', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__mobile', 'tracking_code', 'zarinpal_ref_id')
    ordering = ('-created_at',)
    inlines = (OrderItemInline,)
    readonly_fields = ('created_at', 'updated_at', 'zarinpal_authority', 'zarinpal_ref_id')

    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('user', 'address', 'coupon', 'status', 'tracking_code', 'notes')
        }),
        ('مبالغ', {
            'fields': ('total_price', 'discount_amount', 'tax', 'shipping_cost')
        }),
        ('پرداخت', {
            'fields': ('zarinpal_authority', 'zarinpal_ref_id')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']

    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')
    mark_as_paid.short_description = 'علامت‌گذاری به عنوان پرداخت شده'

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
    mark_as_shipped.short_description = 'علامت‌گذاری به عنوان ارسال شده'

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')
    mark_as_delivered.short_description = 'علامت‌گذاری به عنوان تحویل داده شده'

from .models import ShippingMethod


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'description', 'order', 'is_active')
    list_editable = ('price', 'order', 'is_active')
