from django import template
from django.db.models import Avg, F, OuterRef, Subquery, Sum

from catalog.models import Product

register = template.Library()


def rating_subquery():
    """میانگین امتیاز تأییدشده به‌صورت Subquery — تا با Sum فروش تداخل join نداشته باشد"""
    from reviews.models import Review
    return Subquery(
        Review.objects.filter(product=OuterRef('pk'), is_approved=True)
        .values('product').annotate(a=Avg('rating')).values('a')
    )


def collection_queryset(kind):
    """کوئری مجموعه‌ها: new | discount | bestseller"""
    qs = Product.objects.filter(is_active=True).prefetch_related(
        'images', 'variants__size', 'variants__color'
    ).annotate(avg_rating=rating_subquery())
    if kind == 'discount':
        return qs.filter(original_price__isnull=False,
                         original_price__gt=F('price')).order_by('-created_at')
    if kind == 'bestseller':
        return qs.annotate(sold=Sum('variants__order_items__quantity')).order_by(
            F('sold').desc(nulls_last=True), '-created_at')
    return qs.order_by('-created_at')


@register.inclusion_tag('catalog/_related_row.html', takes_context=True)
def product_row(context, kind='new', title='', limit=8):
    """ردیف اسلایدی محصولات برای استفاده در هر صفحه: {% product_row 'discount' 'تخفیف‌دارها' %}"""
    return {
        'row_title': title,
        'row_kind': kind,
        'row_products': collection_queryset(kind)[:limit],
        'wishlist_ids': context.get('wishlist_ids', []),
        'user': context.get('user'),
    }
