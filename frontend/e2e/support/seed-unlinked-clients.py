"""Synthetic conversations for the unlinked inspector, disposable runtime only."""
from pathlib import Path
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.browser_test_runtime import configure_browser_runtime

configure_browser_runtime()
import django

django.setup()

from django.utils import timezone
from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation, BotMessage

owner = User.objects.get(email="business_owner@example.com")
bot = Bot.objects.filter(business__owner=owner).first()
assert bot is not None
result = {}
for kind in ("create", "link", "states"):
    conversation = BotConversation.objects.create(
        business=bot.business, bot=bot, channel="whatsapp", bot_enabled=False,
        external_user_id=f"Inspector {kind} {uuid.uuid4().hex[:8]}",
        assigned_to=owner, last_message_at=timezone.now(), last_inbound_at=timezone.now(),
    )
    BotMessage.objects.create(conversation=conversation, direction="inbound",
                              sender_type="client", text="Please contact me tomorrow.", status="received")
    result[kind] = conversation.id
print(json.dumps(result))
