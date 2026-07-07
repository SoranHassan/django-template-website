from celery import shared_task
from django.utils import timezone


@shared_task
def auto_cancel_unpaid_orders():
    """لغو خودکار سفارشات پرداخت‌نشده بعد از ۳۰ دقیقه"""
    from .models import Order
    from datetime import timedelta

    threshold = timezone.now() - timedelta(minutes=10)
    cancelled_orders = Order.objects.filter(status='pending',created_at__lt=threshold)
    count = cancelled_orders.count()
    cancelled_orders.update(status='cancelled')

    return f'{count} سفارش پرداخت‌نشده لغو شد'