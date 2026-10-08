from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.bots.models import Bot, BotConversation
from apps.businesses.access import Actions, Resources, ensure_default_roles
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.conversations.inbox_context import build_inbox_context, inbox_list_link_visibility
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.tasks.models import Task


class InboxContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="context-owner", email="context-owner@example.test", role=User.Roles.BUSINESS_OWNER)
        cls.operator = User.objects.create_user(username="context-operator", email="context-operator@example.test", role=User.Roles.STAFF)
        cls.other_owner = User.objects.create_user(username="context-other", email="context-other@example.test", role=User.Roles.BUSINESS_OWNER)
        cls.business = Business.objects.create(owner=cls.owner, name="Context", slug="inbox-context", timezone="Asia/Almaty")
        cls.other = Business.objects.create(owner=cls.other_owner, name="Other", slug="context-other")
        for business in (cls.business, cls.other):
            ensure_default_roles(business)
        for user, business, role in ((cls.owner, cls.business, "owner"), (cls.operator, cls.business, "operator"),
                                     (cls.other_owner, cls.other, "owner")):
            BusinessMember.objects.create(business=business, user=user, role=role,
                business_role=BusinessRole.objects.get(business=business, preset_key=role))
        cls.customer = Client.objects.create(business=cls.business, full_name="Context Customer", phone="+77001112233",
                                           email="context@example.test", notes="Private client note")
        cls.lead = Lead.objects.create(business=cls.business, client=cls.customer, message="Book a consultation", responsible_user=cls.owner)
        cls.pipeline = Pipeline.objects.create(business=cls.business, name="Sales", slug="context-sales")
        cls.stage = PipelineStage.objects.create(business=cls.business, pipeline=cls.pipeline, name="New")
        cls.deal = Deal.objects.create(business=cls.business, client=cls.customer, lead=cls.lead, pipeline=cls.pipeline,
                                      stage=cls.stage, title="Consultation", amount=Decimal("15000.00"), owner=cls.owner)
        cls.service = Service.objects.create(business=cls.business, name="Consultation", duration_minutes=30)
        cls.resource = Resource.objects.create(business=cls.business, name="Specialist", linked_user=cls.owner)
        cls.bot = Bot.objects.create(business=cls.business, name="Context bot")
        cls.conversation = BotConversation.objects.create(business=cls.business, bot=cls.bot, client=cls.customer,
            lead=cls.lead, deal=cls.deal, assigned_to=cls.operator, external_user_id="context-visitor")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.now = timezone.now()
        self.url = f"/api/inbox/conversations/{self.conversation.id}/context/"

    def test_picker_scopes_before_limit_and_rejects_invalid_kind(self):
        BusinessMember.objects.create(business=self.other, user=self.owner, role="owner",
            business_role=BusinessRole.objects.get(business=self.other, preset_key="owner"))
        for index in range(10):
            Client.objects.create(business=self.other, full_name=f"Foreign {index}")
        url = f"/api/inbox/conversations/{self.conversation.id}/link-candidates/"
        response = self.api.get(url, {"kind": "client"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [self.customer.id])
        self.assertEqual(self.api.get(url, {"kind": "client", "term": "missing"}).data, [])
        self.assertEqual(self.api.get(url, {"kind": "secrets"}).status_code, 400)

    def test_link_picker_denies_child_resource_and_scopes_owned_records(self):
        url = f"/api/inbox/conversations/{self.conversation.id}/link-candidates/"
        self.permission(Resources.LEADS, scope="own")
        self.api.force_authenticate(self.operator)
        self.assertEqual(self.api.get(url, {"kind": "lead"}).data, [])
        self.lead.responsible_user = self.operator
        self.lead.save(update_fields=["responsible_user"])
        self.assertEqual([row["id"] for row in self.api.get(url, {"kind": "lead"}).data], [self.lead.id])
        self.permission(Resources.CLIENTS, allowed=False)
        self.assertEqual(self.api.get(url, {"kind": "client"}).status_code, 403)

    def test_list_projection_batches_authorization_for_multiple_records(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        inbox_list_link_visibility([self.conversation], actor=self.owner)  # warm model capability cache
        with CaptureQueriesContext(connection) as single:
            expected = inbox_list_link_visibility([self.conversation], actor=self.owner)
        with CaptureQueriesContext(connection) as many:
            actual = inbox_list_link_visibility([self.conversation] * 30, actor=self.owner)
        self.assertEqual(actual, expected)
        self.assertEqual(len(many), len(single))

    def permission(self, resource, *, allowed=True, scope="business", action="view"):
        role = BusinessRole.objects.get(business=self.business, preset_key="operator")
        RolePermission.objects.update_or_create(business_role=role, resource=resource, action=action,
                                                defaults={"is_allowed": allowed, "scope": scope})

    def appointment(self, **overrides):
        data = dict(business=self.business, client=self.customer, lead=self.lead, service=self.service,
                    resource=self.resource, start_at=self.now + timedelta(days=1), end_at=self.now + timedelta(days=1, minutes=30))
        data.update(overrides)
        return Appointment.objects.create(**data)

    def test_owner_context_contains_real_entities_and_exact_links(self):
        appointment = self.appointment()
        response = self.api.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["client"]["data"]["phone"], self.customer.phone)
        self.assertEqual(data["client"]["data"]["notes"], self.customer.notes)
        self.assertEqual(data["client"]["data"]["href"], f"/app/clients/{self.customer.id}")
        self.assertEqual(data["deal"]["data"]["amount"], "15000.00")
        self.assertEqual(data["deal"]["data"]["stage_name"], "New")
        self.assertEqual(data["lead"]["data"]["title"], self.lead.message)
        self.assertEqual(data["appointments"]["kind"], "client")
        self.assertEqual(data["appointments"]["items"][0]["href"], f"/app/calendar/{appointment.id}")
        self.assertEqual(data["appointments"]["items"][0]["resource_name"], self.resource.name)
        self.assertEqual(data["timezone"], "Asia/Almaty")
        self.assertTrue(data["actions"]["book"])

    def test_upcoming_excludes_terminal_archived_and_past_before_limit(self):
        for status in ("cancelled", "completed", "no_show"):
            self.appointment(status=status)
        self.appointment(is_archived=True)
        self.appointment(start_at=self.now-timedelta(hours=2), end_at=self.now-timedelta(hours=1))
        expected = []
        for offset in (4, 1, 3, 2):
            expected.append(self.appointment(start_at=self.now+timedelta(days=offset),
                end_at=self.now+timedelta(days=offset, minutes=30), status="rescheduled"))
        data = build_inbox_context(self.conversation, actor=self.owner, now=self.now)["appointments"]
        self.assertEqual([row["id"] for row in data["items"]], [item.id for item in sorted(expected, key=lambda x:x.start_at)[:3]])
        self.assertTrue(data["has_more"])

    def test_only_existing_booking_provenance_attributes_appointment_to_conversation(self):
        self.appointment()  # Shared lead/client does not establish provenance.
        linked = self.appointment(start_at=self.now+timedelta(days=3), end_at=self.now+timedelta(days=3, minutes=30))
        ActivityEvent.objects.create(business=self.business, client=self.customer, event_type=ActivityEvents.APPOINTMENT_CREATED,
            entity_type="Appointment", entity_id=str(linked.id), metadata={"conversation_id":self.conversation.id})
        data = self.api.get(self.url).data["appointments"]
        self.assertEqual(data["kind"], "conversation")
        self.assertEqual([row["id"] for row in data["items"]], [linked.id])
        linked.status = "cancelled"
        linked.save(update_fields=["status"])
        self.assertEqual(self.api.get(self.url).data["appointments"]["kind"], "client")

    def test_foreign_conversation_denied_and_unauthenticated_denied(self):
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get(self.url).status_code, 404)
        self.api.force_authenticate(None)
        self.assertIn(self.api.get(self.url).status_code, [401,403])

    def test_conversation_access_does_not_grant_child_access_or_names_in_list(self):
        self.permission(Resources.CLIENTS, allowed=False)
        self.permission(Resources.LEADS, allowed=False)
        self.api.force_authenticate(self.operator)
        self.appointment()
        data = self.api.get(self.url).data
        for key in ("client", "lead", "deal"):
            self.assertEqual(data[key], {"state":"forbidden", "data":None})
            self.assertFalse(data["actions"][f"link_{key}"])
        self.assertEqual(data["appointments"]["items"], [])
        detail = self.api.get(f"/api/inbox/conversations/{self.conversation.id}/").data
        self.assertIsNone(detail["client"])
        self.assertEqual(detail["client_name"], "")
        self.assertEqual(detail["client_phone"], "")
        self.assertIsNone(detail["lead"])
        self.assertIsNone(detail["deal"])
        rows = self.api.get("/api/inbox/conversations/").data["results"]
        self.assertEqual(rows[0]["client_phone"], "")

    def test_sensitive_fields_masked_independently_of_entity_view(self):
        self.permission(Resources.DEALS)
        self.api.force_authenticate(self.operator)
        data = self.api.get(self.url).data
        self.assertEqual(data["client"]["state"], "available")
        self.assertEqual(data["client"]["data"]["notes"], "")
        self.assertEqual(data["deal"]["data"]["title"], self.deal.title)
        self.assertIsNone(data["deal"]["data"]["amount"])
        self.assertEqual(data["deal"]["data"]["currency"], "")

    def test_own_scope_filters_appointments_before_limit_and_hides_other_deal(self):
        self.permission(Resources.APPOINTMENTS, scope="own")
        self.permission(Resources.DEALS, scope="own")
        for _ in range(5):
            self.appointment()
        resource = Resource.objects.create(business=self.business, name="Own specialist", linked_user=self.operator)
        visible = self.appointment(resource=resource, start_at=self.now+timedelta(days=3), end_at=self.now+timedelta(days=3, minutes=30))
        self.api.force_authenticate(self.operator)
        data = self.api.get(self.url).data
        self.assertEqual([row["id"] for row in data["appointments"]["items"]], [visible.id])
        self.assertFalse(data["appointments"]["has_more"])
        self.assertEqual(data["deal"]["state"], "forbidden")
        # Settings permission is separate from appointment permission.
        self.assertEqual(data["appointments"]["items"][0]["resource_name"], "")

    def test_foreign_back_reference_hidden_even_for_multi_business_owner(self):
        BusinessMember.objects.create(business=self.other, user=self.owner, role="admin")
        foreign_client = Client.objects.create(business=self.other, full_name="Foreign secret", phone="foreign-secret")
        BotConversation.objects.filter(pk=self.conversation.pk).update(client=foreign_client)
        data = self.api.get(self.url).data
        self.assertEqual(data["client"], {"state":"forbidden", "data":None})
        self.assertFalse(data["actions"]["book"])
        self.assertNotIn("Foreign secret", str(data))

    def test_disabled_child_capabilities_hide_existing_entities(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="deals", defaults={"is_enabled":False})
        BusinessCapability.objects.update_or_create(business=self.business, module_key="appointments", defaults={"is_enabled":False})
        self.appointment()
        data = self.api.get(self.url).data
        self.assertEqual(data["deal"]["state"], "forbidden")
        self.assertEqual(data["appointments"]["state"], "forbidden")
        self.assertFalse(data["actions"]["book"])

    def test_unlinked_context_has_only_allowed_create_actions(self):
        BotConversation.objects.filter(pk=self.conversation.pk).update(client=None, lead=None, deal=None)
        data = self.api.get(self.url).data
        self.assertEqual(data["client"]["state"], "empty")
        self.assertTrue(data["actions"]["create_client"])
        self.assertTrue(data["actions"]["link_client"])
        self.assertFalse(data["actions"]["book"])
        self.assertEqual(data["appointments"]["state"], "empty")

    def test_task_is_only_unfinished_visible_work_of_this_conversation(self):
        Task.objects.create(business=self.business, conversation=self.conversation, title="Hidden task", assignee=self.owner)
        Task.objects.create(business=self.business, conversation=self.conversation, title="Done task", assignee=self.operator, status="done")
        task = Task.objects.create(business=self.business, conversation=self.conversation, title="Call back", assignee=self.operator)
        self.api.force_authenticate(self.operator)
        data = self.api.get(self.url).data
        self.assertEqual(data["task"]["id"], task.id)
        self.assertEqual(data["task"]["href"], f"/app/tasks?task={task.id}")

    def test_view_only_conversation_cannot_offer_link_or_mutation(self):
        self.permission(Resources.CONVERSATIONS, action=Actions.UPDATE, allowed=False)
        self.api.force_authenticate(self.operator)
        data = self.api.get(self.url).data
        self.assertFalse(data["actions"]["update"])
        self.assertFalse(data["actions"]["link_client"])
        self.assertFalse(data["actions"]["create_task"])
