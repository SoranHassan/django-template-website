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

    # Analytics
    path('analytics/', views.DashboardAnalyticsView.as_view(), name='analytics'),
]