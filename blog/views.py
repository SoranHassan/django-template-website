from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.views import View

from catalog.models import Brand, Product
from .models import Post


def _related_products(post, limit=8):
    """Products related to the post body: match brand/product names; fall back to discounted items."""
    text = f'{post.title} {post.excerpt} {post.body}'.lower()

    matched_brands = [b for b in Brand.objects.filter(is_active=True) if b.name.lower() in text]
    qs = Product.objects.filter(is_active=True).prefetch_related('images')

    if matched_brands:
        related = qs.filter(brand__in=matched_brands).order_by('-created_at')[:limit]
        if related:
            return related, 'محصولات مرتبط با این مطلب'

    # Product names mentioned in the body
    matched = [p.pk for p in qs.only('pk', 'name')[:300] if len(p.name) > 5 and p.name.lower() in text]
    if matched:
        return qs.filter(pk__in=matched)[:limit], 'محصولات مرتبط با این مطلب'

    from django.db.models import F
    return (qs.filter(original_price__isnull=False, original_price__gt=F('price'))
              .order_by('-created_at')[:limit]), 'پیشنهادهای تخفیف‌دار'


class PostListView(View):
    def get(self, request):
        posts = Post.objects.filter(is_published=True)
        page = Paginator(posts, 9).get_page(request.GET.get('page'))
        return render(request, 'blog/list.html', {'page': page})


class PostDetailView(View):
    def get(self, request, slug):
        post = get_object_or_404(Post, slug=slug, is_published=True)
        others = Post.objects.filter(is_published=True).exclude(pk=post.pk)[:4]
        related, related_title = _related_products(post)
        return render(request, 'blog/detail.html', {
            'post': post,
            'other_posts': others,
            'related_products': related,
            'related_title': related_title,
        })
