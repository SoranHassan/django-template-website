import jdatetime
from django import template
from django.utils import timezone

register = template.Library()


def _to_jdate(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return jdatetime.datetime.fromgregorian(datetime=value)


@register.filter
def jalali(value):
    """Jalali (Persian) date, e.g. 1404/04/18."""
    jd = _to_jdate(value)
    return jd.strftime('%Y/%m/%d') if jd else ''


@register.filter
def jalali_dt(value):
    """Jalali (Persian) date and time."""
    jd = _to_jdate(value)
    return jd.strftime('%Y/%m/%d %H:%M') if jd else ''
