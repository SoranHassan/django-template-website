"""DRF serializers for the public JSON API v1.

These mirror the exact shape the OramShop bot (and other clients) expect. Two
rules are enforced here on purpose:

* Wholesale prices never leave the site — any product with ``is_wholesale`` has
  its ``price`` / ``original_price`` returned as ``null``.
* Image and product links are always returned as absolute URLs, so a client can
  use them directly without knowing the site's domain.
"""
from rest_framework import serializers


def _abs(request, url):
    """Turn a relative media/URL path into an absolute one (or ``None``)."""
    return request.build_absolute_uri(url) if url else None


class ProductSummarySerializer(serializers.Serializer):
    """Compact product shape used in list endpoints."""

    id = serializers.IntegerField(source='pk')
    name = serializers.CharField()
    slug = serializers.CharField()
    is_wholesale = serializers.BooleanField()
    price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    gender = serializers.CharField()
    rating = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    def get_price(self, p):
        return None if p.is_wholesale else int(p.price)

    def get_original_price(self, p):
        return None if p.is_wholesale or not p.original_price else int(p.original_price)

    def get_discount_percent(self, p):
        return p.discount_percent or 0

    def get_brand(self, p):
        return p.brand.name if p.brand else None

    def get_category(self, p):
        return p.category.name if p.category else None

    def get_rating(self, p):
        return float(p.avg_rating) if getattr(p, 'avg_rating', None) else None

    def get_in_stock(self, p):
        return any(v.stock > 0 for v in p.variants.all())

    def get_image(self, p):
        return _abs(self.context['request'], p.main_image.image.url) if p.main_image else None

    def get_url(self, p):
        return _abs(self.context['request'], p.get_absolute_url())


class ProductDetailSerializer(ProductSummarySerializer):
    """Full product shape: summary + description, sku, all images and variants."""

    description = serializers.CharField()
    sku = serializers.CharField()
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    def get_images(self, p):
        request = self.context['request']
        return [_abs(request, im.image.url) for im in p.images.all()]

    def get_variants(self, p):
        return [{
            'id': v.pk,
            'size': v.size.name if v.size else None,
            'color': v.color.name if v.color else None,
            'color_hex': v.color.hex_code if v.color else None,
            'stock': v.stock,
            'price': None if p.is_wholesale else int(v.final_price),
        } for v in p.variants.all()]


class CategorySerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk')
    name = serializers.CharField()
    slug = serializers.CharField()


class BrandSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk')
    name = serializers.CharField()
    slug = serializers.CharField()
    logo = serializers.SerializerMethodField()

    def get_logo(self, b):
        return _abs(self.context['request'], b.logo.url) if b.logo else None
