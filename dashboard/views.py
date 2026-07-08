from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from datetime import timedelta
import json
from accounts.models import CustomUser
from accounts.tasks import send_order_status_sms
from orders.models import Order, OrderItem
from reviews.models import Review
from catalog.models import Product, Category, Brand, ProductImage, ProductVariant, Size, Color, SizeChart
from django.utils.text import slugify


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Just Staff Users Has Permission"""

    def test_func(self):
        return self.request.user.is_staff

class DashboardIndexView(StaffRequiredMixin, View):
    def get(self, request):
        now = timezone.now()
        users_count = CustomUser.objects.filter(is_active=True).count()
        pending_orders_count = Order.objects.filter(status='pending').count()
        products_count = Product.objects.filter(is_active=True).count()
        total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_price'))['total'] or 0
        revenue_today = Order.objects.filter(status='delivered', created_at__date=now.date()).aggregate(total=Sum('total_price'))['total'] or 0
        revenue_week = Order.objects.filter(status='delivered', created_at__gte=now - timedelta(days=7)).aggregate(total=Sum('total_price'))['total'] or 0
        revenue_month = Order.objects.filter(status='delivered', created_at__gte=now - timedelta(days=30)).aggregate(total=Sum('total_price'))['total'] or 0
        recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
        pending_reviews = Review.objects.filter(is_approved=False).select_related('user', 'product')[:5]
        pending_reviews_count = Review.objects.filter(is_approved=False).count()

        return render(request, 'dashboard/index.html', {
            'users_count': users_count,
            'orders_count': pending_orders_count,
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
            old_status = order.status
            order.status = new_status
            if tracking_code:
                order.tracking_code = tracking_code
            order.save()

            # اطلاع‌رسانی پیامکی تغییر وضعیت به مشتری (مثلاً تأیید سفارش)
            if new_status != old_status:
                send_order_status_sms.delay(order.user.mobile, order.pk, new_status)

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
    def post(self, request, pk):
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
        return render(request, 'dashboard/product-form.html', {
            'product': product,
            'categories': Category.objects.all(),
            'brands': Brand.objects.all(),
            'variants': product.variants.select_related('size', 'color'),
            'size_charts': product.size_charts.select_related('size'),
            'all_sizes': Size.objects.all(),
            'all_colors': Color.objects.all(),
            'size_chart_fields': [
                ('shoulder', 'شانه'), ('sleeve', 'آستین'), ('chest', 'سینه'), ('length_top', 'قد بالاتنه'),
                ('waist', 'کمر'), ('hip', 'ران'), ('crotch', 'فاق'), ('length_bottom', 'قد پایین‌تنه'),
            ],
        })

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

# ---------- CRUD کامل داخل داشبورد (بدون ریدایرکت به ادمین جنگو) ----------

class DashboardCategoryCreateView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        if name:
            Category.objects.create(
                name=name,
                slug=request.POST.get('slug') or slugify(name, allow_unicode=True),
                parent_id=request.POST.get('parent') or None,
                image=request.FILES.get('image'),
                is_active='is_active' not in request.POST or request.POST.get('is_active') == 'on')
        return redirect('dashboard:categories_list')


class DashboardCategoryEditView(StaffRequiredMixin, View):
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.name = request.POST.get('name', category.name)
        category.slug = request.POST.get('slug') or category.slug
        category.parent_id = request.POST.get('parent') or None
        category.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('image'):
            category.image = request.FILES['image']
        category.save()
        return redirect('dashboard:categories_list')


class DashboardCategoryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Category, pk=pk).delete()
        return redirect('dashboard:categories_list')


class DashboardBrandsListView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/brands-list.html', {'brands': Brand.objects.all()})


class DashboardBrandCreateView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        if name:
            Brand.objects.create(
                name=name,
                slug=request.POST.get('slug') or slugify(name, allow_unicode=True),
                logo=request.FILES.get('logo'),
                is_active=True)
        return redirect('dashboard:brands_list')


class DashboardBrandEditView(StaffRequiredMixin, View):
    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)
        brand.name = request.POST.get('name', brand.name)
        brand.slug = request.POST.get('slug') or brand.slug
        brand.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('logo'):
            brand.logo = request.FILES['logo']
        brand.save()
        return redirect('dashboard:brands_list')


class DashboardBrandDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Brand, pk=pk).delete()
        return redirect('dashboard:brands_list')


class DashboardProductDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        # اگر سفارشی به واریانت‌ها وصل باشد (PROTECT)، به جای حذف غیرفعال می‌کنیم
        try:
            product.delete()
        except Exception:
            product.is_active = False
            product.save()
        return redirect('dashboard:products_list')


def _parse_dt(value):
    from django.utils.dateparse import parse_datetime
    dt = parse_datetime(value or '')
    if dt and timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


class DashboardCouponsListView(StaffRequiredMixin, View):
    def get(self, request):
        from orders.models import Coupon
        return render(request, 'dashboard/coupons-list.html', {
            'coupons': Coupon.objects.all().order_by('-created_at'), 'now': timezone.now()})


class DashboardCouponSaveView(StaffRequiredMixin, View):
    """ایجاد (بدون pk) یا ویرایش (با pk) کد تخفیف"""

    def post(self, request, pk=None):
        from orders.models import Coupon
        coupon = get_object_or_404(Coupon, pk=pk) if pk else Coupon()

        coupon.code = request.POST.get('code', coupon.code or '').strip()
        coupon.discount_type = request.POST.get('discount_type', 'percent')
        coupon.discount_value = request.POST.get('discount_value') or 0
        coupon.min_order_amount = request.POST.get('min_order_amount') or 0
        coupon.max_discount_amount = request.POST.get('max_discount_amount') or None
        coupon.max_uses = request.POST.get('max_uses') or 0
        coupon.max_uses_per_user = request.POST.get('max_uses_per_user') or 1
        coupon.valid_from = _parse_dt(request.POST.get('valid_from')) or coupon.valid_from or timezone.now()
        coupon.valid_until = _parse_dt(request.POST.get('valid_until')) or coupon.valid_until or timezone.now()
        coupon.is_active = request.POST.get('is_active') == 'on'

        if coupon.code:
            coupon.save()
        return redirect('dashboard:coupons_list')


class DashboardCouponDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from orders.models import Coupon
        get_object_or_404(Coupon, pk=pk).delete()
        return redirect('dashboard:coupons_list')


# ---------- مدیریت واریانت (سایز/رنگ/موجودی/قیمت) ----------

class DashboardVariantSaveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        size_id = request.POST.get('size') or None
        color_id = request.POST.get('color') or None
        ProductVariant.objects.update_or_create(
            product=product, size_id=size_id, color_id=color_id,
            defaults={
                'stock': request.POST.get('stock') or 0,
                'price': request.POST.get('price') or None,
            })
        return redirect('dashboard:product_edit', pk=pk)


class DashboardVariantDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        product_pk = variant.product_id
        try:
            variant.delete()
        except Exception:
            variant.stock = 0
            variant.save()
        return redirect('dashboard:product_edit', pk=product_pk)


class DashboardColorCreateView(StaffRequiredMixin, View):
    """افزودن سریع رنگ (نام + کد هگز) از داخل فرم محصول"""

    def post(self, request):
        name = request.POST.get('name', '').strip()
        hex_code = request.POST.get('hex_code', '').strip() or '#000000'
        if name:
            Color.objects.get_or_create(name=name, defaults={'hex_code': hex_code})
        next_url = request.POST.get('next', '')
        if next_url.startswith('/dashboard/'):
            return redirect(next_url)
        return redirect('dashboard:products_list')


class DashboardSizeCreateView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        if name:
            Size.objects.get_or_create(name=name)
        next_url = request.POST.get('next', '')
        if next_url.startswith('/dashboard/'):
            return redirect(next_url)
        return redirect('dashboard:products_list')


# ---------- جدول سایزبندی (سانتی‌متر) ----------

class DashboardSizeChartSaveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        size_id = request.POST.get('size')
        if size_id:
            fields = {}
            for f in ['shoulder', 'sleeve', 'chest', 'length_top', 'waist', 'hip', 'crotch', 'length_bottom']:
                value = request.POST.get(f, '').strip()
                fields[f] = value or None
            SizeChart.objects.update_or_create(product=product, size_id=size_id, defaults=fields)
        return redirect('dashboard:product_edit', pk=pk)


class DashboardSizeChartDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        chart = get_object_or_404(SizeChart, pk=pk)
        product_pk = chart.product_id
        chart.delete()
        return redirect('dashboard:product_edit', pk=product_pk)
