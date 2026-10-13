from datetime import datetime, timedelta, timezone

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.settings import api_settings

from apps.accounts.models import User
from apps.activities.models import Tag, TaggedObject
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client


class ClientWorkspaceFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="filter-owner", email="filter-owner@example.test", password="test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Filters", slug="filters", timezone="Asia/Almaty")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        other = User.objects.create_user(username="other-filter", email="other-filter@example.test", password="test")
        self.foreign = Business.objects.create(owner=other, name="Other", slug="other-filters")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.client = Client.objects.create(business=self.business, full_name="Waiting", source="website")
        self.bot = Bot.objects.create(business=self.business, name="Inbox")
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot, client=self.client, channel="website", external_user_id="workspace", status="open")

    def get(self, **params):
        return self.api.get("/api/clients/", {"workspace": "true", **params})

    def inbound(self):
        return BotMessage.objects.create(conversation=self.conversation, direction="inbound", sender_type="client", status="received", text="Question")

    def test_waiting_reply_uses_delivery_not_read_or_assignment_or_failed_draft(self):
        self.inbound()
        self.conversation.unread_count = 0
        self.conversation.assigned_to = self.owner
        self.conversation.save()
        reply = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="ai", status="failed", text="Failed answer")
        response = self.get(quick_filter="no_reply")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertTrue(response.data["results"][0]["has_no_reply"])
        reply.status = "sent"
        reply.sent_at = datetime.now(timezone.utc)
        reply.save()
        self.assertEqual(self.get(quick_filter="no_reply").data["count"], 0)
        self.inbound()
        self.assertEqual(self.get(quick_filter="no_reply").data["count"], 1)
        self.conversation.status = "closed"
        self.conversation.save()
        self.assertEqual(self.get(quick_filter="no_reply").data["count"], 0)

    def test_handoff_is_separate_and_summary_counts_full_filtered_scope(self):
        self.conversation.handoff_required = True
        self.conversation.save()
        self.assertEqual(self.get(quick_filter="no_reply").data["count"], 0)
        self.assertEqual(self.get(handoff="true").data["count"], 1)
        self.inbound()
        Client.objects.create(business=self.business, full_name="Other source", source="manual")
        Client.objects.create(business=self.foreign, full_name="Foreign", source="website")
        result = self.get(source="website", page_size=1)
        self.assertEqual(result.data["summary"]["total"], 1)
        self.assertEqual(result.data["summary"]["no_reply"], 1)
        self.assertEqual(self.get(q="missing").data["summary"]["no_reply"], 0)

    def test_business_local_dates_are_inclusive_and_validate_range(self):
        # 00:30 on October13 in Almaty is October12 in UTC.
        Client.objects.filter(pk=self.client.pk).update(created_at=datetime(2026, 10, 12, 19, 30, tzinfo=timezone.utc))
        self.assertEqual(self.get(created_from="2026-10-13", created_to="2026-10-13").data["count"], 1)
        self.assertEqual(self.get(created_to="2026-10-12").data["count"], 0)
        for params in [{"created_from": "bad"}, {"created_from": "2026-10-14", "created_to": "2026-10-13"}, {"tag": "no"}, {"tag": "99999999999999999999999"}, {"segment": "1,2"}, {"archive": "bad"}]:
            self.assertEqual(self.get(**params).status_code, 400)

    def test_sources_tags_any_all_archive_and_tenant(self):
        first = Tag.objects.create(business=self.business, name="VIP")
        second = Tag.objects.create(business=self.business, name="Recall")
        foreign = Tag.objects.create(business=self.foreign, name="Foreign")
        TaggedObject.objects.create(business=self.business, tag=first, entity_type="client", entity_id=str(self.client.pk))
        self.assertEqual(self.get(source="website,manual", tag=f"{first.pk},{second.pk}", tag_mode="any").data["count"], 1)
        self.assertEqual(self.get(tag=f"{first.pk},{second.pk}", tag_mode="all").data["count"], 0)
        self.assertEqual(self.get(tag=str(foreign.pk)).data["count"], 0)
        Client.objects.filter(pk=self.client.pk).update(is_archived=True)
        self.assertEqual(self.get().data["count"], 0)
        self.assertEqual(self.get(archive="archived", include_archived="true").data["count"], 1)

    def test_counts_ignore_quick_and_pagination_but_keep_search_and_source(self):
        self.inbound()
        page_size = api_settings.PAGE_SIZE
        Client.objects.bulk_create([
            Client(business=self.business, full_name=f"Waiting {index}", source="website")
            for index in range(page_size)
        ])
        Client.objects.create(business=self.business, full_name="Waiting excluded", source="manual")
        response = self.get(q="Waiting", source="website", quick_filter="no_reply", page_size=1)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["summary"]["total"], page_size + 1)
        self.assertEqual(response.data["summary"]["no_reply"], 1)
        all_rows = self.get(q="Waiting", source="website")
        self.assertEqual(all_rows.data["count"], page_size + 1)
        self.assertEqual(len(all_rows.data["results"]), page_size)
        second_page = self.get(q="Waiting", source="website", page=2)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertEqual(second_page.data["summary"]["total"], page_size + 1)
        self.assertEqual(second_page.data["summary"]["no_reply"], 1)

    def test_requested_page_size_controls_rows_and_preserves_context_counts(self):
        Client.objects.bulk_create([
            Client(business=self.business, full_name=f"Waiting {index}", source="website")
            for index in range(24)
        ])
        first = self.get(q="Waiting", page_size=10)
        second = self.get(q="Waiting", page_size=10, page=2)
        last = self.get(q="Waiting", page_size=10, page=3)
        self.assertEqual([len(response.data["results"]) for response in (first, second, last)], [10, 10, 5])
        identifiers = [row["id"] for response in (first, second, last) for row in response.data["results"]]
        self.assertEqual(len(set(identifiers)), 25)
        for response in (first, second, last):
            self.assertEqual(response.data["count"], 25)
            self.assertEqual(response.data["summary"]["total"], 25)
        self.assertIsNone(last.data["next"])
        self.assertIsNotNone(second.data["previous"])
        self.assertEqual(len(self.get(q="Waiting", page_size=20).data["results"]), 20)
        self.assertEqual(len(self.get(q="Waiting", page_size=30).data["results"]), 25)
        self.assertEqual(self.get(q="Waiting", page_size=10, page=4).status_code, 404)
