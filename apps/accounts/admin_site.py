from django import forms
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext_lazy as _
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.mfa import has_confirmed_mfa, requires_mfa, verify_user_factor


ADMIN_MFA_SESSION_KEY = "platforma_admin_auth"


class AdminLoginThrottle(SimpleRateThrottle):
    scope = "auth_admin_login"

    def __init__(self, identifier):
        self.identifier = identifier.strip().casefold()
        super().__init__()

    def get_cache_key(self, request, view):
        identity = self.get_ident(request) if view == "ip" else salted_hmac("admin-login", self.identifier).hexdigest()
        return self.cache_format % {"scope": self.scope + "_" + view, "ident": identity}


class MfaAdminAuthenticationForm(AdminAuthenticationForm):
    mfa_code = forms.CharField(
        label=_("Authentication or recovery code"), required=False, max_length=64,
        widget=forms.PasswordInput(attrs={"autocomplete": "one-time-code", "autocapitalize": "off", "spellcheck": "false"}),
        help_text=_("Required when two-factor authentication is enabled. Set it up through the CRM sign-in page first."),
    )

    def clean(self):
        # UsernameField has already applied the normalization used by authentication.
        identifier = self.cleaned_data.get("username", "")
        allowed = [AdminLoginThrottle(identifier).allow_request(self.request, identity) for identity in ("ip", "account")]
        if not all(allowed):
            raise ValidationError(_("Too many sign-in attempts. Please try again in a minute."), code="throttled")
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        device_id = None
        if requires_mfa(user):
            if not has_confirmed_mfa(user):
                raise ValidationError(_("Set up two-factor authentication through the CRM sign-in page before using administration."), code="mfa_enrollment_required")
            if not verify_user_factor(user, self.cleaned_data.get("mfa_code"), allow_recovery=True):
                raise ValidationError(_("Enter a valid authentication or unused recovery code."), code="mfa_code_invalid")
            device_id = user.mfa_device.pk
        self.request._verified_admin_auth = {"user_id": str(user.pk), "auth_epoch": user.auth_epoch, "device_id": device_id}


class MfaAdminSite(AdminSite):
    login_form = MfaAdminAuthenticationForm
    login_template = "accounts/admin_login.html"

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        proof = request.session.get(ADMIN_MFA_SESSION_KEY)
        if proof is not None:
            if not isinstance(proof, dict) or proof.get("user_id") != str(request.user.pk) or proof.get("auth_epoch") != request.user.auth_epoch:
                return False
        if requires_mfa(request.user):
            return bool(proof and has_confirmed_mfa(request.user) and proof.get("device_id") == request.user.mfa_device.pk)
        return True

    def login(self, request, extra_context=None):
        response = super().login(request, extra_context)
        proof = getattr(request, "_verified_admin_auth", None)
        if response.status_code == 302 and proof and request.user.is_authenticated and proof["user_id"] == str(request.user.pk):
            request.session[ADMIN_MFA_SESSION_KEY] = proof
        return response
