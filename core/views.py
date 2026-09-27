import json
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET'])
def health_check(request):
    """Health check endpoint that verifies database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'detail': str(e)},
            status=503
        )
