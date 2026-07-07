from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('404/', views.error_404, name='404'),
]