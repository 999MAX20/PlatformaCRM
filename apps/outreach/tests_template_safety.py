from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.notifications.models import Notification
from apps.outreach.models import OutreachCampaign, OutreachRecipient
from apps.outreach.services import launch_campaign, prepare_campaign_recipients, render_message, unsupported_template_variables


TEMPLATE_LIMIT = 16384
MESSAGE_LIMIT = 65536


class BoundedTemplateRenderingTests(SimpleTestCase):
    def setUp(self):
        self.client_data = SimpleNamespace(
            full_name="Клиент", phone="20", email="synthetic@example.invalid",
            business=SimpleNamespace(name="Synthetic Business"), source="telegram",
        )

    def test_plain_variables_unicode_and_escaped_braces_keep_semantics(self):
        text = "{{literal}} {client_name} {phone} {email} {business_name} {channel}"
        self.assertEqual(render_message(text, self.client_data),
                         "{literal} Клиент 20 synthetic@example.invalid Synthetic Business telegram")
        self.assertEqual(unsupported_template_variables("Hello {client_name}"), [])
        self.assertEqual(unsupported_template_variables("{unknown}"), ["unknown"])

    def test_field_values_are_not_recursively_formatted(self):
        self.client_data.full_name = "{phone:999999999}"
        self.assertEqual(render_message("Name: {client_name}", self.client_data), "Name: {phone:999999999}")

    def test_width_is_rejected_with_only_a_small_bounded_baseline_allocation(self):
        # Baseline allocates at most 65,537 characters; never execute extreme widths.
        with self.assertRaises(ValueError):
            render_message("{client_name:65537}", self.client_data)

    def test_extreme_width_is_checked_only_by_validation(self):
        with self.assertRaises(ValueError):
            unsupported_template_variables("{client_name:999999999999999}")

    def test_conversions_nested_specs_attribute_and_index_are_not_template_variables(self):
        for text in ("{client_name!r}", "{client_name:{phone}}", "{client_name.__class__}", "{client_name[0]}", "{}", "{0}"):
            with self.subTest(kind=text[:20]), self.assertRaises(ValueError):
                render_message(text, self.client_data)

    def test_input_limit_is_checked_before_parser_work(self):
        self.assertEqual(render_message("x" * TEMPLATE_LIMIT, self.client_data), "x" * TEMPLATE_LIMIT)
        with self.assertRaises(ValueError):
            render_message("x" * (TEMPLATE_LIMIT + 1), self.client_data)

    def test_cumulative_expansion_has_exact_boundary_without_truncation(self):
        self.client_data.full_name = "x" * 255
        exact = "{client_name}" * 257 + "!"
        self.assertEqual(len(render_message(exact, self.client_data)), MESSAGE_LIMIT)
        with self.assertRaises(ValueError):
            render_message(exact + "!", self.client_data)


class OutreachTemplateSafetyFlowTests(TestCase):
    def setUp(self):
        self.api = APIClient(raise_request_exception=False)
        self.owner = User.objects.create_user(username="safe-template-owner", email="safe-template-owner@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Template boundary", slug="template-boundary")
        self.client_record = Client.objects.create(
            business=self.business, full_name="Short", source="telegram", telegram_id="synthetic-chat-1",
        )
        self.api.force_authenticate(self.owner)

    def campaign(self, **kwargs):
        values = {"business": self.business, "name": "Synthetic campaign", "channel": "telegram",
                  "message_text": "Hello {client_name}", "require_opt_in": False}
        values.update(kwargs)
        return OutreachCampaign.objects.create(**values)

    def test_template_and_campaign_api_reject_advanced_or_malformed_syntax(self):
        for text in ("{client_name:65537}", "{client_name!r}", "{client_name.__class__}", "{"):
            for endpoint, field in (("templates", "body"), ("campaigns", "message_text")):
                with self.subTest(endpoint=endpoint, kind=text[:20]):
                    response = self.api.post(f"/api/outreach/{endpoint}/", {
                        "business": self.business.pk, "name": "Invalid", "channel": "telegram", field: text,
                    }, format="json")
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.data)

    def test_oversized_template_and_personalized_text_are_field_errors(self):
        template = self.api.post("/api/outreach/templates/", {
            "business": self.business.pk, "name": "Too long", "channel": "telegram", "body": "x" * (TEMPLATE_LIMIT + 1),
        }, format="json")
        self.assertEqual(template.status_code, 400)
        self.assertIn("body", template.data)
        campaign = self.campaign()
        recipient = OutreachRecipient.objects.create(
            business=self.business, campaign=campaign, client=self.client_record,
            recipient_id="synthetic-chat-1", personalized_text="Allowed",
        )
        response = self.api.patch(f"/api/outreach/recipients/{recipient.pk}/", {
            "personalized_text": "x" * (MESSAGE_LIMIT + 1),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("personalized_text", response.data)
        recipient.refresh_from_db()
        self.assertEqual(recipient.personalized_text, "Allowed")

    def test_preparation_rolls_back_earlier_recipients_on_expansion_overflow(self):
        Client.objects.create(business=self.business, full_name="x" * 255, source="telegram", telegram_id="synthetic-chat-2")
        campaign = self.campaign(message_text="{client_name}" * 258)
        with self.assertRaises(ValueError):
            prepare_campaign_recipients(campaign)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, OutreachCampaign.Statuses.DRAFT)
        self.assertFalse(campaign.recipients.exists())

    def test_legacy_invalid_template_rejected_even_for_empty_audience(self):
        campaign = self.campaign(message_text="{client_name:65537}", audience_type="manual")
        with self.assertRaises(ValueError):
            prepare_campaign_recipients(campaign, client_ids=[])
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, OutreachCampaign.Statuses.DRAFT)

    def test_launch_rejects_oversized_stored_plain_text_without_notifications(self):
        campaign = self.campaign(status=OutreachCampaign.Statuses.READY)
        recipient = OutreachRecipient.objects.create(
            business=self.business, campaign=campaign, client=self.client_record,
            recipient_id="synthetic-chat-1", personalized_text="x" * (MESSAGE_LIMIT + 1),
        )
        with self.assertRaises(ValueError):
            launch_campaign(campaign)
        campaign.refresh_from_db()
        recipient.refresh_from_db()
        self.assertEqual(campaign.status, OutreachCampaign.Statuses.READY)
        self.assertIsNone(recipient.notification_id)
        self.assertFalse(Notification.objects.filter(business=self.business, category=Notification.Categories.OUTREACH).exists())

    def test_legitimate_prepare_launch_and_stored_literal_braces_remain_local(self):
        campaign = self.campaign(message_text="{{literal}} Hello {client_name}")
        prepare_campaign_recipients(campaign)
        recipient = campaign.recipients.get()
        self.assertEqual(recipient.personalized_text, "{literal} Hello Short")
        recipient.personalized_text = "Literal {client_name:999999999}"
        recipient.save(update_fields=["personalized_text"])
        with patch("apps.outreach.services._notify_outreach_team"):
            result = launch_campaign(campaign)
        self.assertEqual(result["notifications"], 1)
        recipient.refresh_from_db()
        self.assertEqual(recipient.notification.text, "Literal {client_name:999999999}")
        self.assertEqual(recipient.notification.status, Notification.Statuses.PENDING)
