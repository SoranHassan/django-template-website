"""Core maintenance tasks (run by Celery Beat)."""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task
def purge_old_visits(days=90):
    """Delete SiteVisit rows older than `days` so the table never grows unbounded."""
    from .models import SiteVisit
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = SiteVisit.objects.filter(created_at__lt=cutoff).delete()
    return deleted
