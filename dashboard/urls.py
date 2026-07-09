from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardIndexView.as_view(), name='index'),

    # Users
    path('users/', views.DashboardUsersListView.as_view(), name='users_list'),

    # Products
    path('products/', views.DashboardProductsListView.as_view(), name='products_list'),
    path('products/create/', views.DashboardProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.DashboardProductEditView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.DashboardProductDeleteView.as_view(), name='product_delete'),

    # Variants / Colors / Sizes / SizeChart
    path('products/<int:pk>/variants/save/', views.DashboardVariantSaveView.as_view(), name='variant_save'),
    path('variants/<int:pk>/delete/', views.DashboardVariantDeleteView.as_view(), name='variant_delete'),
    path('colors/create/', views.DashboardColorCreateView.as_view(), name='color_create'),
    path('sizes/create/', views.DashboardSizeCreateView.as_view(), name='size_create'),
    path('products/<int:pk>/size-chart/save/', views.DashboardSizeChartSaveView.as_view(), name='sizechart_save'),
    path('size-chart/<int:pk>/delete/', views.DashboardSizeChartDeleteView.as_view(), name='sizechart_delete'),

    # Categories
    path('categories/', views.DashboardCategoriesListView.as_view(), name='categories_list'),
    path('categories/create/', views.DashboardCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.DashboardCategoryEditView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.DashboardCategoryDeleteView.as_view(), name='category_delete'),

    # Brands
    path('brands/', views.DashboardBrandsListView.as_view(), name='brands_list'),
    path('brands/create/', views.DashboardBrandCreateView.as_view(), name='brand_create'),
    path('brands/<int:pk>/edit/', views.DashboardBrandEditView.as_view(), name='brand_edit'),
    path('brands/<int:pk>/delete/', views.DashboardBrandDeleteView.as_view(), name='brand_delete'),

    # Coupons
    path('coupons/', views.DashboardCouponsListView.as_view(), name='coupons_list'),
    path('coupons/create/', views.DashboardCouponSaveView.as_view(), name='coupon_create'),
    path('coupons/<int:pk>/edit/', views.DashboardCouponSaveView.as_view(), name='coupon_edit'),
    path('coupons/<int:pk>/delete/', views.DashboardCouponDeleteView.as_view(), name='coupon_delete'),

    # Orders
    path('orders/', views.DashboardOrdersListView.as_view(), name='orders_list'),
    path('orders/<int:pk>/', views.DashboardOrderDetailView.as_view(), name='order_detail'),

    # Reviews
    path('reviews/', views.DashboardReviewsListView.as_view(), name='reviews_list'),
    path('reviews/<int:pk>/approve/', views.DashboardReviewApproveView.as_view(), name='review_approve'),

    # Shipping / Announcements / Hero / Blog
    path('shipping/', views.DashboardShippingListView.as_view(), name='shipping_list'),
    path('shipping/create/', views.DashboardShippingSaveView.as_view(), name='shipping_create'),
    path('shipping/<int:pk>/edit/', views.DashboardShippingSaveView.as_view(), name='shipping_edit'),
    path('shipping/<int:pk>/delete/', views.DashboardShippingDeleteView.as_view(), name='shipping_delete'),
    path('announcements/', views.DashboardAnnouncementsListView.as_view(), name='announcements_list'),
    path('announcements/create/', views.DashboardAnnouncementSaveView.as_view(), name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.DashboardAnnouncementSaveView.as_view(), name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.DashboardAnnouncementDeleteView.as_view(), name='announcement_delete'),
    path('hero/', views.DashboardHeroListView.as_view(), name='hero_list'),
    path('hero/create/', views.DashboardHeroSaveView.as_view(), name='hero_create'),
    path('hero/<int:pk>/edit/', views.DashboardHeroSaveView.as_view(), name='hero_edit'),
    path('hero/<int:pk>/delete/', views.DashboardHeroDeleteView.as_view(), name='hero_delete'),
    path('blog-posts/', views.DashboardBlogListView.as_view(), name='blog_list'),
    path('blog-posts/create/', views.DashboardBlogSaveView.as_view(), name='blog_create'),
    path('blog-posts/<int:pk>/edit/', views.DashboardBlogSaveView.as_view(), name='blog_edit'),
    path('blog-posts/<int:pk>/delete/', views.DashboardBlogDeleteView.as_view(), name='blog_delete'),

    # Analytics
    path('analytics/', views.DashboardAnalyticsView.as_view(), name='analytics'),
]