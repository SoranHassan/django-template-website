from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('verify/<int:pk>/', views.VerifyPaymentView.as_view(), name='verify_payment'),
    path('complete/<int:pk>/', views.CompleteOrderView.as_view(), name='complete_order'),
    path('retry/<int:pk>/', views.RetryPaymentView.as_view(), name='retry_payment'),
    path('invoice/<int:pk>/', views.InvoiceDownloadView.as_view(), name='invoice'),
    path('coupon/apply/', views.ApplyCouponView.as_view(), name='apply_coupon'),
    path('coupon/remove/', views.RemoveCouponView.as_view(), name='remove_coupon'),
]