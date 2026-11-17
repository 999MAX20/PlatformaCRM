from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from apps.services.models import Service
from apps.tasks.models import Task


class ClientFilterReadScopeTests(TestCase):
    def test_related_filters_use_read_scope_and_do_not_disclose_hidden_records(self):
        owner = User.objects.create_user(username="filter-scope-owner", email="filter-owner@example.test")
        actor = User.objects.create_user(username="filter-scope-actor", email="filter-actor@example.test", role="business_operator")
        business = Business.objects.create(owner=owner, name="Filters", slug="filter-scope")
        role = BusinessRole.objects.create(business=business, name="Client reader")
        BusinessMember.objects.create(business=business, user=actor, role="operator", business_role=role)
        client_permission = RolePermission.objects.create(business_role=role, resource="clients", action="view", scope="business")
        for resource in ("tasks", "appointments"):
            RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="none", is_allowed=False)
        client = Client.objects.create(business=business, full_name="Visible client")
        Task.objects.create(business=business, client=client, title="Hidden task", due_at=timezone.now() - timedelta(days=1))
        service = Service.objects.create(business=business, name="Consultation", duration_minutes=30)
        start = timezone.now() + timedelta(days=1)
        Appointment.objects.create(business=business, client=client, service=service, start_at=start, end_at=start + timedelta(minutes=30))
        api = APIClient()
        api.force_authenticate(actor)
        for params, count in (({"task": "open"}, 0), ({"task": "overdue"}, 0), ({"task": "no_open"}, 1),
                              ({"appointment": "upcoming"}, 0), ({"appointment": "no_upcoming"}, 1),
                              ({"appointment": "period", "appointment_from": start.date().isoformat()}, 0)):
            response = api.get("/api/clients/", {"workspace": "true", **params})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], count)
        client_permission.is_allowed = False
        client_permission.scope = "none"
        client_permission.save()
        api.force_authenticate(User.objects.get(pk=actor.pk))
        response = api.get("/api/clients/", {"workspace": "true", "contact": "missing_email"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
