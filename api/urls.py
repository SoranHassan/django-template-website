from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('brands/', views.brand_list, name='brand_list'),
]
