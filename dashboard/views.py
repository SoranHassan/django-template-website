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
from django.urls import reverse
from core.utils import optimize_image


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only staff users are allowed."""

    def test_func(self):
        return self.request.user.is_staff


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Superuser only - for sensitive operations such as user management and site settings."""

    def test_func(self):
        return self.request.user.is_superuser


class DashboardUserToggleView(StaffRequiredMixin, View):
    """Toggle user flags. Wholesale approval: any staff admin;
    active/staff toggles: superuser only."""

    def post(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        field = request.POST.get('field')
        # Nobody may toggle their own account
        if user == request.user:
            return redirect('dashboard:users_list')
        if field == 'is_wholesale':
            user.is_wholesale = not user.is_wholesale
            user.save(update_fields=['is_wholesale'])
        elif field == 'is_active' and request.user.is_superuser:
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
        elif field == 'is_staff' and request.user.is_superuser:
            user.is_staff = not user.is_staff
            user.save(update_fields=['is_staff'])
        return redirect('dashboard:users_list')

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

        from core.models import SiteVisit
        visits_today = SiteVisit.objects.filter(created_at__date=now.date()).count()
        online_now = SiteVisit.objects.filter(
            created_at__gte=now - timedelta(minutes=5)).values('session_key').distinct().count()

        return render(request, 'dashboard/index.html', {
            'active_nav': 'index',
            'visits_today': visits_today,
            'online_now': online_now,
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

def _mark_seen(request, key):
    """Store the viewed-at time so the section badge resets to zero."""
    request.session[key] = timezone.now().isoformat()


class DashboardUsersListView(StaffRequiredMixin, View):
    def get(self, request):
        _mark_seen(request, 'seen_users_at')
        users = CustomUser.objects.all().order_by('-date_joined')
        staff_count = users.filter(is_staff=True).count()
        wholesale_pending = users.filter(wholesale_requested=True, is_wholesale=False).count()
        return render(request, 'dashboard/users-list.html', {
            'users': users, 'staff_count': staff_count,
            'wholesale_pending': wholesale_pending, 'active_nav': 'users'})

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
            'active_nav': 'products',
            'products': products,
            'categories': Category.objects.all(),
            'total_products': Product.objects.count(),
            'active_products': Product.objects.filter(is_active=True).count(),
            'low_stock': Product.objects.filter(variants__stock__lte=3).distinct().count(),
            'categories_count': Category.objects.count()})

def _unique_product_slug(name, requested_slug='', exclude_pk=None):
    """Slug is always ASCII and unique (like a SKU); Persian never appears in URLs.
    If the name is Persian and nothing ASCII remains, the product-<unique code> pattern is used."""
    base = slugify((requested_slug or '').strip(), allow_unicode=False) \
        or slugify(name or '', allow_unicode=False)
    if not base:
        base = 'product'
    slug = base
    counter = 2
    qs = Product.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def _parse_price(value):
    try:
        price = int(str(value).replace(',', '').strip())
        return price if price >= 0 else None
    except (TypeError, ValueError):
        return None


class DashboardProductCreateView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/product-form.html', {'categories': Category.objects.all(), 'brands': Brand.objects.all(), 'active_nav': 'products'})

    def post(self, request):
        def form_error(message):
            return render(request, 'dashboard/product-form.html', {
                'active_nav': 'products',
                'categories': Category.objects.all(),
                'brands': Brand.objects.all(),
                'error': message})

        name = request.POST.get('name', '').strip()
        if not name:
            return form_error('نام محصول الزامی است')

        price = _parse_price(request.POST.get('price'))
        if price is None:
            return form_error('قیمت باید یک عدد معتبر باشد')

        original_price = _parse_price(request.POST.get('original_price')) if request.POST.get('original_price') else None

        try:
            product = Product.objects.create(
                name=name,
                slug=_unique_product_slug(name, request.POST.get('slug')),
                sku=request.POST.get('sku', '').strip(),
                description=request.POST.get('description', ''),
                price=price,
                original_price=original_price,
                gender=request.POST.get('gender', 'unisex'),
                category_type=request.POST.get('category_type', ''),
                is_active='is_active' in request.POST,
                is_wholesale='is_wholesale' in request.POST,
                category_id=request.POST.get('category') or None,
                brand_id=request.POST.get('brand') or None)

            images = request.FILES.getlist('images')
            try:
                main_index = int(request.POST.get('main_image_index', 0))
            except (TypeError, ValueError):
                main_index = 0

            for index, image in enumerate(images):
                ProductImage.objects.create(product=product, image=optimize_image(image),
                                            is_main=(index == main_index), order=index)
            return redirect('dashboard:product_edit', pk=product.pk)

        except Exception as e:
            return form_error(f'خطا در ذخیره محصول: {e}')

class DashboardCategoriesListView(StaffRequiredMixin, View):
    def get(self, request):
        categories = Category.objects.all()
        return render(request, 'dashboard/categories-list.html',
                      {'categories': categories, 'active_nav': 'categories'})

class DashboardOrdersListView(StaffRequiredMixin, View):
    def get(self, request):
        _mark_seen(request, 'seen_orders_at')
        orders = Order.objects.select_related('user', 'address', 'coupon').prefetch_related('items').order_by('-created_at')
        status = request.GET.get('status')
        if status:
            orders = orders.filter(status=status)

        return render(request, 'dashboard/orders-list.html', {
            'active_nav': 'orders',
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
        return render(request, 'dashboard/order-detail.html', {
            'order': order, 'status_choices': Order.STATUS_CHOICES, 'active_nav': 'orders',
            'confirmed': request.GET.get('confirmed') == '1'})

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status')
        tracking_code = request.POST.get('tracking_code', '')
        confirmed = False

        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            if tracking_code:
                order.tracking_code = tracking_code
            order.save()

            # SMS notification to the customer on status change (e.g. order confirmed)
            if new_status != old_status:
                send_order_status_sms.delay(order.user.mobile, order.pk, new_status)
                # When the order becomes confirmed, prepare the invoice for the admin
                if new_status in ('paid', 'processing', 'shipped', 'delivered'):
                    confirmed = True

        if confirmed:
            return redirect(f"{reverse('dashboard:order_detail', args=[pk])}?confirmed=1")
        return redirect('dashboard:order_detail', pk=pk)

class DashboardReviewsListView(StaffRequiredMixin, View):
    def get(self, request):
        _mark_seen(request, 'seen_reviews_at')
        reviews = Review.objects.select_related('user', 'product').order_by('-created_at')
        approved = request.GET.get('approved')

        if approved == 'true':
            reviews = reviews.filter(is_approved=True)
        elif approved == 'false':
            reviews = reviews.filter(is_approved=False)

        return render(request, 'dashboard/reviews-list.html', {
            'active_nav': 'reviews',
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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or \
                request.headers.get('accept', '').startswith('application/json'):
            from django.http import JsonResponse
            return JsonResponse({'status': 'ok', 'is_approved': review.is_approved})
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

        # ---------- Real site visit statistics ----------
        from core.models import SiteVisit
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        online_since = now - timedelta(minutes=5)

        visits_today = SiteVisit.objects.filter(created_at__date=today).count()
        visits_week = SiteVisit.objects.filter(created_at__gte=week_ago).count()
        visits_month = SiteVisit.objects.filter(created_at__gte=month_ago).count()
        unique_today = SiteVisit.objects.filter(created_at__date=today).values('session_key').distinct().count()
        unique_month = SiteVisit.objects.filter(created_at__gte=month_ago).values('session_key').distinct().count()
        online_now = SiteVisit.objects.filter(created_at__gte=online_since).values('session_key').distinct().count()

        # Daily visits chart for the last 14 days
        from django.db.models.functions import TruncDate
        daily_qs = (SiteVisit.objects.filter(created_at__gte=now - timedelta(days=13))
                    .annotate(day=TruncDate('created_at'))
                    .values('day')
                    .annotate(views=Count('id'), visitors=Count('session_key', distinct=True))
                    .order_by('day'))
        daily_map = {d['day']: d for d in daily_qs}
        visit_labels, visit_views, visit_visitors = [], [], []
        for i in range(13, -1, -1):
            day = today - timedelta(days=i)
            visit_labels.append(day.strftime('%m/%d'))
            row = daily_map.get(day)
            visit_views.append(row['views'] if row else 0)
            visit_visitors.append(row['visitors'] if row else 0)

        # Most visited pages (last month)
        top_pages_qs = (SiteVisit.objects.filter(created_at__gte=month_ago)
                        .values('path').annotate(views=Count('id')).order_by('-views')[:6])
        top_pages = list(top_pages_qs)

        return render(request, 'dashboard/analytics.html', {
            'active_nav': 'analytics',
            'period': period,
            'visits_today': visits_today,
            'visits_week': visits_week,
            'visits_month': visits_month,
            'unique_today': unique_today,
            'unique_month': unique_month,
            'online_now': online_now,
            'visit_labels': json.dumps(visit_labels, ensure_ascii=False),
            'visit_views': json.dumps(visit_views),
            'visit_visitors': json.dumps(visit_visitors),
            'top_pages': top_pages,
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
            'active_nav': 'products',
            'product': product,
            'categories': Category.objects.all(),
            'brands': Brand.objects.all(),
            'variants': product.variants.select_related('size', 'color'),
            'size_charts': product.size_charts.select_related('size'),
            'all_sizes': Size.objects.all().order_by('sort_order', 'name'),
            'all_colors': Color.objects.all(),
            'size_chart_fields': [
                ('shoulder', 'شانه'), ('sleeve', 'آستین'), ('chest', 'سینه'), ('length_top', 'قد بالاتنه'),
                ('waist', 'کمر'), ('hip', 'ران'), ('crotch', 'فاق'), ('length_bottom', 'قد پایین‌تنه'),
            ],
            'saved': request.GET.get('saved'),
        })

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        def form_error(message):
            return render(request, 'dashboard/product-form.html', {
                'active_nav': 'products',
                'product': product,
                'categories': Category.objects.all(),
                'brands': Brand.objects.all(),
                'error': message})

        name = request.POST.get('name', '').strip()
        if not name:
            return form_error('نام محصول الزامی است')

        price = _parse_price(request.POST.get('price'))
        if price is None:
            return form_error('قیمت باید یک عدد معتبر باشد')

        try:
            product.name = name
            product.sku = request.POST.get('sku', '').strip()
            product.slug = _unique_product_slug(name, request.POST.get('slug'), exclude_pk=product.pk)
            product.description = request.POST.get('description', '')
            product.price = price
            product.original_price = _parse_price(request.POST.get('original_price')) if request.POST.get('original_price') else None
            product.gender = request.POST.get('gender', 'unisex')
            product.category_type = request.POST.get('category_type', '')
            product.is_active = 'is_active' in request.POST
            product.is_wholesale = 'is_wholesale' in request.POST
            product.category_id = request.POST.get('category') or None
            product.brand_id = request.POST.get('brand') or None
            product.save()

            images = request.FILES.getlist('images')
            try:
                main_index = int(request.POST.get('main_image_index', 0))
            except (TypeError, ValueError):
                main_index = 0

            if images:
                for index, image in enumerate(images):
                    ProductImage.objects.create(product=product, image=optimize_image(image),
                                                is_main=(index == main_index), order=product.images.count() + index)
            return redirect('dashboard:product_edit', pk=product.pk)

        except Exception as e:
            return form_error(f'خطا در ذخیره محصول: {e}')

# ---------- Full CRUD inside the dashboard (no redirects to Django admin) ----------

def render_form_page(request, *, page_title, fields, action, cancel_url,
                     page_subtitle='', has_richtext=False, error=''):
    """Standard dashboard form page (admin-like) - every edit gets its own page."""
    return render(request, 'dashboard/form-page.html', {
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'fields': fields,
        'action': action,
        'cancel_url': cancel_url,
        'has_richtext': has_richtext,
        'saved': request.GET.get('saved') == '1',
        'error': error,
    })


def _dt_local(value):
    """Format a datetime for input[type=datetime-local]."""
    if not value:
        return ''
    return timezone.localtime(value).strftime('%Y-%m-%dT%H:%M')


class DashboardCategorySaveView(StaffRequiredMixin, View):
    """Create/edit a category on its own page."""

    def get(self, request, pk=None):
        cat = get_object_or_404(Category, pk=pk) if pk else None
        parent_qs = Category.objects.exclude(pk=pk) if pk else Category.objects.all()
        parents = [(c.pk, c.name) for c in parent_qs]
        fields = [
            {'name': 'name', 'label': 'نام دسته‌بندی', 'type': 'text', 'required': True, 'value': cat.name if cat else ''},
            {'name': 'slug', 'label': 'اسلاگ (اختیاری)', 'type': 'text', 'value': cat.slug if cat else '',
             'help': 'خالی بگذارید تا خودکار از روی نام ساخته شود'},
            {'name': 'parent', 'label': 'دسته والد', 'type': 'select', 'allow_blank': True,
             'options': parents, 'value': cat.parent_id if cat and cat.parent_id else ''},
            {'name': 'image', 'label': 'تصویر', 'type': 'image',
             'value': cat.image.url if cat and cat.image else ''},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': cat.is_active if cat else True},
        ]
        return render_form_page(
            request, page_title='ویرایش دسته‌بندی' if pk else 'دسته‌بندی جدید',
            fields=fields,
            action=request.path, cancel_url=reverse('dashboard:categories_list'))

    def post(self, request, pk=None):
        cat = get_object_or_404(Category, pk=pk) if pk else Category()
        name = request.POST.get('name', '').strip()
        if not name:
            return redirect('dashboard:categories_list')
        cat.name = name
        cat.slug = request.POST.get('slug', '').strip() or cat.slug or slugify(name, allow_unicode=True)
        cat.parent_id = request.POST.get('parent') or None
        cat.is_active = 'is_active' in request.POST
        if request.FILES.get('image'):
            cat.image = optimize_image(request.FILES['image'])
        cat.save()
        return redirect(f"{reverse('dashboard:category_edit', args=[cat.pk])}?saved=1")


class DashboardCategoryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Category, pk=pk).delete()
        return redirect('dashboard:categories_list')


class DashboardBrandsListView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/brands-list.html',
                      {'brands': Brand.objects.all(), 'active_nav': 'brands'})


class DashboardBrandSaveView(StaffRequiredMixin, View):
    """Create/edit a brand on its own page."""

    def get(self, request, pk=None):
        brand = get_object_or_404(Brand, pk=pk) if pk else None
        fields = [
            {'name': 'name', 'label': 'نام برند', 'type': 'text', 'required': True, 'value': brand.name if brand else ''},
            {'name': 'slug', 'label': 'اسلاگ (اختیاری)', 'type': 'text', 'value': brand.slug if brand else '',
             'help': 'خالی بگذارید تا خودکار ساخته شود'},
            {'name': 'logo', 'label': 'لوگو', 'type': 'image', 'value': brand.logo.url if brand and brand.logo else ''},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': brand.is_active if brand else True},
        ]
        return render_form_page(
            request, page_title='ویرایش برند' if pk else 'برند جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:brands_list'))

    def post(self, request, pk=None):
        brand = get_object_or_404(Brand, pk=pk) if pk else Brand()
        name = request.POST.get('name', '').strip()
        if not name:
            return redirect('dashboard:brands_list')
        brand.name = name
        brand.slug = request.POST.get('slug', '').strip() or brand.slug or slugify(name, allow_unicode=True)
        brand.is_active = 'is_active' in request.POST
        if request.FILES.get('logo'):
            brand.logo = optimize_image(request.FILES['logo'])
        brand.save()
        return redirect(f"{reverse('dashboard:brand_edit', args=[brand.pk])}?saved=1")


class DashboardBrandDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Brand, pk=pk).delete()
        return redirect('dashboard:brands_list')


class DashboardProductDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        # If orders reference the variants (PROTECT), deactivate instead of deleting
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
            'coupons': Coupon.objects.all().order_by('-created_at'),
            'now': timezone.now(), 'active_nav': 'coupons'})


class DashboardCouponSaveView(StaffRequiredMixin, View):
    """Create (no pk) or edit (with pk) a coupon on its own page."""

    def get(self, request, pk=None):
        from orders.models import Coupon
        c = get_object_or_404(Coupon, pk=pk) if pk else None
        fields = [
            {'name': 'code', 'label': 'کد تخفیف', 'type': 'text', 'required': True, 'value': c.code if c else ''},
            {'name': 'discount_type', 'label': 'نوع تخفیف', 'type': 'select',
             'options': [('percent', 'درصدی'), ('fixed', 'مبلغ ثابت')],
             'value': c.discount_type if c else 'percent'},
            {'name': 'discount_value', 'label': 'مقدار تخفیف', 'type': 'number', 'required': True,
             'value': c.discount_value if c else ''},
            {'name': 'min_order_amount', 'label': 'حداقل مبلغ سفارش', 'type': 'number',
             'value': c.min_order_amount if c else 0},
            {'name': 'max_discount_amount', 'label': 'سقف تخفیف (اختیاری)', 'type': 'number',
             'value': c.max_discount_amount if c and c.max_discount_amount else ''},
            {'name': 'max_uses', 'label': 'حداکثر دفعات استفاده (۰=نامحدود)', 'type': 'number',
             'value': c.max_uses if c else 0},
            {'name': 'max_uses_per_user', 'label': 'حداکثر برای هر کاربر', 'type': 'number',
             'value': c.max_uses_per_user if c else 1},
            {'name': 'valid_from', 'label': 'اعتبار از', 'type': 'datetime-local',
             'value': _dt_local(c.valid_from) if c else ''},
            {'name': 'valid_until', 'label': 'اعتبار تا', 'type': 'datetime-local',
             'value': _dt_local(c.valid_until) if c else ''},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': c.is_active if c else True},
        ]
        return render_form_page(
            request, page_title='ویرایش کد تخفیف' if pk else 'کد تخفیف جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:coupons_list'))

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
        coupon.is_active = 'is_active' in request.POST

        if coupon.code:
            coupon.save()
            return redirect(f"{reverse('dashboard:coupon_edit', args=[coupon.pk])}?saved=1")
        return redirect('dashboard:coupons_list')


class DashboardCouponDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from orders.models import Coupon
        get_object_or_404(Coupon, pk=pk).delete()
        return redirect('dashboard:coupons_list')


# ---------- Variant management (size/color/stock/price) ----------

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
        return redirect(f"{reverse('dashboard:product_edit', args=[pk])}?saved=variant")


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
    """Quick-add a color (name + hex code) from inside the product form."""

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
            # Numeric sizes (e.g. 40, 42) get automatic ordering by numeric value
            sort_order = 0
            try:
                sort_order = int(float(name.replace('٫', '.').replace('،', '')))
            except (TypeError, ValueError):
                sort_order = 0
            Size.objects.get_or_create(name=name, defaults={'sort_order': sort_order})
        next_url = request.POST.get('next', '')
        if next_url.startswith('/dashboard/'):
            return redirect(next_url)
        return redirect('dashboard:products_list')


# ---------- Size chart (centimetres) ----------

class DashboardSizeChartSaveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        size_id = request.POST.get('size')
        if size_id:
            fields = {}
            for f in ['shoulder', 'sleeve', 'chest', 'length_top', 'waist', 'hip',
                      'crotch', 'length_bottom']:
                value = request.POST.get(f, '').strip()
                fields[f] = value or None
            SizeChart.objects.update_or_create(product=product, size_id=size_id, defaults=fields)
        return redirect(f"{reverse('dashboard:product_edit', args=[pk])}?saved=chart")


class DashboardSizeChartDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        chart = get_object_or_404(SizeChart, pk=pk)
        product_pk = chart.product_id
        chart.delete()
        return redirect('dashboard:product_edit', pk=product_pk)


# ---------- Shipping methods / announcements / banners / blog (full management, no Django admin) ----------

class DashboardShippingListView(StaffRequiredMixin, View):
    def get(self, request):
        from orders.models import ShippingMethod
        return render(request, 'dashboard/shipping-list.html',
                      {'methods': ShippingMethod.objects.all(), 'active_nav': 'shipping'})


class DashboardShippingSaveView(StaffRequiredMixin, View):
    def get(self, request, pk=None):
        from orders.models import ShippingMethod
        m = get_object_or_404(ShippingMethod, pk=pk) if pk else None
        fields = [
            {'name': 'name', 'label': 'نام روش ارسال', 'type': 'text', 'required': True, 'value': m.name if m else ''},
            {'name': 'price', 'label': 'هزینه (تومان)', 'type': 'number', 'required': True, 'value': m.price if m else ''},
            {'name': 'description', 'label': 'توضیحات', 'type': 'textarea', 'full': True,
             'value': m.description if m else ''},
            {'name': 'order', 'label': 'ترتیب نمایش', 'type': 'number', 'value': m.order if m else 0},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': m.is_active if m else True},
        ]
        return render_form_page(
            request, page_title='ویرایش روش ارسال' if pk else 'روش ارسال جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:shipping_list'))

    def post(self, request, pk=None):
        from orders.models import ShippingMethod
        method = get_object_or_404(ShippingMethod, pk=pk) if pk else ShippingMethod()
        method.name = request.POST.get('name', method.name or '').strip()
        method.price = _parse_price(request.POST.get('price')) or 0
        method.description = request.POST.get('description', '')
        method.order = request.POST.get('order') or 0
        method.is_active = 'is_active' in request.POST
        if method.name:
            method.save()
            return redirect(f"{reverse('dashboard:shipping_edit', args=[method.pk])}?saved=1")
        return redirect('dashboard:shipping_list')


class DashboardShippingDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from orders.models import ShippingMethod
        get_object_or_404(ShippingMethod, pk=pk).delete()
        return redirect('dashboard:shipping_list')


class DashboardAnnouncementsListView(SuperuserRequiredMixin, View):
    def get(self, request):
        from core.models import Announcement
        return render(request, 'dashboard/announcements-list.html',
                      {'items': Announcement.objects.all(), 'active_nav': 'announcements'})


class DashboardAnnouncementSaveView(SuperuserRequiredMixin, View):
    def get(self, request, pk=None):
        from core.models import Announcement
        a = get_object_or_404(Announcement, pk=pk) if pk else None
        fields = [
            {'name': 'text', 'label': 'متن اطلاعیه', 'type': 'text', 'required': True, 'full': True,
             'value': a.text if a else ''},
            {'name': 'link', 'label': 'لینک (اختیاری)', 'type': 'url', 'value': a.link if a else ''},
            {'name': 'link_text', 'label': 'متن لینک', 'type': 'text', 'value': a.link_text if a else ''},
            {'name': 'order', 'label': 'ترتیب نمایش', 'type': 'number', 'value': a.order if a else 0},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': a.is_active if a else True},
        ]
        return render_form_page(
            request, page_title='ویرایش اطلاعیه' if pk else 'اطلاعیه جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:announcements_list'))

    def post(self, request, pk=None):
        from core.models import Announcement
        item = get_object_or_404(Announcement, pk=pk) if pk else Announcement()
        item.text = request.POST.get('text', item.text or '').strip()
        item.link = request.POST.get('link', '')
        item.link_text = request.POST.get('link_text', '')
        item.order = request.POST.get('order') or 0
        item.is_active = 'is_active' in request.POST
        if item.text:
            item.save()
            return redirect(f"{reverse('dashboard:announcement_edit', args=[item.pk])}?saved=1")
        return redirect('dashboard:announcements_list')


class DashboardAnnouncementDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        from core.models import Announcement
        get_object_or_404(Announcement, pk=pk).delete()
        return redirect('dashboard:announcements_list')


class DashboardHeroListView(SuperuserRequiredMixin, View):
    def get(self, request):
        from core.models import HeroSlide
        return render(request, 'dashboard/hero-list.html',
                      {'slides': HeroSlide.objects.all(), 'active_nav': 'hero'})


class DashboardHeroSaveView(SuperuserRequiredMixin, View):
    def get(self, request, pk=None):
        from core.models import HeroSlide
        s = get_object_or_404(HeroSlide, pk=pk) if pk else None
        fields = [
            {'name': 'title', 'label': 'عنوان', 'type': 'text', 'required': True, 'value': s.title if s else ''},
            {'name': 'subtitle', 'label': 'زیرعنوان', 'type': 'text', 'full': True, 'value': s.subtitle if s else ''},
            {'name': 'image', 'label': 'تصویر بنر', 'type': 'image', 'value': s.image.url if s and s.image else '',
             'aspect': '4',
             'help': 'کادر برش دقیقاً هم‌شکل بنر سایت است (نسبت ۴:۱ مثل ۱۹۲۰×۴۸۰) — همان چیزی که برش می‌دهید نمایش داده می‌شود'},
            {'name': 'button_text', 'label': 'متن دکمه', 'type': 'text', 'value': s.button_text if s else 'خرید کنید'},
            {'name': 'button_link', 'label': 'لینک دکمه', 'type': 'text', 'value': s.button_link if s else '/shop/'},
            {'name': 'order', 'label': 'ترتیب نمایش', 'type': 'number', 'value': s.order if s else 0},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': s.is_active if s else True},
        ]
        return render_form_page(
            request, page_title='ویرایش بنر' if pk else 'بنر جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:hero_list'))

    def post(self, request, pk=None):
        from core.models import HeroSlide
        slide = get_object_or_404(HeroSlide, pk=pk) if pk else HeroSlide()
        slide.title = request.POST.get('title', slide.title or '').strip()
        slide.subtitle = request.POST.get('subtitle', '')
        slide.button_text = request.POST.get('button_text', 'خرید کنید')
        slide.button_link = request.POST.get('button_link', '/shop/')
        slide.order = request.POST.get('order') or 0
        slide.is_active = 'is_active' in request.POST
        if request.FILES.get('image'):
            slide.image = optimize_image(request.FILES['image'])
        if slide.title and (slide.image or pk):
            slide.save()
            return redirect(f"{reverse('dashboard:hero_edit', args=[slide.pk])}?saved=1")
        return redirect('dashboard:hero_list')


class DashboardHeroDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        from core.models import HeroSlide
        get_object_or_404(HeroSlide, pk=pk).delete()
        return redirect('dashboard:hero_list')


class DashboardHomeCardsListView(SuperuserRequiredMixin, View):
    """The 4 category cards under the hero banner on the home page."""

    def get(self, request):
        from core.models import HomeCategoryCard
        return render(request, 'dashboard/home-cards-list.html',
                      {'cards': HomeCategoryCard.objects.all(), 'active_nav': 'home_cards'})


class DashboardHomeCardSaveView(SuperuserRequiredMixin, View):
    def get(self, request, pk=None):
        from core.models import HomeCategoryCard
        c = get_object_or_404(HomeCategoryCard, pk=pk) if pk else None
        fields = [
            {'name': 'title', 'label': 'عنوان', 'type': 'text', 'required': True, 'value': c.title if c else ''},
            {'name': 'subtitle', 'label': 'زیرعنوان', 'type': 'text', 'value': c.subtitle if c else ''},
            {'name': 'link', 'label': 'لینک', 'type': 'text', 'value': c.link if c else '/shop/',
             'help': 'مثال: ‎/shop/?category=tshirt'},
            {'name': 'image', 'label': 'تصویر کارت', 'type': 'image', 'value': c.image.url if c and c.image else '',
             'aspect': '1',
             'help': 'کادر برش مربعی است، دقیقاً هم‌شکل کارت روی سایت — اگر خالی باشد آیکون نمایش داده می‌شود'},
            {'name': 'icon_class', 'label': 'کلاس آیکون (بدون تصویر)', 'type': 'text',
             'value': c.icon_class if c else 'lni lni-tshirt'},
            {'name': 'color', 'label': 'رنگ آیکون', 'type': 'color', 'value': c.color if c else '#00B8CC'},
            {'name': 'order', 'label': 'ترتیب نمایش', 'type': 'number', 'value': c.order if c else 0},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': c.is_active if c else True},
        ]
        return render_form_page(
            request, page_title='ویرایش کارت دسته‌بندی' if pk else 'کارت دسته‌بندی جدید',
            page_subtitle='کارت‌های زیر بنر اصلی صفحه اول (۴ عدد پیشنهاد می‌شود)',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:home_cards_list'))

    def post(self, request, pk=None):
        from core.models import HomeCategoryCard
        card = get_object_or_404(HomeCategoryCard, pk=pk) if pk else HomeCategoryCard()
        card.title = request.POST.get('title', card.title or '').strip()
        card.subtitle = request.POST.get('subtitle', '')
        card.link = request.POST.get('link', '/shop/') or '/shop/'
        card.icon_class = request.POST.get('icon_class', 'lni lni-tshirt')
        card.color = request.POST.get('color', '#00B8CC') or '#00B8CC'
        card.order = request.POST.get('order') or 0
        card.is_active = 'is_active' in request.POST
        if request.FILES.get('image'):
            card.image = optimize_image(request.FILES['image'])
        if card.title:
            card.save()
            return redirect(f"{reverse('dashboard:home_card_edit', args=[card.pk])}?saved=1")
        return redirect('dashboard:home_cards_list')


class DashboardHomeCardDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        from core.models import HomeCategoryCard
        get_object_or_404(HomeCategoryCard, pk=pk).delete()
        return redirect('dashboard:home_cards_list')


class DashboardBlogListView(StaffRequiredMixin, View):
    def get(self, request):
        from blog.models import Post
        return render(request, 'dashboard/blog-list.html',
                      {'posts': Post.objects.all(), 'active_nav': 'blog'})


class DashboardBlogSaveView(StaffRequiredMixin, View):
    def get(self, request, pk=None):
        from blog.models import Post
        p = get_object_or_404(Post, pk=pk) if pk else None
        fields = [
            {'name': 'title', 'label': 'عنوان نوشته', 'type': 'text', 'required': True, 'full': True,
             'value': p.title if p else ''},
            {'name': 'slug', 'label': 'اسلاگ (نام انگلیسی در URL)', 'type': 'text', 'value': p.slug if p else '',
             'help': 'فقط انگلیسی/عدد/خط تیره؛ خالی بگذارید تا خودکار ساخته شود. اگر فارسی وارد شود با شناسه پر می‌شود.'},
            {'name': 'image', 'label': 'تصویر شاخص', 'type': 'image', 'value': p.image.url if p and p.image else ''},
            {'name': 'excerpt', 'label': 'خلاصه', 'type': 'textarea', 'full': True, 'value': p.excerpt if p else ''},
            {'name': 'body', 'label': 'متن نوشته', 'type': 'richtext', 'required': True, 'full': True,
             'value': p.body if p else ''},
            {'name': 'is_published', 'label': 'منتشر شود', 'type': 'checkbox',
             'value': p.is_published if p else True},
        ]
        return render_form_page(
            request, page_title='ویرایش نوشته' if pk else 'نوشته جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:blog_list'),
            has_richtext=True)

    def post(self, request, pk=None):
        from blog.models import Post
        post = get_object_or_404(Post, pk=pk) if pk else Post(author=request.user)
        post.title = request.POST.get('title', post.title or '').strip()
        post.excerpt = request.POST.get('excerpt', '')
        post.body = request.POST.get('body', '')
        post.is_published = 'is_published' in request.POST
        if request.FILES.get('image'):
            post.image = optimize_image(request.FILES['image'])
        if not (post.title and post.body):
            return redirect('dashboard:blog_list')

        # Slug is always ASCII so Persian URLs never cause problems;
        # if the input is Persian and nothing ASCII remains, the pk is used.
        requested = request.POST.get('slug', '').strip()
        base = slugify(requested, allow_unicode=False) or slugify(post.title, allow_unicode=False)
        if base and (not pk or requested):
            slug, i = base, 2
            qs = Post.objects.exclude(pk=post.pk) if pk else Post.objects.all()
            while qs.filter(slug=slug).exists():
                slug, i = f'{base}-{i}', i + 1
            post.slug = slug
        elif not post.slug:
            post.slug = 'post'  # temporary until we have a pk

        post.save()
        if not base and (post.slug == 'post' or not post.slug):
            post.slug = f'post-{post.pk}'
            post.save(update_fields=['slug'])
        return redirect(f"{reverse('dashboard:blog_edit', args=[post.pk])}?saved=1")


class DashboardBlogDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from blog.models import Post
        get_object_or_404(Post, pk=pk).delete()
        return redirect('dashboard:blog_list')


class DashboardPageListView(StaffRequiredMixin, View):
    def get(self, request):
        from core.models import StaticPage
        return render(request, 'dashboard/pages-list.html',
                      {'pages': StaticPage.objects.all(), 'active_nav': 'pages'})


class DashboardPageSaveView(StaffRequiredMixin, View):
    def get(self, request, pk=None):
        from core.models import StaticPage
        p = get_object_or_404(StaticPage, pk=pk) if pk else None
        fields = [
            {'name': 'title', 'label': 'عنوان صفحه', 'type': 'text', 'required': True, 'full': True,
             'value': p.title if p else ''},
            {'name': 'slug', 'label': 'اسلاگ (نام انگلیسی در URL)', 'type': 'text', 'value': p.slug if p else '',
             'help': 'فقط انگلیسی/عدد/خط تیره؛ خالی بگذارید تا خودکار ساخته شود'},
            {'name': 'body', 'label': 'متن صفحه', 'type': 'richtext', 'required': True, 'full': True,
             'value': p.body if p else ''},
            {'name': 'show_in_footer', 'label': 'نمایش لینک در فوتر', 'type': 'checkbox',
             'value': p.show_in_footer if p else True},
            {'name': 'order', 'label': 'ترتیب', 'type': 'number', 'value': p.order if p else 0},
            {'name': 'is_active', 'label': 'فعال', 'type': 'checkbox', 'value': p.is_active if p else True},
        ]
        return render_form_page(
            request, page_title='ویرایش صفحه' if pk else 'صفحه جدید',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:pages_list'),
            has_richtext=True)

    def post(self, request, pk=None):
        from core.models import StaticPage
        page = get_object_or_404(StaticPage, pk=pk) if pk else StaticPage()
        page.title = request.POST.get('title', page.title or '').strip()
        page.body = request.POST.get('body', '')
        page.show_in_footer = 'show_in_footer' in request.POST
        page.is_active = 'is_active' in request.POST
        try:
            page.order = int(request.POST.get('order') or 0)
        except (TypeError, ValueError):
            page.order = 0
        if not (page.title and page.body):
            return redirect('dashboard:pages_list')
        requested = request.POST.get('slug', '').strip()
        base = slugify(requested, allow_unicode=False) or slugify(page.title, allow_unicode=False) or 'page'
        if not pk or requested:
            slug, i = base, 2
            qs = StaticPage.objects.exclude(pk=page.pk) if pk else StaticPage.objects.all()
            while qs.filter(slug=slug).exists():
                slug, i = f'{base}-{i}', i + 1
            page.slug = slug
        page.save()
        return redirect(f"{reverse('dashboard:pages_edit', args=[page.pk])}?saved=1")


class DashboardPageDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from core.models import StaticPage
        get_object_or_404(StaticPage, pk=pk).delete()
        return redirect('dashboard:pages_list')


class DashboardContactMessagesView(StaffRequiredMixin, View):
    def get(self, request):
        from core.models import ContactMessage
        msgs = ContactMessage.objects.all()
        # mark all as read when the admin opens the list
        ContactMessage.objects.filter(is_read=False).update(is_read=True)
        return render(request, 'dashboard/contact-messages.html',
                      {'messages': msgs, 'active_nav': 'contact_messages'})


class DashboardContactMessageDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from core.models import ContactMessage
        get_object_or_404(ContactMessage, pk=pk).delete()
        return redirect('dashboard:contact_messages')


class DashboardNewsletterView(SuperuserRequiredMixin, View):
    """Compose and send the newsletter to all subscribers in one click."""

    def get(self, request):
        from core.models import NewsletterSubscriber, NewsletterCampaign
        return render(request, 'dashboard/newsletter.html', {
            'active_nav': 'newsletter',
            'subscribers': NewsletterSubscriber.objects.filter(is_active=True),
            'subscribers_count': NewsletterSubscriber.objects.filter(is_active=True).count(),
            'campaigns': NewsletterCampaign.objects.all()[:10],
            'sent': request.GET.get('sent'),
            'sent_count': request.GET.get('count'),
        })

    def post(self, request):
        from django.conf import settings as dj_settings
        from django.core.mail import get_connection, EmailMultiAlternatives
        from core.models import NewsletterSubscriber, NewsletterCampaign

        subject = (request.POST.get('subject') or '').strip()
        body = (request.POST.get('body') or '').strip()
        if not (subject and body):
            return redirect('dashboard:newsletter')

        active = NewsletterSubscriber.objects.filter(is_active=True)
        emails = list(active.exclude(email__isnull=True).exclude(email='').values_list('email', flat=True))
        mobiles = list(active.exclude(mobile__isnull=True).exclude(mobile='').values_list('mobile', flat=True))
        from_email = getattr(dj_settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@oramshop.com'
        sent = 0

        # Email - plain text + branded HTML alternative
        if emails:
            try:
                from django.template.loader import render_to_string
                html = render_to_string('emails/newsletter.html', {
                    'subject': subject, 'body': body,
                    'site_url': request.build_absolute_uri('/'),
                })
                connection = get_connection(fail_silently=True)
                messages = []
                for e in emails:
                    msg = EmailMultiAlternatives(subject, body, from_email, [e], connection=connection)
                    msg.attach_alternative(html, 'text/html')
                    messages.append(msg)
                connection.send_messages(messages)
                sent += len(emails)
            except Exception:
                pass

        # SMS (to mobile numbers)
        if mobiles:
            try:
                from accounts.tasks import send_newsletter_sms
                send_newsletter_sms.delay(mobiles, f'{subject}\n{body}')
                sent += len(mobiles)
            except Exception:
                pass

        NewsletterCampaign.objects.create(subject=subject, body=body, recipients_count=sent)
        return redirect(f"{reverse('dashboard:newsletter')}?sent=1&count={sent}")


class DashboardSeoView(SuperuserRequiredMixin, View):
    """Real SEO report - computed from the actual state of the site content."""

    def get(self, request):
        from blog.models import Post

        total = Product.objects.count() or 1
        active = Product.objects.filter(is_active=True).count()
        with_desc = Product.objects.exclude(description='').exclude(description__isnull=True).count()
        with_sku = Product.objects.exclude(sku='').exclude(sku__isnull=True).count()
        with_image = Product.objects.filter(images__isnull=False).distinct().count()
        with_price = Product.objects.filter(original_price__isnull=False).count()
        published_posts = Post.objects.filter(is_published=True).count()

        def pct(n):
            return round(n / total * 100)

        # Each item: (title, score 0-100, weight, suggestion)
        checks = [
            {'title': 'فایل robots.txt', 'score': 100, 'weight': 1,
             'detail': 'فعال است (/robots.txt)', 'ok': True},
            {'title': 'نقشه سایت (sitemap.xml)', 'score': 100, 'weight': 1,
             'detail': 'فعال است (/sitemap.xml)', 'ok': True},
            {'title': 'داده ساختاریافته محصول (Schema.org)', 'score': 100, 'weight': 1,
             'detail': 'JSON-LD روی صفحه محصول فعال است', 'ok': True},
            {'title': 'توضیحات محصولات', 'score': pct(with_desc), 'weight': 2,
             'detail': f'{with_desc} از {total} محصول توضیحات دارند',
             'ok': pct(with_desc) >= 80},
            {'title': 'کد محصول (SKU)', 'score': pct(with_sku), 'weight': 1,
             'detail': f'{with_sku} از {total} محصول SKU دارند',
             'ok': pct(with_sku) >= 70},
            {'title': 'تصویر محصولات (alt خودکار)', 'score': pct(with_image), 'weight': 2,
             'detail': f'{with_image} از {total} محصول حداقل یک تصویر دارند',
             'ok': pct(with_image) >= 90},
            {'title': 'محصولات فعال (ایندکس‌شدنی)', 'score': pct(active), 'weight': 1,
             'detail': f'{active} از {total} محصول فعال‌اند',
             'ok': pct(active) >= 80},
            {'title': 'قیمت قبل از تخفیف (رونق ریچ‌اسنیپت)', 'score': pct(with_price), 'weight': 1,
             'detail': f'{with_price} از {total} محصول قیمت مقایسه‌ای دارند',
             'ok': pct(with_price) >= 40},
            {'title': 'محتوای بلاگ (تازگی محتوا)', 'score': min(100, published_posts * 20), 'weight': 2,
             'detail': f'{published_posts} نوشتهٔ منتشرشده (هدف: ۵+)',
             'ok': published_posts >= 5},
        ]

        total_weight = sum(c['weight'] for c in checks)
        overall = round(sum(c['score'] * c['weight'] for c in checks) / total_weight)

        if overall >= 85:
            grade, grade_color = 'عالی', '#22c55e'
        elif overall >= 70:
            grade, grade_color = 'خوب', '#00B8CC'
        elif overall >= 50:
            grade, grade_color = 'متوسط', '#f59e0b'
        else:
            grade, grade_color = 'ضعیف', '#ef4444'

        return render(request, 'dashboard/seo.html', {
            'active_nav': 'seo',
            'checks': checks,
            'overall': overall,
            'grade': grade,
            'grade_color': grade_color,
        })


class DashboardSiteSettingsView(SuperuserRequiredMixin, View):
    """Site appearance settings (topbar, banners, footer, vectors, about text)."""

    def get(self, request):
        from core.models import SiteSetting
        s = SiteSetting.get()
        fields = [
            # Feature flags: modules toggle off with a checkbox instead of code removal
            {'name': 'feature_blog', 'label': 'بلاگ فعال باشد', 'type': 'checkbox', 'value': s.feature_blog},
            {'name': 'feature_wholesale', 'label': 'بخش عمده‌فروشی فعال باشد', 'type': 'checkbox', 'value': s.feature_wholesale},
            {'name': 'feature_wishlist', 'label': 'علاقه‌مندی‌ها فعال باشد', 'type': 'checkbox', 'value': s.feature_wishlist},
            {'name': 'feature_reviews', 'label': 'نظرات محصول فعال باشد', 'type': 'checkbox', 'value': s.feature_reviews},
            {'name': 'feature_newsletter', 'label': 'خبرنامه فعال باشد', 'type': 'checkbox', 'value': s.feature_newsletter},
            {'name': 'topbar_style', 'label': 'رنگ نوار اطلاعیه بالای سایت', 'type': 'select',
             'options': SiteSetting.TOPBAR_CHOICES, 'value': s.topbar_style},
            # Site-wide non-dismissible alert
            {'name': 'global_alert', 'label': 'پیام سراسری سایت (غیرقابل بستن)', 'type': 'textarea',
             'full': True, 'value': s.global_alert,
             'help': 'در بالای همهٔ صفحات نمایش داده می‌شود و کاربر نمی‌تواند آن را ببندد — خالی بگذارید تا مخفی شود'},
            {'name': 'global_alert_style', 'label': 'رنگ پیام سراسری', 'type': 'select',
             'options': SiteSetting.ALERT_STYLE_CHOICES, 'value': s.global_alert_style},
            # Shop page banner
            {'name': 'shop_banner', 'label': 'بنر صفحه محصولات', 'type': 'image',
             'value': s.shop_banner.url if s.shop_banner else '', 'full': True},
            # Home collection vectors
            {'name': 'men_vector', 'label': 'وکتور کالکشن مردانه', 'type': 'image',
             'value': s.men_vector.url if s.men_vector else '',
             'help': 'اگر خالی بماند وکتور پیش‌فرض استفاده می‌شود — PNG/SVG با پس‌زمینه شفاف'},
            {'name': 'women_vector', 'label': 'وکتور کالکشن زنانه', 'type': 'image',
             'value': s.women_vector.url if s.women_vector else '',
             'help': 'اگر خالی بماند وکتور پیش‌فرض استفاده می‌شود — PNG/SVG با پس‌زمینه شفاف'},
            {'name': 'men_collection_color', 'label': 'رنگ کالکشن مردانه (صفحه اصلی)', 'type': 'color',
             'value': s.men_collection_color},
            {'name': 'women_collection_color', 'label': 'رنگ کالکشن زنانه (صفحه اصلی)', 'type': 'color',
             'value': s.women_collection_color},
            # About-us band before the footer
            {'name': 'about_home', 'label': 'متن دربارهٔ ما (قبل از فوتر صفحه اصلی)', 'type': 'textarea',
             'full': True, 'value': s.about_home},
            # Runtime config (DB overrides .env - applies instantly, no restart)
            {'name': 'zarinpal_merchant_id', 'label': 'مرچنت‌کد زرین‌پال', 'type': 'text',
             'value': s.zarinpal_merchant_id, 'help': 'خالی = استفاده از مقدار .env — تغییر اینجا بدون ری‌استارت اعمال می‌شود'},
            {'name': 'goftino_id_override', 'label': 'کد ویجت گفتینو', 'type': 'text',
             'value': s.goftino_id_override, 'help': 'خالی = استفاده از مقدار .env'},
            {'name': 'bot_api_key_override', 'label': 'کلید API ربات تلگرام', 'type': 'text',
             'value': s.bot_api_key_override, 'help': 'خالی = استفاده از مقدار .env'},
            {'name': 'shop_banner_title', 'label': 'عنوان بنر محصولات', 'type': 'text', 'value': s.shop_banner_title},
            {'name': 'shop_banner_subtitle', 'label': 'زیرعنوان بنر محصولات', 'type': 'text', 'value': s.shop_banner_subtitle},
            # Footer info
            {'name': 'footer_about', 'label': 'متن دربارهٔ فوتر', 'type': 'textarea', 'full': True, 'value': s.footer_about},
            {'name': 'footer_phone', 'label': 'تلفن پشتیبانی', 'type': 'text', 'value': s.footer_phone},
            {'name': 'footer_email', 'label': 'ایمیل', 'type': 'text', 'value': s.footer_email},
            {'name': 'footer_hours', 'label': 'ساعات کاری', 'type': 'text', 'value': s.footer_hours},
            {'name': 'footer_address', 'label': 'آدرس', 'type': 'text', 'full': True, 'value': s.footer_address},
            {'name': 'instagram_url', 'label': 'لینک اینستاگرام', 'type': 'text', 'value': s.instagram_url},
            {'name': 'telegram_url', 'label': 'لینک تلگرام', 'type': 'text', 'value': s.telegram_url},
            {'name': 'whatsapp_url', 'label': 'لینک واتساپ', 'type': 'text', 'value': s.whatsapp_url},
            # Site credit
            {'name': 'credit_text', 'label': 'متن سازندهٔ سایت (پایین صفحه)', 'type': 'text', 'value': s.credit_text},
            {'name': 'credit_url', 'label': 'لینک سازنده', 'type': 'text', 'value': s.credit_url},
            # Footer trust badges
            {'name': 'enamad_code', 'label': 'کد کامل نماد اعتماد (ای‌نماد)', 'type': 'textarea', 'full': True,
             'value': s.enamad_code,
             'help': 'کل کد <a><img></a> که پنل ای‌نماد می‌دهد را اینجا پیست کنید (بهترین روش). لوگو فقط روی دامنهٔ اصلی سایت نمایش داده می‌شود.'},
            {'name': 'enamad_image', 'label': 'تصویر نماد اعتماد (اگر کد کامل ندارید)', 'type': 'image',
             'value': s.enamad_image.url if s.enamad_image else '',
             'help': 'اگر کد کامل بالا را پیست کردید، این را خالی بگذارید'},
            {'name': 'enamad_link', 'label': 'لینک نماد اعتماد', 'type': 'text', 'value': s.enamad_link,
             'help': 'لینک صفحه تأیید (trustseal.enamad.ir/...)'},
            {'name': 'zarinpal_badge_image', 'label': 'تصویر نماد زرین‌پال', 'type': 'image',
             'value': s.zarinpal_badge_image.url if s.zarinpal_badge_image else '',
             'help': 'لوگوی اعتماد زرین‌پال از پنل زرین‌پال'},
            {'name': 'zarinpal_badge_link', 'label': 'لینک نماد زرین‌پال', 'type': 'text', 'value': s.zarinpal_badge_link,
             'help': 'لینک صفحه تأیید درگاه شما در zarinpal.com'},
            # Search rank
            {'name': 'search_rank', 'label': 'رتبهٔ فعلی در گوگل (از سرچ‌کنسول)', 'type': 'number',
             'value': s.search_rank, 'help': 'اگر ۱ تا ۱۰ باشد، در داشبورد آلرت تبریک نمایش داده می‌شود'},
            {'name': 'search_keyword', 'label': 'کلمهٔ کلیدی رتبه', 'type': 'text', 'value': s.search_keyword},
        ]
        return render_form_page(
            request, page_title='تنظیمات سایت',
            page_subtitle='ظاهر صفحه اصلی، بنر محصولات، فوتر و سازنده',
            fields=fields, action=request.path, cancel_url=reverse('dashboard:index'))

    def post(self, request):
        from core.models import SiteSetting
        s = SiteSetting.get()
        # Feature flags (unchecked checkboxes are absent from POST)
        for flag in ('feature_blog', 'feature_wholesale', 'feature_wishlist',
                     'feature_reviews', 'feature_newsletter'):
            setattr(s, flag, request.POST.get(flag) == 'on')
        topbar = request.POST.get('topbar_style', 'black')
        if topbar in dict(SiteSetting.TOPBAR_CHOICES):
            s.topbar_style = topbar
        s.global_alert = request.POST.get('global_alert', '').strip()
        alert_style = request.POST.get('global_alert_style', 'info')
        if alert_style in dict(SiteSetting.ALERT_STYLE_CHOICES):
            s.global_alert_style = alert_style
        # Shop banner + collection vectors
        if request.FILES.get('shop_banner'):
            s.shop_banner = optimize_image(request.FILES['shop_banner'])
        if request.FILES.get('men_vector'):
            s.men_vector = optimize_image(request.FILES['men_vector'])
        if request.FILES.get('women_vector'):
            s.women_vector = optimize_image(request.FILES['women_vector'])
        s.shop_banner_title = request.POST.get('shop_banner_title', '').strip()
        s.shop_banner_subtitle = request.POST.get('shop_banner_subtitle', '').strip()
        s.men_collection_color = request.POST.get('men_collection_color', '').strip()
        s.women_collection_color = request.POST.get('women_collection_color', '').strip()
        s.zarinpal_merchant_id = request.POST.get('zarinpal_merchant_id', '').strip()
        s.goftino_id_override = request.POST.get('goftino_id_override', '').strip()
        s.bot_api_key_override = request.POST.get('bot_api_key_override', '').strip()
        # About + footer
        s.about_home = request.POST.get('about_home', '').strip()
        s.footer_about = request.POST.get('footer_about', '').strip()
        s.footer_phone = request.POST.get('footer_phone', '').strip()
        s.footer_email = request.POST.get('footer_email', '').strip()
        s.footer_hours = request.POST.get('footer_hours', '').strip()
        s.footer_address = request.POST.get('footer_address', '').strip()
        s.instagram_url = request.POST.get('instagram_url', '').strip()
        s.telegram_url = request.POST.get('telegram_url', '').strip()
        s.whatsapp_url = request.POST.get('whatsapp_url', '').strip()
        s.credit_text = request.POST.get('credit_text', '').strip()
        s.credit_url = request.POST.get('credit_url', '').strip()
        # Trust badges
        if request.FILES.get('enamad_image'):
            s.enamad_image = optimize_image(request.FILES['enamad_image'])
        if request.FILES.get('zarinpal_badge_image'):
            s.zarinpal_badge_image = optimize_image(request.FILES['zarinpal_badge_image'])
        s.enamad_code = request.POST.get('enamad_code', '').strip()
        s.enamad_link = request.POST.get('enamad_link', '').strip()
        s.zarinpal_badge_link = request.POST.get('zarinpal_badge_link', '').strip()
        try:
            s.search_rank = int(request.POST.get('search_rank') or 0)
        except (TypeError, ValueError):
            s.search_rank = 0
        s.search_keyword = request.POST.get('search_keyword', '').strip()
        s.save()
        return redirect(f"{reverse('dashboard:site_settings')}?saved=1")
