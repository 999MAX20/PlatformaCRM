"""Synthetic outbox for the isolated ADMIN-03 browser gate; never live delivery."""
import json
import os
import tempfile
import uuid
from pathlib import Path

from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def send_messages(self, messages):
        database = os.environ.get("DATABASE_URL", "")
        assert os.environ.get("ZANI_QUALITY_GATE") == "1" and os.environ.get("E2E_PLATFORM_RECOVERY") == "1"
        assert database.startswith("sqlite:///")
        path = Path(database.removeprefix("sqlite:///")).resolve()
        assert path.name == "gate.sqlite3" and path.parent.name.startswith("zani-quality-gate-")
        assert path.is_relative_to(Path(tempfile.gettempdir()).resolve())
        folder = path.parent / "recovery-mail"
        folder.mkdir(exist_ok=True)
        for message in messages:
            assert all(address.endswith("@example.com") for address in message.to)
            (folder / f"{uuid.uuid4()}.json").write_text(json.dumps({"to": message.to, "body": message.body}), encoding="utf-8")
        return len(messages)
