import time
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings

class RateLimitMiddleware:
    """
    Middleware to prevent request spamming using Redis cache.
    Limits requests per IP address over a short period.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = getattr(settings, 'RATELIMIT_MAX_REQUESTS', 30)  # Max requests
        self.time_window = getattr(settings, 'RATELIMIT_TIME_WINDOW', 60)  # Seconds

    def __call__(self, request):
        if not getattr(settings, 'RATELIMIT_ENABLED', True):
            return self.get_response(request)

        # Skip rate limiting for static/media
        if request.path.startswith(('/static/', '/media/', '/favicon.ico')):
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)
        cache_key = f"ratelimit:{ip}"
        
        # Increment request count in cache
        try:
            requests_count = cache.get(cache_key, 0)
            if requests_count >= self.rate_limit:
                # Security logging for potential spam
                import logging
                logger = logging.getLogger('django.security')
                logger.warning(f"Rate limit exceeded for IP: {ip} on {request.path}")
                
                return HttpResponse(
                    "Too many requests. Please wait a moment before trying again.", 
                    status=429
                )
            
            # Use redis incr if available for atomicity, otherwise fallback
            if hasattr(cache, 'incr'):
                cache.add(cache_key, 0, self.time_window)
                cache.incr(cache_key)
            else:
                cache.set(cache_key, requests_count + 1, self.time_window)
                
        except Exception:
            # If cache is down, we don't want to block the whole site
            pass

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
