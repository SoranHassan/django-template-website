"""Shared test helpers."""
from accounts.models import CustomUser
from catalog.models import Product, ProductVariant, Size, Color


def make_user(mobile='09120000000', password='pass12345', **kwargs):
    return CustomUser.objects.create_user(mobile=mobile, password=password, **kwargs)


def make_product(stock=5, price=1000, slug='test-product', name='محصول تست'):
    product = Product.objects.create(name=name, slug=slug, price=price)
    size, _ = Size.objects.get_or_create(name='L')
    color, _ = Color.objects.get_or_create(name='قرمز', defaults={'hex_code': '#FF0000'})
    variant = ProductVariant.objects.create(product=product, size=size, color=color, stock=stock)
    return product, variant
