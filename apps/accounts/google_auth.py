"""Browser-bound Google identity exchange; raw credentials are never persisted."""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.auth_views import record_login, record_security_event, set_refresh_cookie
from apps.accounts.csrf import AuthCookieCsrfMixin
from apps.accounts.device_sessions import active_device_session
from apps.accounts.legal_documents import record_signup_acknowledgements
from apps.accounts.mfa import has_confirmed_mfa, issue_session, requires_mfa, start_auth_challenge, verify_user_factor
from apps.accounts.models import GoogleAuthFlow, SocialIdentity, User
from apps.accounts.serializers import CurrentUserSerializer, OwnerSignupSerializer
from apps.accounts.social_auth import _decode_id_token
from apps.accounts.session_security import token_matches_auth_epoch
from apps.accounts.google_auth_signup import create_owner_account
from apps.core.domain_errors import DomainAPIException
from apps.core.models import LoginHistory


COOKIE = "platforma_google_flow"
COOKIE_PATH = "/api/auth/google/"
TTL = 600


class GoogleFlowInvalid(DomainAPIException):
    status_code = 400
    error_code = "google_flow_invalid"
    default_detail = "Google sign-in is unavailable or expired. Start again."


class GoogleLinkConflict(DomainAPIException):
    status_code = 409
    error_code = "google_link_conflict"
    category = "conflict"
    default_detail = "This Google identity cannot be linked to this account."


class GoogleProofRequired(DomainAPIException):
    status_code = 403
    error_code = "google_link_proof_required"
    category = "permission"
    default_detail = "Sign in again and confirm your password and verification code."


class GoogleSignupSerializer(OwnerSignupSerializer):
    email = None
    password = None

    def validate(self, attrs):
        # Email comes exclusively from the verified flow; no password is created.
        return attrs


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _flow(request, *, lock=False, verified=False):
    cookie = request.COOKIES.get(COOKIE, "")
    if not isinstance(cookie, str) or len(cookie) != 43:
        raise GoogleFlowInvalid()
    query = GoogleAuthFlow.objects.select_for_update() if lock else GoogleAuthFlow.objects
    flow = query.filter(browser_hash=_hash(cookie), expires_at__gt=timezone.now(), consumed_at=None, failed_attempts__lt=5).first()
    if flow is None or (verified and flow.verified_at is None):
        raise GoogleFlowInvalid()
    return flow


def _consume(flow):
    flow.consumed_at = timezone.now()
    flow.subject = flow.email = flow.full_name = ""
    flow.save(update_fields=["consumed_at", "subject", "email", "full_name"])


def prune_google_flows(*, limit=1000):
    ids = list(GoogleAuthFlow.objects.filter(expires_at__lte=timezone.now())
               .order_by("expires_at", "pk").values_list("pk", flat=True)[:max(0, min(limit, 1000))])
    return GoogleAuthFlow.objects.filter(pk__in=ids, expires_at__lte=timezone.now()).delete()[0]


def _finish(response):
    response.delete_cookie(COOKIE, path=COOKIE_PATH, samesite="Lax")
    return response


def _pending(flow):
    code = "google_link_required" if User.objects.filter(email__iexact=flow.email).exists() else "google_signup_required"
    return {"code": code, "email": flow.email, "full_name": flow.full_name,
            "expires_in": max(0, int((flow.expires_at - timezone.now()).total_seconds()))}


def _session(request, user, *, business=None):
    if not user.is_active:
        raise GoogleFlowInvalid()
    extra = {"created": business is not None, "provider": "google"}
    if business is not None:
        extra.update(user=CurrentUserSerializer(user).data,
                     business={"id": business.id, "name": business.name, "slug": business.slug})
    if requires_mfa(user):
        return _finish(Response({**start_auth_challenge(user), **extra}, status=202))
    refresh = issue_session(user, mfa_verified=False, request=request)
    record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
    return _finish(set_refresh_cookie(Response({"access": str(refresh.access_token), **extra}, status=201 if business else 200), str(refresh)))


class GoogleView(AuthCookieCsrfMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_social"

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class GoogleStartView(GoogleView):
    @transaction.atomic
    def post(self, request):
        if not any(settings.GOOGLE_OAUTH_CLIENT_IDS):
            raise GoogleFlowInvalid()
        prune_google_flows(limit=100)
        previous = request.COOKIES.get(COOKIE, "")
        if previous:
            GoogleAuthFlow.objects.filter(browser_hash=_hash(previous), consumed_at=None).update(
                consumed_at=timezone.now(), subject="", email="", full_name="")
        browser, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        GoogleAuthFlow.objects.create(browser_hash=_hash(browser), nonce_hash=_hash(nonce), expires_at=timezone.now() + timedelta(seconds=TTL))
        response = Response({"nonce": nonce, "expires_in": TTL})
        response.set_cookie(COOKIE, browser, max_age=TTL, httponly=True,
                            secure=settings.AUTH_REFRESH_COOKIE_SECURE, samesite="Lax", path=COOKIE_PATH)
        return response


class GoogleVerifyView(GoogleView):
    def post(self, request):
        flow = _flow(request)
        if flow.verified_at:
            raise GoogleFlowInvalid()
        token = request.data.get("id_token")
        try:
            if not isinstance(token, str) or not 1 <= len(token) <= 16384:
                raise ValueError()
            claims = _decode_id_token("google", token)
            nonce = claims.get("nonce")
            if not isinstance(nonce, str) or not secrets.compare_digest(_hash(nonce), flow.nonce_hash):
                raise ValueError()
            if claims.get("email_verified") is not True:
                raise ValueError()
            subject, name = claims.get("sub"), claims.get("name", "")
            if not isinstance(subject, str) or not 1 <= len(subject) <= 255 or not isinstance(name, str):
                raise ValueError()
            email = serializers.EmailField(max_length=254).run_validation(claims.get("email")).lower()
        except Exception:
            GoogleAuthFlow.objects.filter(pk=flow.pk, consumed_at=None).update(failed_attempts=F("failed_attempts") + 1)
            raise GoogleFlowInvalid() from None
        with transaction.atomic():
            flow = _flow(request, lock=True)
            if flow.verified_at:
                raise GoogleFlowInvalid()
            identity = SocialIdentity.objects.filter(provider="google", subject=subject).first()
            if identity:
                user = User.objects.select_for_update().get(pk=identity.user_id)
                _consume(flow)
                return _session(request, user)
            flow.subject, flow.email, flow.full_name = subject, email, name[:255]
            flow.verified_at = timezone.now()
            flow.save(update_fields=["subject", "email", "full_name", "verified_at"])
            return Response(_pending(flow))


class GoogleFlowView(GoogleView):
    def get(self, request):
        return Response(_pending(_flow(request, verified=True)))


class GoogleSignupView(GoogleView):
    throttle_scope = "auth_signup"

    def post(self, request):
        serializer = GoogleSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                flow = _flow(request, lock=True, verified=True)
                if User.objects.filter(email__iexact=flow.email).exists() or SocialIdentity.objects.filter(provider="google", subject=flow.subject).exists():
                    raise GoogleLinkConflict()
                data = {**serializer.validated_data, "email": flow.email}
                data.setdefault("full_name", flow.full_name)
                user, business = create_owner_account(data)
                SocialIdentity.objects.create(user=user, provider="google", subject=flow.subject, email=flow.email, email_verified=True)
                record_signup_acknowledgements(request, user, data["accepted_documents"], acceptance_method=data["acceptance_method"])
                _consume(flow)
                return _session(request, user, business=business)
        except IntegrityError:
            raise GoogleLinkConflict() from None


class GoogleLinkView(GoogleView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth_login"

    def post(self, request):
        # A failed password/factor must persist its bounded attempt counter.
        flow = _flow(request, verified=True)
        auth_time = request.auth.get("auth_time", 0) if request.auth else 0
        password = request.data.get("password")
        valid = (0 <= timezone.now().timestamp() - auth_time <= TTL
                 and isinstance(password, str) and request.user.check_password(password))
        try:
            with transaction.atomic():
                flow = _flow(request, lock=True, verified=True)
                user = User.objects.select_for_update().get(pk=request.user.pk)
                if not user.is_active or user.email.lower() != flow.email:
                    raise GoogleLinkConflict()
                valid = valid and token_matches_auth_epoch(user, request.auth) and user.check_password(password)
                if valid:
                    try:
                        active_device_session(user, request.auth, lock=True)
                    except TokenError:
                        valid = False
                valid = valid and (not requires_mfa(user) or bool(request.auth.get("mfa_verified")))
                if valid and has_confirmed_mfa(user):
                    valid = verify_user_factor(user, request.data.get("mfa_code"), allow_recovery=True)
                if not valid:
                    flow.failed_attempts += 1
                    flow.save(update_fields=["failed_attempts"])
                    return Response({"code": "google_link_proof_required", "detail": GoogleProofRequired.default_detail}, status=403)
                if SocialIdentity.objects.filter(provider="google", subject=flow.subject).exists() or SocialIdentity.objects.filter(provider="google", user=user).exists():
                    raise GoogleLinkConflict()
                SocialIdentity.objects.create(user=user, provider="google", subject=flow.subject, email=flow.email, email_verified=True)
                record_security_event(request, user=user, event="google_identity_linked")
                _consume(flow)
                return _finish(Response({"ok": True}))
        except IntegrityError:
            raise GoogleLinkConflict() from None
