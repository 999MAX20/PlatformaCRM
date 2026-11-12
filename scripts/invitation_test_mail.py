"""Local outbox for the explicitly isolated invitation browser runner."""
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def send_messages(self, messages):
        url = os.environ.get("DATABASE_URL", "")
        assert os.environ.get("ZANI_QUALITY_GATE") == "1" and url.startswith("sqlite:///")
        database = Path(url.removeprefix("sqlite:///")).resolve()
        assert database.name == "gate.sqlite3" and database.parent.name.startswith("zani-quality-gate-")
        assert database.parent.parent == Path(tempfile.gettempdir()).resolve()
        folder = database.parent / "invitations-mail"
        folder.mkdir(exist_ok=True)
        if (folder / "fail").exists():
            raise OSError("Synthetic email outage")
        for message in messages:
            assert all(address.endswith(("@example.com", "@example.invalid")) for address in message.to)
            (folder / f"{uuid4()}.json").write_text(json.dumps({"to": message.to, "subject": message.subject, "body": message.body}), encoding="utf-8")
        return len(messages)
