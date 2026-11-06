from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.bots.models import BotMessage, BotChannel
from apps.core.models import AuditLog
from apps.integrations.models import BusinessConnector, ConnectorSyncRun

TASK = "DELIVERY-SYNC-20261106"

@transaction.atomic
def resolve():
    messages = list(BotMessage.objects.select_for_update().filter(pk__in=[29, 30, 36]).order_by('pk'))
    connector = BusinessConnector.objects.select_for_update().get(pk=4)
    run = ConnectorSyncRun.objects.select_for_update().get(pk=9)
    if [m.pk for m in messages] != [29, 30, 36]:
        raise CommandError('Expected stand messages are missing.')
    entities = [*messages, connector, run]
    targets = ['cancelled'] * 3 + ['deferred', 'deferred']
    if all(obj.status == status for obj, status in zip(entities, targets)):
        if AuditLog.objects.filter(metadata__task=TASK).count() != 5:
            raise CommandError('Resolved rows have no complete resolution audit.')
        return False
    if any(m.status != 'failed' or m.conversation.business_id != 2 or
           m.conversation.bot_id != 13 or m.conversation.channel != 'website' or
           m.direction != 'outbound' or m.external_message_id or m.sent_at or m.delivered_at or
           m.delivery_locked_at or m.delivery_next_retry_at or
           m.error_text != 'Channel provider is not connected.' for m in messages):
        raise CommandError('Messages changed or have an uncertain delivery outcome.')
    if BotChannel.objects.filter(bot_id=13).exists():
        raise CommandError('A provider was connected; reconcile delivery before cancelling.')
    if (connector.business_id != 2 or connector.provider != '1c' or
        connector.status != 'needs_attention' or connector.credentials.exists() or
        run.connector_id != 4 or run.business_id != 2 or run.status != 'failed' or
        run.mode != 'healthcheck' or run.events_received or run.events_processed):
        raise CommandError('Connector state changed; refusing resolution.')
    for obj, target in zip(entities, targets):
        previous = obj.status
        metadata = {'task': TASK, 'event': 'owner_authorized_historical_resolution',
                    'from_status': previous, 'to_status': target,
                    'reason': 'Owner approved cancellation of stale test sends and deferral of unconfigured 1C; original errors retained.'}
        fields = ['status']
        if obj is connector:
            metadata['previous_next_sync_at'] = str(connector.next_sync_at) if connector.next_sync_at else None
            connector.next_sync_at = None
            fields.append('next_sync_at')
        obj.status = target
        obj.save(update_fields=fields)
        AuditLog.objects.create(business_id=2, action='update', category='system', risk_level='low',
                                entity_type=obj._meta.label, entity_id=str(obj.pk), metadata=metadata)
    return True

class Command(BaseCommand):
    help = 'Apply the owner-approved resolution of five historical stand records; never sends messages.'

    def handle(self, *args, **options):
        self.stdout.write('Applied' if resolve() else 'Already applied; no changes')
