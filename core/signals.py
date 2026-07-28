from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import LoginLog


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    LoginLog.objects.create(
        user=user,
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        session_key=request.session.session_key or "",
        method="LOGIN",
        success=True,
    )
