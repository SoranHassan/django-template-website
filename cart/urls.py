from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.CartView.as_view(), name='cart'),
    path('add/', views.CartAddView.as_view(), name='add'),
    path('remove/', views.CartRemoveView.as_view(), name='remove'),
    path('update/', views.CartUpdateView.as_view(), name='update'),
]