import hashlib
import html
import io
import json
import zipfile

from django.db import transaction
from rest_framework.exceptions import ValidationError
from .document_content import read_document_revision
from .issuance_portal import session_grant, final_item
from .issuance_services import grant_event
from .signing_services import _material

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


@transaction.atomic
def portal_archive(*, business_slug, token):
    grant, _ = session_grant(business_slug, token)
    items = list(grant.items.select_related("version__document", "finalization__artifact__attachment",
        "finalization__version__document").order_by("pk"))
    artifacts = [final_item(item).artifact for item in items]
    if not items or len(items) > 20 or sum(artifact.attachment.size for artifact in artifacts) > MAX_ARCHIVE_BYTES:
        raise ValidationError({"archive": "Download the documents individually; this package exceeds the archive limit."})
    manifest = {"schema": 1, "kind": "issued-document-package", "documents": []}
    links = []
    total = 0
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for item, artifact in zip(items, artifacts):
            content = _material(artifact)
            total += len(content)
            if total > MAX_ARCHIVE_BYTES:
                raise ValidationError({"archive": "Download the documents individually; this package exceeds the archive limit."})
            snapshot = read_document_revision(item.version)
            title = snapshot["template"]["title"]
            name = f"documents/{item.public_id}.pdf"
            archive.writestr(name, content)
            manifest["documents"].append({"id": str(item.public_id), "path": name, "title": title,
                "revision": item.version.revision, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
            links.append(f'<li><a href="{name}">{html.escape(title)}</a> · {item.version.revision}</li>')
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        archive.writestr("index.html", ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;">'
            '<title>Документы / Құжаттар / Documents</title></head><body>'
            '<h1>Документы / Құжаттар / Documents</h1><ul>' + "".join(links) +
            '</ul><p><a href="manifest.json">JSON · SHA-256</a></p></body></html>').encode("utf-8"))
    # Expiry can occur while reading private storage; no partial archive is returned.
    session_grant(business_slug, token)
    for item in items:
        grant_event(grant, "downloaded", version=item.version)
    return output.getvalue()
