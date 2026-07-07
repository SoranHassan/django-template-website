from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Q

from .models import Brand, Category, Product, ProductVariant





class HomeView(View):
    def get(self, request):

        products = Product.objects.filter(is_active=True).prefetch_related('images')[:8]
        brands = Brand.objects.filter(is_active=True)
        return render(request, 'catalog/home.html', {
            'products': products,
            'brands': brands,
        })


class ProductListView(View):
    def get(self, request):
        products = Product.objects.filter(is_active=True).prefetch_related('images', 'variants')
        category_slug = request.GET.get('category')
        if category_slug:
            products = products.filter(category__slug=category_slug)

        brand_slug = request.GET.get('brand')
        if brand_slug:
            products = products.filter(brand__slug=brand_slug)

        gender = request.GET.get('gender')
        if gender:
            products = products.filter(gender=gender)

        size = request.GET.get('size')
        if size:
            products = products.filter(variants__size__name=size)

        color = request.GET.get('color')
        if color:
            products = products.filter(variants__color__name=color)

        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)

        query = request.GET.get('q')
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__name__icontains=query)
            )

        sort = request.GET.get('sort', 'newest')
        if sort == 'newest':
            products = products.order_by('-created_at')
        elif sort == 'price_low':
            products = products.order_by('price')
        elif sort == 'price_high':
            products = products.order_by('-price')

        products = products.distinct()

        categories = Category.objects.filter(is_active=True)
        brands = Brand.objects.filter(is_active=True)

        return render(request, 'catalog/shop-style.html', {
            'products': products,
            'categories': categories,
            'brands': brands,
            'current_category': category_slug,
            'current_brand': brand_slug,
            'current_gender': gender,
            'current_sort': sort,
        })


class ProductDetailView(View):

    def get(self, request, id):
        product = get_object_or_404(
            Product.objects.prefetch_related(
                'images',
                'variants__size',
                'variants__color',
                'reviews'
            ),
            id=id,
            is_active=True
        )

        variants = product.variants.all()
        sizes = set(v.size for v in variants if v.size)
        colors = set(v.color for v in variants if v.color)

        similar_products = Product.objects.filter(
            is_active=True,
            category=product.category
        ).exclude(pk=product.pk).prefetch_related('images')[:6]

        reviews = product.reviews.filter(is_approved=True)
        avg_rating = 0
        if reviews.exists():
            avg_rating = round(
                sum(r.rating for r in reviews) / reviews.count(), 1
            )

        return render(request, 'catalog/shop-single-v1.html', {
            'product': product,
            'variants': variants,
            'sizes': sizes,
            'colors': colors,
            'similar_products': similar_products,
            'reviews': reviews,
            'avg_rating': avg_rating,
        })