import json
import logging
import time
import uuid
from django.conf import settings
from django.utils.decorators import sync_and_async_middleware

logger = logging.getLogger('core')


@sync_and_async_middleware
class RequestTrackingMiddleware:
    """Middleware for request tracking, logging, and APM instrumentation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        request.request_id = request_id

        start_time = time.time()

        response = self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000

        self._log_request(request, response, duration_ms, request_id)
        self._update_apm_context(request, request_id)

        response['X-Request-ID'] = request_id
        if duration_ms > 0:
            response['Server-Timing'] = f'total;dur={duration_ms:.0f}'

        return response

    def _log_request(self, request, response, duration_ms, request_id):
        """Log request details in JSON format."""
        user_id = request.user.id if request.user.is_authenticated else None

        log_data = {
            'request_id': request_id,
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'user_id': user_id,
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

        slow_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1000)

        if response.status_code >= 500:
            logger.error(
                json.dumps({**log_data, 'event': 'request_error'}),
                extra={'request_id': request_id}
            )
        elif duration_ms > slow_threshold:
            logger.warning(
                json.dumps({**log_data, 'event': 'slow_request'}),
                extra={'request_id': request_id}
            )
        else:
            logger.info(
                json.dumps({**log_data, 'event': 'request_ok'}),
                extra={'request_id': request_id}
            )

    def _update_apm_context(self, request, request_id):
        """Add request context to APM transaction."""
        try:
            from elasticapm import get_client
            client = get_client()
            if client:
                client.set_label('request_id', request_id)
                if request.user.is_authenticated:
                    client.set_user_context({
                        'id': str(request.user.id),
                        'username': request.user.username,
                    })
        except Exception:
            pass

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
