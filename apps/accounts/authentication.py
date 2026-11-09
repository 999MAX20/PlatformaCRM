from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.session_security import token_matches_auth_epoch
from apps.accounts.device_sessions import validate_access_device


class SessionEpochJWTAuthentication(JWTAuthentication):
    """Reject access JWTs issued before the user's latest security revocation."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and request.method in {"GET", "HEAD"}:
            # JWTAuthentication loads a fresh User for every request. Keep read
            # projections consistent without retaining permissions across requests.
            result[0]._permission_read_memberships = {}
        return result

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not token_matches_auth_epoch(user, validated_token):
            raise AuthenticationFailed(
                "Session expired or invalid.",
                code="token_not_valid",
            )
        try:
            validate_access_device(user, validated_token)
        except TokenError:
            raise AuthenticationFailed("Session expired or invalid.", code="token_not_valid") from None
        return user
