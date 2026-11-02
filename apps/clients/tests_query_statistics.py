"""Semantic regressions for Client statistics; real PostgreSQL in bounded CI."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import connection
from django.db.models import Q
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.activities.models import Segment, Tag, TaggedObject
from apps.bots.models import Bot, BotConversation
from apps.clients.models import Client
from apps.clients.selectors import annotate_client_list_queryset, build_client_facets, build_client_summary, count_client_queryset
from apps.clients import tests as client_test_fixtures
from apps.clients.views import ClientCountPaginator
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.scheduling.models import Appointment
from apps.tasks.models import Task


class ClientQueryStatisticsTests(TestCase):
    def setUp(self):
        # Reuse the existing validated owner/two-tenant/client setup only.
        client_test_fixtures.DuplicateDetectionFoundationTests.setUp(self)

    def queryset(self):
        return annotate_client_list_queryset(Client.objects.filter(business=self.business)).distinct()

    def tag(self, client, name="vip", business=None):
        business = business or self.business
        tag = Tag.objects.create(business=business, name=name)
        TaggedObject.objects.create(business=business, tag=tag, entity_type="client", entity_id=str(client.pk))
        return tag

    def deal(self, client, **kwargs):
        pipeline, _ = Pipeline.objects.get_or_create(business=self.business, slug="count-test", defaults={"name":"Counts"})
        stage, _ = PipelineStage.objects.get_or_create(business=self.business, pipeline=pipeline, name="First")
        return Deal.objects.create(business=self.business, client=client, pipeline=pipeline, stage=stage, title="Count deal", **kwargs)

    def appointment(self, client, index=0, **kwargs):
        start = datetime(2026, 6, 20, 10, tzinfo=ZoneInfo("Asia/Almaty"))+timedelta(days=index)
        return Appointment.objects.create(business=self.business, client=client, service=self.service, start_at=start, end_at=start+timedelta(hours=1), **kwargs)

    def test_cross_product_counts_and_summary_are_exact(self):
        for _ in range(3):Lead.objects.create(business=self.business, client=self.target)
        for _ in range(2):self.deal(self.target)
        for i in range(4):self.appointment(self.target, i)
        for _ in range(3):Task.objects.create(business=self.business, client=self.target, title="Count task")
        bot = Bot.objects.create(business=self.business, name="Count bot")
        for _ in range(2):BotConversation.objects.create(business=self.business, client=self.target, bot=bot, channel=BotConversation.Channels.WEBSITE)
        query = self.queryset();rows={x.pk:x for x in query}
        actual=tuple(getattr(rows[self.target.pk], key) for key in ("leads_count","deals_count","appointments_count","tasks_count","conversations_count"))
        self.assertEqual(actual,(3,2,4,3,2))
        self.assertEqual(tuple(getattr(rows[self.duplicate.pk],key) for key in ("leads_count","deals_count","appointments_count","tasks_count","conversations_count")),(0,0,0,0,0))
        self.assertEqual(count_client_queryset(query),2)
        self.assertEqual(build_client_summary(query),{"total":2,"active":1,"no_reply":1,"repeat":1})
        self.assertEqual(build_client_facets(query)["activity"],{"active":1,"vip":0,"no_reply":1,"repeat":1})
        self.assertEqual(build_client_facets(query)["source"],{"manual":2})

    def test_vip_only_summary_active_is_not_active_facet(self):
        self.tag(self.target,"vip");self.tag(self.target,"VIP")
        query=self.queryset()
        self.assertEqual(count_client_queryset(query.filter(is_vip=True)),1)
        self.assertEqual(build_client_summary(query),{"total":2,"active":1,"no_reply":0,"repeat":0})
        self.assertEqual(build_client_facets(query)["activity"],{"active":0,"vip":1,"no_reply":0,"repeat":0})
        row=query.get(pk=self.target.pk);self.assertFalse(row.is_active);self.assertTrue(row.is_vip)

    def test_done_cancelled_tasks_count_but_are_not_open(self):
        for status in (Task.Statuses.DONE,Task.Statuses.CANCELLED):Task.objects.create(business=self.business,client=self.target,title=status,status=status)
        Task.objects.create(business=self.business,client=self.target,title="Archived open",is_archived=True)
        Lead.objects.create(business=self.business,client=self.target,is_archived=True)
        self.deal(self.target,is_archived=True);self.appointment(self.target,is_archived=True)
        row=self.queryset().get(pk=self.target.pk)
        self.assertEqual(row.tasks_count,2);self.assertEqual(row.leads_count,0);self.assertEqual(row.deals_count,0);self.assertEqual(row.appointments_count,0);self.assertFalse(row.is_active);self.assertFalse(row.has_no_reply)

    def test_empty_projection_remains_zero(self):
        query=self.queryset().none()
        self.assertEqual(count_client_queryset(query),0)
        self.assertEqual(build_client_summary(query),{"total":0,"active":0,"no_reply":0,"repeat":0})
        self.assertEqual(build_client_facets(query),{"source":{},"activity":{"active":0,"vip":0,"no_reply":0,"repeat":0}})

    def test_quick_filters_change_page_not_summary_scope(self):
        Lead.objects.create(business=self.business,client=self.target)
        Task.objects.create(business=self.business,client=self.duplicate,title="Mine",assignee=self.owner)
        expected={"new":set(),"vip":set(),"no_reply":{self.target.pk},"mine":{self.duplicate.pk}}
        for quick,ids in expected.items():
            with self.subTest(filter=quick):
                response=self.api.get("/api/clients/",{"quick_filter":quick})
                self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],len(ids));self.assertEqual({r["id"] for r in response.data["results"]},ids)
                self.assertEqual(response.data["summary"],{"total":2,"active":1,"no_reply":1,"repeat":0})
                self.assertEqual(response.data["facets"]["activity"],{"active":1,"vip":0,"no_reply":1,"repeat":0})

    def test_search_source_ids_tag_and_foreign_segment_preserved(self):
        self.duplicate.source=Client.Sources.WEBSITE;self.duplicate.save(update_fields=["source"])
        tag=self.tag(self.target)
        checks=[({"q":"MAIN@EXAMPLE.COM"},{self.target.pk}),({"q":"8 (701) 555-01-01"},{self.target.pk,self.duplicate.pk}),({"source":"website"},{self.duplicate.pk}),({"client_ids":str(self.target.pk)},{self.target.pk}),({"tag":tag.pk},{self.target.pk})]
        for params,ids in checks:
            with self.subTest(params=params):
                response=self.api.get("/api/clients/",params);self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],len(ids));self.assertEqual({r["id"] for r in response.data["results"]},ids);self.assertEqual(response.data["summary"]["total"],len(ids))
        foreign=Segment.objects.create(business=self.other_business,name="Foreign segment")
        response=self.api.get("/api/clients/",{"segment":foreign.pk});self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],0);self.assertEqual(response.data["summary"]["total"],0)

    def test_tenant_tag_visibility_roles_and_archive_scope(self):
        self.tag(self.target,business=self.other_business)
        response=self.api.get("/api/clients/");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],2);self.assertEqual(response.data["facets"]["activity"]["vip"],0)
        self.api.force_authenticate(self.other_owner);response=self.api.get("/api/clients/");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],1);self.assertFalse({self.target.pk,self.duplicate.pk}&{x["id"] for x in response.data["results"]});self.assertEqual(self.api.get(f"/api/clients/{self.target.pk}/").status_code,404)
        self.api.force_authenticate(self.view_only_user);response=self.api.get("/api/clients/");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],2)
        self.api.force_authenticate(self.owner);self.duplicate.is_archived=True;self.duplicate.save(update_fields=["is_archived"])
        response=self.api.get("/api/clients/");self.assertEqual(response.data["count"],1);self.assertEqual(response.data["summary"]["total"],1)
        response=self.api.get("/api/clients/",{"include_archived":"true"});self.assertEqual(response.data["count"],2);self.assertEqual(response.data["summary"]["total"],2)

    def test_repeats_and_row_display_fields_unchanged(self):
        self.deal(self.target,status=Deal.Statuses.WON);self.deal(self.target,status=Deal.Statuses.LOST)
        self.appointment(self.target,0,status=Appointment.Statuses.COMPLETED);self.appointment(self.target,1,status=Appointment.Statuses.CANCELLED)
        due=datetime(2026,6,30,12,tzinfo=ZoneInfo("Asia/Almaty"))
        Task.objects.create(business=self.business,client=self.target,title="Call client",assignee=self.owner,due_at=due,priority=Task.Priorities.HIGH)
        response=self.api.get("/api/clients/",{"q":"main@example.com"});self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],1);self.assertEqual(response.data["summary"]["repeat"],1)
        row=response.data["results"][0];self.assertEqual(row["manager_user_id"],self.owner.pk);self.assertEqual(row["next_step_title"],"Call client");self.assertEqual(row["next_step_priority"],"high");self.assertIsNotNone(row["next_step_date"]);self.assertIsNotNone(row["last_activity_at"]);self.assertEqual(row["deals_count"],2);self.assertEqual(row["appointments_count"],2)

    def test_thin_count_and_pagination_do_not_drop_clients(self):
        Client.objects.bulk_create([Client(business=self.business,full_name=f"Page client {i}") for i in range(51)])
        query=self.queryset()
        with CaptureQueriesContext(connection) as captured:self.assertEqual(count_client_queryset(query),53)
        self.assertEqual(len(captured),1)
        text=captured[0]["sql"]
        for table in ("leads_lead","crm_deal","tasks_task","scheduling_appointment","bots_botconversation"):
            self.assertNotIn('JOIN "'+table+'"',text)
        self.assertEqual(ClientCountPaginator(query,50).count,53)
        response=self.api.get("/api/clients/");self.assertEqual(response.status_code,200);self.assertEqual(response.data["count"],53);self.assertEqual(len(response.data["results"]),50);self.assertEqual(len({x["id"] for x in response.data["results"]}),50)
        self.assertEqual(response.data["summary"]["total"],53)
