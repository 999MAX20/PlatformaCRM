"""Executed only by the disposable clinic acceptance runner after its base seed."""
import uuid
from apps.activities.models import ActivityEvent, Note, Tag, TaggedObject
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.clients.models import Client
from apps.core.models import CustomFieldDefinition, CustomFieldValue
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.integrations.models import BusinessConnector
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.scheduling.models import Appointment
from apps.services.models import Service
from apps.tasks.models import Task, TaskComment

clinic = Business.objects.create(owner=owner, name='CRM Acceptance Clinic', slug='crm-acceptance', timezone='Asia/Almaty')
patient = Client.objects.create(business=clinic, full_name='CRM Patient', phone='+77001234567', notes='Patient detail note')
for index in range(23):
    Client.objects.create(business=clinic, full_name=f'Page patient {index:02}', phone=f'+7700000{index:04}')
Client.objects.create(business=clinic, full_name='Archived patient', is_archived=True)
lead = Lead.objects.create(business=clinic, client=patient, message='Consultation request', responsible_user=owner)
pipeline = Pipeline.objects.create(business=clinic, name='Consultations', slug='consultations')
stage = PipelineStage.objects.create(business=clinic, pipeline=pipeline, name='Initial contact')
deal = Deal.objects.create(business=clinic, client=patient, lead=lead, pipeline=pipeline, stage=stage, title='Consultation deal', amount='15000.00', currency='KZT')
service = Service.objects.create(business=clinic, name='Consultation')
visit = Appointment.objects.create(business=clinic, client=patient, lead=lead, service=service, start_at=now, end_at=now+timezone.timedelta(hours=1), booked_price='15000.00')
task = Task.objects.create(business=clinic, title='Call CRM patient', client=patient, deal=deal, appointment=visit, assignee=owner)
TaskComment.objects.create(task=task, author=owner, text='Patient call comment')
bot = Bot.objects.create(business=clinic, name='Reception assistant')
BotChannel.objects.create(bot=bot, channel='website', status='active', config_json={'secret':'DO_NOT_RENDER_CREDENTIAL'})
conversation = BotConversation.objects.create(business=clinic, bot=bot, client=patient, channel='website', unread_count=23)
for index in range(23):
    BotMessage.objects.create(conversation=conversation, direction='inbound', text=f'Patient message {index:02}', payload_json={'token':'DO_NOT_RENDER_CREDENTIAL'})
Payment.objects.create(business=clinic, client=patient, deal=deal, kind='receipt', amount='15000.00', currency='KZT', method='cash', occurred_at=now, submission_id=uuid.uuid4())
BusinessConnector.objects.create(business=clinic, name='CRM website', provider='website', status='connected', config_json={'token':'DO_NOT_RENDER_CREDENTIAL'}, connected_at=now)
definition = CustomFieldDefinition.objects.create(business=clinic, entity_type='client', key='preferred_time', label='Preferred time')
CustomFieldValue.objects.create(business=clinic, definition=definition, entity_type='client', entity_id=str(patient.pk), value_json={'value':'Morning'})
Note.objects.create(business=clinic, client=patient, author=owner, text='CRM patient note')
ActivityEvent.objects.create(business=clinic, client=patient, event_type='client.created', text='Client registered')
tag = Tag.objects.create(business=clinic, name='Follow up')
TaggedObject.objects.create(business=clinic, tag=tag, entity_type='client', entity_id=str(patient.pk))
create_case(actor=staff, business_id=clinic.pk, subject='CRM clinic support', text='Check CRM records', idempotency_key='clinic-crm-browser-support', platform=True)
