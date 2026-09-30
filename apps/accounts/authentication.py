from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.session_security import token_matches_auth_epoch
from apps.accounts.device_sessions import validate_access_device


class SessionEpochJWTAuthentication(JWTAuthentication):
    """Reject access JWTs issued before the user's latest security revocation."""

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
