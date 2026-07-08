from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.views import View

from .models import Post


class PostListView(View):
    def get(self, request):
        posts = Post.objects.filter(is_published=True)
        page = Paginator(posts, 9).get_page(request.GET.get('page'))
        return render(request, 'blog/list.html', {'page': page})


class PostDetailView(View):
    def get(self, request, slug):
        post = get_object_or_404(Post, slug=slug, is_published=True)
        others = Post.objects.filter(is_published=True).exclude(pk=post.pk)[:3]
        return render(request, 'blog/detail.html', {'post': post, 'other_posts': others})
