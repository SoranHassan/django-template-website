from django.apps import AppConfig


def create_default_periodic_tasks(sender, **kwargs):
    """Seed the panel-editable periodic tasks (django-celery-beat) after migrate.

    get_or_create only: rows are created once with sensible defaults and the
    admin can freely re-schedule them from the panel - nothing is overwritten,
    and no server restart is needed for schedule changes (DatabaseScheduler
    picks them up automatically).
    """
    try:
        from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask
    except Exception:
        return

    # Nightly at 03:30 Tehran time - purge expired OTP codes
    otp_cron, _ = CrontabSchedule.objects.get_or_create(
        minute='30', hour='3', day_of_week='*', day_of_month='*', month_of_year='*',
        timezone='Asia/Tehran')
    PeriodicTask.objects.get_or_create(
        name='حذف کدهای OTP منقضی‌شده',
        defaults={'task': 'accounts.tasks.cleanup_expired_otps', 'crontab': otp_cron,
                  'description': 'زمان اجرا از همین‌جا قابل تغییر است - نیاز به ری‌استارت ندارد'})

    # Nightly at 04:00 - purge visit stats older than 90 days
    visits_cron, _ = CrontabSchedule.objects.get_or_create(
        minute='0', hour='4', day_of_week='*', day_of_month='*', month_of_year='*',
        timezone='Asia/Tehran')
    PeriodicTask.objects.get_or_create(
        name='پاک‌سازی آمار بازدید قدیمی (۹۰ روز)',
        defaults={'task': 'core.tasks.purge_old_visits', 'crontab': visits_cron,
                  'kwargs': '{"days": 90}',
                  'description': 'زمان اجرا از همین‌جا قابل تغییر است'})

    # Every 15 minutes - cancel orders unpaid for more than 30 minutes
    every15, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)
    PeriodicTask.objects.get_or_create(
        name='لغو خودکار سفارش‌های پرداخت‌نشده',
        defaults={'task': 'orders.tasks.auto_cancel_unpaid_orders', 'interval': every15,
                  'description': 'سفارش‌های پرداخت‌نشدهٔ قدیمی‌تر از ۳۰ دقیقه لغو می‌شوند'})


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'هسته'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(create_default_periodic_tasks, sender=self,
                             dispatch_uid='core-default-periodic-tasks')
