from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import JsonResponse
from catalog.models import Product
from .models import Review


class ReviewCreateView(LoginRequiredMixin, View):
    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)

        if Review.objects.filter(product=product,user=request.user).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'شما قبلاً برای این محصول نظر ثبت کرده‌اید'
            }, status=400)

        rating = request.POST.get('rating')
        title = request.POST.get('title', '')[:100]
        body = request.POST.get('body')

        if not rating or not body:
            return JsonResponse({
                'status': 'error',
                'message': 'امتیاز و متن نظر الزامی است'
            }, status=400)

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0
        if not 1 <= rating <= 5:
            return JsonResponse({
                'status': 'error',
                'message': 'امتیاز باید عددی بین ۱ تا ۵ باشد'
            }, status=400)

        Review.objects.create(product=product, user=request.user, rating=rating, title=title, body=body, is_approved=False)

        return JsonResponse({
            'status': 'ok',
            'message': 'نظر شما با موفقیت ثبت شد و پس از تأیید نمایش داده می‌شود'
        })