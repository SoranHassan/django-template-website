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
    path('categories/', views.DashboardCategoriesListView.as_view(), name='categories_list'),
    path('products/<int:pk>/edit/', views.DashboardProductEditView.as_view(), name='product_edit'),

    # Orders
    path('orders/', views.DashboardOrdersListView.as_view(), name='orders_list'),
    path('orders/<int:pk>/', views.DashboardOrderDetailView.as_view(), name='order_detail'),

    # Reviews
    path('reviews/', views.DashboardReviewsListView.as_view(), name='reviews_list'),
    path('reviews/<int:pk>/approve/', views.DashboardReviewApproveView.as_view(), name='review_approve'),

    # Analytics
    path('analytics/', views.DashboardAnalyticsView.as_view(), name='analytics'),
]