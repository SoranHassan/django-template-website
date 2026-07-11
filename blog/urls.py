from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='list'),
    path('<str:slug>/', views.PostDetailView.as_view(), name='detail'),  # str: پشتیبانی از اسلاگ فارسی
]
