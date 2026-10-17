from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent, Note
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.conversations.models import Conversation, Message
from apps.leads.models import Lead


class HistoryWriteBoundaryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="history-owner", email="history-owner@example.test", role="business_owner")
        self.other = User.objects.create_user(username="history-other", email="history-other@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="One", slug="history-one")
        self.foreign = Business.objects.create(owner=self.other, name="Two", slug="history-two")
        for business, user in ((self.business, self.owner), (self.foreign, self.other)):
            BusinessMember.objects.create(business=business, user=user, role="owner")
        self.contact = Client.objects.create(business=self.business, full_name="Own")
        self.foreign_contact = Client.objects.create(business=self.foreign, full_name="Foreign")
        self.lead = Lead.objects.create(business=self.business, client=self.contact)
        self.foreign_lead = Lead.objects.create(business=self.foreign, client=self.foreign_contact)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def endpoints(self):
        return (("notes", Note, "author"), ("activity-events", ActivityEvent, "actor"))

    def payload(self, **extra):
        return {"business": self.business.pk, "client": self.contact.pk,
                "text": "Manual history", "event_type": "manual", **extra}

    def test_create_and_update_bind_and_preserve_session_attribution(self):
        for endpoint, model, attribution in self.endpoints():
            with self.subTest(endpoint=endpoint):
                response = self.api.post(f"/api/{endpoint}/", self.payload(**{attribution: self.other.pk}), format="json")
                self.assertEqual(response.status_code, 201, response.data)
                record = model.objects.get(pk=response.data["id"])
                self.assertEqual(getattr(record, f"{attribution}_id"), self.owner.pk)
                response = self.api.patch(f"/api/{endpoint}/{record.pk}/", {attribution: None, "text": "Edited"}, format="json")
                self.assertEqual(response.status_code, 200, response.data)
                record.refresh_from_db()
                self.assertEqual(record.text, "Edited")
                self.assertEqual(getattr(record, f"{attribution}_id"), self.owner.pk)

    def test_foreign_client_rejected_on_create_and_partial_update(self):
        for endpoint, model, _ in self.endpoints():
            with self.subTest(endpoint=endpoint):
                response = self.api.post(f"/api/{endpoint}/", self.payload(client=self.foreign_contact.pk), format="json")
                self.assertEqual(response.status_code, 400, response.data)
                response = self.api.post(f"/api/{endpoint}/", self.payload(), format="json")
                self.assertEqual(response.status_code, 201, response.data)
                record = model.objects.get(pk=response.data["id"])
                response = self.api.patch(f"/api/{endpoint}/{record.pk}/", {"client": self.foreign_contact.pk}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                record.refresh_from_db()
                self.assertEqual(record.client_id, self.contact.pk)

    def test_polymorphic_foreign_missing_and_malformed_links_rejected(self):
        for endpoint, _, _ in self.endpoints():
            for entity_type, entity_id in (("Lead", self.foreign_lead.pk), ("lead", self.foreign_lead.pk),
                                           ("LEAD", 999999), ("Lead", "bad"), ("Lead", ""),
                                           ("", self.lead.pk), ("unknown", self.lead.pk)):
                with self.subTest(endpoint=endpoint, entity_type=entity_type, entity_id=entity_id):
                    response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type=entity_type, entity_id=str(entity_id)), format="json")
                    self.assertEqual(response.status_code, 400, response.data)

    def test_legitimate_polymorphic_link_patch_and_explicit_null_client(self):
        for endpoint, model, _ in self.endpoints():
            response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type="Lead", entity_id=str(self.lead.pk)), format="json")
            self.assertEqual(response.status_code, 201, response.data)
            pk = response.data["id"]
            response = self.api.patch(f"/api/{endpoint}/{pk}/", {"entity_id": str(self.foreign_lead.pk)}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            response = self.api.patch(f"/api/{endpoint}/{pk}/", {"client": None}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIsNone(model.objects.get(pk=pk).client_id)

    def test_foreign_business_and_unauthenticated_writes_denied(self):
        for endpoint, _, _ in self.endpoints():
            response = self.api.post(f"/api/{endpoint}/", self.payload(business=self.foreign.pk, client=None), format="json")
            self.assertEqual(response.status_code, 403, response.data)
        self.api.force_authenticate(None)
        for endpoint, _, _ in self.endpoints():
            self.assertIn(self.api.post(f"/api/{endpoint}/", self.payload(), format="json").status_code, (401, 403))

    def test_parent_scope_is_checked_even_with_broad_history_write_permissions(self):
        staff = User.objects.create_user(username="history-staff", email="history-staff@example.test")
        role = BusinessRole.objects.create(business=self.business, name="History writer")
        BusinessMember.objects.create(business=self.business, user=staff, role="operator", business_role=role)
        for resource in ("clients", "analytics", "leads"):
            for action in ("view", "create", "update"):
                RolePermission.objects.create(business_role=role, resource=resource, action=action,
                    scope="own" if resource == "leads" else "business")
        self.lead.responsible_user = self.owner
        self.lead.save()
        allowed = Lead.objects.create(business=self.business, client=self.contact, responsible_user=staff)
        self.api.force_authenticate(staff)
        for endpoint, model, _ in self.endpoints():
            with self.subTest(endpoint=endpoint):
                response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type="Lead", entity_id=str(self.lead.pk)), format="json")
                self.assertEqual(response.status_code, 403, response.data)
                response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type="Lead", entity_id=str(allowed.pk)), format="json")
                self.assertEqual(response.status_code, 201, response.data)
                pk = response.data["id"]
                model.objects.filter(pk=pk).update(entity_id=str(self.lead.pk))
                response = self.api.patch(f"/api/{endpoint}/{pk}/", {"entity_id": str(allowed.pk)}, format="json")
                self.assertEqual(response.status_code, 403, response.data)

    def test_existing_author_is_not_replaced_by_editor(self):
        for endpoint, model, attribution in self.endpoints():
            values = {"business": self.business, "client": self.contact, "text": "Original", attribution: self.other}
            if model is ActivityEvent:
                values["event_type"] = "manual"
            record = model.objects.create(**values)
            response = self.api.patch(f"/api/{endpoint}/{record.pk}/", {attribution: self.owner.pk, "text": "Edited"}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            record.refresh_from_db()
            self.assertEqual(getattr(record, f"{attribution}_id"), self.other.pk)

    def test_message_links_derive_business_through_conversation(self):
        conversation = Conversation.objects.create(business=self.business, client=self.contact, channel="manual")
        foreign_conversation = Conversation.objects.create(business=self.foreign, client=self.foreign_contact, channel="manual")
        message = Message.objects.create(conversation=conversation, sender_type="client", text="Allowed")
        foreign_message = Message.objects.create(conversation=foreign_conversation, sender_type="client", text="Foreign")
        for endpoint, model, _ in self.endpoints():
            response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type="message", entity_id=str(foreign_message.pk)), format="json")
            self.assertEqual(response.status_code, 400, response.data)
            response = self.api.post(f"/api/{endpoint}/", self.payload(entity_type="message", entity_id=f"00{message.pk}"), format="json")
            self.assertEqual(response.status_code, 201, response.data)
            record = model.objects.get(pk=response.data["id"])
            self.assertEqual((record.entity_type, record.entity_id), ("Message", str(message.pk)))

    def test_foreign_and_missing_client_errors_are_indistinguishable(self):
        for endpoint, _, _ in self.endpoints():
            errors = []
            for client_id in (self.foreign_contact.pk, 999999):
                response = self.api.post(f"/api/{endpoint}/", self.payload(client=client_id), format="json")
                self.assertEqual(response.status_code, 400, response.data)
                errors.append(response.data["errors"])
            self.assertEqual(errors[0], errors[1])
