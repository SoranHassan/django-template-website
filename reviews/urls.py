from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('<slug:slug>/add/', views.ReviewCreateView.as_view(), name='add'),
]