from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@never_cache
@ensure_csrf_cookie
def index(request):
    # This public shell contains no business data. All data/actions use scoped APIs.
    limit = settings.VISION_ENROLLMENT_TOTAL_BYTES
    from .uniform_demo import available
    return render(request,'demo_ui/index.html', {
        'enrollment_limit_bytes': limit,
        'enrollment_limit_mib': limit // (1024 * 1024),
        'uniform_demo_enabled': available(request),
    })
