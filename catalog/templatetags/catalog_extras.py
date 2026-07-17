from django import template
from django.db.models import Avg, F, OuterRef, Subquery, Sum

from catalog.models import Product

register = template.Library()


def rating_subquery():
    """Approved average rating as a Subquery - avoids join interference with the sales Sum."""
    from reviews.models import Review
    return Subquery(
        Review.objects.filter(product=OuterRef('pk'), is_approved=True)
        .values('product').annotate(a=Avg('rating')).values('a')
    )


def collection_queryset(kind):
    """Collection querysets: new | discount | bestseller | wholesale.

    Regular collections exclude wholesale products - they live in their
    own section with per-user price masking.
    """
    qs = Product.objects.filter(is_active=True).prefetch_related(
        'images', 'variants__size', 'variants__color'
    ).annotate(avg_rating=rating_subquery())
    if kind == 'wholesale':
        return qs.filter(is_wholesale=True).order_by('-created_at')
    qs = qs.filter(is_wholesale=False)
    if kind == 'discount':
        return qs.filter(original_price__isnull=False,
                         original_price__gt=F('price')).order_by('-created_at')
    if kind == 'bestseller':
        return qs.annotate(sold=Sum('variants__order_items__quantity')).order_by(
            F('sold').desc(nulls_last=True), '-created_at')
    return qs.order_by('-created_at')


@register.inclusion_tag('catalog/_related_row.html', takes_context=True)
def product_row(context, kind='new', title='', limit=8):
    """Sliding product row usable on any page: {% product_row 'discount' 'Discounted' %}."""
    return {
        'row_title': title,
        'row_kind': kind,
        'row_products': collection_queryset(kind)[:limit],
        'wishlist_ids': context.get('wishlist_ids', []),
        'user': context.get('user'),
    }
