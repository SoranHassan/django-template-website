"""Security helpers wired into settings.

axes_client_ip is used as AXES_CLIENT_IP_CALLABLE so django-axes records the
real client IP behind nginx. We read it explicitly instead of relying on
django-ipware's heuristics (which, in this stack, ignored X-Real-IP and always
returned the unix-socket REMOTE_ADDR, bucketing every attacker under one key).
"""


def axes_client_ip(request):
    """Return the true client IP for a request proxied by nginx.

    nginx sets `X-Real-IP` to $remote_addr and OVERWRITES any client-supplied
    value, so it is the trusted, un-spoofable source. Fall back to the first
    X-Forwarded-For entry, then REMOTE_ADDR, for non-proxied/local use.
    """
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        return real_ip.strip()
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
