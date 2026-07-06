from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from redis import Redis
from redis.exceptions import RedisError


def health_check(request):
    """Verifies Postgres and Redis connectivity, per Documento 04 (used by Azure for restarts)."""
    checks = {"database": False, "redis": False}

    try:
        connections["default"].cursor()
        checks["database"] = True
    except OperationalError:
        pass

    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        checks["redis"] = redis_client.ping()
    except RedisError:
        pass

    healthy = all(checks.values())
    status_code = 200 if healthy else 503
    body = {"status": "ok" if healthy else "unhealthy", "checks": checks}
    return JsonResponse(body, status=status_code)
