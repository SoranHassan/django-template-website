from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from catalog.models import Product


class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return ['catalog:index', 'catalog:shop_style_1']

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Post.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    'products': ProductSitemap,
    'blog': BlogSitemap,
    'static': StaticViewSitemap,
}
