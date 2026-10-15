from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import OperationalError, close_old_connections, connection, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessInvitation, BusinessMember
from apps.core.models import AuditLog


@skipUnless(connection.vendor == "postgresql", "Requires real PostgreSQL row locks.")
class InvitationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="invite-lock-owner", email="invite-lock-owner@example.com")
        self.invitee = User.objects.create_user(username="invite-lock-user", email="invite-lock-user@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Invitation lock", slug="invitation-lock")
        self.invitation = BusinessInvitation.objects.create(
            business=self.business, email=self.invitee.email, invited_by=self.owner,
            role=BusinessMember.Roles.OPERATOR, expires_at=timezone.now() + timezone.timedelta(days=1),
        )
        self.url = "/api/team/invitations/accept/"

    def accept(self):
        client = APIClient()
        client.force_authenticate(self.invitee)
        return client.post(self.url, {"token": str(self.invitation.token)}, format="json")

    def test_nullable_relations_and_concurrent_acceptance_have_one_winner(self):
        barrier = Barrier(2)

        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return self.accept().status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(attempt, (0, 1)))
        self.assertCountEqual(outcomes, [200, 400])
        self.assertEqual(BusinessMember.objects.filter(business=self.business, user=self.invitee).count(), 1)
        self.assertEqual(AuditLog.objects.filter(business=self.business, metadata__source="invitation").count(), 1)
        self.invitation.refresh_from_db()
        self.assertIsNotNone(self.invitation.accepted_at)
        self.assertEqual(self.accept().status_code, 400)

    def test_audit_failure_rolls_back_membership_and_token_consumption(self):
        with patch("apps.businesses.views.write_audit_log", side_effect=OperationalError("audit unavailable")):
            self.assertEqual(self.accept().status_code, 500)
        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.accepted_at)
        self.assertFalse(BusinessMember.objects.filter(business=self.business, user=self.invitee).exists())
        self.assertEqual(self.accept().status_code, 200)
