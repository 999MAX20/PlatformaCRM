"""CSRF boundary for browser authentication that creates or changes cookies."""
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET


class AuthCookieCsrfMixin:
    # DRF exempts APIView.as_view() from middleware enforcement. Protect the
    # dispatch inside that wrapper, including anonymous login requests.
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


@never_cache
@require_GET
@ensure_csrf_cookie
def auth_csrf(request):
    # Returning the masked token supports explicitly trusted separate frontend
    # origins without exposing the HttpOnly refresh credential to JavaScript.
    return JsonResponse({"csrf_token": get_token(request)})
