from celery import shared_task
from django.utils import timezone


@shared_task
def auto_cancel_unpaid_orders():
    """Auto-cancel unpaid orders after 30 minutes."""
    from .models import Order
    from datetime import timedelta

    threshold = timezone.now() - timedelta(minutes=30)
    cancelled_orders = Order.objects.filter(status='pending',created_at__lt=threshold)
    count = cancelled_orders.count()
    cancelled_orders.update(status='cancelled')

    return f'{count} سفارش پرداخت‌نشده لغو شد'