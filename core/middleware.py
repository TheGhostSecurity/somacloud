import time


class PageViewMiddleware:
    """Lightweight page-view logger. Stores request start time and writes a PageViewLog on response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._page_start = time.monotonic()
        response = self.get_response(request)

        if getattr(request, "_skip_pageview_log", False):
            return response

        path = request.path
        if path.startswith("/static/") or path.startswith("/media/") or path.startswith("/favicon"):
            return response

        status = getattr(response, "status_code", 0)
        if status >= 400:
            return response

        duration_ms = int((time.monotonic() - getattr(request, "_page_start", time.monotonic())) * 1000)

        try:
            from .models import PageViewLog

            user = request.user if request.user.is_authenticated else None
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")

            PageViewLog.objects.create(
                user=user,
                path=path[:500],
                view_name=getattr(request, "resolver_match", None) and request.resolver_match.view_name or "",
                method=request.method,
                status_code=status,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                duration_ms=duration_ms,
            )
        except Exception:
            pass

        return response
