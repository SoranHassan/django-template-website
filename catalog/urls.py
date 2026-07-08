from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [

    path('', views.HomeView.as_view(), name='index'),
    path('shop/', views.ProductListView.as_view(), name='shop_style_1'),
    path('shop/<int:id>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('search-suggest/', views.SearchSuggestView.as_view(), name='search_suggest'),
]