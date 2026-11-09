from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.authentication import SessionEpochJWTAuthentication
from apps.accounts.device_sessions import attach_device_session
from apps.accounts.models import AccountSession, User
from apps.businesses.access import Actions, Resources, can, ensure_default_roles, role_permission_allows
from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.clients.models import Client
from apps.tasks.models import Task


@override_settings(AUTH_DEVICE_SESSIONS_ENABLED=True)
class PermissionReadTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="read-owner", email="read-owner@example.test")
        self.user = User.objects.create_user(username="read-user", email="read-user@example.test", role="business_manager")
        self.other = User.objects.create_user(username="read-other", email="read-other@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Read A", slug="read-a")
        self.foreign = Business.objects.create(owner=self.other, name="Read B", slug="read-b")
        ensure_default_roles(self.business)
        self.role = self.business.roles.get(preset_key="admin")
        self.member = BusinessMember.objects.create(business=self.business, user=self.user, role="admin", business_role=self.role)
        self.client_record = Client.objects.create(business=self.business, full_name="Visible")
        self.foreign_client = Client.objects.create(business=self.foreign, full_name="Hidden")
        refresh = RefreshToken.for_user(self.user)
        refresh["auth_epoch"] = self.user.auth_epoch
        attach_device_session(self.user, refresh)
        self.token = str(refresh.access_token)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION="Bearer " + self.token)

    def actor(self, method="get"):
        request = getattr(APIRequestFactory(), method)("/api/tasks/", HTTP_AUTHORIZATION="Bearer " + self.token)
        return SessionEpochJWTAuthentication().authenticate(request)[0]

    def test_read_permissions_fetch_membership_and_rules_once(self):
        actor = self.actor()
        with self.assertNumQueries(2):
            for _ in range(5):
                self.assertTrue(can(actor, self.business, Resources.TASKS, Actions.VIEW).allowed)
                self.assertTrue(can(actor, self.business, Resources.CLIENTS, Actions.UPDATE).allowed)

    def test_uncached_rule_does_not_fetch_deferred_foreign_key(self):
        with self.assertNumQueries(1):
            self.assertEqual(role_permission_allows(self.role, Resources.CLIENTS, Actions.VIEW), "business")

    def test_write_checks_do_not_reuse_read_membership(self):
        actor = self.actor("post")
        self.assertFalse(hasattr(actor, "_permission_read_memberships"))
        self.assertTrue(can(actor, self.business, Resources.CLIENTS, Actions.UPDATE).allowed)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertFalse(can(actor, self.business, Resources.CLIENTS, Actions.UPDATE).allowed)

    def test_new_request_observes_membership_revocation(self):
        path = f"/api/clients/{self.client_record.pk}/"
        self.assertEqual(self.api.get(path).status_code, 200)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertIn(self.api.get(path).status_code, (403, 404))

    def test_new_request_observes_rule_revocation(self):
        path = f"/api/clients/{self.client_record.pk}/"
        self.assertEqual(self.api.get(path).status_code, 200)
        self.role.permissions.filter(resource=Resources.CLIENTS, action=Actions.VIEW).update(is_allowed=False)
        self.assertIn(self.api.get(path).status_code, (403, 404))

    def test_auth_epoch_and_device_revocation_stay_authoritative(self):
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 200)
        AccountSession.objects.filter(user=self.user).update(revoked_at=timezone.now())
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        AccountSession.objects.filter(user=self.user).update(revoked_at=None)
        User.objects.filter(pk=self.user.pk).update(auth_epoch=self.user.auth_epoch + 1)
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)

    def test_tenant_and_object_scopes_are_not_cached_as_global_access(self):
        self.role.permissions.filter(resource=Resources.TASKS, action=Actions.VIEW).update(scope="own")
        own = Task.objects.create(business=self.business, title="Mine", assignee=self.user, created_by=self.owner)
        other = Task.objects.create(business=self.business, title="Other", assignee=self.owner, created_by=self.owner)
        actor = self.actor()
        self.assertTrue(can(actor, self.business, Resources.TASKS, Actions.VIEW, obj=own).allowed)
        self.assertFalse(can(actor, self.business, Resources.TASKS, Actions.VIEW, obj=other).allowed)
        self.assertFalse(can(actor, self.foreign, Resources.CLIENTS, Actions.VIEW).allowed)
        self.assertIn(self.api.get(f"/api/clients/{self.foreign_client.pk}/").status_code, (403, 404))

    def test_manage_fallback_and_explicit_deny_are_preserved(self):
        self.role.permissions.filter(resource=Resources.CLIENTS, action=Actions.VIEW).delete()
        RolePermission.objects.create(business_role=self.role, resource=Resources.CLIENTS, action=Actions.MANAGE, scope="team")
        self.assertEqual(can(self.actor(), self.business, Resources.CLIENTS, Actions.VIEW).scope, "team")
        RolePermission.objects.create(business_role=self.role, resource=Resources.CLIENTS, action=Actions.VIEW, is_allowed=False)
        self.assertFalse(can(self.actor(), self.business, Resources.CLIENTS, Actions.VIEW).allowed)

    def test_profile_permission_queries_are_bounded(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.api.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        role_queries = [q for q in queries if 'FROM "businesses_rolepermission"' in q["sql"]]
        self.assertLessEqual(len(role_queries), 1)
        self.assertIn(str(self.business.pk), response.data["effective_permissions"])
