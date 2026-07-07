from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('variant', 'quantity')
    readonly_fields = ('variant',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'user', 'session_key', 'total_items', 'subtotal', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__mobile', 'session_key')
    ordering = ('-created_at',)
    inlines = (CartItemInline,)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ( 'cart', 'variant', 'quantity', 'total_price')
    search_fields = ('cart__user__mobile', 'variant__product__name')
