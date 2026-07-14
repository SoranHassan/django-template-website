"""JSON API v1 - built for the OramShop Telegram bot (and other integrations).

Plain Django JSON views (no DRF dependency). Authentication is a static
key sent as the ``X-API-Key`` header and configured via the ``BOT_API_KEY``
environment variable. When the variable is empty the whole API is disabled.
"""
from functools import wraps

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from catalog.models import Brand, Category, Product


RATE_LIMIT_PER_MINUTE = 120


def _rate_limited(request):
    """Sliding one-minute counter per client IP (cache-based). True = over limit."""
    from django.core.cache import cache

    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
        or request.META.get('REMOTE_ADDR', 'unknown')
    key = f'api-rl:{ip}'
    try:
        count = cache.get_or_set(key, 0, 60)
        cache.incr(key)
    except ValueError:
        # Key expired between get_or_set and incr
        cache.set(key, 1, 60)
        count = 0
    return count >= RATE_LIMIT_PER_MINUTE


def api_key_required(view):
    """Reject requests without the correct X-API-Key header (401/503/429)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from core.utils import runtime_config
        configured = runtime_config('bot_api_key_override', 'BOT_API_KEY')
        if not configured:
            return JsonResponse(
                {'error': 'API disabled: BOT_API_KEY is not configured'}, status=503)
        if request.headers.get('X-API-Key') != configured:
            return JsonResponse({'error': 'invalid or missing X-API-Key'}, status=401)
        if _rate_limited(request):
            return JsonResponse({'error': 'rate limit exceeded (120 requests/minute)'},
                                status=429)
        return view(request, *args, **kwargs)

    return wrapper


def _abs(request, url):
    """Absolute URL helper so the bot can use links/images directly."""
    return request.build_absolute_uri(url) if url else None


def _product_summary(request, p):
    return {
        'id': p.pk,
        'name': p.name,
        'slug': p.slug,
        'price': int(p.price),
        'original_price': int(p.original_price) if p.original_price else None,
        'discount_percent': p.discount_percent or 0,
        'brand': p.brand.name if p.brand else None,
        'category': p.category.name if p.category else None,
        'gender': p.gender,
        'rating': float(p.avg_rating) if getattr(p, 'avg_rating', None) else None,
        'in_stock': any(v.stock > 0 for v in p.variants.all()),
        'image': _abs(request, p.main_image.image.url) if p.main_image else None,
        'url': _abs(request, p.get_absolute_url()),
    }


@require_GET
@api_key_required
def product_list(request):
    """GET /api/v1/products/?q=&category=&brand=&gender=&page=&page_size="""
    from catalog.templatetags.catalog_extras import rating_subquery
    from django.db.models import Q

    qs = Product.objects.filter(is_active=True).select_related(
        'brand', 'category').prefetch_related('images', 'variants').annotate(
        avg_rating=rating_subquery()).order_by('-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) |
                       Q(brand__name__icontains=q))
    if request.GET.get('category'):
        qs = qs.filter(category__slug=request.GET['category'])
    if request.GET.get('brand'):
        qs = qs.filter(brand__slug=request.GET['brand'])
    if request.GET.get('gender'):
        qs = qs.filter(gender=request.GET['gender'])

    try:
        page_size = min(max(int(request.GET.get('page_size', 10)), 1), 50)
    except ValueError:
        page_size = 10
    paginator = Paginator(qs, page_size)
    try:
        page_num = max(int(request.GET.get('page', 1)), 1)
    except ValueError:
        page_num = 1
    page = paginator.get_page(page_num)

    return JsonResponse({
        'count': paginator.count,
        'page': page.number,
        'pages': paginator.num_pages,
        'results': [_product_summary(request, p) for p in page.object_list],
    })


@require_GET
@api_key_required
def product_detail(request, pk):
    """GET /api/v1/products/<id>/ - full detail incl. variants and images."""
    from catalog.templatetags.catalog_extras import rating_subquery

    try:
        p = Product.objects.select_related('brand', 'category').prefetch_related(
            'images', 'variants__size', 'variants__color').annotate(
            avg_rating=rating_subquery()).get(pk=pk, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'product not found'}, status=404)

    data = _product_summary(request, p)
    data.update({
        'description': p.description,
        'sku': p.sku,
        'images': [_abs(request, im.image.url) for im in p.images.all()],
        'variants': [{
            'id': v.pk,
            'size': v.size.name if v.size else None,
            'color': v.color.name if v.color else None,
            'color_hex': v.color.hex_code if v.color else None,
            'stock': v.stock,
            'price': int(v.final_price),
        } for v in p.variants.all()],
    })
    return JsonResponse(data)


@require_GET
@api_key_required
def category_list(request):
    """GET /api/v1/categories/"""
    cats = Category.objects.filter(is_active=True).order_by('name')
    return JsonResponse({'results': [
        {'id': c.pk, 'name': c.name, 'slug': c.slug} for c in cats]})


@require_GET
@api_key_required
def brand_list(request):
    """GET /api/v1/brands/"""
    brands = Brand.objects.filter(is_active=True).order_by('name')
    return JsonResponse({'results': [
        {'id': b.pk, 'name': b.name, 'slug': b.slug,
         'logo': _abs(request, b.logo.url) if b.logo else None} for b in brands]})
