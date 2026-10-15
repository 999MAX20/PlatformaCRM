import uuid
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.integrations.models import BusinessConnector
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.scheduling.models import Appointment
from apps.services.models import Service
from apps.tasks.models import Task


@override_settings(SUPPORT_REQUIRES_GRANT=True)
class PlatformClinicReadTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="clinic-platform", email="clinic-platform@example.com", role="platform_manager")
        self.owner = User.objects.create_user(username="clinic-owner", email="clinic-owner@example.com", role="business_owner")
        self.foreign_owner = User.objects.create_user(username="clinic-foreign", email="FOREIGN_PERSON@example.com", role="business_owner")
        self.business = Business.objects.create(name="Clinic", slug="clinic-crm", owner=self.owner)
        self.other = Business.objects.create(name="Other", slug="clinic-other", owner=self.foreign_owner)
        self.client = Client.objects.create(business=self.business, full_name="Patient", phone="12345", notes="Private note", source_context_json={"secret":"RAW_SECRET"})
        self.foreign = Client.objects.create(business=self.other, full_name="FOREIGN_PATIENT")
        lead=Lead.objects.create(business=self.business,client=self.client,message="Client request",responsible_user=self.owner)
        pipeline=Pipeline.objects.create(business=self.business,name="Sales",slug="sales")
        stage=PipelineStage.objects.create(business=self.business,pipeline=pipeline,name="New")
        deal=Deal.objects.create(business=self.business,client=self.client,lead=lead,pipeline=pipeline,stage=stage,title="Treatment plan",amount="123.45")
        service=Service.objects.create(business=self.business,name="Consultation")
        now=timezone.now()
        appointment=Appointment.objects.create(business=self.business,client=self.client,lead=lead,service=service,start_at=now,end_at=now+timezone.timedelta(hours=1))
        task=Task.objects.create(business=self.business,title="Call patient",client=self.client,lead=lead,deal=deal,appointment=appointment,assignee=self.owner)
        bot=Bot.objects.create(business=self.business,name="Assistant",settings_json={"key":"RAW_SECRET"})
        conversation=BotConversation.objects.create(business=self.business,bot=bot,client=self.client,channel="website",metadata_json={"token":"RAW_SECRET"},unread_count=4)
        payment=Payment.objects.create(business=self.business,client=self.client,kind="receipt",amount="123.45",currency="KZT",method="cash",occurred_at=now,submission_id=uuid.uuid4(),request_hash="RAW_SECRET")
        connector=BusinessConnector.objects.create(business=self.business,name="Channel",provider="telegram",config_json={"token":"RAW_SECRET"},last_error="RAW_SECRET")
        self.records={"clients":self.client,"leads":lead,"deals":deal,"tasks":task,"appointments":appointment,"conversations":conversation,"payments":payment,"connectors":connector}
        self.api=APIClient();self.api.force_authenticate(self.staff)

    def url(self,kind="clients",record=None,business=None):
        return f"/api/platform/merchants/{(business or self.business).pk}/crm/{kind}/"+(f"{record.pk}/" if record else "")

    def test_every_collection_and_detail_is_audited_without_grant_or_payload(self):
        for kind,row in self.records.items():
            for url in (self.url(kind),self.url(kind,row)):
                with self.subTest(url=url):
                    response=self.api.get(url)
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response['Cache-Control'],'no-store')
                    self.assertNotIn('RAW_SECRET',str(response.data))
                    self.assertEqual(response.data['business']['id'],self.business.pk)
        logs=AuditLog.objects.filter(metadata__kind='platform_crm_read')
        self.assertEqual(logs.count(),16)
        self.assertEqual(set(logs.values_list('business_id',flat=True)),{self.business.pk})
        for log in logs:
            self.assertNotIn('Private note',str(log.metadata))
            self.assertEqual(log.actor_id,self.staff.pk)
        self.assertEqual(self.api.get(self.url('clients',self.client)).data['fields']['notes'],'Private note')

    def test_bound_business_entity_and_client_filter(self):
        self.assertEqual(self.api.get(self.url('clients',self.foreign)).status_code,404)
        self.assertEqual(self.api.get(self.url('clients',self.client,self.other)).status_code,404)
        self.assertEqual(self.api.get(self.url('clients',self.foreign,self.other)).status_code,200)
        self.assertEqual(self.api.get(self.url('tasks'),{'client':self.foreign.pk}).status_code,404)
        self.assertEqual(self.api.get(self.url('tasks'),{'client':self.client.pk}).data['count'],1)

    def test_corrupt_foreign_relations_and_users_are_not_projected_or_searchable(self):
        lead=self.records['leads'];lead.client=self.foreign;lead.responsible_user=self.foreign_owner;lead.save()
        response=self.api.get(self.url('leads',lead))
        self.assertEqual(response.data['relations'],[item for item in response.data['relations'] if item['field']!='client'])
        self.assertEqual(response.data['people'],[])
        self.assertNotIn('FOREIGN_',str(response.data))
        self.assertEqual(self.api.get(self.url('leads'),{'search':'FOREIGN_PATIENT'}).data['count'],0)

    def test_clinic_users_inactive_and_revoked_platform_role_denied(self):
        for actor in (self.owner,self.foreign_owner):
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.get(self.url()).status_code,403)
        self.api.force_authenticate(self.staff)
        User.objects.filter(pk=self.staff.pk).update(role='staff')
        self.assertEqual(self.api.get(self.url()).status_code,403)
        User.objects.filter(pk=self.staff.pk).update(role='platform_manager',is_active=False)
        self.assertEqual(self.api.get(self.url()).status_code,403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(self.url()).status_code,401)

    def test_mutation_methods_rejected_and_read_leaves_domain_unchanged(self):
        for method in ('post','put','patch','delete'):
            for url in (self.url(),self.url('clients',self.client)):
                self.assertEqual(getattr(self.api,method)(url,{}).status_code,405)
        before=self.records['conversations'].__dict__.copy()
        self.api.get(self.url('conversations',self.records['conversations']))
        self.records['conversations'].refresh_from_db()
        for key in ('unread_count','updated_at','bot_enabled','status'):
            self.assertEqual(getattr(self.records['conversations'],key),before[key])

    def test_search_archive_pagination_and_invalid_filters(self):
        for i in range(12):Client.objects.create(business=self.business,full_name=f'Paged {i}')
        Client.objects.create(business=self.business,full_name='Archived',is_archived=True)
        first=self.api.get(self.url(),{'page_size':10});second=self.api.get(self.url(),{'page_size':10,'page':2})
        self.assertEqual(first.data['count'],13)
        self.assertEqual(len({row['id'] for row in first.data['results']+second.data['results']}),13)
        self.assertEqual(self.api.get(self.url(),{'archive':'archived'}).data['count'],1)
        self.assertEqual(self.api.get(self.url(),{'search':'12345'}).data['count'],1)
        for params in ({'page_size':51},{'archive':'bad'},{'status':'bad'},{'page':0}):
            self.assertEqual(self.api.get(self.url(),params).status_code,400)
        self.assertEqual(self.api.get(self.url('unknown')).status_code,400)

    def test_audit_failure_fails_closed_and_retry_recovers(self):
        with patch('apps.core.platform_crm_views.write_audit_log',side_effect=OperationalError('RAW_SECRET')):
            response=self.api.get(self.url('clients',self.client))
        self.assertEqual(response.status_code,503)
        self.assertNotIn('Private note',str(response.data));self.assertNotIn('RAW_SECRET',str(response.data))
        self.assertEqual(self.api.get(self.url('clients',self.client)).status_code,200)

    def test_query_budget_and_no_search_contents_in_audit(self):
        with CaptureQueriesContext(connection) as first:self.api.get(self.url('leads'))
        for i in range(12):Lead.objects.create(business=self.business,client=self.client,responsible_user=self.owner)
        with CaptureQueriesContext(connection) as many:self.api.get(self.url('leads'))
        self.assertLessEqual(len(many),len(first)+1);self.assertLessEqual(len(many),14)
        self.api.get(self.url(),{'search':'Private search text'})
        self.api.get(self.url('clients',self.client),{'page':'Private page text'})
        self.assertNotIn('Private',str(list(AuditLog.objects.values_list('metadata',flat=True))))

    def test_message_pagination_is_scoped_and_does_not_mark_read_or_leak_payload(self):
        conversation=self.records['conversations']
        for i in range(13):
            BotMessage.objects.create(conversation=conversation,direction='inbound',text=f'Message {i}',payload_json={'token':'RAW_SECRET'})
        url=self.url('conversations',conversation)+'messages/'
        first=self.api.get(url,{'page_size':10});second=self.api.get(url,{'page_size':10,'page':2})
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.data['count'],13)
        self.assertEqual(len({row['id'] for row in first.data['results']+second.data['results']}),13)
        self.assertNotIn('RAW_SECRET',str(first.data))
        conversation.refresh_from_db();self.assertEqual(conversation.unread_count,4)
        self.assertFalse(conversation.messages.exclude(read_at=None).exists())
        self.assertEqual(self.api.get(self.url('conversations',conversation,self.other)+'messages/').status_code,404)
        self.assertEqual(self.api.post(url,{'text':'Must not send'}).status_code,405)
        self.assertEqual(conversation.messages.count(),13)

    def test_custom_fields_tags_notes_and_comments_reject_foreign_definitions(self):
        from apps.core.models import CustomFieldDefinition, CustomFieldValue
        from apps.activities.models import Tag, TaggedObject, Note, ActivityEvent
        from apps.tasks.models import TaskComment
        definition=CustomFieldDefinition.objects.create(business=self.business,entity_type='client',key='preference',label='Preference')
        foreign=CustomFieldDefinition.objects.create(business=self.other,entity_type='client',key='foreign',label='FOREIGN_FIELD')
        for field,value in ((definition,'Own value'),(foreign,'FOREIGN_VALUE')):
            CustomFieldValue.objects.create(business=self.business,definition=field,entity_type='client',entity_id=str(self.client.pk),value_json={'value':value,'secret':'RAW_SECRET'})
        tag=Tag.objects.create(business=self.business,name='Own tag')
        foreign_tag=Tag.objects.create(business=self.other,name='FOREIGN_TAG')
        for item in (tag,foreign_tag):TaggedObject.objects.create(business=self.business,tag=item,entity_type='client',entity_id=str(self.client.pk))
        Note.objects.create(business=self.business,client=self.client,author=self.owner,text='Own note')
        Note.objects.create(business=self.other,client=self.client,author=self.foreign_owner,text='FOREIGN_NOTE')
        ActivityEvent.objects.create(business=self.business,client=self.client,event_type='client.created',text='Own activity',metadata={'secret':'RAW_SECRET'})
        for section in ('custom_fields','tags','notes','activity'):
            response=self.api.get(self.url('clients',self.client)+section+'/')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.data['count'],1)
            self.assertNotIn('FOREIGN_',str(response.data));self.assertNotIn('RAW_SECRET',str(response.data))
        TaskComment.objects.create(task=self.records['tasks'],author=self.owner,text='Task comment')
        response=self.api.get(self.url('tasks',self.records['tasks'])+'comments/')
        self.assertEqual(response.data['results'][0]['text'],'Task comment')
        self.assertEqual(self.api.get(self.url('clients',self.client)+'messages/').status_code,400)

    def test_channel_derived_scope_and_tokens_never_projected(self):
        channel=BotChannel.objects.create(bot=self.records['conversations'].bot,channel='website',config_json={'secret':'RAW_SECRET'})
        for url in (self.url('channels'),self.url('channels',channel)):
            response=self.api.get(url)
            self.assertEqual(response.status_code,200)
            self.assertNotIn('RAW_SECRET',str(response.data));self.assertNotIn(str(channel.public_token),str(response.data))
        self.assertEqual(self.api.get(self.url('channels',channel,self.other)).status_code,404)

    def test_access_history_is_business_bound_metadata_only_and_audited(self):
        self.api.get(self.url('clients',self.client))
        self.api.get(self.url('clients',self.foreign,self.other))
        url=f'/api/platform/merchants/{self.business.pk}/crm-access-log/'
        response=self.api.get(url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['count'],1)
        self.assertEqual(response.data['results'][0]['record_id'],self.client.pk)
        self.assertNotIn('Private note',str(response.data))
        self.assertEqual(AuditLog.objects.filter(business=self.business,metadata__resource='access_log').count(),1)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(url).status_code,403)
