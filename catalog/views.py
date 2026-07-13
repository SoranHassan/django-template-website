from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Q

from core.models import HeroSlide
from .models import Brand, Category, Product, ProductVariant


class SearchSuggestView(View):
    """Live search suggestions for the dropdown under the search box."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if len(query) < 2:
            return JsonResponse({'results': []})

        products = Product.objects.filter(
            Q(name__icontains=query) | Q(brand__name__icontains=query),
            is_active=True,
        ).prefetch_related('images')[:6]

        results = [{
            'name': p.name,
            'url': p.get_absolute_url(),
            'price': f'{p.price:,.0f}',
            'image': p.main_image.image.url if p.main_image else '',
        } for p in products]

        return JsonResponse({'results': results})


class HomeView(View):
    def get(self, request):
        from .templatetags.catalog_extras import collection_queryset, rating_subquery
        base_qs = Product.objects.filter(is_active=True).prefetch_related(
            'images', 'variants__size', 'variants__color').annotate(avg_rating=rating_subquery())

        from core.models import HomeCategoryCard
        from reviews.models import Review
        from accounts.models import CustomUser
        from django.db.models import Avg

        recent_reviews = Review.objects.filter(is_approved=True).select_related(
            'user', 'product').order_by('-created_at')[:6]

        stats = {
            'products': Product.objects.filter(is_active=True).count(),
            'brands': Brand.objects.filter(is_active=True).count(),
            'customers': CustomUser.objects.filter(is_active=True).count(),
            'rating': round(Review.objects.filter(is_approved=True).aggregate(a=Avg('rating'))['a'] or 5, 1),
        }

        # Default home category cards (when none are defined in the panel) - linked to real categories
        cat_specs = [
            ('تیشرت', 'خنک و راحت', 'app/img/categories/tshirt.svg', ['تیشرت', 'تی‌شرت', 'تی شرت']),
            ('هودی و سویشرت', 'گرم و اسپرت', 'app/img/categories/hoodie.svg', ['هودی و سویشرت', 'هودی', 'سویشرت']),
            ('شلوار', 'جین و کتان', 'app/img/categories/pants.svg', ['شلوار']),
            ('کفش', 'اسپرت و رسمی', 'app/img/categories/shoes.svg', ['کفش']),
        ]
        default_cats = []
        for title, sub, img, names in cat_specs:
            cat = Category.objects.filter(name__in=names, is_active=True).first()
            link = f'/shop/?category={cat.slug}' if cat else '/shop/'
            default_cats.append({'title': title, 'sub': sub, 'img': img, 'link': link})

        return render(request, 'catalog/home.html', {
            'hero_slides': HeroSlide.objects.filter(is_active=True),
            'products': collection_queryset('bestseller')[:8],
            'new_products': base_qs.order_by('-created_at')[:10],
            'men_products': base_qs.filter(gender__in=['men', 'unisex']).order_by('-created_at')[:10],
            'women_products': base_qs.filter(gender__in=['women', 'unisex']).order_by('-created_at')[:10],
            'brands': Brand.objects.filter(is_active=True),
            'home_cards': HomeCategoryCard.objects.filter(is_active=True),
            'recent_reviews': recent_reviews,
            'stats': stats,
            'default_cats': default_cats,
        })


class ProductListView(View):
    def get(self, request):
        from .templatetags.catalog_extras import rating_subquery
        products = Product.objects.filter(is_active=True).prefetch_related(
            'images', 'variants__size', 'variants__color').annotate(avg_rating=rating_subquery())
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

        # Collections: newest / discounted / bestseller
        from django.db.models import F, Sum
        collection = request.GET.get('collection', '')
        if collection == 'discount':
            products = products.filter(original_price__isnull=False, original_price__gt=F('price'))
        elif collection == 'bestseller':
            products = products.annotate(sold=Sum('variants__order_items__quantity'))

        sort = request.GET.get('sort', 'newest')
        if collection == 'bestseller':
            products = products.order_by(F('sold').desc(nulls_last=True), '-created_at')
        elif sort == 'price_low':
            products = products.order_by('price')
        elif sort == 'price_high':
            products = products.order_by('-price')
        else:
            products = products.order_by('-created_at')

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
            'current_collection': collection,
            'collections': [('', 'همه'), ('new', 'جدیدترین'), ('discount', 'تخفیف‌دار'), ('bestseller', 'پرفروش')],
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
        # Sizes in numeric/logical order (small to large), not random
        seen = set()
        sizes = []
        for v in sorted(variants, key=lambda x: (x.size.sort_order, x.size.name) if x.size else (0, '')):
            if v.size and v.size.pk not in seen:
                seen.add(v.size.pk)
                sizes.append(v.size)
        colors = list({v.color.pk: v.color for v in variants if v.color}.values())

        # Size chart (centimetres) - always shown when data exists;
        # only columns with at least one value are displayed (independent of product type)
        size_charts = list(product.size_charts.select_related('size').all())
        _chart_labels = [
            ('shoulder', 'عرض شانه'), ('sleeve', 'طول آستین'), ('chest', 'عرض سینه'),
            ('length_top', 'قد بالاتنه'), ('waist', 'عرض کمر'), ('hip', 'عرض ران'),
            ('crotch', 'فاق'), ('length_bottom', 'قد پایین‌تنه'),
        ]
        size_chart_columns = [
            (f, label) for f, label in _chart_labels
            if any(getattr(c, f) is not None for c in size_charts)
        ]
        # Prepare the rows against the active columns for simple template rendering
        size_chart_rows = [
            {'size': c.size.name, 'values': [getattr(c, f) for f, _ in size_chart_columns]}
            for c in size_charts
        ]

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
            'size_charts': size_charts,
            'size_chart_columns': size_chart_columns,
            'size_chart_rows': size_chart_rows,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'similar_products': similar_products,
        })