"""JSON API v1 — Django REST Framework class-based views.

Built for the OramShop Telegram bot (and any other external integration).

Security model (unchanged from the original plain-Django version):

* Authentication is a single static key sent in the ``X-API-Key`` header and
  configured via the ``BOT_API_KEY`` environment variable — or overridden at
  runtime from the dashboard (``bot_api_key_override``).
* When no key is configured the whole API is disabled (HTTP 503).
* A wrong/missing key is HTTP 401.
* Each client IP is limited to ``RATE_LIMIT_PER_MINUTE`` requests per minute
  (HTTP 429 once exceeded).

The gate lives in :class:`BotApiView.initial` so every endpoint inherits it,
and only ``GET`` handlers are defined, so any other method returns 405.
"""
from django.core.paginator import Paginator
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Brand, Category, Product
from .serializers import (BrandSerializer, CategorySerializer,
                          ProductDetailSerializer, ProductSummarySerializer)

# Requests per minute, per client IP. Tests patch this name — keep it here.
RATE_LIMIT_PER_MINUTE = 120


class ServiceDisabled(APIException):
    status_code = 503
    default_detail = 'API disabled: BOT_API_KEY is not configured'
    default_code = 'service_disabled'


class InvalidApiKey(APIException):
    status_code = 401
    default_detail = 'invalid or missing X-API-Key'
    default_code = 'invalid_api_key'


class RateLimited(APIException):
    status_code = 429
    default_detail = 'rate limit exceeded (120 requests/minute)'
    default_code = 'rate_limited'


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


class BotApiView(APIView):
    """Base view: X-API-Key gate (503/401) + per-IP rate limit (429).

    DRF's own auth/permission layers are disabled (see ``REST_FRAMEWORK`` in
    settings); the key check is done explicitly so we can return 503 vs 401.
    """

    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from core.utils import runtime_config
        configured = runtime_config('bot_api_key_override', 'BOT_API_KEY')
        if not configured:
            raise ServiceDisabled()
        if request.headers.get('X-API-Key') != configured:
            raise InvalidApiKey()
        if _rate_limited(request):
            raise RateLimited()


class ProductListView(BotApiView):
    """GET /api/v1/products/?q=&category=&brand=&gender=&page=&page_size="""

    def get(self, request):
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

        results = ProductSummarySerializer(
            page.object_list, many=True, context={'request': request}).data
        return Response({
            'count': paginator.count,
            'page': page.number,
            'pages': paginator.num_pages,
            'results': results,
        })


class ProductDetailView(BotApiView):
    """GET /api/v1/products/<id>/ — full detail incl. variants and images."""

    def get(self, request, pk):
        from catalog.templatetags.catalog_extras import rating_subquery

        try:
            p = Product.objects.select_related('brand', 'category').prefetch_related(
                'images', 'variants__size', 'variants__color').annotate(
                avg_rating=rating_subquery()).get(pk=pk, is_active=True)
        except Product.DoesNotExist:
            raise NotFound('product not found')

        return Response(ProductDetailSerializer(p, context={'request': request}).data)


class CategoryListView(BotApiView):
    """GET /api/v1/categories/"""

    def get(self, request):
        cats = Category.objects.filter(is_active=True).order_by('name')
        return Response({'results': CategorySerializer(
            cats, many=True, context={'request': request}).data})


class BrandListView(BotApiView):
    """GET /api/v1/brands/"""

    def get(self, request):
        brands = Brand.objects.filter(is_active=True).order_by('name')
        return Response({'results': BrandSerializer(
            brands, many=True, context={'request': request}).data})
