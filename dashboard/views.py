from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from datetime import timedelta
import json
from accounts.models import CustomUser
from orders.models import Order, OrderItem
from reviews.models import Review
from catalog.models import Product, Category, Brand, ProductImage
from django.utils.text import slugify


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Just Staff Users Has Permission"""

    def test_func(self):
        return self.request.user.is_staff

class DashboardIndexView(StaffRequiredMixin, View):
    def get(self, request):
        now = timezone.now()
        users_count = CustomUser.objects.filter(is_active=True).count()
        orders_count = Order.objects.filter(status='pending').count()
        products_count = Product.objects.filter(is_active=True).count()
        total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_price'))['total'] or 0
        revenue_today = Order.objects.filter(status='delivered', created_at__date=now.date()).aggregate(total=Sum('total_price'))['total'] or 0
        revenue_week = Order.objects.filter(status='delivered', created_at__gte=now - timedelta(days=7)).aggregate(total=Sum('total_price'))['total'] or 0
        revenue_month = Order.objects.filter(status='delivered', created_at__gte=now - timedelta(days=30)).aggregate(total=Sum('total_price'))['total'] or 0
        recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
        pending_reviews = Review.objects.filter(is_approved=False).select_related('user', 'product')[:5]
        pending_reviews_count = Review.objects.filter(is_approved=False).count()
        pending_orders_count = Order.objects.filter(status='pending').count()

        return render(request, 'dashboard/index.html', {
            'users_count': users_count,
            'orders_count': orders_count,
            'products_count': products_count,
            'total_revenue': total_revenue,
            'revenue_today': revenue_today,
            'revenue_week': revenue_week,
            'revenue_month': revenue_month,
            'recent_orders': recent_orders,
            'pending_reviews': pending_reviews,
            'pending_reviews_count': pending_reviews_count,
            'pending_orders_count': pending_orders_count,
        })

class DashboardUsersListView(StaffRequiredMixin, View):
    def get(self, request):
        users = CustomUser.objects.all().order_by('-date_joined')
        staff_count = users.filter(is_staff=True).count()
        return render(request, 'dashboard/users-list.html', {'users': users,'staff_count': staff_count})

class DashboardProductsListView(StaffRequiredMixin, View):
    def get(self, request):
        products = Product.objects.select_related('brand', 'category').prefetch_related('images', 'variants')
        category = request.GET.get('category')
        status = request.GET.get('status')
        gender = request.GET.get('gender')

        if category:
            products = products.filter(category__pk=category)
        if status == 'active':
            products = products.filter(is_active=True)
        elif status == 'inactive':
            products = products.filter(is_active=False)
        if gender:
            products = products.filter(gender=gender)

        return render(request, 'dashboard/products-list.html', {
            'products': products,
            'categories': Category.objects.all(),
            'total_products': Product.objects.count(),
            'active_products': Product.objects.filter(is_active=True).count(),
            'low_stock': Product.objects.filter(variants__stock__lte=3).distinct().count(),
            'categories_count': Category.objects.count()})

class DashboardProductCreateView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/product-form.html', {'categories': Category.objects.all(), 'brands': Brand.objects.all(),})

    def post(self, request):
        try:
            product = Product.objects.create(
                name=request.POST.get('name'),
                slug=request.POST.get('slug') or slugify(request.POST.get('name'), allow_unicode=True),
                sku=request.POST.get('sku', ''),
                description=request.POST.get('description', ''),
                price=request.POST.get('price'),
                original_price=request.POST.get('original_price') or None,
                gender=request.POST.get('gender', 'unisex'),
                category_type=request.POST.get('category_type', ''),
                is_active='is_active' in request.POST,
                category_id=request.POST.get('category') or None,
                brand_id=request.POST.get('brand') or None)

            images = request.FILES.getlist('images')
            main_index = int(request.POST.get('main_image_index', 0))

            for index, image in enumerate(images):
                ProductImage.objects.create(product=product, image=image, is_main=(index == main_index), order=index)
            return redirect('dashboard:products_list')

        except Exception as e:
            return render(request, 'dashboard/product-form.html', {
                'categories': Category.objects.all(),
                'brands': Brand.objects.all(),
                'error': str(e)})

class DashboardCategoriesListView(StaffRequiredMixin, View):
    def get(self, request):
        categories = Category.objects.all()
        return render(request, 'dashboard/categories-list.html', {'categories': categories})

class DashboardOrdersListView(StaffRequiredMixin, View):
    def get(self, request):
        orders = Order.objects.select_related('user', 'address', 'coupon').prefetch_related('items').order_by('-created_at')
        status = request.GET.get('status')
        if status:
            orders = orders.filter(status=status)

        return render(request, 'dashboard/orders-list.html', {
            'orders': orders,
            'status_choices': Order.STATUS_CHOICES,
            'current_status': status,
            'pending_count': Order.objects.filter(status='pending').count(),
            'processing_count': Order.objects.filter(status='processing').count(),
            'shipped_count': Order.objects.filter(status='shipped').count(),
            'delivered_count': Order.objects.filter(status='delivered').count(),})

class DashboardOrderDetailView(StaffRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('user', 'address').prefetch_related('items__variant__product'),pk=pk)
        return render(request, 'dashboard/order-detail.html', {'order': order, 'status_choices': Order.STATUS_CHOICES})

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status')
        tracking_code = request.POST.get('tracking_code', '')

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            if tracking_code:
                order.tracking_code = tracking_code
            order.save()

        return redirect('dashboard:order_detail', pk=pk)

class DashboardReviewsListView(StaffRequiredMixin, View):
    def get(self, request):
        reviews = Review.objects.select_related('user', 'product').order_by('-created_at')
        approved = request.GET.get('approved')

        if approved == 'true':
            reviews = reviews.filter(is_approved=True)
        elif approved == 'false':
            reviews = reviews.filter(is_approved=False)

        return render(request, 'dashboard/reviews-list.html', {
            'reviews': reviews,
            'total_count': Review.objects.count(),
            'pending_reviews_count': Review.objects.filter(is_approved=False).count(),
            'approved_count': Review.objects.filter(is_approved=True).count(),
            'avg_rating': Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0,})

class DashboardReviewApproveView(StaffRequiredMixin, View):
    def get(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.is_approved = not review.is_approved
        review.save()
        return redirect('dashboard:reviews_list')

class DashboardAnalyticsView(StaffRequiredMixin, View):
    def get(self, request):
        now = timezone.now()
        period = request.GET.get('period', 'month')

        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)

        total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_price'))['total'] or 0
        total_orders = Order.objects.filter(created_at__gte=start_date).count()
        new_users = CustomUser.objects.filter(date_joined__gte=start_date).count()
        avg_rating = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        prev_revenue = Order.objects.filter(status='delivered', created_at__gte=start_date - timedelta(days=30), created_at__lt=start_date).aggregate(total=Sum('total_price'))['total'] or 0
        curr_revenue = Order.objects.filter(status='delivered', created_at__gte=start_date).aggregate(total=Sum('total_price'))['total'] or 0
        revenue_growth = 0

        if prev_revenue > 0:
            revenue_growth = round((curr_revenue - prev_revenue) / prev_revenue * 100)

        prev_orders = Order.objects.filter(created_at__gte=start_date - timedelta(days=30), created_at__lt=start_date).count()
        curr_orders_count = Order.objects.filter(created_at__gte=start_date).count()
        orders_growth = 0

        if prev_orders > 0:
            orders_growth = round((curr_orders_count - prev_orders) / prev_orders * 100)

        monthly_data = Order.objects.filter(status='delivered', created_at__gte=now - timedelta(days=365)).annotate(month=TruncMonth('created_at')).values('month').annotate(revenue=Sum('total_price')).order_by('month')
        monthly_labels = []
        monthly_revenue = []

        for item in monthly_data:
            monthly_labels.append(item['month'].strftime('%Y/%m'))
            monthly_revenue.append(float(item['revenue'] or 0))

        weekly_data = Order.objects.filter(created_at__gte=now - timedelta(weeks=8)).annotate(week=TruncWeek('created_at')).values('week').annotate(count=Count('id')).order_by('week')
        weekly_labels = []
        weekly_orders = []

        for item in weekly_data:
            weekly_labels.append(item['week'].strftime('%Y/%m/%d'))
            weekly_orders.append(item['count'])

        status_data_qs = Order.objects.values('status').annotate(count=Count('id'))
        status_map = {
            'pending': 'در انتظار',
            'paid': 'پرداخت شده',
            'processing': 'پردازش',
            'shipped': 'ارسال شده',
            'delivered': 'تحویل شده',
            'cancelled': 'لغو شده',
            'returned': 'مرجوع',
        }
        status_labels = []
        status_counts = []

        for item in status_data_qs:
            status_labels.append(status_map.get(item['status'], item['status']))
            status_counts.append(item['count'])

        from catalog.models import Category

        categories_data = OrderItem.objects.values('variant__product__category__name').annotate(total=Count('id')).order_by('-total')[:5]
        category_labels = []
        category_counts = []

        for item in categories_data:
            name = item['variant__product__category__name'] or 'نامشخص'
            category_labels.append(name)
            category_counts.append(item['total'])

        from catalog.models import Product

        top_products_qs = OrderItem.objects.values('variant__product').annotate(total_sold=Sum('quantity'), total_revenue=Sum('price')).order_by('-total_sold')[:5]
        top_products = []

        for item in top_products_qs:
            try:
                product = Product.objects.get(pk=item['variant__product'])
                product.total_sold = item['total_sold']
                product.total_revenue = item['total_revenue']
                top_products.append(product)
            except Product.DoesNotExist:
                pass

        recent_users = CustomUser.objects.order_by('-date_joined')[:6]

        return render(request, 'dashboard/analytics.html', {
            'period': period,
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'new_users': new_users,
            'avg_rating': avg_rating,
            'revenue_growth': revenue_growth,
            'orders_growth': orders_growth,
            'monthly_labels': json.dumps(monthly_labels, ensure_ascii=False),
            'monthly_revenue': json.dumps(monthly_revenue),
            'weekly_labels': json.dumps(weekly_labels, ensure_ascii=False),
            'weekly_orders': json.dumps(weekly_orders),
            'status_labels': json.dumps(status_labels, ensure_ascii=False),
            'status_data': json.dumps(status_counts),
            'category_labels': json.dumps(category_labels, ensure_ascii=False),
            'category_data': json.dumps(category_counts),
            'top_products': top_products,
            'recent_users': recent_users})

class DashboardProductEditView(StaffRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, 'dashboard/product-form.html', {'product': product, 'categories': Category.objects.all(), 'brands': Brand.objects.all(),})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        try:
            product.name = request.POST.get('name')
            product.sku = request.POST.get('sku', '')
            product.slug = request.POST.get('slug') or slugify(request.POST.get('name'), allow_unicode=True)
            product.description = request.POST.get('description', '')
            product.price = request.POST.get('price')
            product.original_price = request.POST.get('original_price') or None
            product.gender = request.POST.get('gender', 'unisex')
            product.category_type = request.POST.get('category_type', '')
            product.is_active = 'is_active' in request.POST
            product.category_id = request.POST.get('category') or None
            product.brand_id = request.POST.get('brand') or None
            product.save()

            images = request.FILES.getlist('images')
            main_index = int(request.POST.get('main_image_index', 0))

            if images:
                for index, image in enumerate(images):
                    ProductImage.objects.create(product=product, image=image, is_main=(index == main_index), order=product.images.count() + index)
            return redirect('dashboard:products_list')

        except Exception as e:
            return render(request, 'dashboard/product-form.html', {
                'product': product,
                'categories': Category.objects.all(),
                'brands': Brand.objects.all(),
                'error': str(e),
            })