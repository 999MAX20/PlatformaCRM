# Security Review: PlatformaCRM

## Scope

The scan was configured for the include paths and exclusions listed below.

- Scan mode: deep_repository
- Target kind: git_worktree
- Target ID: target_sha256_7e2f38411c6cb6d0c9572f1dc975372f1e7dc8831553245e1594a77f40befd37
- Revision: df2b9708401a3075e590b3e5e97bc5369383c34a
- Snapshot digest: codex-security-snapshot/v1:sha256:230fd7f877f6e3107caa575f3753bc767d91a70bab6b85ca6597845c29f1eda3
- Inventory strategy: repository
- Included paths: .
- Excluded paths: none

### Scan Summary

| Field | Value |
| --- | --- |
| Scan outcome | canceled |
| Reportable DSS findings | 36 |
| Report instances | 36 |
| Report severity mix | medium: 19, low: 17 |
| Report confidence mix | high: 35, medium: 1 |
| Coverage | partial |
| Validation mode | not recorded |

Canonical artifacts: `scan-manifest.json`, `findings.json`, and `coverage.json`. This report is a deterministic projection of those files.

## Threat Model

PlatformaCRM is a multi-tenant React/Django REST CRM with tenant records, scheduling, messaging, file upload/import/export, AI tools, integrations and platform administration (config/urls.py:133,182,200). Docker runs migrations, collectstatic and Gunicorn; Compose adds PostgreSQL, Redis, Celery and ClamAV (Dockerfile:19; docker-compose.yml:1-145). The Render blueprint is an example, not deployment evidence. Model generated from an independent architecture review and parent checks; mapping alone is not completed source-audit coverage.

### Assets

- Tenant CRM records and linked entities; business membership and resource/record-scoped permissions protect ownership (apps/core/permissions.py:25; apps/core/viewsets.py:138,215).
- User identity, access JWTs, HttpOnly refresh cookies, device sessions and auth epochs (config/settings.py:263; apps/accounts/authentication.py:12; apps/accounts/auth_views.py:23).
- Attachments stored as private/attachments/business-{id}/{uuid}{ext} under default storage, with scan state and digest-verified byte snapshots (apps/core/models.py:20,183; apps/core/file_scanning.py:88).
- Avatar originals are transient; normalized fresh 256x256 JPEG is stored as UserAvatar database binary (apps/accounts/avatars.py:23-61).
- Imports and export results are default-storage FileFields with imports/YYYY/MM/DD and exports/YYYY/MM/DD keys (apps/core/models.py:301,344).
- Connector AES-GCM envelopes and separately provisioned encryption keys; database and broker authority; audit records (apps/integrations/credential_encryption.py:42; config/settings.py:44,69,174,315).
- Distinct platform-support grants, AI approvals, scoped API tokens and outbound provider authority (apps/core/permissions.py:10; apps/ai_core/crm_approval.py:9; apps/integrations/views.py:426).

### Trust Boundaries

- Browser/API -\> Django: JWT and IsAuthenticated defaults; independent CORS/CSRF/security middleware; public endpoint overrides. Middleware alone does not protect CSRF-exempt DRF views (config/settings.py:142-151,261-268).
- User -\> tenant: ownership, active membership and unexpired support grants form accessible_businesses; global platform-admin access depends on SUPPORT_REQUIRES_GRANT; querysets and mutations apply separate policy (apps/core/permissions.py:10-52; apps/core/viewsets.py:130-235).
- Caller -\> attachment: target entity resolved inside business, UPDATE for upload and VIEW for download; quota and scanner checks independent (apps/core/file_attachments.py:23; apps/core/file_attachment_views.py:48,75).
- Untrusted bytes -\> parsers: extension/MIME/size/signature checks, tokenized scan leases, clean-only release, immutable size/hash-checked snapshot; avatar byte/pixel/frame limits and re-encoding (apps/core/file_validation.py:28; apps/core/file_scanning.py:35,88; apps/accounts/avatars.py:23).
- Backend -\> storage: local writes use MEDIA_ROOT/private/attachments; legacy local route checks PRIVATE_MEDIA_ROOT/path then opens FileField storage; S3 disables that route. Host/bucket policy must prevent direct-access bypass (config/settings.py:194-195,233-257; apps/core/file_views.py:19-46).
- Web/workers -\> Redis/ClamAV: queue names route jobs but do not isolate equal-privilege processes sharing environment and media. Scanner is unauthenticated internal INSTREAM with no published scanner port (docker-compose.yml:30-114; config/settings.py:315-327).
- External API client -\> public clients API: separate bearer token scope clients:read and token.business filter; token issuance/rotation stores hashes and returns raw value once (apps/integrations/views.py:431,445,521).
- Webhook destination -\> transport: address filtering, pinned TLS, bounded redirects and per-hop validation belong to webhook transport; provider adapters require separate review (apps/integrations/webhooks.py:25-167).
- AI proposal -\> execution: locked approval binds business, log, requester, action type and fingerprint, status/expiry and current approver permission; mutation paths for that approval must preserve binding (apps/ai_core/crm_approval.py:9-23).
- Operator -\> deployment: startup holds database schema and environment credential authority (Dockerfile:19; config/settings.py:37).

### Attacker Capabilities

- Unauthenticated callers can submit public login/intake/webhook/API requests when deployed publicly; no assumed filesystem, database, broker or signing-key access.
- Authenticated tenant members control permitted form fields, filenames/MIME/bytes and record identifiers, but not unrelated businesses or objects outside their role scope.
- Integration managers can configure permitted outbound destinations; internal-network access is not an intended webhook capability.
- Provider payloads and AI-generated content are untrusted. Provider secrets, API tokens and approval artifacts grant distinct limited capabilities.
- Runtime environment, mount and key-file operators already have privileged deployment authority; require a lower-privilege boundary before claiming additional security impact.

### Security Objectives

- Enforce tenant/record/linked-resource authorization consistently across API, bulk operations, exports and jobs.
- Reject revoked identities and independently enforce support grants, API scopes and exact AI command approval.
- Fail closed on scanning; serve the exact scanned bytes only to currently authorized users; do not persist avatar originals.
- Bound file/archive/image/tabular decoding and shared-resource consumption; default attachment maximum 10 MiB, avatar 5 MiB/16 million pixels/one frame, separate import/export/report bounds (config/settings.py:198-209; apps/accounts/avatars.py:13-14).
- Keep provider credentials and encryption key material confidential, and redact errors.
- Constrain outbound HTTP targets and bind approved input to actual side effect.
- User-context priorities: SQL injection; HTTP/API/session/CSRF/SSRF; attachments/avatars, active content, MIME/origin/storage/download protection. These priorities are not findings.

### Assumptions

- No supplied authoritative model or knowledge-base location; no tracked SECURITY.md found and policy helper emitted no output. Current-source review is offline and read-only.
- Actual deployed environment, bucket ACL, reverse proxy, firewall and provider configuration remain unknown; source defaults do not establish actual exposure.
- PRIVATE_MEDIA_ROOT independently defaults to BASE_DIR/media/private rather than deriving from overridden MEDIA_ROOT. Defaults coincide but custom values may diverge; this is a configuration discrepancy, not demonstrated disclosure (config/settings.py:194-195; apps/core/file_views.py:24).
- Operational contract requires file_scans worker and periodic due processing. Compose has celery-files and profile-gated beat; older Render example omits file worker; chosen deployment completeness is unverified (docs/current/operations.md:147; docker-compose.yml:70,97; deploy/render.h1.example.yaml:63).
- Compose publishes PostgreSQL 5432 and Redis 6379 without loopback-specific binding; scanner port is unpublished. Internet reachability depends on host networking/firewall (docker-compose.yml:92,124,137).
- Production/staging default to secure cookies, SSL redirect, required support grants and privileged MFA; development differs (config/settings.py:301-306,360-373).
- Machine-local development key mode 0600/chmod is not proof of effective Windows ACL confidentiality (config/local_connector_keys.py:23-29,45).
- Architecture mapping does not prove full endpoint/ORM/provider/backup/deployment coverage or executed tests.
- Effective DB resource: DATABASE_URL wins, then Supabase-derived URL with sslmode=require, otherwise BASE_DIR/db.sqlite3 (local C:/Users/user/Desktop/PlatformaCRM/db.sqlite3; Docker /app/db.sqlite3). Web, workers and management share configured DB authority; Compose postgres_data mounts /var/lib/postgresql/data (config/settings.py:69-98,174; Dockerfile:6; docker-compose.yml:116-123).
- Effective broker/results: REDIS_URL defaults redis://redis:6379/0; same URL for both; redis_data:/data, host port 6379. Network access governs producers/consumers, queue routing is not authorization (config/settings.py:315-318; docker-compose.yml:132-137).
- Effective local attachment bytes: C:/Users/user/Desktop/PlatformaCRM/media/private/attachments/business-{id}/{uuid}{ext}, or /app/media/private/attachments/... on Compose media_data. Web/file worker recipients use default storage; current entity/scanner/digest controls enforce API access (config/settings.py:194; apps/core/models.py:20,183; docker-compose.yml:100; apps/core/file_scanning.py:88).
- Effective legacy route: default PRIVATE_MEDIA_ROOT/{relative-path}, local media/private or Docker /app/media/private, then matching attachment and storage snapshot. safe_join, current entity auth and clean state apply; USE_S3 disables route (apps/core/file_views.py:19-46).
- Effective S3 storage: configured bucket with private/attachments/business-{id}/{uuid}{ext}, imports/YYYY/MM/DD/... and exports/YYYY/MM/DD/...; defaults querystring_auth=true, ACL=null, overwrite=false. App processes and storage service receive bytes; external bucket access/origin policies remain prerequisites (config/settings.py:233-257; apps/core/models.py:301,344).
- Effective avatar resource: UserAvatar DB binary, fresh 256x256 JPEG \<=128 KiB; own account API/database are recipients, original input not persisted (apps/accounts/avatar_views.py:24; apps/accounts/avatars.py:23-61).
- Effective scanner: Compose web/file worker CLAMD_HOST/PORT -\> clamav:3310; clamav_data:/var/lib/clamav and deploy/clamav/clamd.conf read-only. No published port, daemon resource limits and application timeout/clean-only release (docker-compose.yml:86-104; config/settings.py:199-203).
- Effective connector key resource: explicit CONNECTOR_CREDENTIAL_LOCAL_KEY_FILE, else %LOCALAPPDATA%/Zani/connector-credential-key.json, else ~/.zani/connector-credential-key.json, only in development without env keys. Exclusive mode 0600 creation/chmod; same host user recipients, Windows ACL unknown. Production/staging requires environment keyring/active ID without automatic local fallback (config/local_connector_keys.py:23-51; config/settings.py:44-55; apps/integrations/credential_encryption.py:42).

## Findings

| Findings | Reports | Severity | Confidence | Detailed write-up |
| --- | --- | --- | --- | --- |
| Anonymous intake can reverse an existing client's WhatsApp opt-out | [occ_04f5c787d4121c7886790cd8](#finding-1) | medium | high | occ_04f5c787d4121c7886790cd8: inline below |
| Import files accumulate outside aggregate storage quotas | [occ_197579e53e33314971a1c68f](#finding-2) | medium | high | occ_197579e53e33314971a1c68f: inline below |
| Repeated imports bypass tenant storage quotas and retain failed uploads | [occ_1b071c6064ba9151ec05a367](#finding-3) | medium | high | occ_1b071c6064ba9151ec05a367: inline below |
| Sparse spreadsheets exhaust import resources before the row limit runs (AUD-22) | [occ_1cf421c05f945504b33f3448](#finding-4) | medium | high | occ_1cf421c05f945504b33f3448: inline below |
| Ordinary members can hard-delete an unprotected business | [tenant-hard-delete](#finding-5) | medium | high | tenant-hard-delete: inline below |
| XLSX imports allocate the worksheet before enforcing limits | [occ_24be2d8e48228bcce413ff75](#finding-6) | medium | high | occ_24be2d8e48228bcce413ff75: inline below |
| Read-only team viewers can claim privileged invitations | [occ_2dd8587c6f5e60bf59af9294](#finding-7) | medium | high | occ_2dd8587c6f5e60bf59af9294: inline below |
| Password reset leaves earlier MFA enrollment authority valid | [occ_4267614dd150cb8442f2bf1f](#finding-8) | medium | high | occ_4267614dd150cb8442f2bf1f: inline below |
| Spoofed forwarded headers bypass anonymous rate limits | [occ_547c861428bb44cc474251c9](#finding-9) | medium | high | occ_547c861428bb44cc474251c9: inline below |
| Saved exports remain downloadable after record access is narrowed (AUD-18) | [occ_5d8d1f17f3bd85a0990b45ab](#finding-10) | medium | high | occ_5d8d1f17f3bd85a0990b45ab: inline below |
| Lead duplicate lookup bypasses record permissions and support grants | [occ_6a6ee988289b65ada536d8ef](#finding-11) | medium | high | occ_6a6ee988289b65ada536d8ef: inline below |
| Anonymous forms and chat can reverse another client’s opt-out | [anonymous-consent-overwrite](#finding-12) | medium | high | anonymous-consent-overwrite: inline below |
| A pending MFA enrollment can restore attacker access after password reset | [occ_7e9c25d332d60df168a3fc9b](#finding-13) | medium | high | occ_7e9c25d332d60df168a3fc9b: inline below |
| Multipart file bytes reach temporary storage before upload limits | [occ_81f9365d46499f6ef788a474](#finding-14) | medium | high | occ_81f9365d46499f6ef788a474: inline below |
| AUD-22: XLSX allocation precedes row and expansion limits | [occ_89d730bd7a12ece1792e2071](#finding-15) | medium | high | occ_89d730bd7a12ece1792e2071: inline below |
| Ordinary business members can invoke tenant deletion | [occ_960615f550e02ad327da57e0](#finding-16) | medium | high | occ_960615f550e02ad327da57e0: inline below |
| XLSX imports expand worksheets before enforcing row limits (AUD-22) | [occ_9c007e5853e270fef0c99341](#finding-17) | medium | high | occ_9c007e5853e270fef0c99341: inline below |
| Team readers receive invitation tokens that can grant administrator access | [occ_ae55d7617a5d226dc6a9584e](#finding-18) | medium | high | occ_ae55d7617a5d226dc6a9584e: inline below |
| Ordinary members can delete businesses that lack protective dependent records | [occ_ba9bc7724dc11a5f76ed8497](#finding-19) | medium | high | occ_ba9bc7724dc11a5f76ed8497: inline below |
| An approved AI request can be reused for a different command | [mutable-approval-snapshot](#finding-20) | low | high | mutable-approval-snapshot: inline below |
| Concurrent attachment uploads exceed the storage entitlement | [occ_06666827ccc23fffbbc2d70a](#finding-21) | low | high | occ_06666827ccc23fffbbc2d70a: inline below |
| Public lead forms disclose whether a contact is already a client | [occ_4169fe2718ad1197a9429aba](#finding-22) | low | high | occ_4169fe2718ad1197a9429aba: inline below |
| Changing X-Forwarded-For bypasses anonymous authentication rate limits | [occ_48c86cf0ab076b2c4a59e7e3](#finding-23) | low | high | occ_48c86cf0ab076b2c4a59e7e3: inline below |
| Mark-all-read changes notifications outside the caller's UPDATE scope (AUD-17) | [occ_4bb7fad8e08e1bb2bc8f9903](#finding-24) | low | high | occ_4bb7fad8e08e1bb2bc8f9903: inline below |
| Import previews disclose clients outside read permissions | [import-duplicate-disclosure](#finding-25) | low | high | import-duplicate-disclosure: inline below |
| Merchant settings can clear a platform business restriction | [occ_5d351da902fc7ab9c96f1469](#finding-26) | low | high | occ_5d351da902fc7ab9c96f1469: inline below |
| Social login retains an attacker’s pre-registered password when MFA is optional | [occ_629f030a17567c796f83c10d](#finding-27) | low | high | occ_629f030a17567c796f83c10d: inline below |
| Imports modify existing clients without client UPDATE permission | [occ_82aa4f025f358ed35672b437](#finding-28) | low | high | occ_82aa4f025f358ed35672b437: inline below |
| Bulk read action modifies notifications outside the caller’s update scope | [occ_82d11dc86c5d075bf0ff375b](#finding-29) | low | high | occ_82d11dc86c5d075bf0ff375b: inline below |
| Cross-origin login can seed another account’s refresh cookie | [occ_9eaf08ecdb7550098abcf5ae](#finding-30) | low | medium | occ_9eaf08ecdb7550098abcf5ae: inline below |
| Cross-site login can restore the browser into an attacker-controlled account | [occ_a38028cf16ecb2b9db119d40](#finding-31) | low | high | occ_a38028cf16ecb2b9db119d40: inline below |
| Password-change MFA verification lacks a failed-attempt budget | [occ_a6b30047182b8fa22e562f14](#finding-32) | low | high | occ_a6b30047182b8fa22e562f14: inline below |
| Public intake responses expose private CRM identity relationships | [public-intake-identities](#finding-33) | low | high | public-intake-identities: inline below |
| Imports update existing clients without client update permission | [import-client-mutation](#finding-34) | low | high | import-client-mutation: inline below |
| Cached exports disclose rows after permissions are narrowed | [occ_ef1337d6e481c76e5ebb720c](#finding-35) | low | high | occ_ef1337d6e481c76e5ebb720c: inline below |
| Password changes accept unlimited MFA guesses | [password-change-mfa](#finding-36) | low | high | password-change-mfa: inline below |

### Confidence Scale

| Label | Meaning |
| --- | --- |
| high | Direct evidence supports the finding with no material unresolved blocker. |
| medium | Evidence supports a plausible issue, but material runtime or reachability proof remains. |
| low | Evidence is incomplete and the item is retained only for explicit follow-up. |

<a id="finding-1"></a>

### [1] Anonymous intake can reverse an existing client's WhatsApp opt-out

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Both public paths call an unconditional OPTED_IN upsert; the campaign gate trusts that state. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | apps/leads/forms_service.py:63-95, apps/bots/serializers.py:382-402, apps/outreach/services.py:138-152, apps/outreach/services.py:88-94, apps/leads/views.py:508-524, apps/bots/views.py:332-342 |

#### Summary

A public form or website-chat visitor can match an existing client by email or phone and set a consent checkbox, overwriting that client's recorded WhatsApp opt-out without proving control of the destination.

#### Root Cause

Anonymous contact matching selects an existing client, but input consent is treated as authenticated authority over that client. Both form and chat paths call the same unconditional upsert, which clears opt-out state. Matching by email allows an arbitrary nonempty submitted phone to satisfy the gate without knowing the client's actual WhatsApp number.

**Public intake writes existing client's consent** — `apps/leads/forms_service.py:88`

The client was selected by supplied email OR phone. Any nonempty submitted phone and truthy consent field triggers the protected write.

```
        if phone and payload_has_explicit_consent(payload, channel=OutreachCampaign.Channels.WHATSAPP):
            record_explicit_consent(
                client=client,
                channel=OutreachCampaign.Channels.WHATSAPP,
                source="lead_form",
```

**Website chat repeats the same write** — `apps/bots/serializers.py:382`

Existing-client profile protection does not cover the separate consent mutation.

```
        if client is not None and phone and payload_has_explicit_consent(validated_data, channel=OutreachCampaign.Channels.WHATSAPP):
            record_explicit_consent(
                client=client,
                channel=OutreachCampaign.Channels.WHATSAPP,
                source="website_chat",
```

**Existing opt-out overwritten** — `apps/outreach/services.py:140`

An existing opt-out is replaced and its opt-out timestamp cleared without a verified identity/channel transition.

```
    return OutreachConsent.objects.update_or_create(
        business=client.business,
        client=client,
        channel=channel,
        defaults={
            "status": OutreachConsent.Statuses.OPTED_IN,
            "source": source,
            "note": note,
            "evidence_json": evidence or {},
            "opted_in_at": now,
            "opted_out_at": None,
        },
    )[0]
```

**Campaign trusts modified consent** — `apps/outreach/services.py:88`

The forged state changes downstream recipient eligibility.

```
def can_receive_campaign(client, campaign):
    consent = consent_for_client(client, campaign.channel)
    if consent and consent.status == OutreachConsent.Statuses.OPTED_OUT:
        return False, OPTED_OUT_REASON
    if campaign.require_opt_in and (not consent or consent.status != OutreachConsent.Statuses.OPTED_IN):
        return False, OPT_IN_REQUIRED_REASON
    return True, ""
```

#### Validation

Verified AllowAny public routes, email/phone client matching, permissive consent parsing, unconditional state overwrite and subsequent campaign eligibility consumer.

Validation method: independent static source trace

Counterevidence and remaining uncertainty:
- Public throttles and active form/channel requirements apply.
- No marketing message is sent merely by this write; a later eligible campaign/provider configuration is required.
- The website chat intentionally preserves existing profile fields, but not consent.

Limitations:
- No runtime campaign or external message was sent.

#### Dataflow

Public chosen email/phone + consent -\> existing client match -\> OPTED_IN upsert clearing opt-out -\> campaign gate allows recipient.

#### Reachability

Anonymous caller knowing active form/chat ID and one existing contact identifier; required form fields and any nonempty phone must be supplied.

#### Severity

**Medium** — An unauthenticated visitor with a published intake ID and known contact can directly change a protected consent decision. Impact is consent integrity and unwanted marketing eligibility, not account takeover.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Store anonymous consent as an unverified assertion. Preserve existing opt-outs until destination-bound confirmation or an authorized staff action, binding proof to client, channel and exact destination.

Tests:
- Existing opted-out client remains opted out after anonymous matching-email submission with a different phone and consent=true.
- Cover both public form and website-chat paths.

<a id="finding-2"></a>

### [2] Import files accumulate outside aggregate storage quotas

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Save-before-preview, failure retention, storage accounting and absence of source-level import cleanup were checked. Live storage/retention is unknown. |
| Category | Unbounded persistent resource allocation |
| CWE | CWE-770 |
| Affected lines | apps/core/import_export_views.py:46-62, apps/billing/storage.py:19-25, apps/core/models.py:298-313 |

#### Summary

An authorized importer can repeatedly save CSV/XLSX source files without an aggregate storage check. Files are persisted before preview/AV parsing; failed previews retain them. Storage accounting sums only FileAttachment bytes, so these retained imports never consume the tenant's storage entitlement.

#### Root Cause

The persistent import consumer bypasses aggregate admission/accounting and has no observed lifecycle retention cleanup.

**Source persists before preview and stays after failure** — `apps/core/import_export_views.py:52-62`

Each accepted-size upload allocates storage even when AV/preview later rejects it; the failure branch does not delete source bytes.

```
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
except Exception as exc:
    job.status = ImportJob.Statuses.FAILED
    job.error = sanitize_error_text(exc)
    job.save(update_fields=["status", "error", "updated_at"])
    mark_excel_csv_import_failed(job, exc)
    raise
```

**Import source is durable default storage** — `apps/core/models.py:298-301`

Uploads persist in filesystem/S3 default storage, not a temporary parsing buffer.

```
business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="import_jobs")
actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="import_jobs")
entity_type = models.CharField(max_length=32, choices=EntityTypes.choices, default=EntityTypes.CLIENTS)
source_file = models.FileField(upload_to="imports/%Y/%m/%d/")
```

**Storage quota counts attachments only** — `apps/billing/storage.py:19-25`

ImportJob.source_file allocations are absent from the aggregate, independent of concurrent upload races.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

#### Validation

Verified import route CREATE/module authorization, per-file validation and durable source save. Core tasks/lifecycle searches found no import source pruning. Same root does not depend on AV accepting malware: ordinary valid CSV files suffice.

Validation method: Offline static trace and cleanup search

**Source persists before preview and stays after failure** — `apps/core/import_export_views.py:52-62`

Each accepted-size upload allocates storage even when AV/preview later rejects it; the failure branch does not delete source bytes.

```
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
except Exception as exc:
    job.status = ImportJob.Statuses.FAILED
    job.error = sanitize_error_text(exc)
    job.save(update_fields=["status", "error", "updated_at"])
    mark_excel_csv_import_failed(job, exc)
    raise
```

**Import source is durable default storage** — `apps/core/models.py:298-301`

Uploads persist in filesystem/S3 default storage, not a temporary parsing buffer.

```
business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="import_jobs")
actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="import_jobs")
entity_type = models.CharField(max_length=32, choices=EntityTypes.choices, default=EntityTypes.CLIENTS)
source_file = models.FileField(upload_to="imports/%Y/%m/%d/")
```

**Storage quota counts attachments only** — `apps/billing/storage.py:19-25`

ImportJob.source_file allocations are absent from the aggregate, independent of concurrent upload races.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

Counterevidence and remaining uncertainty:
- Per-file byte/type/signature limits and authenticated import permission remain.
- External infrastructure quotas and retention were not inspected.
- Export retention has related accounting concerns but is not asserted as a fully validated separate attack in this finding.

#### Dataflow

Repeated authorized CSV/XLSX POST -\> validate individual size -\> source_file save -\> preview success/failure -\> retained object uncounted by storage quota.

**Source persists before preview and stays after failure** — `apps/core/import_export_views.py:52-62`

Each accepted-size upload allocates storage even when AV/preview later rejects it; the failure branch does not delete source bytes.

```
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
except Exception as exc:
    job.status = ImportJob.Statuses.FAILED
    job.error = sanitize_error_text(exc)
    job.save(update_fields=["status", "error", "updated_at"])
    mark_excel_csv_import_failed(job, exc)
    raise
```

**Storage quota counts attachments only** — `apps/billing/storage.py:19-25`

ImportJob.source_file allocations are absent from the aggregate, independent of concurrent upload races.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

#### Reachability

Tenant member with import CREATE can repeat uploads; no prerequisite of concurrency or malicious active file content.

#### Severity

**Medium** — Repeated tenant-controlled durable writes can consume shared disk or object-storage capacity/cost. High availability impact is conditional on deployment capacity and external retention, so likelihood and final severity are medium.

An enforced external per-tenant quota/short retention would reduce impact; confirmed shared-volume exhaustion would strengthen it.

#### Remediation

Include retained import sources in atomic tenant storage reservations, delete failed uploads where safe, and enforce bounded retention for completed/failed jobs. Reconcile object cleanup with database transactions.

Tests:
- At tenant quota, valid imports and preview-failed imports must not allocate extra persistent storage.
- Retention cleanup must remove objects and release accounted bytes safely.

<a id="finding-3"></a>

### [3] Repeated imports bypass tenant storage quotas and retain failed uploads

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Verified complete import view, shared quota aggregate, persistent FileField and failure handling; cleanup search found no application source-file retention task. |
| Category | Missing persistent storage resource limit |
| CWE | CWE-770 |
| Affected lines | apps/core/import_export_views.py:44-61, apps/billing/storage.py:19-25, apps/core/models.py:301 |

#### Summary

An authenticated tenant import creator can repeatedly upload individually allowed files through `/api/import-jobs/`. The endpoint stores each source without a quota reservation, and storage accounting counts only attachments. Failed previews retain their source files. Sequential requests therefore accumulate persistent bytes beyond the tenant's storage allowance.

#### Root Cause

Import creation validates role, capability and individual file size/type, then calls serializer.save before parsing. The storage quota helper is never invoked there and the quota aggregate has no ImportJob input. Preview exceptions update FAILED status without deleting the already-persisted file. Thus neither successful nor failed import sources reduce the tenant's available storage allowance.

**Import saves bytes before preview** — `apps/core/import_export_views.py:44-61`

An authorized creator persists source_file without storage accounting; error handling retains the failed job/source.

```
        return queryset.filter(actor=self.request.user) if not self.request.user.is_platform_user else queryset

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
        except Exception as exc:
            job.status = ImportJob.Statuses.FAILED
            job.error = sanitize_error_text(exc)
            job.save(update_fields=["status", "error", "updated_at"])
            mark_excel_csv_import_failed(job, exc)
```

**Import source uses persistent storage** — `apps/core/models.py:298-303`

The submitted source is a FileField in configured default storage, not a temporary preview buffer.

```
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="import_jobs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="import_jobs")
    entity_type = models.CharField(max_length=32, choices=EntityTypes.choices, default=EntityTypes.CLIENTS)
    source_file = models.FileField(upload_to="imports/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.UPLOADED)
```

**Storage usage counts only attachments** — `apps/billing/storage.py:19-25`

ImportJob bytes never contribute to the billed tenant storage aggregate.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

**Attachment writes check quota** — `apps/core/file_attachment_views.py:57-60`

The same tenant storage capacity is enforced for attachment writes, demonstrating the missing import guard.

```
        assert_can(self.request.user, business, resource, Actions.UPDATE, obj=entity)
        uploaded_file = serializer.validated_data["file"]
        assert_storage_quota_allows(business, getattr(uploaded_file, "size", 0) or 0)
        attachment = serializer.save(uploaded_by=self.request.user)
```

**Scan happens after persistence** — `apps/core/import_export.py:608-618`

Unavailability or rejection during scan occurs only after source_file has already been saved.

```
    # Scan and parse the same bounded bytes, including old jobs and confirmation.
    with (path.open("rb") if hasattr(path, "storage") else open(path, "rb")) as source:
        content = source.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("Import file exceeds the upload size limit.")
    try:
        result = scan_stream(BytesIO(content))
    except ScanUnavailable:
        raise TemporaryServiceFailure("File security check is temporarily unavailable. Retry later.") from None
    if not result.clean:
        raise ValidationError("File was blocked by the security check.")
```

#### Validation

Verified the inherited create path has no transaction/guard reserving import storage, ImportJob.source_file uses persistent storage, failed preview preserves bytes, and storage usage sums FileAttachment only. Searched apps/config/scripts for import cleanup/source_file deletion without a matching lifecycle implementation.

Validation method: Offline source trace and cleanup-reference search

**Import saves bytes before preview** — `apps/core/import_export_views.py:44-61`

An authorized creator persists source_file without storage accounting; error handling retains the failed job/source.

```
        return queryset.filter(actor=self.request.user) if not self.request.user.is_platform_user else queryset

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
        except Exception as exc:
            job.status = ImportJob.Statuses.FAILED
            job.error = sanitize_error_text(exc)
            job.save(update_fields=["status", "error", "updated_at"])
            mark_excel_csv_import_failed(job, exc)
```

**Import source uses persistent storage** — `apps/core/models.py:298-303`

The submitted source is a FileField in configured default storage, not a temporary preview buffer.

```
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="import_jobs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="import_jobs")
    entity_type = models.CharField(max_length=32, choices=EntityTypes.choices, default=EntityTypes.CLIENTS)
    source_file = models.FileField(upload_to="imports/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.UPLOADED)
```

**Storage usage counts only attachments** — `apps/billing/storage.py:19-25`

ImportJob bytes never contribute to the billed tenant storage aggregate.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

**Attachment writes check quota** — `apps/core/file_attachment_views.py:57-60`

The same tenant storage capacity is enforced for attachment writes, demonstrating the missing import guard.

```
        assert_can(self.request.user, business, resource, Actions.UPDATE, obj=entity)
        uploaded_file = serializer.validated_data["file"]
        assert_storage_quota_allows(business, getattr(uploaded_file, "size", 0) or 0)
        attachment = serializer.save(uploaded_by=self.request.user)
```

**Scan happens after persistence** — `apps/core/import_export.py:608-618`

Unavailability or rejection during scan occurs only after source_file has already been saved.

```
    # Scan and parse the same bounded bytes, including old jobs and confirmation.
    with (path.open("rb") if hasattr(path, "storage") else open(path, "rb")) as source:
        content = source.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("Import file exceeds the upload size limit.")
    try:
        result = scan_stream(BytesIO(content))
    except ScanUnavailable:
        raise TemporaryServiceFailure("File security check is temporarily unavailable. Retry later.") from None
    if not result.clean:
        raise ValidationError("File was blocked by the security check.")
```

Counterevidence and remaining uncertainty:
- Authentication, tenant/resource CREATE and capability checks apply.
- Each file has a default 10 MiB size cap; clean antivirus verdict is required for parsing, but does not undo prior allocation.
- External retention rules or operator cleanup may exist; none was inspected.

Limitations:
- No runtime exhaustion or real storage inspection.

#### Dataflow

Authorized import POST → per-file validation → persistent source_file.save → preview or failure → retained bytes excluded from tenant usage sum.

#### Reachability

Any tenant actor permitted to create the selected import resource can repeat uploads sequentially. A finite attachment quota does not stop these independent persistent allocations.

#### Severity

**Medium** — A tenant creator can consume shared disk/object storage and cost without concurrency or aggregate quota enforcement. Each request remains capped at 10 MiB by default and infrastructure storage/lifecycle limits are unknown, limiting the demonstrated impact to unbounded application-level accumulation.

An enforced storage lifecycle/cap covering imports would reduce impact; demonstrated shared storage exhaustion would increase impact confidence.

#### Remediation

Count and atomically reserve import source bytes in the tenant storage budget before writing; release failed reservations and implement source retention/deletion for completed, failed and cancelled imports.

Tests:
- Import upload at exhausted tenant storage must fail before persistent allocation.
- Repeated failed previews must not accumulate unaccounted source files.
- Import deletion/expiry must release exact recorded bytes.

<a id="finding-4"></a>

### [4] Sparse spreadsheets exhaust import resources before the row limit runs (AUD-22)

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Both application materialization and installed pinned openpyxl sparse-row generation were inspected; no malicious workbook was executed. |
| Category | Unbounded parser resource consumption |
| CWE | CWE-400 |
| Affected lines | apps/core/import_export.py:630-640, apps/core/import_export.py:621-626, apps/core/import_export.py:644-655, apps/core/import_export_views.py:44-55, .venv/Lib/site-packages/openpyxl/worksheet/_read_only.py:73-102 |

#### Summary

A tenant user with import CREATE permission can upload a small sparse XLSX with wide dimensions and a distant populated row. `read_tabular_file` collects the iterator and processes every virtual cell before checking `IMPORT_MAX_ROWS`, consuming shared web-worker memory/CPU. This confirms the existing AUD-22 mechanism rather than creating a second risk-register item.

#### Root Cause

The import view saves an allowed upload and synchronously previews it. After scanning bounded input bytes, the XLSX branch consumes every row and converts every cell without dimension/cell/time limits; normalization checks row count only afterwards. openpyxl fills gaps up to attacker-selected row positions using attacker-selected column width. A sparse file therefore amplifies parser work independently of ZIP decompression size. CSV also collects all rows before the limit, with amplification bounded more tightly by source bytes.

**Upload is persisted then previewed** — `apps/core/import_export_views.py:44-61`

Authorized source_file is persisted and passed to synchronous preview; per-file validation is not a parser allocation budget.

```
        return queryset.filter(actor=self.request.user) if not self.request.user.is_platform_user else queryset

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
        except Exception as exc:
            job.status = ImportJob.Statuses.FAILED
            job.error = sanitize_error_text(exc)
            job.save(update_fields=["status", "error", "updated_at"])
            mark_excel_csv_import_failed(job, exc)
```

**Preview parses stored upload** — `apps/core/import_export.py:169-174`

The locked preview transaction calls read_tabular_file with the attacker-controlled stored file.

```
@transaction.atomic
def build_import_preview(job: ImportJob, mapping=None, request=None):
    job = _locked_import_job(job, request)
    if job.status in {ImportJob.Statuses.IMPORTED, ImportJob.Statuses.CANCELLED}:
        raise ValidationError("A completed or cancelled import cannot be previewed again.")
    rows = read_tabular_file(job.source_file)
```

**Input byte and antivirus controls** — `apps/core/import_export.py:608-618`

The same bounded bytes must pass antivirus, but these controls do not bound sparse worksheet dimensions.

```
    # Scan and parse the same bounded bytes, including old jobs and confirmation.
    with (path.open("rb") if hasattr(path, "storage") else open(path, "rb")) as source:
        content = source.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("Import file exceeds the upload size limit.")
    try:
        result = scan_stream(BytesIO(content))
    except ScanUnavailable:
        raise TemporaryServiceFailure("File security check is temporarily unavailable. Retry later.") from None
    if not result.clean:
        raise ValidationError("File was blocked by the security check.")
```

**Full worksheet is materialized** — `apps/core/import_export.py:627-640`

Unbounded iterator output and every cell are materialized before normalization; read_only does not preserve streaming here.

```
    if extension == ".xlsx":
        if load_workbook is None:
            raise ValidationError("XLSX import requires openpyxl. Install requirements.txt and retry.")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValidationError("Import file is empty.")
        headers = [str(value or "").strip() for value in rows[0]]
        result = []
        for values in rows[1:]:
            result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
        workbook.close()
        return normalize_tabular_rows(result)
```

**Row limit follows allocation** — `apps/core/import_export.py:644-656`

Only normalized nonempty rows are counted, after all input rows and cells were already processed.

```
def normalize_tabular_rows(rows):
    if not rows:
        raise ValidationError("Import file is empty.")
    normalized_rows = []
    for row in rows:
        clean_row = {str(key or "").strip(): cell_to_string(value) for key, value in (row or {}).items() if str(key or "").strip()}
        if any(value for value in clean_row.values()):
            normalized_rows.append(clean_row)
    if not normalized_rows:
        raise ValidationError("Import file has headers but no data rows.")
    if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
        raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
    return normalized_rows
```

**Dependency synthesizes rows** — `.venv/Lib/site-packages/openpyxl/worksheet/_read_only.py:73-102`

Worksheet dimensions determine row width, and sparse row indices cause filler rows before a far-away populated row.

```
            empty_row = (filler,) * (max_col + 1 - min_col)

        counter = min_row
        idx = 1
        with self._get_source() as src:
            parser = WorkSheetParser(src,
                                     self._shared_strings,
                                     data_only=self.parent.data_only,
                                     epoch=self.parent.epoch,
                                     date_formats=self.parent._date_formats,
                                     timedelta_formats=self.parent._timedelta_formats)

            for idx, row in parser.parse():
                if max_row is not None and idx > max_row:
                    break

                # some rows are missing
                for _ in range(counter, idx):
                    counter += 1
                    yield empty_row

                # return cells from a row
                if counter <= idx:
                    row = self._get_row(row, min_col, max_col, values_only)
                    counter += 1
                    yield row

        if max_row is not None and max_row < idx:
            for _ in range(counter, max_row+1):
                yield empty_row
```

#### Validation

Verified authenticated CREATE flow, scan-before-parse, unbounded iterator list, per-cell conversion and late normalized-row check. The openpyxl iterator synthesizes missing rows; file size and AV bounds do not address virtual cell work.

Validation method: Offline source trace including installed openpyxl

**Upload is persisted then previewed** — `apps/core/import_export_views.py:44-61`

Authorized source_file is persisted and passed to synchronous preview; per-file validation is not a parser allocation budget.

```
        return queryset.filter(actor=self.request.user) if not self.request.user.is_platform_user else queryset

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
        except Exception as exc:
            job.status = ImportJob.Statuses.FAILED
            job.error = sanitize_error_text(exc)
            job.save(update_fields=["status", "error", "updated_at"])
            mark_excel_csv_import_failed(job, exc)
```

**Preview parses stored upload** — `apps/core/import_export.py:169-174`

The locked preview transaction calls read_tabular_file with the attacker-controlled stored file.

```
@transaction.atomic
def build_import_preview(job: ImportJob, mapping=None, request=None):
    job = _locked_import_job(job, request)
    if job.status in {ImportJob.Statuses.IMPORTED, ImportJob.Statuses.CANCELLED}:
        raise ValidationError("A completed or cancelled import cannot be previewed again.")
    rows = read_tabular_file(job.source_file)
```

**Input byte and antivirus controls** — `apps/core/import_export.py:608-618`

The same bounded bytes must pass antivirus, but these controls do not bound sparse worksheet dimensions.

```
    # Scan and parse the same bounded bytes, including old jobs and confirmation.
    with (path.open("rb") if hasattr(path, "storage") else open(path, "rb")) as source:
        content = source.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("Import file exceeds the upload size limit.")
    try:
        result = scan_stream(BytesIO(content))
    except ScanUnavailable:
        raise TemporaryServiceFailure("File security check is temporarily unavailable. Retry later.") from None
    if not result.clean:
        raise ValidationError("File was blocked by the security check.")
```

**Full worksheet is materialized** — `apps/core/import_export.py:627-640`

Unbounded iterator output and every cell are materialized before normalization; read_only does not preserve streaming here.

```
    if extension == ".xlsx":
        if load_workbook is None:
            raise ValidationError("XLSX import requires openpyxl. Install requirements.txt and retry.")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValidationError("Import file is empty.")
        headers = [str(value or "").strip() for value in rows[0]]
        result = []
        for values in rows[1:]:
            result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
        workbook.close()
        return normalize_tabular_rows(result)
```

**Row limit follows allocation** — `apps/core/import_export.py:644-656`

Only normalized nonempty rows are counted, after all input rows and cells were already processed.

```
def normalize_tabular_rows(rows):
    if not rows:
        raise ValidationError("Import file is empty.")
    normalized_rows = []
    for row in rows:
        clean_row = {str(key or "").strip(): cell_to_string(value) for key, value in (row or {}).items() if str(key or "").strip()}
        if any(value for value in clean_row.values()):
            normalized_rows.append(clean_row)
    if not normalized_rows:
        raise ValidationError("Import file has headers but no data rows.")
    if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
        raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
    return normalized_rows
```

**Dependency synthesizes rows** — `.venv/Lib/site-packages/openpyxl/worksheet/_read_only.py:73-102`

Worksheet dimensions determine row width, and sparse row indices cause filler rows before a far-away populated row.

```
            empty_row = (filler,) * (max_col + 1 - min_col)

        counter = min_row
        idx = 1
        with self._get_source() as src:
            parser = WorkSheetParser(src,
                                     self._shared_strings,
                                     data_only=self.parent.data_only,
                                     epoch=self.parent.epoch,
                                     date_formats=self.parent._date_formats,
                                     timedelta_formats=self.parent._timedelta_formats)

            for idx, row in parser.parse():
                if max_row is not None and idx > max_row:
                    break

                # some rows are missing
                for _ in range(counter, idx):
                    counter += 1
                    yield empty_row

                # return cells from a row
                if counter <= idx:
                    row = self._get_row(row, min_col, max_col, values_only)
                    counter += 1
                    yield row

        if max_row is not None and max_row < idx:
            for _ in range(counter, max_row+1):
                yield empty_row
```

Counterevidence and remaining uncertainty:
- Default 10 MiB input cap; clean antivirus verdict required.
- read_only=True limits library cell retention only when callers stream; this caller collects the entire iterator.
- No runtime exhaustion test, crafted file, or production availability claim.

Limitations:
- Actual memory/time exhaustion magnitude and scanner acceptance were not tested.

#### Dataflow

POST import-jobs → validate/store source_file → build_import_preview → scan bounded bytes → openpyxl sparse iterator → list and full-cell conversion → late row count.

#### Reachability

Tenant import creator supplies a valid sparse XLSX after authentication and CREATE checks; processor consumes shared resources without crossing file execution boundaries.

#### Severity

**Medium** — Input is authenticated and antivirus-gated, but a small valid sparse worksheet drives very large synchronous work and can disrupt shared worker availability. Production limits and actual scanner verdict are untested, so no catastrophic outage or anonymous reachability is claimed.

A verified ingress-independent parser memory/time cap would reduce impact; demonstrated shared-service outage would raise confidence in impact.

#### Remediation

Enforce row, column and total-cell budgets before and during iteration, stop streaming on the first excess element, bound ZIP/XML/shared-string expansion, close workbooks in finally, and isolate parsing under hard memory/time budgets.

Tests:
- A small sparse workbook with a distant row and excessive width must be rejected before full iteration.
- CSV input above the row budget must stop at the budget plus one row.
- Parser failures must release workbook resources and roll back preview state.

<a id="finding-5"></a>

### [5] Ordinary members can hard-delete an unprotected business

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Missing tenant lifecycle authorization |
| CWE | CWE-862 |
| Affected lines | apps/businesses/views.py:47-74, apps/core/permissions.py:59-73 |

#### Summary

BusinessViewSet inherits generic destroy with only a membership check, so even a specialist can delete the Business and cascading records when no protective foreign-key references block deletion.

#### Root Cause

BusinessViewSet is separate from TenantModelViewSet. Its create/update overrides never protect inherited destroy. accessible_businesses includes active members of every role; IsTenantMember accepts the Business as its own tenant. DRF DestroyModelMixin then calls instance.delete.

**Business API omits delete authorization** — `apps/businesses/views.py:47-74`

Only create/update are overridden; generic destroy remains reachable.

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("owner") or self.request.user
        business = serializer.save(owner=owner)
        BusinessMember.objects.get_or_create(
            business=business,
            user=owner,
            defaults={"role": BusinessMember.Roles.OWNER, "is_active": True},
        )
        from apps.crm.services import ensure_default_pipeline

        ensure_default_pipeline(business)
        ensure_default_roles(business)
        write_audit_log(self.request, AuditLog.Actions.CREATE, business)

    @transaction.atomic
    def perform_update(self, serializer):
        # Refresh under the same lock as platform detail corrections. A serializer
        # loaded before that correction must not save stale unrelated fields.
        serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
        assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
        business = serializer.save()
```

**Membership is the only object gate** — `apps/core/permissions.py:59-73`

Any active member satisfies the object permission; no role-specific deletion check occurs.

```
        business = getattr(obj, "business", None)

        if business is None and obj.__class__.__name__ == "Business":
            business = obj
        if business is None and hasattr(obj, "conversation"):
            business = obj.conversation.business
        if business is None and hasattr(obj, "bot"):
            business = obj.bot.business

        return user_can_access_business(request.user, business)


class IsPlatformUser(BasePermission):
    def has_permission(self, request, view):
        return is_platform_user(request.user)
```

#### Validation

Cannot choose a business without membership/support access. Payments, deals with protected references, support cases, billing offers and ownership transfers may block deletion. A newly created tenant with default roles/pipeline and only unprotected clients/tasks remains a valid path; PROTECT is not authorization.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

member DELETE business -\> accessible_businesses -\> IsTenantMember -\> inherited destroy -\> Business.delete -\> cascades

- **Outcome:** Permanent business, membership and unprotected CRM/audit deletion.

#### Reachability

Authenticated active low-privilege member of a business whose data graph contains no protecting references.

- **Attacker:** Authenticated active low-privilege member of a business whose data graph contains no protecting references.

#### Severity

**Medium** — High data-integrity impact within an existing tenant; active membership and absence of PROTECT relations are required, reducing likelihood and scope.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Disable generic Business deletion or require explicit privileged lifecycle authorization, locking and audit in a dedicated service.

Tests:
- A specialist must receive denial deleting a new business with no PROTECT-related data; assert business and cascades remain intact.

<a id="finding-6"></a>

### [6] XLSX imports allocate the worksheet before enforcing limits

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Both readers call list(iter_rows) before enforcing row limits; dependency source confirms expansion of row gaps and worksheet column allocation. No runtime resource test performed. |
| Category | Unbounded spreadsheet parsing |
| CWE | CWE-400 |
| Affected lines | apps/core/import_export_views.py:46-56, apps/core/import_export.py:630-640, apps/core/import_export.py:644-655, apps/outreach/views.py:209-227, apps/outreach/imports.py:59-70 |

#### Summary

Core and outreach imports synchronously materialize an attacker-supplied XLSX worksheet before checking IMPORT_MAX_ROWS, allowing small sparse spreadsheets to drive excessive memory and CPU consumption (AUD-22).

#### Root Cause

Both readers accept untrusted ZIP/XML worksheet structure and immediately list the iter_rows generator. read_only mode cannot protect the application from this eager list, per-row column tuples, sparse row gaps or later duplicate normalization allocations. Limits only apply to compressed bytes and the final nonempty-row count.

**Authorized upload reaches synchronous parser** — `apps/outreach/views.py:209-227`

Role and compressed-file checks precede read_consent_upload but do not constrain expanded rows or columns.

```

    @action(detail=False, methods=["post"], url_path="bulk-import-file")
    def bulk_import_file(self, request):
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "File is required."})
        validate_file_upload(
            upload,
            allowed_extensions=["csv", "xlsx"],
            allowed_content_types=[
                "text/csv",
                "application/csv",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ],
        )
        business = self._resolve_business_for_import(request.data.get("business"))
        _assert_outreach_role(request.user, business, OUTREACH_MANAGE_ROLES)
        rows = read_consent_upload(upload)
```

**Core parser materializes rows** — `apps/core/import_export.py:627-640`

The bounded and scanned XLSX bytes are decoded into all worksheet rows before any row-count guard.

```
    if extension == ".xlsx":
        if load_workbook is None:
            raise ValidationError("XLSX import requires openpyxl. Install requirements.txt and retry.")
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValidationError("Import file is empty.")
        headers = [str(value or "").strip() for value in rows[0]]
        result = []
        for values in rows[1:]:
            result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
        workbook.close()
        return normalize_tabular_rows(result)
```

**Outreach repeats the eager reader** — `apps/outreach/imports.py:59-70`

Consent uploads independently materialize every worksheet row; normalize_consent_rows later checks the row count.

```
def _read_xlsx(upload):
    if load_workbook is None:
        raise ValidationError({"file": "XLSX import requires openpyxl."})
    upload.seek(0)
    workbook = load_workbook(upload, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        raise ValidationError({"file": "Import file is empty."})
    headers = [_cell_to_string(value) for value in rows[0]]
    return normalize_consent_rows([{headers[index]: value for index, value in enumerate(values) if index < len(headers)} for values in rows[1:]])
```

**Row cap is enforced after allocation** — `apps/core/import_export.py:644-655`

Normalization traverses already materialized rows before comparing their number against IMPORT_MAX_ROWS.

```
def normalize_tabular_rows(rows):
    if not rows:
        raise ValidationError("Import file is empty.")
    normalized_rows = []
    for row in rows:
        clean_row = {str(key or "").strip(): cell_to_string(value) for key, value in (row or {}).items() if str(key or "").strip()}
        if any(value for value in clean_row.values()):
            normalized_rows.append(clean_row)
    if not normalized_rows:
        raise ValidationError("Import file has headers but no data rows.")
    if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
        raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
```

#### Validation

Confirmed core preview and confirm reach read_tabular_file and outreach bulk-import-file reaches _read_xlsx. Installed openpyxl _read_only.py:60-105 uses worksheet dimensions for row tuple width and iterates gaps preceding supplied row indices. A compact sparse file can induce large iteration/allocation without exceeding archive-byte limits. ClamAV MaxFileSize 10M, MaxScanSize 40M, MaxScanTime 20000 and AlertExceedsMax constrain ordinary archive bombs but do not provide application row/cell quotas.

Validation method: offline static source and dependency inspection

Limitations:
- No workbook payload generated or executed; exact memory/latency not measured.
- Core parser requires an available clean antivirus result; outreach has no equivalent scan call in this path.

#### Dataflow

multipart XLSX -\> compressed-byte validation -\> core scan or outreach role check -\> load_workbook -\> list(iter_rows) -\> late row count

- **Source:** uploaded worksheet XML/dimensions

- **Sink:** Python full worksheet list and normalization

- **Outcome:** Excessive shared worker memory/CPU consumption

#### Reachability

Core entity CREATE or outreach owner/admin/marketer import permission is required; worker resources are shared across business requests.

#### Severity

**Medium** — Authorized importers can consume shared web-worker resources; potentially high availability impact with medium likelihood because import rights and parser workload are required.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Use one bounded reader: validate rows/columns/cells, archive entries and expanded sizes before and during parsing; stop iteration early, close workbooks in finally, and isolate decoding under hard memory/time budgets.

Tests:
- Reject sparse extreme-row and extreme-column XLSX before allocating large cell arrays.
- Verify normal bounded imports, antivirus failure and parser cleanup.
- Exercise both core preview/confirm and outreach import.

<a id="finding-7"></a>

### [7] Read-only team viewers can claim privileged invitations

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Invitation credential disclosure |
| CWE | CWE-200 |
| Affected lines | apps/businesses/views.py:350-361, apps/businesses/serializers.py:319-338, apps/businesses/views.py:433-465 |

#### Summary

Invitation lists expose token and invite_path to TEAM VIEW users. A viewer can use a pending administrator invitation for an unregistered recipient to create a password account and claim its role without mailbox access.

#### Root Cause

The list queryset authorizes TEAM VIEW while the serializer projects a bearer token. Anonymous accept relies on possession of that token and creates a new User with the supplied password when the invited email is unregistered, then grants the invitation's role.

**Team-view users list invitations** — `apps/businesses/views.py:350-361`

Read access selects the invitation without management permission.

```
class BusinessInvitationViewSet(TeamAccessMixin, ModelViewSet):
    serializer_class = BusinessInvitationSerializer
    queryset = BusinessInvitation.objects.select_related("business", "business_role", "invited_by")

    def get_permissions(self):
        if getattr(self, "action", "") in {"accept", "preview"}:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = self.queryset.filter(business_id__in=self.accessible_business_ids(Actions.VIEW))
        return self.filter_requested_business(queryset)
```

**Read projection exposes bearer token** — `apps/businesses/serializers.py:319-338`

Read-only serializer fields prevent writes, not disclosure of the credential.

```
            "role",
            "business_role",
            "business_role_name",
            "team",
            "invited_by",
            "invited_by_email",
            "delivery_channel",
            "token",
            "invite_path",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["token", "invited_by", "expires_at", "accepted_at", "revoked_at", "created_at", "updated_at"]

    def get_invite_path(self, obj):
        return f"/invite/{obj.token}"
```

**Bearer token creates account and role** — `apps/businesses/views.py:433-465`

An unauthenticated holder selects a password for a new recipient and receives the invitation membership.

```
        user = User.objects.filter(email__iexact=invitation.email).first()
        if user is not None and user.pk == invitation.business.owner_id:
            raise ValidationError("The current owner's membership cannot be replaced by an invitation.")
        full_name = serializer.validated_data.get("full_name") or invitation.full_name
        phone = (serializer.validated_data.get("phone") or invitation.phone or "").strip()
        if user is None:
            if request.user.is_authenticated:
                raise PermissionDenied("Sign out before accepting an invitation for a new account.")
            password = serializer.validated_data.get("password")
            if not password:
                raise ValidationError({"password": "A password is required for a new account."})
            user = User.objects.create_user(
                username=invitation.email,
                email=invitation.email,
                password=password,
                full_name=full_name,
                phone=phone,
                role=_user_role_for_business_member(invitation.role),
            )
        else:
            if not request.user.is_authenticated:
                raise InvitationAccountAuthenticationRequired()
            if request.user.pk != user.pk:
                raise PermissionDenied("This invitation belongs to another account.")
        membership, _ = BusinessMember.objects.update_or_create(
            business=invitation.business,
            user=user,
            defaults={
                "role": invitation.role,
                "business_role": invitation.business_role,
                "is_active": True,
            },
        )
```

#### Validation

Existing-account invitations require the correct authenticated recipient. Tokens must be pending, unexpired and unrevoked; owner roles are rejected. Built-in owners/admins already have manage, so custom read-only permission matters. MFA enrollment for the new account can be performed by the claimant and does not restore recipient-only token secrecy.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

TEAM VIEW list -\> invitation token -\> anonymous accept/password -\> new User -\> privileged membership

- **Outcome:** Escalation to the role carried by the invitation, including business admin.

#### Reachability

Business member with TEAM VIEW but no TEAM MANAGE; a higher-role invitation for a new account is pending.

- **Attacker:** Business member with TEAM VIEW but no TEAM MANAGE; a higher-role invitation for a new account is pending.

#### Severity

**Medium** — High privilege impact within a business, requiring a custom TEAM VIEW-only role and a pending higher-role invitation for an unregistered email.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Remove bearer token and invite_path from TEAM VIEW output. Expose or deliver invitation credentials only through a TEAM MANAGE-authorized flow.

Tests:
- TEAM VIEW-only list/detail responses must omit usable token/path; accepting known tokens still obeys recipient and expiry controls.

<a id="finding-8"></a>

### [8] Password reset leaves earlier MFA enrollment authority valid

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Challenge storage/resolution, password reset and session issuance are directly traceable in source; no runtime execution was performed. |
| Category | Incomplete authentication revocation |
| CWE | CWE-613 |
| Affected lines | apps/accounts/session_security.py:59-87, apps/accounts/mfa.py:281-293, apps/accounts/mfa.py:119-175, apps/accounts/mfa_views.py:60-81, apps/accounts/views.py:185-209 |

#### Summary

An attacker who obtained an enrollment challenge with the victim's former password can finish enrollment after the victim resets that password, within the default five-minute challenge lifetime. Confirmation installs the attacker's factor and issues tokens at the new auth epoch.

#### Root Cause

JWT revocation does not revoke the outstanding primary-authentication capability represented by an enrollment challenge. Its resolver has no epoch or password-version check.

**Challenge resolution ignores revocation epoch** — `apps/accounts/mfa.py:287-293`

A challenge minted before password reset remains valid until expiry or explicit consumption.

```
challenge = queryset.filter(token_hash=_token_hash(token), purpose=purpose).first()
now = timezone.now()
if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
    raise MfaChallengeInvalid()
if challenge.failed_attempts >= MFA_MAX_CHALLENGE_ATTEMPTS:
    raise MfaChallengeInvalid()
return challenge
```

**Password reset revokes JWT epoch only** — `apps/accounts/session_security.py:79-84`

The invoked revocation helper blacklists outstanding JWTs and increments auth_epoch, but neither invalidates MfaChallenge nor clears pending enrollment devices.

```
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
```

**Confirmation upgrades stale challenge to fresh session** — `apps/accounts/mfa_views.py:63-73`

After verifying the attacker's pending enrollment secret, confirmation issues a current-epoch session; subsequent JWT epoch checks do not reject it.

```
user, recovery_codes = confirm_enrollment(
    challenge_token=_challenge_token(request),
    code=request.data.get("code"),
)
except Exception:
    if audit_user:
        record_security_event(request, user=audit_user, event="mfa_enrollment_failed")
    raise
revoked_sessions = revoke_user_refresh_sessions(user)
refresh = issue_session(user, mfa_verified=True, request=request)
record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
```

#### Validation

Validated the password reset caller, challenge model, resolver, enrollment secret issuance and new-session flow. Reset never consumes outstanding challenges. Administrative account recovery does consume them at apps/accounts/recovery.py:221, but the ordinary reset helper does not.

Validation method: Offline static source tracing

**Challenge resolution ignores revocation epoch** — `apps/accounts/mfa.py:287-293`

A challenge minted before password reset remains valid until expiry or explicit consumption.

```
challenge = queryset.filter(token_hash=_token_hash(token), purpose=purpose).first()
now = timezone.now()
if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
    raise MfaChallengeInvalid()
if challenge.failed_attempts >= MFA_MAX_CHALLENGE_ATTEMPTS:
    raise MfaChallengeInvalid()
return challenge
```

**Password reset revokes JWT epoch only** — `apps/accounts/session_security.py:79-84`

The invoked revocation helper blacklists outstanding JWTs and increments auth_epoch, but neither invalidates MfaChallenge nor clears pending enrollment devices.

```
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
```

**Confirmation upgrades stale challenge to fresh session** — `apps/accounts/mfa_views.py:63-73`

After verifying the attacker's pending enrollment secret, confirmation issues a current-epoch session; subsequent JWT epoch checks do not reject it.

```
user, recovery_codes = confirm_enrollment(
    challenge_token=_challenge_token(request),
    code=request.data.get("code"),
)
except Exception:
    if audit_user:
        record_security_event(request, user=audit_user, event="mfa_enrollment_failed")
    raise
revoked_sessions = revoke_user_refresh_sessions(user)
refresh = issue_session(user, mfa_verified=True, request=request)
record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
```

Counterevidence and remaining uncertainty:
- Challenges expire after 300 seconds by default and allow five failed attempts; a new same-purpose challenge consumes the previous one.
- An already enrolled victim requires their existing second factor; the primary scenario is pending enrollment.
- Administrative assisted recovery consumes challenges; this finding is not that flow.

Limitations:
- No live reproduction or deployment verification.

#### Dataflow

Old password -\> token endpoint enrollment challenge -\> enrollment/start reveals pending seed -\> victim password-reset/confirm advances epoch -\> attacker enrollment/confirm with seed TOTP -\> new current-epoch access/refresh tokens.

**Challenge resolution ignores revocation epoch** — `apps/accounts/mfa.py:287-293`

A challenge minted before password reset remains valid until expiry or explicit consumption.

```
challenge = queryset.filter(token_hash=_token_hash(token), purpose=purpose).first()
now = timezone.now()
if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
    raise MfaChallengeInvalid()
if challenge.failed_attempts >= MFA_MAX_CHALLENGE_ATTEMPTS:
    raise MfaChallengeInvalid()
return challenge
```

**Password reset revokes JWT epoch only** — `apps/accounts/session_security.py:79-84`

The invoked revocation helper blacklists outstanding JWTs and increments auth_epoch, but neither invalidates MfaChallenge nor clears pending enrollment devices.

```
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
```

**Confirmation upgrades stale challenge to fresh session** — `apps/accounts/mfa_views.py:63-73`

After verifying the attacker's pending enrollment secret, confirmation issues a current-epoch session; subsequent JWT epoch checks do not reject it.

```
user, recovery_codes = confirm_enrollment(
    challenge_token=_challenge_token(request),
    code=request.data.get("code"),
)
except Exception:
    if audit_user:
        record_security_event(request, user=audit_user, event="mfa_enrollment_failed")
    raise
revoked_sessions = revoke_user_refresh_sessions(user)
refresh = issue_session(user, mfa_verified=True, request=request)
record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
```

#### Reachability

Requires previously compromised primary credentials and an account eligible for enrollment. Attacker holds a still-unexpired challenge and finishes after victim reset, without knowing the new password.

#### Severity

**Medium** — Account takeover after an intended security revocation has high impact, but requires prior password compromise, an account awaiting MFA enrollment and completion in a short window; likelihood is medium.

Lower risk if enrollment is never pending or revocation invalidates challenges; wider challenge lifetimes increase exposure.

#### Remediation

Bind challenges to auth_epoch and verify under the same locked user transaction as consumption/session issuance. Consume pending challenges on every password change and account-wide revocation; invalidate pending enrollment secrets as appropriate.

Tests:
- Issue enrollment challenge, reset password, then verify start/confirm with the old challenge are rejected.
- Race revocation with enrollment confirmation and ensure no post-revocation session survives from stale authority.

<a id="finding-9"></a>

### [9] Spoofed forwarded headers bypass anonymous rate limits

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Direct source trace establishes caller, guard gap and sink; no runtime execution. |
| Category | Untrusted rate-limit identity |
| CWE | CWE-307 |
| Affected lines | .venv/Lib/site-packages/rest_framework/throttling.py:23-41, config/settings.py:261-284, docker-compose.yml:2-12 |

#### Summary

The supplied direct Gunicorn deployment accepts caller-chosen X-Forwarded-For as DRF’s anonymous throttle identity, so rotating it bypasses login and other public endpoint limits.

#### Root Cause

ScopedRateThrottle calls get_ident for unauthenticated users. REST_FRAMEWORK does not set NUM_PROXIES, leaving the framework default None; get_ident uses the entire X-Forwarded-For value. Compose publishes Gunicorn directly and provides no header sanitation boundary.

**Framework uses supplied forwarding identity** — `.venv/Lib/site-packages/rest_framework/throttling.py:23-41`

No configured proxy count leaves caller-provided XFF as the anonymous key.

```
    def get_ident(self, request):
        """
        Identify the machine making the request by parsing HTTP_X_FORWARDED_FOR
        if present and number of proxies is > 0. If not use all of
        HTTP_X_FORWARDED_FOR if it is available, if not use REMOTE_ADDR.
        """
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        num_proxies = api_settings.NUM_PROXIES

        if num_proxies is not None:
            if num_proxies == 0 or xff is None:
                return remote_addr
            addrs = xff.split(',')
            client_addr = addrs[-min(num_proxies, len(addrs))]
            return client_addr.strip()

        return ''.join(xff.split()) if xff else remote_addr

```

**Application configures scoped throttles** — `config/settings.py:261-284`

Login/reset/public routes use scoped throttles without a proxy count.

```
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionEpochJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": env("AUTH_LOGIN_RATE", default="10/min"),
        "auth_refresh": env("AUTH_REFRESH_RATE", default="30/min"),
        "auth_social": env("AUTH_SOCIAL_RATE", default="20/min"),
        "auth_signup": env("AUTH_SIGNUP_RATE", default="10/hour"),
        "auth_password_reset": env("AUTH_PASSWORD_RESET_RATE", default="5/hour"),
        "auth_profile": "10/min",
        "auth_email_change": "5/hour",
        "auth_mfa": env("AUTH_MFA_RATE", default="10/min"),
        "public_api": env("PUBLIC_API_RATE", default="120/min"),
        "public_form": env("PUBLIC_FORM_RATE", default="60/min"),
```

**Gunicorn published directly** — `docker-compose.yml:2-12`

The supported Compose path exposes the app without an included sanitizing proxy.

```
  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
    volumes:
      - static_data:/app/staticfiles
      - media_data:/app/media
    ports:
      - "8000:8000"
```

#### Validation

Authenticated throttles key by user. An ingress overwriting headers or trusted-hop configuration can mitigate. MFA is still required where configured. No independent per-account login failure budget exists in the inspected login path.

Validation method: offline static source trace

Limitations:
- No application execution or network reproduction.

#### Dataflow

caller X-Forwarded-For -\> BaseThrottle.get_ident -\> scoped cache key -\> fresh bucket

- **Outcome:** Repeated login guesses and public endpoint abuse outside configured per-client limits.

#### Reachability

Unauthenticated caller reaching direct port 8000 or ingress that retains untrusted header components.

- **Attacker:** Unauthenticated caller reaching direct port 8000 or ingress that retains untrusted header components.

#### Severity

**Medium** — Login/public abuse limits are directly bypassable when client forwarded headers reach the service; MFA and trusted ingress constrain account-compromise impact.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Configure trusted proxy topology explicitly; for direct exposure use NUM_PROXIES=0. Strip untrusted headers at ingress and add per-account authentication attempt limits.

Tests:
- Rotate X-Forwarded-For while holding the connection identity fixed; requests must share the limit.

<a id="finding-10"></a>

### [10] Saved exports remain downloadable after record access is narrowed (AUD-18)

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | The source serves stored bytes after a resource-level check that does not filter rows. |
| Category | Authorization bypass |
| CWE | CWE-863 |
| Affected lines | apps/core/import_export_views.py:105-123, apps/businesses/access.py:340-349, apps/core/export_jobs.py:139-147 |

#### Summary

A member who generated an export while holding broader record access can download the saved rows after their VIEW scope is narrowed to OWN or TEAM.

#### Root Cause

The download handler selects the actor's job and checks current resource VIEW, but `can()` applies OWN/TEAM constraints only to a supplied object. It then returns the previously generated file, preserving rows authorized under the former scope.

**Resource-only download authorization** — `apps/core/import_export_views.py:109`

No record object or row scope is supplied when authorizing the persisted export.

```
        assert_can(request.user, job.business, _resource_for_export_key(job.export_key), Actions.VIEW)
```

**Scoped permission accepts absent object** — `apps/businesses/access.py:345`

OWN/TEAM remains allowed when no concrete record is checked.

```
    result = PermissionResult(True, scope)
    if obj is not None and scope in {RolePermission.Scopes.OWN, RolePermission.Scopes.TEAM}:
        if not _object_matches_scope(obj, user, business, scope, action):
            return PermissionResult(False, scope=scope, reason="Object is outside your permitted scope.")
    return result
```

**Saved export returned** — `apps/core/import_export_views.py:123`

Original rows are streamed from the file rather than regenerated under current permissions.

```
        return FileResponse(job.result_file.open("rb"), as_attachment=True, filename=f"{job.export_key}.csv")
```

#### Validation

Confirmed the selected job is membership/actor constrained, yet its byte contents are not reevaluated under the new row scope.

Validation method: independent static source trace

Counterevidence and remaining uncertainty:
- Membership loss and complete VIEW denial prevent download.
- Client notes can be redacted at download; this does not remove unauthorized rows.
- The user could have downloaded before revocation; finding concerns server access after revocation.

Limitations:
- No runtime or deployed permission-change test performed.

#### Dataflow

Export generated under broad scope -\> persisted result_file -\> role narrowed -\> resource VIEW check -\> unchanged CSV bytes.

#### Reachability

Authenticated member retains membership and resource VIEW but loses access to some rows; a successful saved export must predate narrowing.

#### Severity

**Medium** — Potentially large tenant data disclosure after explicit access reduction; exploitation requires a pre-existing export and retained membership/VIEW, so likelihood is medium.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Invalidate saved exports on relevant permission/ownership changes or regenerate them using the current actor's row and field scope before download.

Tests:
- Generate a multi-owner export, narrow creator to OWN, and verify download cannot disclose other owners' rows.

<a id="finding-11"></a>

### [11] Lead duplicate lookup bypasses record permissions and support grants

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Collection route, inherited authentication-only permission and raw serializer queries are verified; platform_user includes platform_manager. No live requests were sent. |
| Category | Improper resource and tenant authorization |
| CWE | CWE-863 |
| Affected lines | apps/leads/views.py:434-438, apps/leads/serializers.py:226-253, apps/core/permissions.py:54-56, apps/accounts/models.py:29-34 |

#### Summary

POST /api/leads/check-duplicates/ accepts a business/client identifier and returns contact duplicates and recent lead messages without invoking normal lead/client scope checks. Platform users additionally receive an explicit fallback to arbitrary Business IDs even when no tenant grant exists.

#### Root Cause

An auxiliary collection endpoint implements its own tenant lookup and raw read projection, bypassing both shared scoped querysets and support-grant enforcement.

**Collection action bypasses scoped queryset** — `apps/leads/views.py:434-438`

The action never calls get_queryset/get_object or assert_can; inherited IsTenantMember.has_permission only requires authentication.

```
@action(detail=False, methods=["post"], url_path="check-duplicates")
def check_duplicates(self, request):
    serializer = LeadDuplicateCheckSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    return Response(serializer.duplicates())
```

**Platform fallback ignores accessible businesses** — `apps/leads/serializers.py:226-235`

Grant-restricted platform accounts can choose a business absent from their permitted set.

```
def validate_business(self, value):
    request = self.context["request"]
    business = accessible_businesses(request.user).filter(id=value).first()
    if business is None and getattr(request.user, "is_platform_user", False):
        from apps.businesses.models import Business

        business = Business.objects.filter(id=value).first()
    if business is None:
        raise serializers.ValidationError("Business is not available.")
    return business
```

**Raw related leads returned without resource scope** — `apps/leads/serializers.py:247-253`

Membership alone or the platform fallback reveals lead messages even when LEADS.VIEW is absent or limited to other owners/teams.

```
if client:
    related_leads = Lead.objects.filter(business=business, client=client).order_by("-created_at")[:5]
    lead_rows = [
        {"id": lead.id, "client": lead.client_id, "status": lead.status, "source": lead.source, "message": lead.message}
        for lead in related_leads
    ]
return {"duplicates": client_rows, "related_leads": lead_rows}
```

#### Validation

Verified LeadViewSet inherits TenantModelViewSet with authentication-only pre-action permission, ordinary scopes run only in get_queryset/get_object, and duplicate action does not invoke either. Accountant preset lacks LEADS.VIEW; platform_manager qualifies for fallback.

Validation method: Offline source tracing

**Collection action bypasses scoped queryset** — `apps/leads/views.py:434-438`

The action never calls get_queryset/get_object or assert_can; inherited IsTenantMember.has_permission only requires authentication.

```
@action(detail=False, methods=["post"], url_path="check-duplicates")
def check_duplicates(self, request):
    serializer = LeadDuplicateCheckSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    return Response(serializer.duplicates())
```

**Platform fallback ignores accessible businesses** — `apps/leads/serializers.py:226-235`

Grant-restricted platform accounts can choose a business absent from their permitted set.

```
def validate_business(self, value):
    request = self.context["request"]
    business = accessible_businesses(request.user).filter(id=value).first()
    if business is None and getattr(request.user, "is_platform_user", False):
        from apps.businesses.models import Business

        business = Business.objects.filter(id=value).first()
    if business is None:
        raise serializers.ValidationError("Business is not available.")
    return business
```

**Raw related leads returned without resource scope** — `apps/leads/serializers.py:247-253`

Membership alone or the platform fallback reveals lead messages even when LEADS.VIEW is absent or limited to other owners/teams.

```
if client:
    related_leads = Lead.objects.filter(business=business, client=client).order_by("-created_at")[:5]
    lead_rows = [
        {"id": lead.id, "client": lead.client_id, "status": lead.status, "source": lead.source, "message": lead.message}
        for lead in related_leads
    ]
return {"duplicates": client_rows, "related_leads": lead_rows}
```

Counterevidence and remaining uncertainty:
- Ordinary merchant callers remain limited to accessible businesses.
- Related leads are capped at five per client; repeated IDs still expose other clients.
- Client sibling duplicate endpoint has CREATE authorization; not implicated here.

#### Dataflow

Authenticated caller -\> business/client/phone/email input -\> membership or platform fallback -\> raw Client lookup/duplicate helper -\> raw related Lead rows -\> message/contact response.

**Collection action bypasses scoped queryset** — `apps/leads/views.py:434-438`

The action never calls get_queryset/get_object or assert_can; inherited IsTenantMember.has_permission only requires authentication.

```
@action(detail=False, methods=["post"], url_path="check-duplicates")
def check_duplicates(self, request):
    serializer = LeadDuplicateCheckSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    return Response(serializer.duplicates())
```

**Platform fallback ignores accessible businesses** — `apps/leads/serializers.py:226-235`

Grant-restricted platform accounts can choose a business absent from their permitted set.

```
def validate_business(self, value):
    request = self.context["request"]
    business = accessible_businesses(request.user).filter(id=value).first()
    if business is None and getattr(request.user, "is_platform_user", False):
        from apps.businesses.models import Business

        business = Business.objects.filter(id=value).first()
    if business is None:
        raise serializers.ValidationError("Business is not available.")
    return business
```

**Raw related leads returned without resource scope** — `apps/leads/serializers.py:247-253`

Membership alone or the platform fallback reveals lead messages even when LEADS.VIEW is absent or limited to other owners/teams.

```
if client:
    related_leads = Lead.objects.filter(business=business, client=client).order_by("-created_at")[:5]
    lead_rows = [
        {"id": lead.id, "client": lead.client_id, "status": lead.status, "source": lead.source, "message": lead.message}
        for lead in related_leads
    ]
return {"duplicates": client_rows, "related_leads": lead_rows}
```

#### Reachability

Tenant member without lead access can select known client IDs. Platform support role can cross grant boundary with business/client IDs even when SUPPORT_REQUIRES_GRANT is enabled.

#### Severity

**Medium** — Unauthorized customer data disclosure is directly reachable by a low-privilege tenant member; cross-tenant access requires a platform role. Five leads per client and privileged prerequisite narrow the impact; severity is reduced accordingly.

Anonymous access or larger bulk disclosure would raise severity; removing fallback and enforcing both client/lead scopes closes the path.

#### Remediation

Use accessible_businesses without bypass, require the intended client/lead capability, and scope every returned client and lead through current permissions. Do not expose messages in duplicate hints unless authorized.

Tests:
- No LEADS.VIEW and OWN/TEAM users cannot obtain unauthorized lead messages through duplicate checks.
- Platform manager/admin without required grant cannot query arbitrary business IDs.

<a id="finding-12"></a>

### [12] Anonymous forms and chat can reverse another client’s opt-out

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Missing consent-change authorization |
| CWE | CWE-862 |
| Affected lines | apps/leads/forms_service.py:63-76, apps/leads/forms_service.py:88-95, apps/bots/serializers.py:382-402, apps/outreach/services.py:138-152, apps/outreach/services.py:88-94 |

#### Summary

Public lead forms and website chat resolve existing clients from unverified phone/email, then accept caller consent flags that overwrite OPTED_OUT with OPTED_IN and clear opted_out_at.

#### Root Cause

Both public intake paths treat an asserted contact match as authority to update the matched person's consent. record_explicit_consent unconditionally writes opt-in, while campaign eligibility trusts that record. No proof of phone/email control is required before replacing an opt-out.

**Public form selects existing client** — `apps/leads/forms_service.py:63-76`

Unverified contact input chooses whose consent will be changed.

```
    duplicates = find_duplicate_clients(lead_form.business, phone=phone, email=email)
    duplicate_rows = duplicate_payload(duplicates, phone=phone, email=email)

    with transaction.atomic():
        responsible_user = lead_form.default_responsible_user or lead_form.business.owner
        try:
            validate_form_assignee(business=lead_form.business, user=responsible_user)
        except APIException as exc:
            # A legacy or since-disabled default must not receive a new lead.
            # Keep the public error generic and let the view retain its error log.
            raise ValueError("The form's responsible user is not available.") from exc
        if duplicates:
            client = duplicates[0]
            _fill_missing_client_source_attribution(client, source_detail=source_detail, source_context=source_context)
```

**Form records caller-asserted consent** — `apps/leads/forms_service.py:88-95`

Public consent fields reach the authoritative update service.

```
        if phone and payload_has_explicit_consent(payload, channel=OutreachCampaign.Channels.WHATSAPP):
            record_explicit_consent(
                client=client,
                channel=OutreachCampaign.Channels.WHATSAPP,
                source="lead_form",
                note=f"Explicit consent from form {lead_form.public_id}.",
                evidence={"lead_form": str(lead_form.public_id), "fields": {key: payload.get(key) for key in ["marketing_consent", "outreach_consent", "newsletter_consent", "whatsapp_consent"]}},
            )
```

**Chat repeats unverified identity binding** — `apps/bots/serializers.py:382-402`

The alternate public entry point resolves an existing client and records consent.

```
        if client is not None and phone and payload_has_explicit_consent(validated_data, channel=OutreachCampaign.Channels.WHATSAPP):
            record_explicit_consent(
                client=client,
                channel=OutreachCampaign.Channels.WHATSAPP,
                source="website_chat",
                note="Explicit website chat consent.",
                evidence={"fields": {key: validated_data.get(key) for key in ["marketing_consent", "outreach_consent", "newsletter_consent", "whatsapp_consent"]}},
            )
        record_message_received_event(conversation=conversation, message=bot_message, provider=BotConversation.Channels.WEBSITE)
        return {"conversation": conversation, "message": bot_message, "client": conversation.client, "lead": conversation.lead}

    def _get_or_create_client(self, business, full_name, phone, email, *, bot=None):
        queryset = Client.objects.filter(business=business)
        client = None
        if email:
            client = queryset.filter(email=email).first()
        if client is None and phone:
            client = queryset.filter(phone=phone).first()
        if client:
            # Contact capture is not staff approval to alter an existing client.
            return client
```

**Opt-out overwritten** — `apps/outreach/services.py:138-152`

Shared update_or_create forces OPTED_IN and clears opted_out_at.

```
def record_explicit_consent(*, client, channel, source, note="", evidence=None):
    now = timezone.now()
    return OutreachConsent.objects.update_or_create(
        business=client.business,
        client=client,
        channel=channel,
        defaults={
            "status": OutreachConsent.Statuses.OPTED_IN,
            "source": source,
            "note": note,
            "evidence_json": evidence or {},
            "opted_in_at": now,
            "opted_out_at": None,
        },
    )[0]
```

**Campaign selection trusts changed consent** — `apps/outreach/services.py:88-94`

This is an operational eligibility change, not merely a stored form assertion.

```
def can_receive_campaign(client, campaign):
    consent = consent_for_client(client, campaign.channel)
    if consent and consent.status == OutreachConsent.Statuses.OPTED_OUT:
        return False, OPTED_OUT_REASON
    if campaign.require_opt_in and (not consent or consent.status != OutreachConsent.Statuses.OPTED_IN):
        return False, OPT_IN_REQUIRED_REASON
    return True, ""
```

#### Validation

No campaign is sent by this operation alone. Tenant-bound lookup, active channel/form, conversation quota and public throttles constrain volume but do not establish contact ownership. Existing chat profile fields are preserved, but consent is still changed.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

public contact + consent flag -\> tenant-wide existing client -\> record_explicit_consent -\> OPTED_IN/cleared opt-out -\> campaign eligible

- **Outcome:** Unauthorized reversal of outreach preferences and eligibility for unwanted WhatsApp campaigns.

#### Reachability

Anonymous visitor with active public form/channel UUID and a victim contact identifier; nonempty phone and explicit consent flag supplied.

- **Attacker:** Anonymous visitor with active public form/channel UUID and a victim contact identifier; nonempty phone and explicit consent flag supplied.

#### Severity

**Medium** — An unauthenticated visitor can directly change another person's authoritative consent using known contact data; campaign launch remains a separate requirement.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Preserve existing opt-outs on anonymous intake. Store asserted consent as pending and require verified channel interaction or contact ownership proof before changing authoritative consent.

Tests:
- Both public form and chat must preserve an existing victim opt-out despite matching contact and true consent flags; verified opt-in must still work.

<a id="finding-13"></a>

### [13] A pending MFA enrollment can restore attacker access after password reset

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Inspected challenge creation/resolution, reset/revocation, enrollment and current-epoch issuance. Support recovery provides explicit counterexample consuming challenges. |
| Category | Incomplete invalidation of authentication state |
| CWE | CWE-613 |
| Affected lines | apps/accounts/session_security.py:59-87, apps/accounts/mfa.py:268-293, apps/accounts/mfa_views.py:55-81, apps/accounts/views.py:189-209 |

#### Summary

An attacker who obtained an MFA enrollment challenge and seed using the old password can complete enrollment after the owner resets that password. Reset advances the JWT epoch but does not invalidate the pending challenge. Enrollment then returns recovery codes and a fresh session carrying the new epoch, without the attacker knowing the new password.

#### Root Cause

The preauthentication challenge is a credential-derived capability but has no issuance epoch. Ordinary password reset revokes JWTs only. A still-valid challenge can confirm the unconfirmed factor and cause issue_session to reload the user and mint a token with the updated epoch. JWT revocation therefore does not invalidate all paths that can mint replacement credentials.

**Old credentials create enrollment capability** — `apps/accounts/mfa.py:105-115`

Password login calls start_auth_challenge; an unenrolled account receives an enrollment challenge.

```
@transaction.atomic
def start_auth_challenge(user):
    purpose = MfaChallenge.Purposes.LOGIN if has_confirmed_mfa(user) else MfaChallenge.Purposes.ENROLLMENT
    if purpose == MfaChallenge.Purposes.ENROLLMENT:
        MfaDevice.objects.filter(user=user, confirmed_at__isnull=True).delete()
    token, challenge = _create_challenge(user, purpose)
    return {
        "code": "mfa_required" if purpose == MfaChallenge.Purposes.LOGIN else "mfa_enrollment_required",
        "challenge_token": token,
        "expires_at": challenge.expires_at,
        "method": "totp",
```

**Challenge yields factor seed** — `apps/accounts/mfa.py:119-142`

The challenge holder obtains the unconfirmed device seed needed to complete enrollment.

```
def start_enrollment(*, challenge_token):
    with transaction.atomic():
        challenge = _resolve_challenge(challenge_token, MfaChallenge.Purposes.ENROLLMENT, lock=True)
        try:
            device = MfaDevice.objects.select_for_update().get(user=challenge.user)
        except MfaDevice.DoesNotExist:
            secret = pyotp.random_base32()
            device = MfaDevice.objects.create(
                user=challenge.user,
                encrypted_secret=encrypt_credential_value(secret),
            )
        else:
            if device.is_confirmed:
                raise ValidationError({"detail": "MFA is already enabled.", "code": "mfa_already_enabled"})
            secret = decrypt_credential_value(device.encrypted_secret)
        label = challenge.user.email
        uri = pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=settings.AUTH_MFA_ISSUER)
        return {
            "challenge_token": challenge_token,
            "manual_key": secret,
            "otpauth_uri": uri,
            "issuer": settings.AUTH_MFA_ISSUER,
            "account": label,
            "expires_at": challenge.expires_at,
```

**Password reset revokes sessions** — `apps/accounts/views.py:189-209`

Legitimate reset calls update_password_and_revoke_sessions after checking the reset token.

```
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except Exception:
            user = None
        if user is None or not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=400)
        try:
            enforce_password_policy(serializer.validated_data["password"], user=user)
        except ValidationError as exc:
            raise ValidationError({"password": exc.detail}) from exc
        revoked_sessions, _ = update_password_and_revoke_sessions(
            user,
            serializer.validated_data["password"],
        )
        record_security_event(
            request,
            user=user,
            event="password_reset_confirmed",
            sessions_revoked=revoked_sessions,
        )
        return clear_refresh_cookie(Response({"ok": True}))
```

**Revocation does not consume challenges** — `apps/accounts/session_security.py:59-87`

The credential revocation changes password/epoch and blacklists JWTs but leaves pending MFA transactions usable.

```
@transaction.atomic
def revoke_user_refresh_sessions(user):
    """Blacklist refresh sessions and advance the epoch checked by every JWT."""
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    tokens = list(
        OutstandingToken.objects.select_for_update(of=("self",))
        .filter(user=locked_user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True)
        .only("id")
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in tokens],
        ignore_conflicts=True,
    )
    locked_user.auth_epoch += 1
    locked_user.save(update_fields=["auth_epoch"])
    user.auth_epoch = locked_user.auth_epoch
    return len(tokens)


@transaction.atomic
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
    if replacement is not None:
        replacement["auth_epoch"] = int(user.auth_epoch)
    return revoked_sessions, replacement
```

**Challenge is not bound to epoch** — `apps/accounts/mfa.py:268-293`

Stored challenge carries expiry and user but no epoch; resolution checks neither password version nor revocation.

```
def _create_challenge(user, purpose):
    now = timezone.now()
    MfaChallenge.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True).update(consumed_at=now)
    token = secrets.token_urlsafe(MFA_CHALLENGE_BYTES)
    challenge = MfaChallenge.objects.create(
        user=user,
        purpose=purpose,
        token_hash=_token_hash(token),
        expires_at=now + timedelta(seconds=settings.AUTH_MFA_CHALLENGE_SECONDS),
    )
    return token, challenge


def _resolve_challenge(token, purpose, *, lock):
    if not token:
        raise MfaChallengeInvalid()
    queryset = MfaChallenge.objects.select_related("user")
    if lock:
        queryset = queryset.select_for_update()
    challenge = queryset.filter(token_hash=_token_hash(token), purpose=purpose).first()
    now = timezone.now()
    if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
        raise MfaChallengeInvalid()
    if challenge.failed_attempts >= MFA_MAX_CHALLENGE_ATTEMPTS:
        raise MfaChallengeInvalid()
    return challenge
```

**Old challenge issues fresh session** — `apps/accounts/mfa_views.py:55-81`

Successful enrollment revokes sessions again, then issues a current-epoch session and recovery codes.

```
class MfaEnrollmentConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_mfa"

    def post(self, request):
        audit_user = challenge_user(_challenge_token(request), MfaChallenge.Purposes.ENROLLMENT)
        try:
            user, recovery_codes = confirm_enrollment(
                challenge_token=_challenge_token(request),
                code=request.data.get("code"),
            )
        except Exception:
            if audit_user:
                record_security_event(request, user=audit_user, event="mfa_enrollment_failed")
            raise
        revoked_sessions = revoke_user_refresh_sessions(user)
        refresh = issue_session(user, mfa_verified=True, request=request)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        record_security_event(
            request,
            user=user,
            event="mfa_enrolled",
            sessions_revoked=revoked_sessions,
            risk_level=AuditLog.RiskLevels.HIGH,
        )
        return _session_response(refresh, extra={"recovery_codes": recovery_codes})
```

**Session issuance uses current user epoch** — `apps/accounts/mfa.py:92-102`

Reloading the user under lock installs the current auth_epoch rather than rejecting the old challenge.

```
@transaction.atomic
def issue_session(user, *, mfa_verified=False, request=None):
    from apps.accounts.device_sessions import attach_device_session

    user = User.objects.select_for_update().get(pk=user.pk)
    refresh = RefreshToken.for_user(user)
    refresh["mfa_verified"] = bool(mfa_verified)
    refresh["auth_time"] = int(timezone.now().timestamp())
    refresh["auth_epoch"] = int(user.auth_epoch)
    attach_device_session(user, refresh, request)
    return refresh
```

#### Validation

Verified no auth_epoch field in MfaChallenge, no epoch/credential comparison in _resolve_challenge, no challenge consumption in ordinary password reset, and post-confirmation current-epoch session creation.

Validation method: Offline static authentication transaction trace

**Old credentials create enrollment capability** — `apps/accounts/mfa.py:105-115`

Password login calls start_auth_challenge; an unenrolled account receives an enrollment challenge.

```
@transaction.atomic
def start_auth_challenge(user):
    purpose = MfaChallenge.Purposes.LOGIN if has_confirmed_mfa(user) else MfaChallenge.Purposes.ENROLLMENT
    if purpose == MfaChallenge.Purposes.ENROLLMENT:
        MfaDevice.objects.filter(user=user, confirmed_at__isnull=True).delete()
    token, challenge = _create_challenge(user, purpose)
    return {
        "code": "mfa_required" if purpose == MfaChallenge.Purposes.LOGIN else "mfa_enrollment_required",
        "challenge_token": token,
        "expires_at": challenge.expires_at,
        "method": "totp",
```

**Challenge yields factor seed** — `apps/accounts/mfa.py:119-142`

The challenge holder obtains the unconfirmed device seed needed to complete enrollment.

```
def start_enrollment(*, challenge_token):
    with transaction.atomic():
        challenge = _resolve_challenge(challenge_token, MfaChallenge.Purposes.ENROLLMENT, lock=True)
        try:
            device = MfaDevice.objects.select_for_update().get(user=challenge.user)
        except MfaDevice.DoesNotExist:
            secret = pyotp.random_base32()
            device = MfaDevice.objects.create(
                user=challenge.user,
                encrypted_secret=encrypt_credential_value(secret),
            )
        else:
            if device.is_confirmed:
                raise ValidationError({"detail": "MFA is already enabled.", "code": "mfa_already_enabled"})
            secret = decrypt_credential_value(device.encrypted_secret)
        label = challenge.user.email
        uri = pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=settings.AUTH_MFA_ISSUER)
        return {
            "challenge_token": challenge_token,
            "manual_key": secret,
            "otpauth_uri": uri,
            "issuer": settings.AUTH_MFA_ISSUER,
            "account": label,
            "expires_at": challenge.expires_at,
```

**Password reset revokes sessions** — `apps/accounts/views.py:189-209`

Legitimate reset calls update_password_and_revoke_sessions after checking the reset token.

```
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except Exception:
            user = None
        if user is None or not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=400)
        try:
            enforce_password_policy(serializer.validated_data["password"], user=user)
        except ValidationError as exc:
            raise ValidationError({"password": exc.detail}) from exc
        revoked_sessions, _ = update_password_and_revoke_sessions(
            user,
            serializer.validated_data["password"],
        )
        record_security_event(
            request,
            user=user,
            event="password_reset_confirmed",
            sessions_revoked=revoked_sessions,
        )
        return clear_refresh_cookie(Response({"ok": True}))
```

**Revocation does not consume challenges** — `apps/accounts/session_security.py:59-87`

The credential revocation changes password/epoch and blacklists JWTs but leaves pending MFA transactions usable.

```
@transaction.atomic
def revoke_user_refresh_sessions(user):
    """Blacklist refresh sessions and advance the epoch checked by every JWT."""
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    tokens = list(
        OutstandingToken.objects.select_for_update(of=("self",))
        .filter(user=locked_user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True)
        .only("id")
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in tokens],
        ignore_conflicts=True,
    )
    locked_user.auth_epoch += 1
    locked_user.save(update_fields=["auth_epoch"])
    user.auth_epoch = locked_user.auth_epoch
    return len(tokens)


@transaction.atomic
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
    if replacement is not None:
        replacement["auth_epoch"] = int(user.auth_epoch)
    return revoked_sessions, replacement
```

**Challenge is not bound to epoch** — `apps/accounts/mfa.py:268-293`

Stored challenge carries expiry and user but no epoch; resolution checks neither password version nor revocation.

```
def _create_challenge(user, purpose):
    now = timezone.now()
    MfaChallenge.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True).update(consumed_at=now)
    token = secrets.token_urlsafe(MFA_CHALLENGE_BYTES)
    challenge = MfaChallenge.objects.create(
        user=user,
        purpose=purpose,
        token_hash=_token_hash(token),
        expires_at=now + timedelta(seconds=settings.AUTH_MFA_CHALLENGE_SECONDS),
    )
    return token, challenge


def _resolve_challenge(token, purpose, *, lock):
    if not token:
        raise MfaChallengeInvalid()
    queryset = MfaChallenge.objects.select_related("user")
    if lock:
        queryset = queryset.select_for_update()
    challenge = queryset.filter(token_hash=_token_hash(token), purpose=purpose).first()
    now = timezone.now()
    if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
        raise MfaChallengeInvalid()
    if challenge.failed_attempts >= MFA_MAX_CHALLENGE_ATTEMPTS:
        raise MfaChallengeInvalid()
    return challenge
```

**Old challenge issues fresh session** — `apps/accounts/mfa_views.py:55-81`

Successful enrollment revokes sessions again, then issues a current-epoch session and recovery codes.

```
class MfaEnrollmentConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_mfa"

    def post(self, request):
        audit_user = challenge_user(_challenge_token(request), MfaChallenge.Purposes.ENROLLMENT)
        try:
            user, recovery_codes = confirm_enrollment(
                challenge_token=_challenge_token(request),
                code=request.data.get("code"),
            )
        except Exception:
            if audit_user:
                record_security_event(request, user=audit_user, event="mfa_enrollment_failed")
            raise
        revoked_sessions = revoke_user_refresh_sessions(user)
        refresh = issue_session(user, mfa_verified=True, request=request)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        record_security_event(
            request,
            user=user,
            event="mfa_enrolled",
            sessions_revoked=revoked_sessions,
            risk_level=AuditLog.RiskLevels.HIGH,
        )
        return _session_response(refresh, extra={"recovery_codes": recovery_codes})
```

**Session issuance uses current user epoch** — `apps/accounts/mfa.py:92-102`

Reloading the user under lock installs the current auth_epoch rather than rejecting the old challenge.

```
@transaction.atomic
def issue_session(user, *, mfa_verified=False, request=None):
    from apps.accounts.device_sessions import attach_device_session

    user = User.objects.select_for_update().get(pk=user.pk)
    refresh = RefreshToken.for_user(user)
    refresh["mfa_verified"] = bool(mfa_verified)
    refresh["auth_time"] = int(timezone.now().timestamp())
    refresh["auth_epoch"] = int(user.auth_epoch)
    attach_device_session(user, refresh, request)
    return refresh
```

Counterevidence and remaining uncertainty:
- Default challenge expiry is 300 seconds and failed challenge attempts are capped.
- New same-purpose challenge consumes predecessors; already-confirmed devices prevent this enrollment scenario.
- Support-assisted recovery consumes challenges (apps/accounts/recovery.py:221); disable_mfa also invalidates them. Those paths are not affected.

Limitations:
- No runtime password/MFA operation performed.

#### Dataflow

Old password → enrollment challenge/seed → legitimate password reset → surviving challenge confirmation → recovery codes plus new-epoch JWT.

#### Reachability

Attacker already holding a pre-reset enrollment capability races within its expiry window while the device remains unconfirmed, regaining login without new credentials.

#### Severity

**Medium** — Restores compromised account access across an intended revocation boundary, but requires a previously obtained enrollment challenge, an unconfirmed device, victim reset during the default five-minute challenge window, and completion before expiry/new challenge issuance.

A longer-lived or routinely reachable post-revocation challenge would increase likelihood; atomic challenge consumption/epoch binding removes the path.

#### Remediation

Bind all MFA challenges to auth_epoch and validate under the user lock, or consume every pending challenge atomically on credential/session revocation. Ensure challenge confirmation and session minting cannot race a revocation.

Tests:
- Pre-reset enrollment and login challenges must fail after password reset and account-wide revocation.
- Concurrent challenge confirmation and revocation must not produce a session authorized by revoked credentials.

<a id="finding-14"></a>

### [14] Multipart file bytes reach temporary storage before upload limits

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Parser selection, post-parse validation, default upload-handler implementation and Compose startup are inspected offline; deployment/exploit execution was not performed. |
| Category | Unbounded multipart request resource consumption |
| CWE | CWE-400 |
| Affected lines | apps/core/file_attachment_views.py:18-22, apps/core/file_validation.py:38-40, apps/accounts/avatar_views.py:40-46, apps/accounts/avatars.py:23-28, config/settings.py:142-152, docker-compose.yml:4-12 |

#### Summary

The 10MiB attachment and 5MiB avatar limits run after multipart parsing. Default Django upload handlers can spool a much larger file, including an unused file field, to temporary disk before serializer/avatar validation rejects it. The checked-in Compose deployment publishes Gunicorn directly without a body cap.

#### Root Cause

File-size validation is placed after the first resource-consuming parser boundary; no custom streaming upload handler or aggregate body limit is configured.

**Attachment endpoint accepts multipart** — `apps/core/file_attachment_views.py:18-22`

DRF accesses parsed data before serializer validation. Default TemporaryFileUploadHandler writes received file chunks without a byte cap.

```
class FileAttachmentViewSet(ModelViewSet):
    serializer_class = FileAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsTenantMember]
    http_method_names = ["get", "post", "head", "options"]
```

**Size is checked on an already parsed UploadedFile** — `apps/core/file_validation.py:38-40`

This rejects persistence but does not bound earlier multipart temporary-file writes.

```
size = getattr(uploaded_file, "size", 0) or 0
if size > max_size_bytes:
    raise ValidationError({"file": f"File is too large. Maximum size is {max_size_mb} MB."})
```

**Avatar parses full body before its own limit** — `apps/accounts/avatar_views.py:40-46`

request.data triggers multipart parsing, even for file parts unused by save_avatar.

```
def post(self, request):
    crop = None
    if any(key in request.data for key in ("x", "y", "size")):
        serializer = AvatarCropSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        crop = tuple(serializer.validated_data[key] for key in ("x", "y", "size"))
    avatar = save_avatar(request.user, request.FILES.get("file"), crop=crop)
```

**Compose publishes direct Gunicorn** — `docker-compose.yml:4-12`

No checked-in ingress body limiter protects this supported startup.

```
command: >
  sh -c "python manage.py migrate &&
         python manage.py collectstatic --noinput &&
         gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
volumes:
  - static_data:/app/staticfiles
  - media_data:/app/media
ports:
  - "8000:8000"
```

#### Validation

Django TemporaryFileUploadHandler.receive_data_chunk writes raw chunks; multipart DATA_UPLOAD_MAX_MEMORY_SIZE applies to non-file fields, while files have a count limit. No FILE_UPLOAD_HANDLERS/body limiter was found in checked configuration.

Validation method: Offline app and installed Django source inspection

**Attachment endpoint accepts multipart** — `apps/core/file_attachment_views.py:18-22`

DRF accesses parsed data before serializer validation. Default TemporaryFileUploadHandler writes received file chunks without a byte cap.

```
class FileAttachmentViewSet(ModelViewSet):
    serializer_class = FileAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsTenantMember]
    http_method_names = ["get", "post", "head", "options"]
```

**Size is checked on an already parsed UploadedFile** — `apps/core/file_validation.py:38-40`

This rejects persistence but does not bound earlier multipart temporary-file writes.

```
size = getattr(uploaded_file, "size", 0) or 0
if size > max_size_bytes:
    raise ValidationError({"file": f"File is too large. Maximum size is {max_size_mb} MB."})
```

**Avatar parses full body before its own limit** — `apps/accounts/avatar_views.py:40-46`

request.data triggers multipart parsing, even for file parts unused by save_avatar.

```
def post(self, request):
    crop = None
    if any(key in request.data for key in ("x", "y", "size")):
        serializer = AvatarCropSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        crop = tuple(serializer.validated_data[key] for key in ("x", "y", "size"))
    avatar = save_avatar(request.user, request.FILES.get("file"), crop=crop)
```

**Compose publishes direct Gunicorn** — `docker-compose.yml:4-12`

No checked-in ingress body limiter protects this supported startup.

```
command: >
  sh -c "python manage.py migrate &&
         python manage.py collectstatic --noinput &&
         gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
volumes:
  - static_data:/app/staticfiles
  - media_data:/app/media
ports:
  - "8000:8000"
```

Counterevidence and remaining uncertainty:
- Authentication is required on attachment/avatar routes.
- Avatar mutation throttle is 10/min but does not limit bytes of one request.
- External reverse-proxy limits may mitigate production; they were not available.
- Per-file durable validation and AV limits still work after parsing.

#### Dataflow

Authenticated multipart POST -\> MultiPartParser -\> default temporary-file handler -\> oversized bytes written -\> later UploadedFile size rejection.

**Attachment endpoint accepts multipart** — `apps/core/file_attachment_views.py:18-22`

DRF accesses parsed data before serializer validation. Default TemporaryFileUploadHandler writes received file chunks without a byte cap.

```
class FileAttachmentViewSet(ModelViewSet):
    serializer_class = FileAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsTenantMember]
    http_method_names = ["get", "post", "head", "options"]
```

**Avatar parses full body before its own limit** — `apps/accounts/avatar_views.py:40-46`

request.data triggers multipart parsing, even for file parts unused by save_avatar.

```
def post(self, request):
    crop = None
    if any(key in request.data for key in ("x", "y", "size")):
        serializer = AvatarCropSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        crop = tuple(serializer.validated_data[key] for key in ("x", "y", "size"))
    avatar = save_avatar(request.user, request.FILES.get("file"), crop=crop)
```

**Compose publishes direct Gunicorn** — `docker-compose.yml:4-12`

No checked-in ingress body limiter protects this supported startup.

```
command: >
  sh -c "python manage.py migrate &&
         python manage.py collectstatic --noinput &&
         gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
volumes:
  - static_data:/app/staticfiles
  - media_data:/app/media
ports:
  - "8000:8000"
```

#### Reachability

Any authenticated caller able to reach these routes can submit large file parts; business/object authorization is later than parsing on attachment create. Requires no effective external body cap.

#### Severity

**Medium** — Authenticated requests can consume shared temporary disk and worker capacity before size rejection. Impact can be high in direct Compose deployment; external ingress limits and actual capacity are unknown.

A verified aggregate streaming ingress cap mitigates the path; confirmed shared-disk exhaustion would strengthen impact.

#### Remediation

Enforce aggregate actual-byte limits at ingress and in a streaming upload handler before temporary writes, reject excess/unused file parts, and do not trust Content-Length alone.

Tests:
- Oversized multipart and extra file fields must abort while receiving, before large temporary allocation.
- Test missing/false Content-Length and aggregate multi-file limits.

<a id="finding-15"></a>

### [15] AUD-22: XLSX allocation precedes row and expansion limits

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Direct source shows eager list conversion preceding limits; baseline inspected local openpyxl dimension-driven read-only iteration. No hostile workbook was executed. |
| Category | Unbounded spreadsheet resource consumption |
| CWE | CWE-400 |
| Affected lines | apps/core/import_export.py:630-655, apps/core/import_export.py:170-174, apps/core/import_export.py:218-223, apps/core/import_export_views.py:46-61 |

#### Summary

An authorized importer can submit a small XLSX with excessive worksheet dimensions or expanded content. read_tabular_file materializes all rows before IMPORT_MAX_ROWS is checked, allowing expensive CPU/memory allocation in the shared request worker.

#### Root Cause

The parser treats read_only=True as sufficient bounding but immediately eagerly materializes the attacker-controlled iterator; row limit is after allocation and ignores expansion/cell budgets.

**Upload synchronously previews stored workbook** — `apps/core/import_export_views.py:50-56`

Authorized tenant input reaches build_import_preview -\> read_tabular_file in the request worker.

```
assert_can(self.request.user, business, resource, Actions.CREATE)
assert_resource_enabled(business, resource)
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
```

**Eager allocation despite read-only workbook** — `apps/core/import_export.py:630-640`

All worksheet rows/cells are retained and copied before application limits apply.

```
workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
sheet = workbook.active
rows = list(sheet.iter_rows(values_only=True))
if not rows:
    raise ValidationError("Import file is empty.")
headers = [str(value or "").strip() for value in rows[0]]
result = []
for values in rows[1:]:
    result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
workbook.close()
return normalize_tabular_rows(result)
```

**Limit checked after parsing and normalization** — `apps/core/import_export.py:648-655`

Even empty worksheet expansion occurs before nonempty-row counting.

```
for row in rows:
    clean_row = {str(key or "").strip(): cell_to_string(value) for key, value in (row or {}).items() if str(key or "").strip()}
    if any(value for value in clean_row.values()):
        normalized_rows.append(clean_row)
if not normalized_rows:
    raise ValidationError("Import file has headers but no data rows.")
if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
    raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
```

#### Validation

Validated create/preview/confirm callers and parser ordering. Preserves previously documented AUD-22 rather than creating a duplicate issue.

Validation method: Offline source tracing

**Upload synchronously previews stored workbook** — `apps/core/import_export_views.py:50-56`

Authorized tenant input reaches build_import_preview -\> read_tabular_file in the request worker.

```
assert_can(self.request.user, business, resource, Actions.CREATE)
assert_resource_enabled(business, resource)
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
```

**Eager allocation despite read-only workbook** — `apps/core/import_export.py:630-640`

All worksheet rows/cells are retained and copied before application limits apply.

```
workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
sheet = workbook.active
rows = list(sheet.iter_rows(values_only=True))
if not rows:
    raise ValidationError("Import file is empty.")
headers = [str(value or "").strip() for value in rows[0]]
result = []
for values in rows[1:]:
    result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
workbook.close()
return normalize_tabular_rows(result)
```

**Limit checked after parsing and normalization** — `apps/core/import_export.py:648-655`

Even empty worksheet expansion occurs before nonempty-row counting.

```
for row in rows:
    clean_row = {str(key or "").strip(): cell_to_string(value) for key, value in (row or {}).items() if str(key or "").strip()}
    if any(value for value in clean_row.values()):
        normalized_rows.append(clean_row)
if not normalized_rows:
    raise ValidationError("Import file has headers but no data rows.")
if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
    raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
```

Counterevidence and remaining uncertainty:
- Per-file compressed input byte cap and fail-closed AV scanning remain effective.
- Requires authenticated resource CREATE and enabled module.
- No live workload/availability reproduction performed.

#### Dataflow

Tenant XLSX upload -\> stored ImportJob -\> preview/confirm -\> read_tabular_file -\> read-only workbook iterator -\> unbounded list and dictionaries -\> late row limit.

**Upload synchronously previews stored workbook** — `apps/core/import_export_views.py:50-56`

Authorized tenant input reaches build_import_preview -\> read_tabular_file in the request worker.

```
assert_can(self.request.user, business, resource, Actions.CREATE)
assert_resource_enabled(business, resource)
upload = serializer.validated_data["source_file"]
_validate_import_file(upload)
job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
try:
    serializer.instance = build_import_preview(job, request=self.request)
```

**Eager allocation despite read-only workbook** — `apps/core/import_export.py:630-640`

All worksheet rows/cells are retained and copied before application limits apply.

```
workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
sheet = workbook.active
rows = list(sheet.iter_rows(values_only=True))
if not rows:
    raise ValidationError("Import file is empty.")
headers = [str(value or "").strip() for value in rows[0]]
result = []
for values in rows[1:]:
    result.append({headers[index]: cell_to_string(value) for index, value in enumerate(values) if index < len(headers)})
workbook.close()
return normalize_tabular_rows(result)
```

#### Reachability

Authorized tenant importer controls workbook structure under compressed byte limit; parsing occupies a shared web worker.

#### Severity

**Medium** — Tenant-authenticated imports reach shared web-worker parsing; compressed byte and AV controls do not bound worksheet expansion. Shared availability impact is high but deployment memory limits and practical allocation timing remain unverified.

Worker isolation and hard parser memory/CPU budgets lower impact; demonstrated service-wide exhaustion would increase confidence in impact.

#### Remediation

Retain AUD-22 and enforce row, column, total cell and decompressed XML/shared-string budgets before/during parsing. Stream at most limit+1 rows, reject oversized dimensions and isolate parsing with resource limits.

Tests:
- Reject tiny XLSX with oversized dimensions without large allocation.
- Bound archive expansion/shared strings, row width and sparse worksheets; ensure failure cleanup.

<a id="finding-16"></a>

### [16] Ordinary business members can invoke tenant deletion

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Router registration, inheritance, membership checks and cascading relations are source-backed; framework destroy was inspected offline. No deletion was executed. |
| Category | Missing function-level authorization |
| CWE | CWE-862 |
| Affected lines | apps/businesses/views.py:47-75, apps/core/permissions.py:54-68, config/urls.py:135, apps/clients/models.py:18, apps/leads/models.py:30, apps/crm/models.py:64, apps/tasks/models.py:25, apps/core/models.py:47 |

#### Summary

An authenticated active member can DELETE /api/businesses/{id}/ even without settings or deletion privileges. BusinessViewSet inherits DRF destroy and checks only tenant membership. In businesses without protective child records, deletion cascades through CRM records, membership and audit rows.

#### Root Cause

The Business API uses unrestricted ModelViewSet CRUD while adding action-specific authorization only to update. Membership establishes tenant reachability but is incorrectly sufficient for destructive deletion.

**Full CRUD view exposes destroy with membership permission** — `apps/businesses/views.py:47-52`

No destroy override or method restriction exists in this class. DRF DestroyModelMixin invokes instance.delete() after get_object().

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)
```

**Tenant access includes every active member** — `apps/core/permissions.py:47-50`

IsTenantMember.has_object_permission delegates to this membership predicate; no settings/owner/destructive capability is required.

```
return (
    business.owner_id == user.id or
    business.members.filter(user=user, is_active=True).exists()
    or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
```

**Update has stronger authorization that destroy lacks** — `apps/businesses/views.py:72-75`

This control runs for updates only, not inherited deletion.

```
serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
business = serializer.save()
write_audit_log(self.request, AuditLog.Actions.UPDATE, business)
```

**Client data cascades with business** — `apps/clients/models.py:18`

Deleting the selected business destroys its client rows; leads/deals/tasks/members/audit also have CASCADE.

```
business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="clients")
```

#### Validation

Verified router and default destroy -\> perform_destroy -\> instance.delete; queryset/object checks admit ordinary active members. Business class ends after perform_update. Confirmed CASCADE children and protective relations.

Validation method: Offline source and installed DRF inspection

**Full CRUD view exposes destroy with membership permission** — `apps/businesses/views.py:47-52`

No destroy override or method restriction exists in this class. DRF DestroyModelMixin invokes instance.delete() after get_object().

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)
```

**Tenant access includes every active member** — `apps/core/permissions.py:47-50`

IsTenantMember.has_object_permission delegates to this membership predicate; no settings/owner/destructive capability is required.

```
return (
    business.owner_id == user.id or
    business.members.filter(user=user, is_active=True).exists()
    or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
```

**Client data cascades with business** — `apps/clients/models.py:18`

Deleting the selected business destroys its client rows; leads/deals/tasks/members/audit also have CASCADE.

```
business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="clients")
```

**Update has stronger authorization that destroy lacks** — `apps/businesses/views.py:72-75`

This control runs for updates only, not inherited deletion.

```
serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
business = serializer.save()
write_audit_log(self.request, AuditLog.Actions.UPDATE, business)
```

Counterevidence and remaining uncertainty:
- No cross-tenant deletion is established: queryset restricts accessible_businesses.
- Existing PROTECT children such as billing offers/orders, support cases, payments or ownership transfers may prevent deletion; a trial business without such children is still exposed.
- Business.owner PROTECT protects deletion of the owner, not deletion of Business.

#### Dataflow

Member Bearer JWT -\> router DELETE businesses/{id} -\> accessible_businesses -\> IsTenantMember membership -\> inherited DestroyModelMixin -\> Business.delete -\> CASCADE.

**Full CRUD view exposes destroy with membership permission** — `apps/businesses/views.py:47-52`

No destroy override or method restriction exists in this class. DRF DestroyModelMixin invokes instance.delete() after get_object().

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)
```

**Tenant access includes every active member** — `apps/core/permissions.py:47-50`

IsTenantMember.has_object_permission delegates to this membership predicate; no settings/owner/destructive capability is required.

```
return (
    business.owner_id == user.id or
    business.members.filter(user=user, is_active=True).exists()
    or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
```

**Client data cascades with business** — `apps/clients/models.py:18`

Deleting the selected business destroys its client rows; leads/deals/tasks/members/audit also have CASCADE.

```
business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="clients")
```

#### Reachability

Any active tenant member of a deletable business can trigger the path without SETTINGS.UPDATE or owner authority. Requires absence of protective child records.

#### Severity

**Medium** — A low-privilege member can destructively affect the entire same-tenant workspace through one request. Impact is severe but confined to the member's tenant and blocked when protected billing/support/payment/ownership rows exist; severity is reduced for that constrained boundary.

Broader tenant reach or bypass of protected-child restrictions would raise severity; disabling DELETE or an owner-only guard removes this path.

#### Remediation

Disable tenant deletion on this generic endpoint unless it is an explicit product operation. If needed, use an owner/platform-admin-only destructive workflow with current authorization, locked state, retention policy and durable audit.

Tests:
- Assert low-privilege active member DELETE is denied even when no PROTECT children exist.
- Exercise owner/admin deletion policy and preservation of audit/retention invariants.

<a id="finding-17"></a>

### [17] XLSX imports expand worksheets before enforcing row limits (AUD-22)

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Direct source establishes unbounded row materialization before the limit; no live exhaustion test was run. |
| Category | Uncontrolled resource consumption |
| CWE | CWE-400 |
| Affected lines | apps/core/import_export_views.py:48-56, apps/core/import_export.py:630-640, apps/core/import_export.py:644-655 |

#### Summary

An import-authorized member can submit a small XLSX whose worksheet dimensions or contents cause large CPU/memory use during synchronous preview, before IMPORT_MAX_ROWS is checked.

#### Root Cause

Uploaded bytes are capped and antivirus-scanned, then `read_tabular_file()` opens XLSX in streaming mode but converts the entire iterator to a list and constructs another result collection. `normalize_tabular_rows()` checks the row maximum only after that work, so compressed-byte limits do not bound virtual worksheet expansion.

**Full worksheet materialization** — `apps/core/import_export.py:630`

The attacker-controlled worksheet is materialized without a max row/column/cell bound despite read_only mode.

```
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
```

**Limit after normalization** — `apps/core/import_export.py:654`

The application checks row count after expansion and building additional normalized collections.

```
    if len(normalized_rows) > settings.IMPORT_MAX_ROWS:
        raise ValidationError(f"Import file has too many rows. Maximum is {settings.IMPORT_MAX_ROWS}.")
```

#### Validation

Traced synchronous ImportJob creation/preview and confirmation to this parser. Inspected installed openpyxl iterator: worksheet max column drives filler row allocation and missing rows are yielded, so read_only does not bound application list consumption.

Validation method: static source and local dependency inspection

Counterevidence and remaining uncertainty:
- Input defaults to 10 MiB and scanning fails closed.
- ClamAV configuration caps expanded archives and alerts on limits; virtual sparse cell expansion is distinct from scanned archive bytes.
- No actual service outage or exact memory threshold demonstrated.

Limitations:
- AUD-22 runtime sizing remains unperformed; no malicious workbook was executed.

#### Dataflow

Authorized XLSX upload -\> bounded compressed bytes and clean scan -\> openpyxl iterator -\> list of all worksheet rows -\> normalization -\> late row rejection.

#### Reachability

Authenticated member with import CREATE permission, operational scanner and openpyxl; preview is synchronous in web request.

#### Severity

**Medium** — Potential shared request-worker exhaustion has high impact but requires import authorization and suitable content; deployment magnitude and likelihood are unmeasured.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Validate archive expansion and worksheet dimensions, cap rows/columns/total cells while streaming, stop before allocation exceeds limits, and always close the workbook in finally.

Tests:
- In an isolated resource-limited test process, reject sparse oversized dimensions and excessive cells before list allocation.

<a id="finding-18"></a>

### [18] Team readers receive invitation tokens that can grant administrator access

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | List authorization, unconditional token serialization, anonymous new-account acceptance and role assignment are directly verified. Existing tests establish the TEAM.VIEW-only role. |
| Category | Authorization bypass through invitation capability disclosure |
| CWE | CWE-863 |
| Affected lines | apps/businesses/serializers.py:325-338, apps/businesses/views.py:354-361, apps/businesses/views.py:438-464, apps/businesses/views.py:117-125 |

#### Summary

A custom role with TEAM.VIEW but no TEAM.MANAGE can list pending invitation tokens. If a higher-privilege invitation targets an email without an existing User, the reader can sign out, accept that token with a chosen password and sign in as the invited administrator.

#### Root Cause

Invitation administration metadata and the enrollment bearer capability use the same read serializer. Team-list visibility is insufficient authority to possess every invitation secret.

**Read permission exposes invitation queryset** — `apps/businesses/views.py:359-361`

TEAM.VIEW alone selects invitations; no manage permission is required to list.

```
def get_queryset(self):
    queryset = self.queryset.filter(business_id__in=self.accessible_business_ids(Actions.VIEW))
    return self.filter_requested_business(queryset)
```

**Serializer exposes the bearer capability** — `apps/businesses/serializers.py:325-338`

Read-only prevents writes but still returns token and token-bearing path to the team reader.

```
    "delivery_channel",
    "token",
    "invite_path",
    "expires_at",
    "accepted_at",
    "revoked_at",
    "status",
    "created_at",
    "updated_at",
]
read_only_fields = ["token", "invited_by", "expires_at", "accepted_at", "revoked_at", "created_at", "updated_at"]

def get_invite_path(self, obj):
    return f"/invite/{obj.token}"
```

**New account password chosen by token holder** — `apps/businesses/views.py:438-451`

No separate proof of email ownership is needed for the new account; token secrecy is the authority.

```
if user is None:
    if request.user.is_authenticated:
        raise PermissionDenied("Sign out before accepting an invitation for a new account.")
    password = serializer.validated_data.get("password")
    if not password:
        raise ValidationError({"password": "A password is required for a new account."})
    user = User.objects.create_user(
        username=invitation.email,
        email=invitation.email,
        password=password,
        full_name=full_name,
        phone=phone,
        role=_user_role_for_business_member(invitation.role),
    )
```

**Invitation grants membership role** — `apps/businesses/views.py:457-464`

A pending admin/custom privileged role is installed on the attacker-controlled new account.

```
membership, _ = BusinessMember.objects.update_or_create(
    business=invitation.business,
    user=user,
    defaults={
        "role": invitation.role,
        "business_role": invitation.business_role,
        "is_active": True,
    },
```

#### Validation

Verified TeamAccessMixin filters with resource TEAM/action VIEW, supported custom reader fixture, public accept action, pending-token locks and new-user branch. Normal login can use attacker-selected password; required MFA can then be enrolled by that new account.

Validation method: Offline source tracing

**Read permission exposes invitation queryset** — `apps/businesses/views.py:359-361`

TEAM.VIEW alone selects invitations; no manage permission is required to list.

```
def get_queryset(self):
    queryset = self.queryset.filter(business_id__in=self.accessible_business_ids(Actions.VIEW))
    return self.filter_requested_business(queryset)
```

**Serializer exposes the bearer capability** — `apps/businesses/serializers.py:325-338`

Read-only prevents writes but still returns token and token-bearing path to the team reader.

```
    "delivery_channel",
    "token",
    "invite_path",
    "expires_at",
    "accepted_at",
    "revoked_at",
    "status",
    "created_at",
    "updated_at",
]
read_only_fields = ["token", "invited_by", "expires_at", "accepted_at", "revoked_at", "created_at", "updated_at"]

def get_invite_path(self, obj):
    return f"/invite/{obj.token}"
```

**New account password chosen by token holder** — `apps/businesses/views.py:438-451`

No separate proof of email ownership is needed for the new account; token secrecy is the authority.

```
if user is None:
    if request.user.is_authenticated:
        raise PermissionDenied("Sign out before accepting an invitation for a new account.")
    password = serializer.validated_data.get("password")
    if not password:
        raise ValidationError({"password": "A password is required for a new account."})
    user = User.objects.create_user(
        username=invitation.email,
        email=invitation.email,
        password=password,
        full_name=full_name,
        phone=phone,
        role=_user_role_for_business_member(invitation.role),
    )
```

**Invitation grants membership role** — `apps/businesses/views.py:457-464`

A pending admin/custom privileged role is installed on the attacker-controlled new account.

```
membership, _ = BusinessMember.objects.update_or_create(
    business=invitation.business,
    user=user,
    defaults={
        "role": invitation.role,
        "business_role": invitation.business_role,
        "is_active": True,
    },
```

Counterevidence and remaining uncertainty:
- Existing-account invitation requires matching authenticated account, preventing this takeover variant.
- Owner invitations are prohibited; admin invitations remain permitted.
- Random UUID token, expiry/revocation and transaction locks prevent guessing/replay but not disclosure to readers.

#### Dataflow

TEAM.VIEW reader -\> GET team/invitations -\> token/invite_path -\> anonymous POST accept with chosen password -\> active high-role membership -\> login.

**Read permission exposes invitation queryset** — `apps/businesses/views.py:359-361`

TEAM.VIEW alone selects invitations; no manage permission is required to list.

```
def get_queryset(self):
    queryset = self.queryset.filter(business_id__in=self.accessible_business_ids(Actions.VIEW))
    return self.filter_requested_business(queryset)
```

**Serializer exposes the bearer capability** — `apps/businesses/serializers.py:325-338`

Read-only prevents writes but still returns token and token-bearing path to the team reader.

```
    "delivery_channel",
    "token",
    "invite_path",
    "expires_at",
    "accepted_at",
    "revoked_at",
    "status",
    "created_at",
    "updated_at",
]
read_only_fields = ["token", "invited_by", "expires_at", "accepted_at", "revoked_at", "created_at", "updated_at"]

def get_invite_path(self, obj):
    return f"/invite/{obj.token}"
```

**New account password chosen by token holder** — `apps/businesses/views.py:438-451`

No separate proof of email ownership is needed for the new account; token secrecy is the authority.

```
if user is None:
    if request.user.is_authenticated:
        raise PermissionDenied("Sign out before accepting an invitation for a new account.")
    password = serializer.validated_data.get("password")
    if not password:
        raise ValidationError({"password": "A password is required for a new account."})
    user = User.objects.create_user(
        username=invitation.email,
        email=invitation.email,
        password=password,
        full_name=full_name,
        phone=phone,
        role=_user_role_for_business_member(invitation.role),
    )
```

**Invitation grants membership role** — `apps/businesses/views.py:457-464`

A pending admin/custom privileged role is installed on the attacker-controlled new account.

```
membership, _ = BusinessMember.objects.update_or_create(
    business=invitation.business,
    user=user,
    defaults={
        "role": invitation.role,
        "business_role": invitation.business_role,
        "is_active": True,
    },
```

#### Reachability

Requires same-tenant reader role and unconsumed high-privilege invitation to an email not yet registered. No victim mailbox access is necessary after token disclosure.

#### Severity

**Medium** — Escalation from team reader to tenant admin has high impact, but requires a pending higher-privilege invitation for a new account in the same tenant. Conditional likelihood and same-tenant scope reduce severity.

No pending new-account high-role invitation removes the immediate escalation; exposing tokens across tenants would raise severity.

#### Remediation

Use a metadata-only serializer for list/detail readers. Reveal invitation capabilities only to explicitly authorized managers when issuing/reissuing them; consider recipient email proof before elevated-role acceptance.

Tests:
- TEAM.VIEW-only list/detail must omit token and invite_path.
- Reader cannot consume a manager-only new-admin invitation; matching existing-account safeguards remain.

<a id="finding-19"></a>

### [19] Ordinary members can delete businesses that lack protective dependent records

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Inspected complete view class, membership guard, actual DRF destruction mixin and model relationships; no DELETE was executed. |
| Category | Missing authorization for destructive tenant operation |
| CWE | CWE-862 |
| Affected lines | apps/businesses/views.py:47-52, apps/core/permissions.py:54-68, .venv/Lib/site-packages/rest_framework/mixins.py:85-95, config/urls.py:135 |

#### Summary

An active nonadministrator member can send `DELETE /api/businesses/{id}/`. `BusinessViewSet` uses a membership guard but inherits unrestricted generic destruction. Where no direct or indirect PROTECT relationships block collection, the business and cascading configuration, memberships, clients and audit records are deleted without administrative authorization.

#### Root Cause

The business resource uses plain ModelViewSet rather than the action-authorizing tenant viewset. Its queryset includes active members and its object permission verifies only membership; neither checks DELETE authority. Only update has a SETTINGS.UPDATE check. Inherited DRF destruction therefore reaches model deletion, subject only to relational PROTECT constraints rather than role policy.

**Business uses unguarded generic deletion** — `apps/businesses/views.py:47-75`

Membership-scoped ModelViewSet implements update authorization but inherits generic destruction unchanged.

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("owner") or self.request.user
        business = serializer.save(owner=owner)
        BusinessMember.objects.get_or_create(
            business=business,
            user=owner,
            defaults={"role": BusinessMember.Roles.OWNER, "is_active": True},
        )
        from apps.crm.services import ensure_default_pipeline

        ensure_default_pipeline(business)
        ensure_default_roles(business)
        write_audit_log(self.request, AuditLog.Actions.CREATE, business)

    @transaction.atomic
    def perform_update(self, serializer):
        # Refresh under the same lock as platform detail corrections. A serializer
        # loaded before that correction must not save stale unrelated fields.
        serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
        assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
        business = serializer.save()
        write_audit_log(self.request, AuditLog.Actions.UPDATE, business)
```

**All active members see the tenant** — `apps/core/permissions.py:25-39`

The target business appears for any active member, independently of role.

```
def accessible_businesses(user):
    from apps.businesses.models import Business
    from apps.core.models import SupportAccessGrant

    if platform_admin_has_global_access(user):
        return Business.objects.all()

    owned_query = Business.objects.filter(owner=user)
    membership_query = Business.objects.filter(members__user=user, members__is_active=True)
    support_query = Business.objects.filter(
        support_access_grants__user=user,
        support_access_grants__is_active=True,
        support_access_grants__expires_at__gt=timezone.now(),
    )
    return (owned_query | membership_query | support_query).distinct()
```

**Object guard checks membership only** — `apps/core/permissions.py:42-68`

Business object access grants no additional action-specific deletion check.

```
def user_can_access_business(user, business):
    if platform_admin_has_global_access(user):
        return True
    if not user or not user.is_authenticated or business is None:
        return False
    return (
        business.owner_id == user.id or
        business.members.filter(user=user, is_active=True).exists()
        or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
    )


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        business = getattr(obj, "business", None)

        if business is None and obj.__class__.__name__ == "Business":
            business = obj
        if business is None and hasattr(obj, "conversation"):
            business = obj.conversation.business
        if business is None and hasattr(obj, "bot"):
            business = obj.bot.business

        return user_can_access_business(request.user, business)
```

**Inherited destroy deletes the model** — `.venv/Lib/site-packages/rest_framework/mixins.py:85-95`

Generic destroy resolves the permitted object and calls instance.delete.

```
class DestroyModelMixin:
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
```

**Tenant audit records are cascading children** — `apps/core/models.py:43-50`

Deleting a business with no protective relationships also removes its business-linked audit records.

```
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=Actions.choices)
    category = models.CharField(max_length=32, choices=Categories.choices, default=Categories.DATA)
```

#### Validation

Verified route registration, no destroy/method restriction in BusinessViewSet or custom Business.delete override, membership acceptance and inherited instance.delete sink. Reviewed PROTECT declarations and narrowed impact to businesses without those dependencies.

Validation method: Offline source and ORM relationship inspection

**Business uses unguarded generic deletion** — `apps/businesses/views.py:47-75`

Membership-scoped ModelViewSet implements update authorization but inherits generic destruction unchanged.

```
class BusinessViewSet(ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Business.objects.all() if platform_admin_has_global_access(self.request.user) else accessible_businesses(self.request.user)

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("owner") or self.request.user
        business = serializer.save(owner=owner)
        BusinessMember.objects.get_or_create(
            business=business,
            user=owner,
            defaults={"role": BusinessMember.Roles.OWNER, "is_active": True},
        )
        from apps.crm.services import ensure_default_pipeline

        ensure_default_pipeline(business)
        ensure_default_roles(business)
        write_audit_log(self.request, AuditLog.Actions.CREATE, business)

    @transaction.atomic
    def perform_update(self, serializer):
        # Refresh under the same lock as platform detail corrections. A serializer
        # loaded before that correction must not save stale unrelated fields.
        serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
        assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
        business = serializer.save()
        write_audit_log(self.request, AuditLog.Actions.UPDATE, business)
```

**All active members see the tenant** — `apps/core/permissions.py:25-39`

The target business appears for any active member, independently of role.

```
def accessible_businesses(user):
    from apps.businesses.models import Business
    from apps.core.models import SupportAccessGrant

    if platform_admin_has_global_access(user):
        return Business.objects.all()

    owned_query = Business.objects.filter(owner=user)
    membership_query = Business.objects.filter(members__user=user, members__is_active=True)
    support_query = Business.objects.filter(
        support_access_grants__user=user,
        support_access_grants__is_active=True,
        support_access_grants__expires_at__gt=timezone.now(),
    )
    return (owned_query | membership_query | support_query).distinct()
```

**Object guard checks membership only** — `apps/core/permissions.py:42-68`

Business object access grants no additional action-specific deletion check.

```
def user_can_access_business(user, business):
    if platform_admin_has_global_access(user):
        return True
    if not user or not user.is_authenticated or business is None:
        return False
    return (
        business.owner_id == user.id or
        business.members.filter(user=user, is_active=True).exists()
        or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
    )


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        business = getattr(obj, "business", None)

        if business is None and obj.__class__.__name__ == "Business":
            business = obj
        if business is None and hasattr(obj, "conversation"):
            business = obj.conversation.business
        if business is None and hasattr(obj, "bot"):
            business = obj.bot.business

        return user_can_access_business(request.user, business)
```

**Inherited destroy deletes the model** — `.venv/Lib/site-packages/rest_framework/mixins.py:85-95`

Generic destroy resolves the permitted object and calls instance.delete.

```
class DestroyModelMixin:
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
```

**Tenant audit records are cascading children** — `apps/core/models.py:43-50`

Deleting a business with no protective relationships also removes its business-linked audit records.

```
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=Actions.choices)
    category = models.CharField(max_length=32, choices=Categories.choices, default=Categories.DATA)
```

Counterevidence and remaining uncertainty:
- Direct PROTECT relationships include payments, support cases, billing offers/orders, ownership transfers and account recovery.
- Indirect PROTECT includes Lead.client, Deal.client/pipeline/stage, Conversation.client, Appointment.client/service/branch and branch/AI relationships; these can abort business collection even when both records are business-owned.
- No claim that every mature business can be deleted or that existing protected leads/deals cascade successfully.

Limitations:
- No runtime ORM deletion or destructive API request.

#### Dataflow

Member JWT → business queryset → membership object check → inherited destroy → Business.delete and eligible CASCADE children.

#### Reachability

An active operator/specialist targets their own tenant ID with DELETE; deletion succeeds only for a business with no applicable PROTECT blockers, such as a new tenant with unreferenced clients/configuration.

#### Severity

**Medium** — Destructive same-tenant privilege escalation has high impact but applies only to businesses without protective dependencies. Existing leads/deals/appointments, billing/support/recovery or other protected relationships can stop the ORM deletion; this materially narrows likely affected tenants.

Proof that ordinary populated tenants remain deletable would increase severity; disabling generic deletion or enforcing an authorized lifecycle removes the path.

#### Remediation

Disable generic business DELETE and use an explicit owner-authorized lifecycle operation with current permission, recent authentication, dependency-aware archival/deletion and durable audit.

Tests:
- Operator and specialist DELETE against a business without protected children must be denied.
- Test permitted lifecycle behavior separately from incidental PROTECT exceptions.

<a id="finding-20"></a>

### [20] An approved AI request can be reused for a different command

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Mutable approval authorization |
| CWE | CWE-863 |
| Affected lines | apps/ai_core/views.py:115-130, apps/ai_core/serializers.py:153-180, apps/ai_core/crm_approval.py:9-22 |

#### Summary

Generic PATCH can replace an approved request's tool log, payload fingerprint and expiry while preserving its prior decision, allowing a user without pipeline APPROVE to execute a new command under an old approval.

#### Root Cause

ApprovalRequestViewSet inherits generic update using AI_AUTOMATION permissions. Its serializer protects decision status/approver but not the command reference, action, payload or validity interval. Execution compares the new command with those mutable values, so the comparison no longer proves what the approver authorized.

**Approval resource inherits generic update** — `apps/ai_core/views.py:115-130`

The access resource is AI_AUTOMATION, independent of pipeline APPROVE.

```
class ApprovalRequestViewSet(TenantModelViewSet):
    queryset = ApprovalRequest.objects.select_related(
        "business",
        "requested_by",
        "approved_by",
        "rejected_by",
        "ai_request_log",
        "ai_tool_call_log",
    )
    serializer_class = ApprovalRequestSerializer
    access_resource = Resources.AI_AUTOMATION
    action_permission_map = {
        **TenantModelViewSet.action_permission_map,
        "approve": Actions.APPROVE,
        "reject": Actions.APPROVE,
    }
```

**Command and payload remain writable** — `apps/ai_core/serializers.py:153-180`

Only decision fields are read-only, and validation checks business identity without invalidating prior approval.

```
class ApprovalRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)
    rejected_by_email = serializers.EmailField(source="rejected_by.email", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "requested_by",
            "status",
            "approved_by",
            "approved_at",
            "rejected_by",
            "rejected_at",
        ]

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        ai_request_log = attrs.get("ai_request_log") if "ai_request_log" in attrs else getattr(self.instance, "ai_request_log", None)
        ai_tool_call_log = attrs.get("ai_tool_call_log") if "ai_tool_call_log" in attrs else getattr(self.instance, "ai_tool_call_log", None)
        if ai_request_log and business and ai_request_log.business_id != business.id:
            raise serializers.ValidationError({"ai_request_log": "AI request log must belong to the selected business."})
        if ai_tool_call_log and business and ai_tool_call_log.business_id != business.id:
            raise serializers.ValidationError({"ai_tool_call_log": "AI tool call must belong to the selected business."})
        return attrs
```

**Execution trusts mutable approval snapshot** — `apps/ai_core/crm_approval.py:9-22`

The current fingerprint matches attacker-replaced approval data, not an immutable decision record.

```
def validate_locked_approval(log, user, approval_id):
    from apps.ai_core.tool_registry import tool_call_fingerprint
    assert_can(user, log.business, Resources.AI_PIPELINE, Actions.EXECUTE, obj=log)
    approval = ApprovalRequest.objects.select_for_update().filter(pk=approval_id,
        business=log.business, ai_tool_call_log=log, requested_by=user,
        action_type=ApprovalRequest.ActionTypes.AI_PIPELINE).first()
    if (approval is None or log.user_id != user.pk
            or approval.status not in {ApprovalRequest.Statuses.APPROVED, ApprovalRequest.Statuses.EXECUTED}
            or (approval.expires_at and approval.expires_at <= timezone.now())
            or not isinstance(approval.payload, dict)
            or approval.payload.get("tool_fingerprint") != tool_call_fingerprint(log)
            or approval.approved_by_id is None):
        raise PermissionDenied("A current approval for this exact command is required.")
    assert_can(approval.approved_by, log.business, Resources.AI_PIPELINE, Actions.APPROVE, obj=log)
```

#### Validation

Tenant ownership cannot be changed; requester, approver's current authority and CRM object permissions still apply. Default owners/admins already approve, so the meaningful gain requires distinct custom permissions. Existing fingerprint tests changing only the tool do not cover writable approval state.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

AI_AUTOMATION MANAGE -\> PATCH old approved request/tool+fingerprint -\> pipeline EXECUTE -\> locked validator accepts rewritten snapshot -\> new command handler

- **Outcome:** Bypasses fresh exact-command approval and attributes a new mutation to the old approver.

#### Reachability

Same-business actor with AI_AUTOMATION MANAGE, pipeline SUGGEST/EXECUTE and ordinary CRM mutation permissions but not pipeline APPROVE; owns an approval whose approver remains authorized.

- **Attacker:** Same-business actor with AI_AUTOMATION MANAGE, pipeline SUGGEST/EXECUTE and ordinary CRM mutation permissions but not pipeline APPROVE; owns an approval whose approver remains authorized.

#### Severity

**Low** — Same-business approval integrity violation requires a specific custom permission split, a historical approval and ordinary mutation rights; no cross-tenant or broader CRM permission bypass is established.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Make command identity, fingerprint, action and validity interval immutable after decision; edited proposals must create a new pending approval with cleared decision authority. Restrict generic updates and validate an immutable snapshot under the execution lock.

Tests:
- Custom actor without pipeline APPROVE cannot rebind an approved request to a second proposal or extend expiry; second execution requires fresh approval.

<a id="finding-21"></a>

### [21] Concurrent attachment uploads exceed the storage entitlement

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | The check and save are separate, with no reservation/tenant lock in the view, quota helper or serializer; no concurrency test was run. |
| Category | Non-atomic resource quota enforcement |
| CWE | CWE-362 |
| Affected lines | apps/core/file_attachment_views.py:58-60, apps/billing/storage.py:19-25, apps/billing/entitlements.py:121-125, apps/core/serializers.py:354-360 |

#### Summary

Concurrent uploads for the same tenant can all pass the storage SUM check before any new attachment is saved. Each then persists its file, leaving usage above the purchased quota.

#### Root Cause

Quota check and durable allocation are not one serialized admission operation.

**Quota admission and save are unlocked** — `apps/core/file_attachment_views.py:58-60`

Concurrent requests can read the same free capacity before either creates the counted row.

```
uploaded_file = serializer.validated_data["file"]
assert_storage_quota_allows(business, getattr(uploaded_file, "size", 0) or 0)
attachment = serializer.save(uploaded_by=self.request.user)
```

**Usage reads only already committed attachments** — `apps/billing/storage.py:19-25`

The aggregate does not reserve bytes for in-flight uploads.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

#### Validation

Validated helper -\> entitlement comparison -\> serializer/model create path. No atomic reservation or Business lock exists across the check and insert.

Validation method: Offline static concurrency reasoning

**Quota admission and save are unlocked** — `apps/core/file_attachment_views.py:58-60`

Concurrent requests can read the same free capacity before either creates the counted row.

```
uploaded_file = serializer.validated_data["file"]
assert_storage_quota_allows(business, getattr(uploaded_file, "size", 0) or 0)
attachment = serializer.save(uploaded_by=self.request.user)
```

**Usage reads only already committed attachments** — `apps/billing/storage.py:19-25`

The aggregate does not reserve bytes for in-flight uploads.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

Counterevidence and remaining uncertainty:
- Per-file 10MiB limit remains.
- Sequential requests after visible overshoot are denied.
- Existing storage test covers sequential rejection, not concurrent admission.

#### Dataflow

Parallel permitted uploads -\> same SUM usage -\> all pass usage+size limit -\> independent saves -\> quota overshoot.

**Quota admission and save are unlocked** — `apps/core/file_attachment_views.py:58-60`

Concurrent requests can read the same free capacity before either creates the counted row.

```
uploaded_file = serializer.validated_data["file"]
assert_storage_quota_allows(business, getattr(uploaded_file, "size", 0) or 0)
attachment = serializer.save(uploaded_by=self.request.user)
```

**Usage reads only already committed attachments** — `apps/billing/storage.py:19-25`

The aggregate does not reserve bytes for in-flight uploads.

```
def get_storage_usage_bytes(business):
    return (
        FileAttachment.objects.filter(business=business)
        .aggregate(total=Sum("size"))
        .get("total")
        or 0
    )
```

#### Reachability

Requires update access to an attachment target and enough remaining space for one upload; only same-tenant quota is crossed.

#### Severity

**Low** — This is a same-tenant quota bypass with limited overshoot bounded by concurrently admitted, individually capped uploads. It does not establish unlimited storage or cross-tenant compromise.

A repeatable unbounded allocation path or demonstrated shared-service exhaustion would raise impact.

#### Remediation

Reserve exact bytes atomically under a tenant lock before durable persistence, with consistent rollback/cleanup. Use the reservation for every upload path.

Tests:
- Parallel uploads exceeding combined remaining capacity must admit only those that fit.

<a id="finding-22"></a>

### [22] Public lead forms disclose whether a contact is already a client

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Public response directly exposes the result of tenant client matching. |
| Category | Observable response discrepancy |
| CWE | CWE-204 |
| Affected lines | apps/leads/views.py:508-540, apps/leads/forms_service.py:63-64, apps/clients/services.py:23-61 |

#### Summary

An anonymous visitor can submit a chosen contact to an active lead form and read duplicate_warning to learn whether that person already existed in the merchant's private client database.

#### Root Cause

The anonymous form normalizes supplied contact fields and performs tenant-wide deduplication. Its result is appropriate for staff processing but the endpoint returns the duplicate-presence boolean publicly, turning the private lookup into a chosen-contact oracle.

**Intake checks supplied contact against private clients** — `apps/leads/forms_service.py:63`

Phone/email supplied by an unauthenticated caller selects the private membership predicate returned to that caller.

```
    duplicates = find_duplicate_clients(lead_form.business, phone=phone, email=email)
    duplicate_rows = duplicate_payload(duplicates, phone=phone, email=email)
```

**Anonymous response reveals duplicate result** — `apps/leads/views.py:540`

The public caller observes whether matching private client records were found before this intake created records.

```
                "duplicate_warning": bool(submission.duplicate_json.get("duplicates")),
```

#### Validation

Confirmed AllowAny active-form submission, exact normalized phone/email matching of nonarchived clients, and response derived from duplicate rows collected before creating a new client.

Validation method: independent static trace

Counterevidence and remaining uncertainty:
- No names or full records appear in this public response.
- Public-form throttle, required fields, active form ID and generated intake records limit stealth/volume.
- Repeated probes change state; the first probe still reveals prior membership.

#### Dataflow

Anonymous chosen phone/email -\> tenant duplicate lookup -\> duplicate_json -\> duplicate_warning response.

#### Reachability

Publicly exposed active form identifier and valid required fields; no account required.

#### Severity

**Low** — Only a membership bit is disclosed per probe, with exact-contact knowledge, throttling and noisy intake side effects; no complete record disclosure.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Return the same public acknowledgement whether or not a duplicate exists. Expose deduplication details only to authorized staff.

Tests:
- Existing and new contact submissions must have indistinguishable duplicate-related public response fields.

<a id="finding-23"></a>

### [23] Changing X-Forwarded-For bypasses anonymous authentication rate limits

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Verified configured throttle classes, installed get_ident implementation and Compose direct binding; no live requests. |
| Category | Authentication attempt restriction bypass |
| CWE | CWE-307 |
| Affected lines | config/settings.py:261-289, .venv/Lib/site-packages/rest_framework/throttling.py:23-41, apps/accounts/auth_views.py:88-93, apps/accounts/views.py:135-139, docker-compose.yml:7-12 |

#### Summary

A client reaching the directly published application can vary `X-Forwarded-For` on each login attempt. DRF uses that supplied string as its throttle identity because `NUM_PROXIES` is unset, selecting a fresh cache bucket without changing the actual client address. The same identity handling applies to anonymous password-reset and public scoped endpoints.

#### Root Cause

Application settings delegate anonymous rate identity to DRF without fixing its proxy trust boundary. The installed default reads the complete forwarded-for header when NUM_PROXIES is None. Compose allows direct client access, preserving an untrusted value as the limit key; scoped rates are consequently per attacker-chosen header rather than per client.

**Only scoped limits configured** — `config/settings.py:261-289`

Settings enable scoped throttles with authentication/public rates but omit a trusted proxy count.

```
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionEpochJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": env("AUTH_LOGIN_RATE", default="10/min"),
        "auth_refresh": env("AUTH_REFRESH_RATE", default="30/min"),
        "auth_social": env("AUTH_SOCIAL_RATE", default="20/min"),
        "auth_signup": env("AUTH_SIGNUP_RATE", default="10/hour"),
        "auth_password_reset": env("AUTH_PASSWORD_RESET_RATE", default="5/hour"),
        "auth_profile": "10/min",
        "auth_email_change": "5/hour",
        "auth_mfa": env("AUTH_MFA_RATE", default="10/min"),
        "public_api": env("PUBLIC_API_RATE", default="120/min"),
        "public_form": env("PUBLIC_FORM_RATE", default="60/min"),
        "public_widget": env("PUBLIC_WIDGET_RATE", default="120/min"),
        "integration_webhook": env("INTEGRATION_WEBHOOK_RATE", default="300/min"),
        "ai_assistant": env("AI_ASSISTANT_RATE", default="30/min"),
    },
}
```

**Untrusted forwarded value selects identity** — `.venv/Lib/site-packages/rest_framework/throttling.py:23-41`

With NUM_PROXIES unset, a client-supplied X-Forwarded-For string becomes the throttle identity.

```
    def get_ident(self, request):
        """
        Identify the machine making the request by parsing HTTP_X_FORWARDED_FOR
        if present and number of proxies is > 0. If not use all of
        HTTP_X_FORWARDED_FOR if it is available, if not use REMOTE_ADDR.
        """
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        num_proxies = api_settings.NUM_PROXIES

        if num_proxies is not None:
            if num_proxies == 0 or xff is None:
                return remote_addr
            addrs = xff.split(',')
            client_addr = addrs[-min(num_proxies, len(addrs))]
            return client_addr.strip()

        return ''.join(xff.split()) if xff else remote_addr
```

**Login uses scoped throttle** — `apps/accounts/auth_views.py:88-103`

Public token login applies auth_login then processes password attempts.

```
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("email") or request.data.get("username") or ""
        user = authenticate(request=request, username=identifier, password=request.data.get("password"))
        if user is None:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            raise AuthenticationFailed("No active account found with the given credentials.", code="no_active_account")
        if requires_mfa(user):
            return Response(start_auth_challenge(user), status=status.HTTP_202_ACCEPTED)

        refresh = issue_session(user, mfa_verified=False, request=request)
        update_last_login(None, user)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        return set_refresh_cookie(Response({"access": str(refresh.access_token)}), str(refresh))
```

**Direct HTTP port is published** — `docker-compose.yml:1-12`

Compose exposes Gunicorn directly, so the supplied topology does not guarantee header rewriting by a trusted proxy.

```
services:
  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
    volumes:
      - static_data:/app/staticfiles
      - media_data:/app/media
    ports:
      - "8000:8000"
```

#### Validation

No NUM_PROXIES configuration or custom identity sanitizer was found in apps/config. Inspected DRF get_ident and scoped login setup plus the bare Gunicorn publication.

Validation method: Offline application/dependency/deployment source trace

**Only scoped limits configured** — `config/settings.py:261-289`

Settings enable scoped throttles with authentication/public rates but omit a trusted proxy count.

```
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionEpochJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": env("AUTH_LOGIN_RATE", default="10/min"),
        "auth_refresh": env("AUTH_REFRESH_RATE", default="30/min"),
        "auth_social": env("AUTH_SOCIAL_RATE", default="20/min"),
        "auth_signup": env("AUTH_SIGNUP_RATE", default="10/hour"),
        "auth_password_reset": env("AUTH_PASSWORD_RESET_RATE", default="5/hour"),
        "auth_profile": "10/min",
        "auth_email_change": "5/hour",
        "auth_mfa": env("AUTH_MFA_RATE", default="10/min"),
        "public_api": env("PUBLIC_API_RATE", default="120/min"),
        "public_form": env("PUBLIC_FORM_RATE", default="60/min"),
        "public_widget": env("PUBLIC_WIDGET_RATE", default="120/min"),
        "integration_webhook": env("INTEGRATION_WEBHOOK_RATE", default="300/min"),
        "ai_assistant": env("AI_ASSISTANT_RATE", default="30/min"),
    },
}
```

**Untrusted forwarded value selects identity** — `.venv/Lib/site-packages/rest_framework/throttling.py:23-41`

With NUM_PROXIES unset, a client-supplied X-Forwarded-For string becomes the throttle identity.

```
    def get_ident(self, request):
        """
        Identify the machine making the request by parsing HTTP_X_FORWARDED_FOR
        if present and number of proxies is > 0. If not use all of
        HTTP_X_FORWARDED_FOR if it is available, if not use REMOTE_ADDR.
        """
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        num_proxies = api_settings.NUM_PROXIES

        if num_proxies is not None:
            if num_proxies == 0 or xff is None:
                return remote_addr
            addrs = xff.split(',')
            client_addr = addrs[-min(num_proxies, len(addrs))]
            return client_addr.strip()

        return ''.join(xff.split()) if xff else remote_addr
```

**Login uses scoped throttle** — `apps/accounts/auth_views.py:88-103`

Public token login applies auth_login then processes password attempts.

```
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("email") or request.data.get("username") or ""
        user = authenticate(request=request, username=identifier, password=request.data.get("password"))
        if user is None:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            raise AuthenticationFailed("No active account found with the given credentials.", code="no_active_account")
        if requires_mfa(user):
            return Response(start_auth_challenge(user), status=status.HTTP_202_ACCEPTED)

        refresh = issue_session(user, mfa_verified=False, request=request)
        update_last_login(None, user)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        return set_refresh_cookie(Response({"access": str(refresh.access_token)}), str(refresh))
```

**Direct HTTP port is published** — `docker-compose.yml:1-12`

Compose exposes Gunicorn directly, so the supplied topology does not guarantee header rewriting by a trusted proxy.

```
services:
  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-3}"
    volumes:
      - static_data:/app/staticfiles
      - media_data:/app/media
    ports:
      - "8000:8000"
```

Counterevidence and remaining uncertainty:
- A gateway that overwrites XFF and prohibits direct backend access defeats this specific bypass.
- Privileged account MFA and password verification remain enforced.
- This is a rate-limit bypass, not demonstrated account compromise.

Limitations:
- Actual production ingress and rate-limit cache topology were not inspected.

#### Dataflow

Client-controlled X-Forwarded-For → DRF get_ident → scoped throttle cache key → repeated login/reset requests.

#### Reachability

Anonymous client with direct HTTP access changes forwarding-header contents across attempts; no account or existing session required.

#### Severity

**Low** — The bypass is straightforward on the supported direct-port topology, but does not by itself reveal credentials or bypass MFA. Meaningful compromise still requires successful guessing or endpoint abuse; gateways that overwrite headers and block direct traffic mitigate it.

Evidence of exploitable weak passwords or high-impact public abuse would increase severity; trusted proxy enforcement and account-oriented throttles reduce it.

#### Remediation

Use REMOTE_ADDR for direct deployments (`NUM_PROXIES=0`) or configure the exact trusted proxy topology and prevent direct ingress. Add account-oriented authentication limits independent of client headers.

Tests:
- Requests from one REMOTE_ADDR with varying untrusted XFF must share the expected throttle bucket.
- Verify trusted proxy forwarding and direct-port denial in the deployment configuration.

<a id="finding-24"></a>

### [24] Mark-all-read changes notifications outside the caller's UPDATE scope (AUD-17)

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Bulk action directly updates the VIEW-scoped queryset, while individual actions explicitly check UPDATE. |
| Category | Incorrect authorization |
| CWE | CWE-863 |
| Affected lines | apps/notifications/views.py:116-121, apps/core/viewsets.py:149-161, apps/businesses/access.py:162-167 |

#### Summary

The bulk mark-all-read action updates every VIEW-visible unread notification, allowing a marketer or custom role to mark other recipients' notifications read despite narrower or denied UPDATE permission.

#### Root Cause

TenantModelViewSet builds list querysets using VIEW. The bulk action's action_permission_map entry is not automatically enforced by collection permissions, and mark_all_read directly updates that read queryset.

**Bulk write uses read queryset** — `apps/notifications/views.py:116`

No action-level UPDATE guard or update-scoped filtering precedes the database mutation.

```
    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        queryset = self.get_queryset().filter(read_at__isnull=True)
        now = timezone.now()
        updated = queryset.update(read_at=now, updated_at=now)
        return Response({"updated": updated})
```

**Individual action checks object UPDATE** — `apps/notifications/views.py:102`

Sibling single-record action enforces the permission the bulk operation omits.

```
        notification = self.get_object()
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.UPDATE, obj=notification)
        notification.mark_read()
```

#### Validation

Confirmed IsTenantMember collection permission checks authentication only, queryset scopes VIEW, and marketer preset grants notifications VIEW business but UPDATE own. Individual actions do not share the omission.

Validation method: independent static source trace

Counterevidence and remaining uncertainty:
- Tenant isolation and conversation recipient exclusion remain.
- Only unread-state timestamps are changed.

#### Dataflow

Authenticated bulk POST -\> VIEW-visible unread rows -\> direct read_at/updated_at update.

#### Reachability

Default marketer or supported custom role with broader notification VIEW than UPDATE; non-conversation notifications demonstrate the gap.

#### Severity

**Low** — Tenant-local, reversible unread-state manipulation with limited impact. Conversation notifications addressed to other users are excluded.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Authorize bulk mutation using UPDATE scope per business and exclude every row outside that scope; reject roles without UPDATE.

Tests:
- A role with VIEW business and UPDATE own must not mark another recipient's notification read.

<a id="finding-25"></a>

### [25] Import previews disclose clients outside read permissions

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Direct source trace establishes caller, guard gap and sink; no runtime execution. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | apps/core/import_export_views.py:46-56, apps/core/import_export.py:686-698, apps/clients/services.py:78-90, apps/core/serializers.py:138-151 |

#### Summary

The immediate create response for client/lead imports returns duplicate client names, phone numbers and emails from a business-wide lookup without enforcing CLIENTS VIEW scope.

#### Root Cause

Import creation checks CREATE then builds preview before returning. duplicate_preview uses an unscoped business-wide duplicate lookup, serializes identity fields into duplicates_json and exposes it through the read-only output field. Actor-only retrieval cannot protect the immediate creation response.

**Create builds preview immediately** — `apps/core/import_export_views.py:46-56`

Entity CREATE alone permits preview before response.

```
    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
```

**Duplicates are looked up without actor** — `apps/core/import_export.py:686-698`

Lookup has only business and caller contact values.

```
def duplicate_preview(job, rows, mapping):
    result = []
    seen = {}
    for index, row in enumerate(rows, start=1):
        payload = mapped_payload(row, mapping, job.entity_type)
        row_key = stable_import_row_key(payload)
        if row_key in seen:
            result.append({"row": index, "payload": payload, "duplicates": [{"id": "", "full_name": f"Duplicate row {seen[row_key]}", "matched_fields": ["file_row"]}]})
            continue
        seen[row_key] = index
        duplicates = find_duplicate_clients(job.business, phone=payload.get("phone"), email=payload.get("email"))
        if duplicates:
            result.append({"row": index, "payload": payload, "duplicates": duplicate_payload(duplicates, phone=payload.get("phone"), email=payload.get("email"))})
```

**Duplicate payload includes private contacts** — `apps/clients/services.py:78-90`

Identity fields are returned to the import preview consumer.

```
        if instagram_id and client.instagram_id == instagram_id:
            matched_fields.append("instagram_id")
        rows.append(
            {
                "id": client.id,
                "full_name": client.full_name,
                "phone": client.phone,
                "email": client.email,
                "matched_fields": matched_fields,
            }
        )
    return rows

```

**Serializer exposes duplicates_json** — `apps/core/serializers.py:138-151`

Read-only output is still disclosed in successful creation responses.

```
        fields = [
            "id",
            "business",
            "actor",
            "actor_email",
            "entity_type",
            "source_file",
            "original_filename",
            "status",
            "mapping_json",
            "preview_json",
            "duplicates_json",
            "errors_json",
            "summary_json",
```

#### Validation

Matches remain tenant-bound and require a supplied matching identifier. Only initial preview rows are used. No later job retrieval is needed to receive create-response duplicates.

Validation method: offline static source trace

Limitations:
- No application execution or network reproduction.

#### Dataflow

uploaded phone/email -\> create import -\> duplicate_preview -\> business clients -\> duplicate_payload -\> duplicates_json response

- **Outcome:** Disclosure of client IDs/names/phone/email outside current read scope.

#### Reachability

Business member with client or lead import CREATE and absent or restricted clients VIEW.

- **Attacker:** Business member with client or lead import CREATE and absent or restricted clients VIEW.

#### Severity

**Low** — Same-business disclosure requires import CREATE and a known or guessed matching contact; previews are bounded but can reveal names and alternate contacts absent VIEW permission.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Apply current CLIENTS VIEW scope and field privacy before duplicate suggestions; use nonidentifying outcomes for inaccessible matches.

Tests:
- CREATE-only and narrowed-VIEW users must not receive identifying duplicate fields for inaccessible clients.

<a id="finding-26"></a>

### [26] Merchant settings can clear a platform business restriction

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Mass assignment of operational status |
| CWE | CWE-915 |
| Affected lines | apps/businesses/serializers.py:22-27, apps/businesses/views.py:67-74, apps/billing/application.py:31-40 |

#### Summary

A merchant with SETTINGS UPDATE can PATCH a blocked/inactive Business to active through the generic serializer, bypassing the business_restricted condition relied on by billing application.

#### Root Cause

BusinessSerializer exposes all model fields except owner/timestamps. perform_update authorizes ordinary SETTINGS UPDATE then saves status without a platform-only transition. apply_order later trusts that same status for its operational restriction.

**Serializer exposes status** — `apps/businesses/serializers.py:22-27`

All fields except owner/timestamps are writable.

```
class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = "__all__"
        read_only_fields = ["owner", "created_at", "updated_at"]
    read_only_fields = ["owner", "created_at", "updated_at"]
```

**Merchant permission saves supplied status** — `apps/businesses/views.py:67-74`

SETTINGS UPDATE is sufficient for the generic mutation.

```

    @transaction.atomic
    def perform_update(self, serializer):
        # Refresh under the same lock as platform detail corrections. A serializer
        # loaded before that correction must not save stale unrelated fields.
        serializer.instance = Business.objects.select_for_update().get(pk=serializer.instance.pk)
        assert_can(self.request.user, serializer.instance, Resources.SETTINGS, Actions.UPDATE)
        business = serializer.save()
```

**Billing trusts operational status** — `apps/billing/application.py:31-40`

Clearing status removes this specific restriction while other payment conditions remain.

```
    now = timezone.now()
    if order.period_start > now:
        return block(order, "period_not_started", actor=actor, case=case)
    if order.period_end <= now:
        return block(order, "period_expired", actor=actor, case=case)
    if order.business.status in {"blocked", "inactive"}:
        return block(order, "business_restricted", actor=actor, case=case)
    subscription = Subscription.objects.select_for_update().filter(business_id=business_id).first()
    if subscription and subscription.status in {"paused", "cancelled"}:
        return block(order, "subscription_restricted", actor=actor, case=case)
```

#### Validation

Does not forge payment or directly grant a plan. Commerce gate, confirmed financial state, dates, subscription state/revision and plan terms still apply. The finding concerns the separate status boundary.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

merchant PATCH status=active -\> serializer.save -\> apply_order checks status -\> restriction no longer blocks

- **Outcome:** Clears platform operational status; otherwise valid billing orders can pass the business restriction.

#### Reachability

Owner/admin or custom SETTINGS UPDATE member of a blocked/inactive business.

- **Attacker:** Owner/admin or custom SETTINGS UPDATE member of a blocked/inactive business.

#### Severity

**Low** — Merchant/platform authority crossing is real but concrete billing impact requires commerce enabled and an otherwise fully valid confirmed order; payment and subscription checks remain.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Use a merchant-writable settings allowlist and reserve operational status for the platform lifecycle service.

Tests:
- Merchant PATCH must not alter blocked/inactive status; authorized platform transition and billing restrictions must remain consistent.

<a id="finding-27"></a>

### [27] Social login retains an attacker’s pre-registered password when MFA is optional

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Source establishes unverified local signup, email-based social linking and preservation of the password; applicability is explicitly conditional. |
| Category | Unverified account linking |
| CWE | CWE-287 |
| Affected lines | apps/accounts/views.py:219-234, apps/accounts/social_auth.py:167-193, apps/accounts/views.py:117-123 |

#### Summary

If privileged MFA is disabled and no factor is enrolled, an attacker can pre-register a victim email, then retain password access after the victim’s social identity is automatically linked to that account.

#### Root Cause

A local account can claim an email before proving ownership. get_or_create_social_user then treats email equality as sufficient linkage and preserves existing password/session credentials. In the no-MFA configuration this lets both the original password holder and actual social identity owner access the same account.

**Signup accepts email without ownership proof** — `apps/accounts/views.py:219-234`

Attacker chooses victim email and a known password for an active local account.

```
        serializer = OwnerSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            return Response({"email": ["User with this email already exists."]}, status=400)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=data["password"],
            full_name=data.get("full_name", "").strip(),
            phone=data.get("phone", "").strip(),
            role=User.Roles.BUSINESS_OWNER,
            is_active=True,
        )
```

**Social identity linked by email** — `apps/accounts/social_auth.py:167-193`

An existing matching local user keeps its password while receiving the verified provider identity.

```
    user = User.objects.filter(email=claims.email).first()
    created = False
    if user is None:
        user = User.objects.create_user(
            username=_unique_username(claims.email),
            email=claims.email,
            password=None,
            full_name=claims.full_name,
            role=User.Roles.BUSINESS_OWNER,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        created = True
        _ensure_first_business(user)
    elif claims.full_name and not user.full_name:
        user.full_name = claims.full_name
        user.save(update_fields=["full_name"])

    SocialIdentity.objects.create(
        user=user,
        provider=claims.provider,
        subject=claims.subject,
        email=claims.email,
        email_verified=claims.email_verified,
        raw_claims=claims.claims,
    )
    return user, created
```

**Optional-MFA path issues session** — `apps/accounts/views.py:117-123`

With MFA disabled and absent, victim signs into the shared account without removing attacker credentials.

```
        user, created = get_or_create_social_user(claims)
        if requires_mfa(user):
            return Response(
                {**start_auth_challenge(user), "created": created, "provider": claims.provider},
                status=202,
            )
        refresh = issue_session(user, mfa_verified=False, request=request)
```

**Production MFA default constrains impact** — `config/settings.py:303-306`

Production/staging default to requiring MFA, a significant deployment condition.

```
AUTH_PRIVILEGED_MFA_REQUIRED = env.bool(
    "AUTH_PRIVILEGED_MFA_REQUIRED",
    default=IS_PRODUCTION_LIKE_ENVIRONMENT,
)
```

#### Validation

Validated conditional path. Production privileged MFA interrupts password-only access; MfaEnrollmentConfirmView revokes earlier refresh sessions and requires the newly enrolled factor thereafter. This is not reported as an unconditional production takeover.

Validation method: offline static source trace

Limitations:
- No social provider contacted; actual deployment MFA policy not inspected.

#### Dataflow

unverified local email/password -\> email-match social link -\> unchanged local credentials -\> later password login

- **Outcome:** Attacker retains access to victim-used account

#### Reachability

Requires AUTH_PRIVILEGED_MFA_REQUIRED=False, no confirmed factor, configured social login, prior unused email, and later victim use.

#### Severity

**Low** — Potential account-data compromise requires pre-registration, a later victim social login and an optional no-MFA configuration; production defaults require privileged MFA.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Verify local email ownership before activating or linking accounts. Require explicit authenticated linking; do not silently retain unverified pre-existing credentials when a verified identity claims the address.

Tests:
- Pre-register unverified email then social-login as its verified owner; ensure attacker credentials cannot remain valid.
- Preserve MFA enrollment revocation and existing verified-account linking rules.

<a id="finding-28"></a>

### [28] Imports modify existing clients without client UPDATE permission

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | CREATE-only import authorization, default marketer grants and direct client save are source-confirmed. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | apps/core/import_export.py:147-156, apps/core/import_export.py:379-385, apps/core/import_export.py:405-412, apps/core/import_export.py:439-455, apps/core/import_export.py:562-596, apps/businesses/access.py:162-164 |

#### Summary

A default marketer can import a lead matching an existing client and fill that client's missing contact fields despite having only client VIEW permission. Client and deal imports share the same unguarded mutation helper.

#### Root Cause

Preview/confirm require CREATE on the imported resource. Row handlers match existing clients by phone/email across the tenant and call an actor-free helper that writes missing fields. The same flow handles client, lead and deal imports, so existing-client side effects bypass the permissions enforced by normal client updates.

**Default read-only client role can create leads** — `apps/businesses/access.py:162`

A supported default role reaches lead import while lacking client UPDATE.

```
    BusinessMember.Roles.MARKETER: {
        Resources.CLIENTS: {Actions.VIEW: RolePermission.Scopes.BUSINESS},
        Resources.LEADS: {Actions.VIEW: RolePermission.Scopes.BUSINESS, Actions.CREATE: RolePermission.Scopes.BUSINESS},
```

**Confirmation authorizes only entity CREATE** — `apps/core/import_export.py:153`

The importer verifies CREATE for the selected imported entity, not UPDATE on existing related clients.

```
        resource = import_resource(job.entity_type)
        assert_can(request.user, job.business, resource, Actions.CREATE)
        assert_resource_enabled(job.business, resource)
```

**Lead import mutates matched client** — `apps/core/import_export.py:408`

Attacker-supplied contact identifiers resolve a tenant client and flow into a mutation helper without actor context.

```
    client = find_import_client(job.business, payload)
    if client:
        fill_missing_client_fields(client, payload)
```

**Direct client write** — `apps/core/import_export.py:583`

Missing fields and OTHER source can be overwritten with no current client object UPDATE or field-privacy check.

```
def fill_missing_client_fields(client, payload):
    changed_fields = []
    for field in ["full_name", "phone", "email", "notes"]:
        value = payload.get(field)
        if value and not getattr(client, field):
            setattr(client, field, value)
            changed_fields.append(field)
    source = normalize_client_source(payload.get("source"))
    if source and source != client.source and client.source == Client.Sources.OTHER:
        client.source = source
        changed_fields.append("source")
    if changed_fields:
        client.save(update_fields=[*changed_fields, "updated_at"])
    return bool(changed_fields)
```

#### Validation

Verified ImportJob retrieval uses client VIEW plus actor ownership, the marketer has client VIEW and lead CREATE, and confirm dispatches to the lead row handler under CREATE-only authorization.

Validation method: independent static source trace

Counterevidence and remaining uncertainty:
- All client lookup remains tenant constrained.
- Only missing profile fields and OTHER source change; populated values are retained.
- Import locks, antivirus and transactions are present but do not authorize client updates.

Limitations:
- No runtime role/CSV test executed.

#### Dataflow

Lead CSV containing known client phone and new email -\> CREATE-authorized import -\> tenant client match -\> direct fill_missing_client_fields save.

#### Reachability

Default marketer with clients VIEW business/leads CREATE, or a custom client CREATE role denied UPDATE; operational scanner; an existing client with a matching identifier and blank target field.

#### Severity

**Low** — Concrete tenant-local record integrity violation; nonempty fields are generally preserved. Constrained impact warrants low despite reachable default marketer role.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Pass the actor through import row services and require current client UPDATE and field permissions before changing matched clients. Reject or skip unauthorized upserts consistently across client, lead and deal imports.

Tests:
- Default marketer lead import must not fill another client's email when client UPDATE is denied.
- Client/deal imports must check UPDATE and private-note permissions for existing matches.

<a id="finding-29"></a>

### [29] Bulk read action modifies notifications outside the caller’s update scope

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Source traces collection action through VIEW-only queryset; IsTenantMember checks only authentication and no update guard executes. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | apps/notifications/views.py:116-121, apps/core/viewsets.py:165-172, apps/core/permissions.py:59-61, apps/businesses/access.py:162-167 |

#### Summary

A member with notification VIEW access can mark every visible notification read using mark-all-read even when UPDATE is denied or restricted to their own notifications (AUD-17).

#### Root Cause

mark_all_read uses get_queryset, which applies tenant membership, resource VIEW and VIEW scope. The action_permission_map declaration is only consumed on serializer writes; the direct queryset.update does not invoke it. Collection permission checks authenticate without enforcing UPDATE.

**Bulk mutation omits update permission** — `apps/notifications/views.py:116`

An authenticated collection POST directly mutates the read-visible set, bypassing object-level UPDATE checks.

```
    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        queryset = self.get_queryset().filter(read_at__isnull=True)
        now = timezone.now()
        updated = queryset.update(read_at=now, updated_at=now)
        return Response({"updated": updated})
```

**Individual action enforces update authorization** — `apps/notifications/views.py:102-106`

Sibling individual mutation enforces the missing permission, confirming intended write invariant.

```
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.UPDATE, obj=notification)
        notification.mark_read()
```

#### Validation

Reviewed NotificationViewSet, TenantModelViewSet, IsTenantMember and permission presets. Marketer VIEW BUSINESS and UPDATE OWN remain different because role_allows prioritizes explicit action scope over MANAGE fallback. Custom VIEW-only roles are also affected. Inbox-specific exclusions remain effective; cross-tenant writes are not established.

Validation method: offline static source trace

Limitations:
- No requests executed.

#### Dataflow

collection POST -\> get_queryset(VIEW) -\> filter unread -\> bulk UPDATE

- **Source:** authenticated member’s POST

- **Sink:** Notification queryset.update

- **Outcome:** Unauthorized read-state changes to other users’ visible non-Inbox notifications

#### Reachability

Requires active membership and resource VIEW; marketer preset or custom narrowed UPDATE role suffices. Tenant and Inbox filters constrain impact.

- **Attacker:** Business member with broader VIEW than UPDATE scope

#### Severity

**Low** — Direct same-business integrity violation affecting notification read state; tenant filtering remains and impact is limited.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Enforce UPDATE and its object scope for every affected business before bulk mutation; apply branch restrictions as applicable and retain tenant/Inbox filters.

Tests:
- Deny VIEW-only bulk writes.
- Ensure marketer cannot alter another recipient’s notifications outside UPDATE OWN.
- Preserve allowed own writes and cross-business denial.

<a id="finding-30"></a>

### [30] Cross-origin login can seed another account’s refresh cookie

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | medium |
| Confidence rationale | Static framework/application trace; browser navigation was not reproduced. |
| Category | Login CSRF |
| CWE | CWE-352 |
| Affected lines | apps/accounts/auth_views.py:88-103, frontend/src/lib/storage.ts:5-10, frontend/src/api/token.ts:39-46, frontend/src/api/token.ts:201-212 |

#### Summary

The login endpoint accepts form credentials without CSRF/origin validation and sets a refresh cookie. A cross-site top-level form submission with attacker credentials can seed the victim browser; a fresh frontend load restores that account.

#### Root Cause

TokenObtainPairView inherits DRF CSRF exemption and empty authentication classes; default FormParser accepts ordinary form posts. The custom post authenticates the supplied account and sets the refresh cookie without origin binding. Startup identity is memory-only and null, so refresh identity comparison does not reject an attacker account on a fresh load.

**Login accepts supplied credentials and sets cookie** — `apps/accounts/auth_views.py:88-103`

No request-origin/CSRF binding precedes cookie creation.

```
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("email") or request.data.get("username") or ""
        user = authenticate(request=request, username=identifier, password=request.data.get("password"))
        if user is None:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            raise AuthenticationFailed("No active account found with the given credentials.", code="no_active_account")
        if requires_mfa(user):
            return Response(start_auth_challenge(user), status=status.HTTP_202_ACCEPTED)

        refresh = issue_session(user, mfa_verified=False, request=request)
        update_last_login(None, user)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        return set_refresh_cookie(Response({"access": str(refresh.access_token)}), str(refresh))
```

**Fresh page has no expected identity** — `frontend/src/lib/storage.ts:5-10`

Identity persistence cannot reject an unsolicited cookie on initial load.

```
const USER_EMAIL_KEY = "ai_smb_user_email";

let accessToken: string | null = null;
let sessionGeneration = 0;
let userId: string | null = null;
export const AUTH_EXPIRED_EVENT = "zani:auth-expired";
```

**Null expected identity passes** — `frontend/src/api/token.ts:39-46`

The client consistency guard returns when a new page has no known user.

```
function assertSameRefreshUser(access: string, originalAccess: string | null) {
  const previous = readSessionIdentity(originalAccess);
  const incoming = readSessionIdentity(access);
  if (previous?.sessionId && previous.sessionId !== incoming?.sessionId) {
    throw new SessionIdentityChangedError("Refresh device session changed");
  }
  const expected = tokenStorage.getUserId();
  if (expected === null) return;
```

**Cookie refresh is adopted** — `frontend/src/api/token.ts:201-212`

Fresh restoration stores the access token derived from the cookie.

```
    return axios
      .post<{ access: string }>(
        `${baseURL}/api/auth/token/refresh/`,
        activity ? { activity: true } : {},
        cookieRequestOptions,
      );
  })
      .then(({ data }) => {
        assertCurrentSession(generation);
        assertSameRefreshUser(data.access, originalAccess);
        tokenStorage.setAccess(data.access);
        return data.access;
```

#### Validation

SameSite=Lax prevents many cross-site cookie-sending flows but login does not need an existing cookie. MFA stops password-only completion for accounts requiring it. Frontend session-ID/user-ID checks reject changes when an old in-memory session exists, but storage.ts initializes both to null on reload.

Validation method: offline static source trace

Limitations:
- No application execution or network reproduction.

#### Dataflow

cross-site form credentials -\> login POST -\> Set-Cookie refresh -\> fresh frontend -\> restoreSession -\> attacker account

- **Outcome:** Victim may enter CRM data into an attacker-controlled account; no direct victim token theft is asserted.

#### Reachability

Website operator with credentials for an account not requiring MFA; victim browser can navigate to login endpoint.

- **Attacker:** Website operator with credentials for an account not requiring MFA; victim browser can navigate to login endpoint.

#### Severity

**Low** — Requires victim navigation to attacker-controlled content, an attacker account that can complete login without MFA, and victim subsequently using the silently restored account; existing in-memory identity checks constrain active-session switching.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Enforce CSRF or validated Origin/Referer on login and all cookie-mutating authentication endpoints; ensure fresh session restoration cannot silently accept an unsolicited login.

Tests:
- Reject cross-origin form login even without an existing cookie; preserve valid same-origin login and refresh.

<a id="finding-31"></a>

### [31] Cross-site login can restore the browser into an attacker-controlled account

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Direct source trace of DRF form-compatible CSRF-exempt login, cookie issuance, and fresh-page restore; no live browser reproduction. |
| Category | Login CSRF |
| CWE | CWE-352 |
| Affected lines | apps/accounts/auth_views.py:91-103, apps/accounts/mfa_views.py:88-108, apps/accounts/mfa.py:178-187, frontend/src/api/token.ts:39-46, frontend/src/lib/storage.ts:7-9 |

#### Summary

An attacker can submit their own credentials through a cross-site top-level form to `/api/auth/token/`, or a valid attacker-owned MFA challenge/factor to the MFA verification endpoint. These endpoints set a refresh cookie without an origin or CSRF check. On a subsequent fresh application page, automatic session restoration accepts that cookie, so data a deceived victim enters can be saved into the attacker's account. This resolves the login-CSRF portion of AUD-V01; it does not expose the victim's previous account directly.

#### Root Cause

`request.data` credentials or MFA challenge/factor establish which account receives a new session, but neither entrypoint verifies browser login intent. DRF APIView dispatch is CSRF-exempt and inherited parsers accept forms; JWT-only/default or empty token-view authentication does not enforce session CSRF. The resulting cookie is later consumed by refresh. The client compares users only when an in-memory identity exists, which is not true on a fresh page.

**Password form installs session** — `apps/accounts/auth_views.py:88-103`

Attacker account credentials in request.data reach issue_session and set_refresh_cookie without binding the login to the initiating browser origin.

```python
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("email") or request.data.get("username") or ""
        user = authenticate(request=request, username=identifier, password=request.data.get("password"))
        if user is None:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            raise AuthenticationFailed("No active account found with the given credentials.", code="no_active_account")
        if requires_mfa(user):
            return Response(start_auth_challenge(user), status=status.HTTP_202_ACCEPTED)

        refresh = issue_session(user, mfa_verified=False, request=request)
        update_last_login(None, user)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        return set_refresh_cookie(Response({"access": str(refresh.access_token)}), str(refresh))
```

**Refresh credential is a browser cookie** — `apps/accounts/auth_views.py:23-34`

The new refresh token is set as HttpOnly cookie; cross-site top-level form navigation can install the attacker's session without reading the response.

```python
def set_refresh_cookie(response, refresh_token):
    """Persist refresh credentials outside JavaScript-accessible storage."""
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max(0, int(RefreshToken(refresh_token)["exp"] - timezone.now().timestamp())),
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )
    return response
```

**MFA login also installs caller-selected session** — `apps/accounts/mfa_views.py:83-108`

A valid attacker-owned challenge and unused factor reach _session_response; verifying the attacker's factor does not establish the victim browser's login intent.

```python
class MfaVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_mfa"

    def post(self, request):
        audit_user = challenge_user(_challenge_token(request), MfaChallenge.Purposes.LOGIN)
        try:
            user, refresh = verify_login_challenge(
                request=request,
                challenge_token=_challenge_token(request),
                code=request.data.get("code"),
            )
        except Exception:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            if audit_user:
                record_security_event(request, user=audit_user, event="mfa_login_failed")
            raise
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        record_security_event(
            request,
            user=user,
            event="mfa_login_verified",
            risk_level=AuditLog.RiskLevels.LOW,
        )
        return _session_response(refresh)
```

**Challenge maps to its account** — `apps/accounts/mfa.py:178-190`

The supplied challenge resolves its user and valid factor then issues that user's session for the request.

```python
def verify_login_challenge(*, challenge_token, code, request=None):
    failed = False
    with transaction.atomic():
        challenge = _resolve_challenge(challenge_token, MfaChallenge.Purposes.LOGIN, lock=True)
        if not verify_user_factor(challenge.user, code, allow_recovery=True):
            _register_failure(challenge)
            failed = True
        else:
            _consume_challenge(challenge)
            result = (challenge.user, issue_session(challenge.user, mfa_verified=True, request=request))
    if failed:
        raise MfaCodeInvalid()
    return result
```

**MFA result sets same cookie** — `apps/accounts/mfa_views.py:32-34`

The validated attacker session is persisted through the same cookie helper.

```python
def _session_response(refresh, *, extra=None, status_code=status.HTTP_200_OK):
    payload = {"access": str(refresh.access_token), **(extra or {})}
    return set_refresh_cookie(Response(payload, status=status_code), str(refresh))
```

**Refresh uses cookie** — `apps/accounts/auth_views.py:109-117`

A later same-origin refresh adopts the planted refresh cookie.

```python
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        if not data.get("refresh"):
            cookie_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
            if cookie_token:
                data["refresh"] = cookie_token
        serializer = self.get_serializer(data=data)
        try:
            response_data = refresh_browser_session(request, data, serializer)
```

**Fresh page has no prior identity** — `frontend/src/lib/storage.ts:7-9`

Access token and expected user are memory-only and initially null, so a reload loses the comparison identity.

```typescript
let accessToken: string | null = null;
let sessionGeneration = 0;
let userId: string | null = null;
```

**Existing-tab guard has fresh-page exception** — `frontend/src/api/token.ts:39-46`

Session and user comparison cannot reject an attacker identity when original access and expected user are absent.

```typescript
function assertSameRefreshUser(access: string, originalAccess: string | null) {
  const previous = readSessionIdentity(originalAccess);
  const incoming = readSessionIdentity(access);
  if (previous?.sessionId && previous.sessionId !== incoming?.sessionId) {
    throw new SessionIdentityChangedError("Refresh device session changed");
  }
  const expected = tokenStorage.getUserId();
  if (expected === null) return;
```

**Page startup restores cookie session** — `frontend/src/features/auth/AuthProvider.tsx:91-101`

Startup refresh and current-user lookup accept the cookie account without checking it against the prior account's stored email.

```typescript
  const restoreCurrentSession = useCallback(() => {
    if (restoring.current) return restoring.current;
    const generation = tokenStorage.getGeneration();
    const hadPreviousSession = Boolean(tokenStorage.getEmail());
    setRecovering(true);
    const promise = (async () => {
      try {
        await restoreSession();
        const currentUser = await getCurrentUser();
        acceptUser(currentUser, generation);
        setRecoveryError(null);
```

#### Validation

Verified registered token endpoint, password/MFA cookie paths, DRF APIView.as_view csrf_exempt and default FormParser, no route-specific CSRF/origin enforcement in middleware, automatic refresh on page load, and null initial expected identity.

Validation method: Offline static source and installed-framework inspection

**Password form installs session** — `apps/accounts/auth_views.py:88-103`

Attacker account credentials in request.data reach issue_session and set_refresh_cookie without binding the login to the initiating browser origin.

```python
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        identifier = request.data.get("email") or request.data.get("username") or ""
        user = authenticate(request=request, username=identifier, password=request.data.get("password"))
        if user is None:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            raise AuthenticationFailed("No active account found with the given credentials.", code="no_active_account")
        if requires_mfa(user):
            return Response(start_auth_challenge(user), status=status.HTTP_202_ACCEPTED)

        refresh = issue_session(user, mfa_verified=False, request=request)
        update_last_login(None, user)
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        return set_refresh_cookie(Response({"access": str(refresh.access_token)}), str(refresh))
```

**Refresh credential is a browser cookie** — `apps/accounts/auth_views.py:23-34`

The new refresh token is set as HttpOnly cookie; cross-site top-level form navigation can install the attacker's session without reading the response.

```python
def set_refresh_cookie(response, refresh_token):
    """Persist refresh credentials outside JavaScript-accessible storage."""
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max(0, int(RefreshToken(refresh_token)["exp"] - timezone.now().timestamp())),
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )
    return response
```

**MFA login also installs caller-selected session** — `apps/accounts/mfa_views.py:83-108`

A valid attacker-owned challenge and unused factor reach _session_response; verifying the attacker's factor does not establish the victim browser's login intent.

```python
class MfaVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_mfa"

    def post(self, request):
        audit_user = challenge_user(_challenge_token(request), MfaChallenge.Purposes.LOGIN)
        try:
            user, refresh = verify_login_challenge(
                request=request,
                challenge_token=_challenge_token(request),
                code=request.data.get("code"),
            )
        except Exception:
            record_login(request, status=LoginHistory.Statuses.FAILED)
            if audit_user:
                record_security_event(request, user=audit_user, event="mfa_login_failed")
            raise
        record_login(request, user=user, email=user.email, status=LoginHistory.Statuses.SUCCESS)
        record_security_event(
            request,
            user=user,
            event="mfa_login_verified",
            risk_level=AuditLog.RiskLevels.LOW,
        )
        return _session_response(refresh)
```

**Challenge maps to its account** — `apps/accounts/mfa.py:178-190`

The supplied challenge resolves its user and valid factor then issues that user's session for the request.

```python
def verify_login_challenge(*, challenge_token, code, request=None):
    failed = False
    with transaction.atomic():
        challenge = _resolve_challenge(challenge_token, MfaChallenge.Purposes.LOGIN, lock=True)
        if not verify_user_factor(challenge.user, code, allow_recovery=True):
            _register_failure(challenge)
            failed = True
        else:
            _consume_challenge(challenge)
            result = (challenge.user, issue_session(challenge.user, mfa_verified=True, request=request))
    if failed:
        raise MfaCodeInvalid()
    return result
```

**MFA result sets same cookie** — `apps/accounts/mfa_views.py:32-34`

The validated attacker session is persisted through the same cookie helper.

```python
def _session_response(refresh, *, extra=None, status_code=status.HTTP_200_OK):
    payload = {"access": str(refresh.access_token), **(extra or {})}
    return set_refresh_cookie(Response(payload, status=status_code), str(refresh))
```

**Refresh uses cookie** — `apps/accounts/auth_views.py:109-117`

A later same-origin refresh adopts the planted refresh cookie.

```python
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        if not data.get("refresh"):
            cookie_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
            if cookie_token:
                data["refresh"] = cookie_token
        serializer = self.get_serializer(data=data)
        try:
            response_data = refresh_browser_session(request, data, serializer)
```

**Fresh page has no prior identity** — `frontend/src/lib/storage.ts:7-9`

Access token and expected user are memory-only and initially null, so a reload loses the comparison identity.

```typescript
let accessToken: string | null = null;
let sessionGeneration = 0;
let userId: string | null = null;
```

**Existing-tab guard has fresh-page exception** — `frontend/src/api/token.ts:39-46`

Session and user comparison cannot reject an attacker identity when original access and expected user are absent.

```typescript
function assertSameRefreshUser(access: string, originalAccess: string | null) {
  const previous = readSessionIdentity(originalAccess);
  const incoming = readSessionIdentity(access);
  if (previous?.sessionId && previous.sessionId !== incoming?.sessionId) {
    throw new SessionIdentityChangedError("Refresh device session changed");
  }
  const expected = tokenStorage.getUserId();
  if (expected === null) return;
```

**Page startup restores cookie session** — `frontend/src/features/auth/AuthProvider.tsx:91-101`

Startup refresh and current-user lookup accept the cookie account without checking it against the prior account's stored email.

```typescript
  const restoreCurrentSession = useCallback(() => {
    if (restoring.current) return restoring.current;
    const generation = tokenStorage.getGeneration();
    const hadPreviousSession = Boolean(tokenStorage.getEmail());
    setRecovering(true);
    const promise = (async () => {
      try {
        await restoreSession();
        const currentUser = await getCurrentUser();
        acceptUser(currentUser, generation);
        setRecoveryError(null);
```

Counterevidence and remaining uncertainty:
- SameSite=Lax limits sending existing cookies but does not prevent cookie installation by a cross-site top-level navigation response.
- CORS prevents attacker JavaScript reading responses, not form navigation.
- MFA blocks password-only login for protected accounts, but an attacker can supply their own valid challenge/factor to the equally unbound MFA verification endpoint.
- An existing tab rejects identity-changing refreshes; fresh pages initialize the comparison identity to null.

Limitations:
- No browser, server or external provider was contacted.
- Effect requires the victim to revisit/reload the application and act under the attacker identity; prior tenant data is not shown to become available.

#### Dataflow

Attacker credentials or challenge/factor → login handler → issue_session → Set-Cookie → fresh-page restoreSession → refresh cookie → current user accepted.

#### Reachability

Attacker hosts a form posting their own valid login material to the public auth endpoint, induces top-level navigation, and later has victim open a fresh CRM page. Victim-entered data goes into the attacker account; victim credentials need not be sent.

#### Severity

**Low** — Requires victim navigation and subsequent interaction in the attacker's account; current-tab identity checks limit silent switching, and no theft of the victim's existing session is established. Attacker controls credentials/factors for their own account.

A proven workflow silently collecting sensitive victim data would increase impact; enforced origin/CSRF checks on cookie-setting endpoints eliminate the path.

#### Remediation

Require a trusted Origin/Referer and CSRF token bound to the initiating browser on every cookie-setting authentication endpoint, including password, social, MFA and enrollment flows. Keep the current-tab identity guard as defense in depth.

Tests:
- Cross-origin form POST with valid attacker password must not set a refresh cookie.
- Cross-origin MFA verification with valid attacker challenge/factor must not set a cookie.
- Fresh-page session restore after rejected cross-site login must retain the legitimate account or remain unauthenticated.

<a id="finding-32"></a>

### [32] Password-change MFA verification lacks a failed-attempt budget

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Verified current-password serializer, view lacking scope, configured ScopedRateThrottle no-scope behavior, and factor code with no failure accounting. |
| Category | Insufficient MFA attempt restriction |
| CWE | CWE-307 |
| Affected lines | apps/accounts/views.py:51-65, apps/accounts/mfa.py:193-201, apps/accounts/mfa.py:296-313 |

#### Summary

A caller who has a live session and knows the current password can repeatedly submit guessed six-digit MFA codes to the password-change endpoint. Unlike dedicated MFA routes, the view has no throttle scope, and shared factor verification tracks no failed-attempt budget. A successful guess changes the password and issues a new session.

#### Root Cause

ChangePasswordView relies on the globally configured scoped throttle but never declares a scope. verify_user_factor performs TOTP/recovery verification without recording failed guesses, so neither the route nor the shared verifier bounds repeated attempts. MfaChallenge's failure cap does not apply to this authenticated route.

**Sensitive route verifies factor without scope** — `apps/accounts/views.py:51-80`

Authenticated caller supplies current password and guessed mfa_code; no throttle_scope applies.

```


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if has_confirmed_mfa(request.user) and not verify_user_factor(
            request.user,
            request.data.get("mfa_code"),
            allow_recovery=True,
        ):
            record_security_event(request, user=request.user, event="password_change_mfa_failed")
            raise AuthenticationFailed("The verification code is invalid.", code="mfa_code_invalid")
        revoked_sessions, _ = update_password_and_revoke_sessions(
            request.user,
            serializer.validated_data["new_password"],
        )
        refresh = issue_session(request.user, mfa_verified=has_confirmed_mfa(request.user), request=request)
        record_security_event(
            request,
            user=request.user,
            event="password_changed",
            sessions_revoked=revoked_sessions,
        )
        return set_refresh_cookie(Response({"ok": True}), str(refresh))


class CurrentUserLoginHistoryView(APIView):
```

**Shared verification has no failure budget** — `apps/accounts/mfa.py:193-201`

Failed factor guesses simply return false; only successful use changes the device counter.

```
@transaction.atomic
def verify_user_factor(user, code, *, allow_recovery):
    try:
        device = MfaDevice.objects.select_for_update().get(user=user, confirmed_at__isnull=False)
    except MfaDevice.DoesNotExist:
        return False
    if _verify_totp(device, code, commit_counter=True):
        return True
    return allow_recovery and _consume_recovery_code(user, code)
```

**Six-digit factor checking** — `apps/accounts/mfa.py:296-313`

Verifier checks three adjacent TOTP counters; replay prevention handles successes, not repeated failures.

```
def _verify_totp(device, code, *, commit_counter):
    normalized = "".join(character for character in str(code or "") if character.isdigit())
    if len(normalized) != 6:
        return False
    secret = None
    try:
        secret = decrypt_credential_value(device.encrypted_secret)
        totp = pyotp.TOTP(secret)
        current_counter = totp.timecode(timezone.now())
        for counter in range(current_counter - 1, current_counter + 2):
            if secrets.compare_digest(totp.generate_otp(counter), normalized):
                if counter <= device.last_used_counter:
                    return False
                if commit_counter:
                    device.last_used_counter = counter
                    device.save(update_fields=["last_used_counter", "updated_at"])
                return True
        return False
```

**No scope means no scoped throttling** — `.venv/Lib/site-packages/rest_framework/throttling.py:205-225`

The only configured global rate throttle permits requests when throttle_scope is missing.

```
class ScopedRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls by different amounts for various parts of
    the API.  Any view that has the `throttle_scope` property set will be
    throttled.  The unique cache key will be generated by concatenating the
    user id of the request, and the scope of the view being accessed.
    """
    scope_attr = 'throttle_scope'

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)

        # If a view does not have a `throttle_scope` always allow the request
        if not self.scope:
            return True
```

#### Validation

Confirmed password validation precedes factor verification, no throttle_scope on the full view, and ScopedRateThrottle returns True without scope. Compared dedicated auth_mfa endpoints and challenge failure counters.

Validation method: Offline source/dependency trace

**Sensitive route verifies factor without scope** — `apps/accounts/views.py:51-80`

Authenticated caller supplies current password and guessed mfa_code; no throttle_scope applies.

```


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if has_confirmed_mfa(request.user) and not verify_user_factor(
            request.user,
            request.data.get("mfa_code"),
            allow_recovery=True,
        ):
            record_security_event(request, user=request.user, event="password_change_mfa_failed")
            raise AuthenticationFailed("The verification code is invalid.", code="mfa_code_invalid")
        revoked_sessions, _ = update_password_and_revoke_sessions(
            request.user,
            serializer.validated_data["new_password"],
        )
        refresh = issue_session(request.user, mfa_verified=has_confirmed_mfa(request.user), request=request)
        record_security_event(
            request,
            user=request.user,
            event="password_changed",
            sessions_revoked=revoked_sessions,
        )
        return set_refresh_cookie(Response({"ok": True}), str(refresh))


class CurrentUserLoginHistoryView(APIView):
```

**Shared verification has no failure budget** — `apps/accounts/mfa.py:193-201`

Failed factor guesses simply return false; only successful use changes the device counter.

```
@transaction.atomic
def verify_user_factor(user, code, *, allow_recovery):
    try:
        device = MfaDevice.objects.select_for_update().get(user=user, confirmed_at__isnull=False)
    except MfaDevice.DoesNotExist:
        return False
    if _verify_totp(device, code, commit_counter=True):
        return True
    return allow_recovery and _consume_recovery_code(user, code)
```

**Six-digit factor checking** — `apps/accounts/mfa.py:296-313`

Verifier checks three adjacent TOTP counters; replay prevention handles successes, not repeated failures.

```
def _verify_totp(device, code, *, commit_counter):
    normalized = "".join(character for character in str(code or "") if character.isdigit())
    if len(normalized) != 6:
        return False
    secret = None
    try:
        secret = decrypt_credential_value(device.encrypted_secret)
        totp = pyotp.TOTP(secret)
        current_counter = totp.timecode(timezone.now())
        for counter in range(current_counter - 1, current_counter + 2):
            if secrets.compare_digest(totp.generate_otp(counter), normalized):
                if counter <= device.last_used_counter:
                    return False
                if commit_counter:
                    device.last_used_counter = counter
                    device.save(update_fields=["last_used_counter", "updated_at"])
                return True
        return False
```

**No scope means no scoped throttling** — `.venv/Lib/site-packages/rest_framework/throttling.py:205-225`

The only configured global rate throttle permits requests when throttle_scope is missing.

```
class ScopedRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls by different amounts for various parts of
    the API.  Any view that has the `throttle_scope` property set will be
    throttled.  The unique cache key will be generated by concatenating the
    user id of the request, and the scope of the view being accessed.
    """
    scope_attr = 'throttle_scope'

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)

        # If a view does not have a `throttle_scope` always allow the request
        if not self.scope:
            return True
```

Counterevidence and remaining uncertainty:
- Caller needs current password and a valid session.
- Password hash computation and rotating TOTP windows constrain practical guessing; successful counters cannot be reused.
- External ingress rate limits remain unknown; no brute-force test run.

#### Dataflow

Authenticated password-change POST → correct current_password → guessed mfa_code → unbudgeted verify_user_factor → password change/new session if successful.

#### Reachability

An attacker already possessing session and password but lacking the factor can use this route as a repeatable factor oracle.

#### Severity

**Low** — The missing limit weakens a sensitive second-factor gate, but exploitation requires both a valid session and password, repeated expensive password checks and a successful guess within rotating TOTP windows. Account takeover from anonymous access is not established.

Demonstrated practical guessing throughput or a lower-prerequisite verifier would increase likelihood; a shared per-user factor budget removes this bypass.

#### Remediation

Apply an auth_mfa throttle to password changes and enforce a per-user failure budget shared across all factor verification routes, with bounded recovery behavior.

Tests:
- Repeated incorrect factor guesses at password-change must hit a limit.
- Switching among factor-verification routes must not reset the shared budget.

<a id="finding-33"></a>

### [33] Public intake responses expose private CRM identity relationships

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Parent independently traced entry point, effective guards and sink in current source; no runtime reproduction. |
| Category | Public contact enumeration |
| CWE | CWE-200, CWE-204 |
| Affected lines | apps/leads/forms_service.py:63-64, apps/leads/views.py:534-542, apps/bots/serializers.py:393-402, apps/bots/views.py:358-366 |

#### Summary

Public forms return whether a phone/email matched an existing client, and website chat returns the matched internal client ID, exposing CRM identity relationships to anonymous visitors.

#### Root Cause

Both public intake paths use unverified contact data to resolve tenant clients and include internal duplicate/identity results in the public response. The matching is tenant-bound but its result is not authorized for the anonymous submitter.

**Form checks tenant clients** — `apps/leads/forms_service.py:63-64`

Public contact inputs generate internal duplicate metadata.

```
    duplicates = find_duplicate_clients(lead_form.business, phone=phone, email=email)
    duplicate_rows = duplicate_payload(duplicates, phone=phone, email=email)
```

**Public response exposes duplicate presence** — `apps/leads/views.py:534-542`

Boolean response distinguishes existing clients.

```
        return Response(
            {
                "ok": True,
                "success_message": form.success_message,
                "submission_id": submission.id,
                "lead_id": submission.lead_id,
                "duplicate_warning": bool(submission.duplicate_json.get("duplicates")),
            },
            status=201,
```

**Chat resolves existing client from asserted identity** — `apps/bots/serializers.py:393-402`

Email or phone selects an internal record without identity proof.

```
    def _get_or_create_client(self, business, full_name, phone, email, *, bot=None):
        queryset = Client.objects.filter(business=business)
        client = None
        if email:
            client = queryset.filter(email=email).first()
        if client is None and phone:
            client = queryset.filter(phone=phone).first()
        if client:
            # Contact capture is not staff approval to alter an existing client.
            return client
```

**Chat exposes selected client identifier** — `apps/bots/views.py:358-366`

Public response leaks the selected internal identity.

```
        return Response(
            {
                "conversation_id": str(conversation.public_id),
                "message_id": message.id,
                "lead_id": lead.id if lead else None,
                "client_id": client.id if client else None,
                "status": conversation.status,
            },
            status=201,
```

#### Validation

Form returns only a boolean, not duplicate details. Chat creates a new random conversation capability and does not reuse existing conversation access. Active forms/channels, quotas and throttles remain; internal ID alone is not an auth bypass.

Validation method: offline static source trace

Limitations:
- No live requests or application execution.

#### Dataflow

public phone/email -\> existing tenant client match -\> duplicate_warning or client_id in public success response

- **Outcome:** Contact-existence inference and correlation of phone/email to internal client IDs; no full client-record access demonstrated.

#### Reachability

Anonymous visitor knowing an active public form/channel UUID and contact data.

- **Attacker:** Anonymous visitor knowing an active public form/channel UUID and contact data.

#### Severity

**Low** — Limited disclosure: contact membership/internal identifiers rather than full records. Attacker needs a public form/channel and known or guessed contact; each probe creates intake data.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Use uniform public success responses and return only the new public conversation capability; keep duplicate warnings and CRM identifiers in authorized staff views.

Tests:
- Existing/new contact form submissions return indistinguishable public metadata; chat response omits internal client/lead IDs.

<a id="finding-34"></a>

### [34] Imports update existing clients without client update permission

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Direct source trace establishes caller, guard gap and sink; no runtime execution. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | apps/core/import_export.py:147-155, apps/core/import_export.py:379-385, apps/core/import_export.py:405-410, apps/core/import_export.py:439-455, apps/core/import_export.py:562-595 |

#### Summary

Client, lead and deal imports check permission to create the imported entity but can fill fields on existing business-wide clients without checking CLIENTS UPDATE for that object.

#### Root Cause

The locked job checks actor ownership and entity CREATE. Concrete import helpers match clients across the business by phone/email and call fill_missing_client_fields without actor context or client UPDATE authorization. That helper saves blank contact/note fields and changes OTHER source.

**Import only checks entity CREATE** — `apps/core/import_export.py:147-155`

Job ownership does not establish authorization to modify an existing client.

```
def _locked_import_job(job, request=None):
    # Do not trust the object loaded before waiting for another preview/confirm.
    job = ImportJob.objects.select_for_update().get(pk=job.pk)
    if request is not None:
        if job.actor_id != request.user.pk and not request.user.is_platform_user:
            raise PermissionDenied("This import belongs to another user.")
        resource = import_resource(job.entity_type)
        assert_can(request.user, job.business, resource, Actions.CREATE)
        assert_resource_enabled(job.business, resource)
```

**Client import updates matched client** — `apps/core/import_export.py:379-385`

Existing client row reaches shared mutation without UPDATE check.

```
def import_client_row(job, payload, connector=None):
    if not payload.get("full_name") and not payload.get("phone") and not payload.get("email"):
        return "skipped"
    existing = find_import_client(job.business, payload)
    if existing:
        changed = fill_missing_client_fields(existing, payload)
        if changed:
```

**Lead import also updates matched client** — `apps/core/import_export.py:405-410`

Creating a lead carries the same unauthorized client side effect.

```
def import_lead_row(job, payload, connector=None):
    if not payload.get("full_name") and not payload.get("phone") and not payload.get("email") and not payload.get("message"):
        return "skipped"
    client = find_import_client(job.business, payload)
    if client:
        fill_missing_client_fields(client, payload)
```

**Deal import repeats mutation** — `apps/core/import_export.py:439-455`

Deal creation maps client fields into the same update helper.

```
def import_deal_row(job, payload, connector=None):
    assert_resource_enabled(job.business, Resources.DEALS)
    if not payload.get("title") and not payload.get("client_name") and not payload.get("phone") and not payload.get("email"):
        return "skipped"
    deal_payload = normalize_deal_payload(payload)
    client = find_import_client(job.business, {"phone": deal_payload.get("phone"), "email": deal_payload.get("email")})
    if client:
        fill_missing_client_fields(
            client,
            {
                "full_name": deal_payload.get("client_name"),
                "phone": deal_payload.get("phone"),
                "email": deal_payload.get("email"),
                "source": deal_payload.get("source"),
                "notes": deal_payload.get("notes"),
            },
        )
```

**Tenant-wide match and unchecked save** — `apps/core/import_export.py:562-595`

Contact match bypasses object write scope and saves permitted blank fields.

```
def find_import_client(business, payload):
    query = Q()
    if payload.get("phone"):
        query |= Q(phone=payload["phone"])
    if payload.get("email"):
        query |= Q(email__iexact=payload["email"])
    if not query:
        return None
    return Client.objects.filter(business=business).filter(query).first()


def client_defaults(payload, fallback="Imported client"):
    return {
        "full_name": payload.get("full_name") or payload.get("phone") or payload.get("email") or fallback,
        "phone": payload.get("phone", ""),
        "email": payload.get("email", ""),
        "source": normalize_client_source(payload.get("source")),
        "notes": payload.get("notes", ""),
    }


def fill_missing_client_fields(client, payload):
    changed_fields = []
    for field in ["full_name", "phone", "email", "notes"]:
        value = payload.get(field)
        if value and not getattr(client, field):
            setattr(client, field, value)
            changed_fields.append(field)
    source = normalize_client_source(payload.get("source"))
    if source and source != client.source and client.source == Client.Sources.OTHER:
        client.source = source
        changed_fields.append("source")
    if changed_fields:
        client.save(update_fields=[*changed_fields, "updated_at"])
```

#### Validation

All matches are business-bound. Job locking, actor checks, validated mappings and terminal state checks are effective. Most fields must initially be empty; source must be OTHER. These constrain but do not authorize writes.

Validation method: offline static source trace

Limitations:
- No application execution or network reproduction.

#### Dataflow

import payload phone/email -\> entity CREATE -\> business-wide existing-client match -\> fill_missing_client_fields -\> client.save

- **Outcome:** Unauthorized modification of another member’s client contact details, notes or source.

#### Reachability

Active member with permitted entity import CREATE and sufficient clients VIEW to retrieve/confirm their job, but lacking client UPDATE or object scope.

- **Attacker:** Active member with permitted entity import CREATE and sufficient clients VIEW to retrieve/confirm their job, but lacking client UPDATE or object scope.

#### Severity

**Low** — Same-tenant limited integrity impact: attacker needs import CREATE and clients VIEW to confirm, a matching contact and empty mutable fields; existing nonempty values are largely preserved.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Pass the actor into import helpers and enforce CLIENTS UPDATE with obj=client before every existing-client mutation; define safe handling of inaccessible matches.

Tests:
- Import matched clients with VIEW+CREATE but UPDATE denied and with UPDATE OWN for another member’s client; no forbidden fields may change.

<a id="finding-35"></a>

### [35] Cached exports disclose rows after permissions are narrowed

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Source generation scopes current rows, but download checks only resource permission and returns cached bytes. |
| Category | Stale export authorization |
| CWE | CWE-863 |
| Affected lines | apps/core/import_export_views.py:90-116, apps/core/export_jobs.py:124-145 |

#### Summary

An export creator can download an earlier broad export after their row permissions narrow to OWN or TEAM, provided resource VIEW remains allowed (AUD-18).

#### Root Cause

Export processing persists the actor-scoped result. Later download resolves the creator's job and checks resource VIEW, which permits narrower OWN/TEAM scopes without an object. It does not compare an authorization snapshot or regenerate rows before returning the saved artifact.

**Export result persisted** — `apps/core/export_jobs.py:138-145`

Generation stores a static CSV for later reuse.

```
        content = bytes(response.content)
        filename = f"{job.export_key}-{job.id}.csv"
        job.result_file.save(filename, ContentFile(content), save=False)
        job.row_count = max(content.count(b"\n") - 1, 0)
        job.status = ExportJob.Statuses.SUCCEEDED
        job.completed_at = timezone.now()
        job.error = ""
        job.save(update_fields=["result_file", "row_count", "status", "completed_at", "error", "updated_at"])
```

**Download returns old export bytes** — `apps/core/import_export_views.py:99-116`

Current resource VIEW is checked without row scope; special note redaction does not remove unauthorized rows.

```
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != ExportJob.Statuses.SUCCEEDED or not job.result_file:
            raise ValidationError({"export": "Export file is not ready."})
        assert_can(request.user, job.business, _resource_for_export_key(job.export_key), Actions.VIEW)
        write_audit_log(
            request,
            AuditLog.Actions.CREATE,
            job,
            business=job.business,
            metadata={"kind": "file_download", "entity_type": "export_job", "export_key": job.export_key},
        )
        if job.kind == ExportJob.Kinds.ENTITY and job.export_key == "clients" and not can_view_sensitive_field(
            request.user, job.business, Resources.CLIENTS, "notes"
        ):
            return private_notes_redacted_csv(job.result_file)
        return FileResponse(job.result_file.open("rb"), as_attachment=True, filename=f"{job.export_key}.csv")
```

#### Validation

Validated cached generation, actor/business filtering, resource-level check and direct FileResponse. Note redaction handles sensitive client fields but preserves rows. No server revocation can retract a previously downloaded copy; this finding concerns new downloads from retained server artifacts after narrowing.

Validation method: offline static source trace

#### Dataflow

previous broad rows -\> stored CSV -\> current VIEW-only check -\> cached file response

- **Outcome:** Rows outside current scope disclosed

#### Reachability

Requires own completed export and subsequent scope narrowing with membership and resource VIEW retained.

#### Severity

**Low** — Same-tenant confidentiality violation with a prior completed export and later permission narrowing required; full membership/VIEW revocation remains enforced.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Invalidate exports on relevant permission/team/ownership changes or regenerate at download under current scope; bind artifacts to an authorization snapshot.

Tests:
- Narrow BUSINESS to OWN/TEAM and confirm old artifacts cannot return excluded rows.
- Verify full revocation denial and allowed unchanged-scope download.

<a id="finding-36"></a>

### [36] Password changes accept unlimited MFA guesses

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Direct source trace establishes caller, guard gap and sink; no runtime execution. |
| Category | Missing MFA attempt limit |
| CWE | CWE-307 |
| Affected lines | apps/accounts/views.py:53-77, apps/accounts/mfa.py:192-201, .venv/Lib/site-packages/rest_framework/throttling.py:219-227 |

#### Summary

ChangePasswordView invokes the six-digit MFA verifier without a throttle scope or shared failure budget, bypassing limits used by dedicated MFA endpoints.

#### Root Cause

Global ScopedRateThrottle allows views without throttle_scope. ChangePasswordView has no scope and calls verify_user_factor directly; that service locks the device and checks/replay-protects successful TOTP codes but does not count failed attempts. Login challenge counters do not apply.

**Password change has no scope** — `apps/accounts/views.py:53-77`

Caller-supplied MFA code reaches direct factor verification before credentials are changed.

```
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if has_confirmed_mfa(request.user) and not verify_user_factor(
            request.user,
            request.data.get("mfa_code"),
            allow_recovery=True,
        ):
            record_security_event(request, user=request.user, event="password_change_mfa_failed")
            raise AuthenticationFailed("The verification code is invalid.", code="mfa_code_invalid")
        revoked_sessions, _ = update_password_and_revoke_sessions(
            request.user,
            serializer.validated_data["new_password"],
        )
        refresh = issue_session(request.user, mfa_verified=has_confirmed_mfa(request.user), request=request)
        record_security_event(
            request,
            user=request.user,
            event="password_changed",
            sessions_revoked=revoked_sessions,
        )
        return set_refresh_cookie(Response({"ok": True}), str(refresh))
```

**Direct factor checks lack failure tracking** — `apps/accounts/mfa.py:192-201`

Failed calls return without decrementing a shared attempt budget.

```

@transaction.atomic
def verify_user_factor(user, code, *, allow_recovery):
    try:
        device = MfaDevice.objects.select_for_update().get(user=user, confirmed_at__isnull=False)
    except MfaDevice.DoesNotExist:
        return False
    if _verify_totp(device, code, commit_counter=True):
        return True
    return allow_recovery and _consume_recovery_code(user, code)
```

**No scope means allow** — `.venv/Lib/site-packages/rest_framework/throttling.py:219-227`

Global scoped throttling does not automatically protect this endpoint.

```
    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)

        # If a view does not have a `throttle_scope` always allow the request
        if not self.scope:
            return True

        # Determine the allowed request rate as we normally would during
```

#### Validation

Current password is checked first, imposing hashing cost. Valid codes cannot be replayed. Challenges separately enforce failed-attempt counts. Existing session access is a prerequisite, not a newly granted capability.

Validation method: offline static source trace

Limitations:
- No application execution or network reproduction.

#### Dataflow

authenticated POST/current password -\> mfa_code -\> verify_user_factor -\> TOTP verifier -\> password replacement/session revocation

- **Outcome:** Unbounded online factor guesses can authorize credential replacement if a guess succeeds.

#### Reachability

Holder of a valid authenticated access token and current password who lacks the second factor.

- **Attacker:** Holder of a valid authenticated access token and current password who lacks the second factor.

#### Severity

**Low** — Potential password takeover requires both a valid session and current password plus successful online factor guessing; password hashing and short TOTP validity lower likelihood.

Additional runtime or deployment evidence could raise or lower this severity.

#### Remediation

Apply an authenticated password-change throttle and a shared account/device MFA failure budget in the verification service across all callers.

Tests:
- Repeated bad MFA codes on password change must trigger the shared account budget; other verifier endpoints must share it.

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Saved export permission revocation (AUD-18) | not recorded | Reported | Current-source validation retained AUD-18; actor/membership checks and notes redaction do not enforce changed row scope. |
| XLSX import expansion limits (AUD-22) | not recorded | Reported | Missing pre-materialization bound confirmed; compressed-size/antivirus controls retained as counterevidence. Runtime magnitude remains unmeasured. |
| Import side-effect authorization | not recorded | Reported | Default marketer path established; new finding distinct from AUD-20 lifecycle and AUD-21 concurrency. |
| Proposed client merge duplicate-scope bypass | not recorded | Rejected | Original candidate: merge checks target DELETE only and selects duplicate by same tenant (apps/clients/views.py:86-112; serializers.py:142-162; services.py:93-136). Rejected claimed OWN/TEAM attacker path: Client model has no recognized ownership fields (models.py:8-62); access.py:559-586 returns none for such scoped querysets, and view get_object cannot select a target. No demonstrated attacker with target permission but without same-tenant duplicate permission. |
| Anonymous lead-form response privacy | not recorded | Reported | Chosen-contact membership disclosure validated; throttle and no full-record response limit severity. |
| Public intake consent authority | not recorded | Reported | Form and website-chat share an unconditional consent transition; merged as one broken control with both entrypoints. |
| Social email auto-link pre-hijacking under production defaults | not recorded | Rejected | Signup email is unverified and auto-link retains password (accounts/views.py:212-281; social_auth.py:160-194), but all signup users are BUSINESS_OWNER, production/staging requires privileged MFA (settings.py:303-306; mfa.py:62-90), SocialAuthView gates session issuance with requires_mfa (views.py:117-124), and enrollment revokes existing sessions (mfa_views.py:71). Attacker-enrolled MFA blocks victim completion; victim-enrolled MFA blocks attacker password-only access. Rejected as general production takeover. Disabled-MFA deployments retain a conditional concern not runtime-validated. |
| Notification bulk UPDATE scope (AUD-17) | not recorded | Reported | Current-source AUD-17 confirmed; limited to VIEW-visible nonexcluded rows. |
| Cookie authentication and fresh-page session restoration (AUD-V01) | not recorded | Reported | Validated login-CSRF; current-tab identity guard is counterevidence limiting the exploit. Password and MFA entrypoints share missing browser-intent check. |
| CSV/XLSX import parser budgets (AUD-22) | not recorded | Reported | Independent duplicate discoveries merged under AUD-22. Input-byte and antivirus controls retained as counterevidence; sparse virtual worksheet expansion remains unbounded before row validation. |
| Persistent import storage allocation | not recorded | Reported | Import storage excluded from attachment quota; successful and failed uploads persist. External retention remains unknown. |
| Anonymous throttle identity and proxy trust | not recorded | Reported | Validated conditional direct-port identity spoofing; severity narrowed to low because no account compromise is shown and a trusted ingress can mitigate. |
| Business deletion authorization | not recorded | Reported | Validated missing action guard. Parent narrowed baseline impact/severity for indirect as well as direct PROTECT dependencies; no general claim of deleting populated tenants. |
| MFA preauthentication challenge revocation | not recorded | Reported | Ordinary password reset leaves challenge valid; support recovery does consume challenges. Severity calibrated to short enrollment window and prior credential capability. |
| Password-change MFA attempt limits | not recorded | Reported | No route scope or shared failure budget. Severity narrowed for session+password prerequisites, hashing cost and rotating factor windows. |
| Password reset and pending MFA enrollment | not recorded | Reported | Validated mfa-challenge-revocation. Assisted recovery already consumes challenges at apps/accounts/recovery.py:221; ordinary password reset does not. |
| Tenant destruction through BusinessViewSet | not recorded | Reported | Ordinary membership gates inherited destroy. Protective children constrain but do not eliminate the path. |
| XLSX import parsing (existing AUD-22) | not recorded | Reported | Current code still materializes workbook rows before row limit; compressed byte/AV checks do not close expansion risk. |
| Team invitation capability exposure | not recorded | Reported | TEAM.VIEW reads token; pending new-account higher-role invitation can be consumed. Existing-account acceptance remains protected. |
| Concurrent attachment quota admission | not recorded | Reported | Validated bounded same-tenant overshoot; calibrated low, not unlimited resource exhaustion. |
| Persistent import storage admission and retention | not recorded | Reported | Separate from bounded attachment race: sequential imports bypass aggregate accounting. |
| Pre-validation multipart request budgets | not recorded | Reported | Direct Compose/default handler path validated; external production ingress cap unknown. |
| Lead duplicate lookup authorization | not recorded | Reported | Validated resource-scope bypass and privileged platform grant bypass; bounded five-lead response. |
| Notification bulk mutation authorization (AUD-17) | not recorded | Reported | Validated collection action bypass; other-business and Inbox exclusions remain effective. |
| Core and outreach XLSX resource bounds (AUD-22) | not recorded | Reported | Both readers reviewed; antivirus byte/expansion limits constrain ordinary archive bombs but not application worksheet allocation. |
| Cached export row authorization (AUD-18) | not recorded | Reported | Full VIEW/membership revocation and client-note redaction remain effective, but row-scope narrowing does not invalidate cached bytes. |
| Spoofed forwarded headers bypass anonymous rate limits | not recorded | Reported | Authenticated throttles key by user. An ingress overwriting headers or trusted-hop configuration can mitigate. MFA is still required where configured. No independent per-account login failure budget exists in the inspected login path. |
| Password changes accept unlimited MFA guesses | not recorded | Reported | Current password is checked first, imposing hashing cost. Valid codes cannot be replayed. Challenges separately enforce failed-attempt counts. Existing session access is a prerequisite, not a newly granted capability. |
| Imports update existing clients without client update permission | not recorded | Reported | All matches are business-bound. Job locking, actor checks, validated mappings and terminal state checks are effective. Most fields must initially be empty; source must be OTHER. These constrain but do not authorize writes. |
| Import previews disclose clients outside read permissions | not recorded | Reported | Matches remain tenant-bound and require a supplied matching identifier. Only initial preview rows are used. No later job retrieval is needed to receive create-response duplicates. |
| Cross-origin login can seed another account’s refresh cookie | not recorded | Reported | SameSite=Lax prevents many cross-site cookie-sending flows but login does not need an existing cookie. MFA stops password-only completion for accounts requiring it. Frontend session-ID/user-ID checks reject changes when an old in-memory session exists, but storage.ts initializes both to null on reload. |
| Ordinary members can hard-delete an unprotected business | not recorded | Reported | Cannot choose a business without membership/support access. Payments, deals with protected references, support cases, billing offers and ownership transfers may block deletion. A newly created tenant with default roles/pipeline and only unprotected clients/tasks remains a valid path; PROTECT is not authorization. |
| Read-only team viewers can claim privileged invitations | not recorded | Reported | Existing-account invitations require the correct authenticated recipient. Tokens must be pending, unexpired and unrevoked; owner roles are rejected. Built-in owners/admins already have manage, so custom read-only permission matters. MFA enrollment for the new account can be performed by the claimant and does not restore recipient-only token secrecy. |
| Merchant settings can clear a platform business restriction | not recorded | Reported | Does not forge payment or directly grant a plan. Commerce gate, confirmed financial state, dates, subscription state/revision and plan terms still apply. The finding concerns the separate status boundary. |
| An approved AI request can be reused for a different command | not recorded | Reported | Tenant ownership cannot be changed; requester, approver's current authority and CRM object permissions still apply. Default owners/admins already approve, so the meaningful gain requires distinct custom permissions. Existing fingerprint tests changing only the tool do not cover writable approval state. |
| Anonymous forms and chat can reverse another client’s opt-out | not recorded | Reported | No campaign is sent by this operation alone. Tenant-bound lookup, active channel/form, conversation quota and public throttles constrain volume but do not establish contact ownership. Existing chat profile fields are preserved, but consent is still changed. |
| Public intake responses expose private CRM identity relationships | not recorded | Reported | Form returns only a boolean, not duplicate details. Chat creates a new random conversation capability and does not reuse existing conversation access. Active forms/channels, quotas and throttles remain; internal ID alone is not an auth bypass. |
| Conditional social account pre-hijacking | not recorded | Reported | Only optional-MFA/no-enrolled-factor deployments; production MFA defaults and enrollment revocation are explicit counterevidence. |
| Remaining whole-repository source review | not recorded | Needs follow-up | 1944 explicit paths retained in deferred; no search-hit counting or overlapping worker totals. |
| Existing AUD register reconciliation | not recorded | Needs follow-up | AUD-17/18/22 retained with existing IDs; AUD-V01 duplicate-warning/login-CSRF addressed; AUD-13 stored-object UPDATE check exists at core/viewsets.py:182-199. AUD-16 server input restrictions and AUD-21 locking have current counterevidence. Other document statuses retained without unsupported closure. |
| Attachments and avatar execution/access hypotheses | not recorded | Rejected | Shallow magic checks alone do not prove inert files, but no executable-content bypass established: file_attachment_views.py:75-87 and file_views.py:43-61 require linked-object permission, clean scan snapshot and attachment disposition; file_scanning.py:88-133 checks size/hash/current clean state. avatars.py:23-61 enforces byte/pixel/frame limits and fresh JPEG; avatar_views.py binds request.user. Direct bucket/media exposure remains deployment-dependent. |
| SQL injection sinks | not recorded | No issue found | Offline product Python searches for raw/extra/RawSQL/cursor/execute found only constant SELECT 1 in apps/core/views.py:22-35. No attacker-controlled raw SQL established. This is bounded sink-search evidence, not completion of every ORM consumer. |
| Outbound webhook SSRF | not recorded | Rejected | apps/integrations/webhooks.py:42-80 rejects private/local destinations and credentials; :84-107 pins validated IP, checks peer and TLS hostname; :148-164 revalidates redirects; bounded timeout/redirect/body. Other reviewed provider bases originate in operator settings; not all HTTP clients fully reviewed. |
| Embedded credentials/current-source search | not recorded | No issue found | Baseline searched product/config/scripts/deploy/docs/archive/frontend/landing/reference/environment examples for credential/key literals. Reviewed hits were synthetic fixtures or isolated verification credentials; no reportable operational secret established. No credential used; absence of search hits is not full-file review. |
| Historical import tampering and duplicate-confirm claims (AUD-16/AUD-21) | not recorded | Rejected | apps/core/serializers.py:122-161 uses input allowlist and read-only server fields; import_export_views.py:34-35 disables PATCH/PUT; import_export.py:147-155 locks job/rechecks actor and CREATE, :218-225 checks terminal state under lock. Reject old unqualified no-lock/tamper descriptions; no concurrency runtime certification claimed. |
| Provider callback authentication and website capabilities | not recorded | No issue found | Investigator traced WhatsApp live mode and Instagram HMAC over raw body with compare_digest before writes. Telegram wrapper permissiveness alone rejected: resolve_telegram_channel requires matching nonempty channel secret. Website message UUID is additionally scoped to channel.bot/WEBSITE; public channel token alone cannot select another bot's conversation. |
| Non-live WhatsApp secret/channel binding | not recorded | Needs follow-up | Original conditional candidate retained in deferred; deployment applicability and attacker secret access not established. |
| Legacy AI create_\* transactional approval recheck | not recorded | Needs follow-up | CRM branch is audited and mutable approval finding reported. Legacy endpoint checks exist but revoked-approval/concurrency guarantees remain unresolved at views.py:394/437 and tool_registry.py:145. |
| AI execution and conversation isolation controls | not recorded | No issue found | Independent reviewer: crm_tools.py:116/131 locks target and verifies object permission/fingerprint; field/entity allowlists at :43/155/198. Conversation routes scope staff owner, revision, memory epoch and permissions; cancellation rejects pending logs/approvals/jobs. Provider prompts/all read/export/downstream autonomous flows not comprehensively reviewed. |
| Payment/refund and support lifecycle controls | not recorded | No issue found | Baseline fully reviewed listed payment/billing/ownership/recovery services. Actor derived server-side, linked records tenant-validated, Business locks serialize money writers, idempotency bound to actor/request and refunds capped. Ownership/recovery/employee repair verify authority, MFA/consent, revisions and epochs. Business-status exception separately reported; no runtime concurrency proof. |
| Public widget HTML sinks | not recorded | Rejected | frontend/widget/src/index.ts:89/94 innerHTML receives constants only; :184-188 addMessage uses textContent for user text. No user-controlled HTML execution in the reviewed widget. |
| Source defaults versus actual deployment | not recorded | Needs follow-up | Actual storage privacy, media serving, ingress, Redis/database exposure, scanner process resource limits, Windows ACLs and effective production configuration were not inspected. Render H1 example lacks resources required by operations contract; example mismatch is not proof of live exposure. |

## Open Questions And Follow Up

- Does any supported deployed social-login environment disable mandatory MFA for password-signup owners? Auto-link by unverified signup email remains unsafe under that condition.
- Are raw local media paths or object-store buckets reachable outside authenticated download handlers?
- Does deployed ingress overwrite forwarded headers and prevent direct Gunicorn access?
- Are Compose Redis/PostgreSQL host ports externally reachable and protected by authentication/firewall policy?
- Which effective MFA policy and social-login providers are enabled? Conditional linking finding requires optional/no-enrolled MFA.
- Do actual file workers/scanners and Windows connector-key ACLs satisfy the documented deployment guarantees?
- Remaining source paths and AUD items are explicitly deferred; no complete repository, dependency or deployment assurance is claimed.
- Public form normalization is recursive without an explicit depth cap and chat message fields lack explicit max_length; effective upstream body limits and concrete exhaustion impact remain unverified.
- Parent validation pending: browser auth endpoints issue/use refresh cookies without explicit CSRF/origin check; verify effective SameSite and DRF middleware before reporting.
  - Follow-up prompt: Review deferred unit csrf-review and close its stated proof gap.
- Investigator candidate pending parent validation.
  - Follow-up prompt: Review deferred unit duplicate-lookup-review and close its stated proof gap.
- Architecture investigator candidate; awaiting role reachability and parent validation.
  - Follow-up prompt: Review deferred unit approval-patch-review and close its stated proof gap.
- Investigator candidate pending parent validation.
  - Follow-up prompt: Review deferred unit working-hours-review and close its stated proof gap.
- Baseline candidate awaiting parent validation.
  - Follow-up prompt: Review deferred unit whatsapp-routing-review and close its stated proof gap.
- Investigator candidate awaiting parent validation.
  - Follow-up prompt: Review deferred unit note-parent-scope-review and close its stated proof gap.
- Investigator candidate pending parent validation.
  - Follow-up prompt: Review deferred unit duplicate-lookup-review-bca8a7d0fd729f2b and close its stated proof gap.
- Baseline candidate awaiting source/role validation.
  - Follow-up prompt: Review deferred unit inbox-preview-review and close its stated proof gap.
- Investigator candidate pending field-policy validation.
  - Follow-up prompt: Review deferred unit ai-brief-amount-review and close its stated proof gap.
- Investigator candidate pending aggregate-policy validation.
  - Follow-up prompt: Review deferred unit analytics-scope-review and close its stated proof gap.
- Investigator candidate pending parent validation and shared financial projection reconciliation.
  - Follow-up prompt: Review deferred unit financial-export-review and close its stated proof gap.
- Investigator candidate awaiting source validation.
  - Follow-up prompt: Review deferred unit task-assignment-review and close its stated proof gap.
- Existing AUD-V01 policy uncertainty: configuration accepts objectless OWN grants but runtime owner authority is explicitly documented; exact intended delegation boundary unresolved.
  - Follow-up prompt: Review deferred unit automation-delegation-review and close its stated proof gap.
- Static concurrency hypothesis, not proven exploitable; needs complete reassignment/locking interleaving.
  - Follow-up prompt: Review deferred unit appointment-race-review and close its stated proof gap.
- Investigator candidate pending parent validation and shared financial projection reconciliation.
  - Follow-up prompt: Review deferred unit financial-export-review-1f3009320ae12c18 and close its stated proof gap.
- Baseline candidate pending parent validation; original investigator severity high retained pending calibration.
  - Follow-up prompt: Review deferred unit mfa-challenge-review and close its stated proof gap.
- Baseline candidate awaiting source/role validation.
  - Follow-up prompt: Review deferred unit inbox-preview-review-fe62ccb459e43c40 and close its stated proof gap.
- Focused investigator candidate pending parent verification of quota accounting and reachable concurrent storage writes.
  - Follow-up prompt: Review deferred unit attachment-quota-race and close its stated proof gap.
- Source-backed investigator candidate awaiting parent validation of parser selection, upload handler and ingress controls.
  - Follow-up prompt: Review deferred unit multipart-spool-limit and close its stated proof gap.
- AI investigator candidate pending parent validation of editable fields, effective update permissions and approval binding.
  - Follow-up prompt: Review deferred unit approval-retarget and close its stated proof gap.
- Investigator candidate pending validation of feature configuration and resolved channel versus authenticated secret.
  - Follow-up prompt: Review deferred unit whatsapp-channel-confusion and close its stated proof gap.
- Baseline lead awaiting finalized source proof and MFA counterevidence.
  - Follow-up prompt: Review deferred unit social-preaccount and close its stated proof gap.
- Focused investigator candidate pending parent validation of anonymous identity matching, consent overwrite and campaign consumer.
  - Follow-up prompt: Review deferred unit public-consent-override and close its stated proof gap.
- Baseline candidate pending parent validation; consolidate with existing AUD-17.
  - Follow-up prompt: Review deferred unit aud-17-notification-bulk and close its stated proof gap.
- Public form contact-existence signal is source-backed; privacy/reportability policy and precise disclosure validation pending.
  - Follow-up prompt: Review deferred unit aud-v01-duplicate-warning and close its stated proof gap.
- Investigator lead pending validation of editor record scope and owner-authority execution.
  - Follow-up prompt: Review deferred unit automation-owner-authority and close its stated proof gap.
- Baseline source candidate pending parent verification; consolidate AUD-18.
  - Follow-up prompt: Review deferred unit aud-18-export-revocation and close its stated proof gap.
- Frontend/deployment investigator candidate pending parent validation of archive copy/exclusions and predeploy gate.
  - Follow-up prompt: Review deferred unit archive-private-backups and close its stated proof gap.
- Investigator lead pending delivery consumer validation.
  - Follow-up prompt: Review deferred unit outreach-stale-optout and close its stated proof gap.
- Baseline lead pending duplicate/source authorization validation.
  - Follow-up prompt: Review deferred unit client-merge-source-scope and close its stated proof gap.
- Current AUD-18 evidence returned; awaiting parent validation.
  - Follow-up prompt: Review deferred unit aud-18-export and close its stated proof gap. Paths: apps/core/export_jobs.py, apps/core/import_export.py, apps/core/import_export_views.py.
- Requires pre-upgrade unscoped browser sessionStorage; cross-account migration impact not yet independently validated.
  - Follow-up prompt: Review deferred unit legacy-inbox-draft and close its stated proof gap. Paths: frontend/src/features/conversations/hooks/useInboxDraft.ts.
- Baseline role-boundary candidate awaiting parent validation.
  - Follow-up prompt: Review deferred unit lead-task-scope and close its stated proof gap. Paths: apps/leads/views.py, apps/leads/serializers.py, apps/leads/services.py, apps/tasks/policy.py.
- Baseline sensitive-field candidate awaiting parent validation.
  - Follow-up prompt: Review deferred unit deal-money-summary and close its stated proof gap. Paths: apps/crm/views.py, apps/crm/selectors.py, apps/crm/serializers.py.
- Baseline sensitive-field candidate awaiting parent validation.
  - Follow-up prompt: Review deferred unit deal-money-summary-fbf1714889edbd41 and close its stated proof gap. Paths: apps/crm/views.py, apps/crm/selectors.py, apps/crm/serializers.py.
- Analytics investigator candidate awaiting full route and scope validation.
  - Follow-up prompt: Review deferred unit analytics-manager-scope and close its stated proof gap. Paths: apps/analytics/crm_metrics.py.
- Notification investigator candidate awaiting parent validation of mutable delivery fields and worker authority.
  - Follow-up prompt: Review deferred unit notification-delivery-update and close its stated proof gap. Paths: apps/notifications/serializers.py, apps/notifications/views.py, apps/notifications/services.py.
- Investigator candidate awaiting validation of format grammar and reachable prepare controls.
  - Follow-up prompt: Review deferred unit outreach-format-expansion and close its stated proof gap. Paths: apps/outreach/services.py.
- Investigator candidate awaiting validation of status route authorization and returned personal data.
  - Follow-up prompt: Review deferred unit appointment-notification-status and close its stated proof gap. Paths: apps/outreach/views.py.
- Potential AUD-22 sibling and independent missing AV control awaiting parent validation.
  - Follow-up prompt: Review deferred unit outreach-xlsx-sibling and close its stated proof gap. Paths: apps/outreach.
- Investigator candidate awaiting parent validation of direct notes API versus linked record scopes.
  - Follow-up prompt: Review deferred unit note-linked-scope and close its stated proof gap. Paths: apps/activities/views.py, apps/activities/serializers.py, apps/core/viewsets.py.
- AI investigator candidate awaiting immutable approval binding and role-split validation.
  - Follow-up prompt: Review deferred unit approval-rebind and close its stated proof gap. Paths: apps/ai_core/views.py, apps/ai_core/serializers.py, apps/ai_core/crm_approval.py.
- Analytics investigator candidate awaiting full route and scope validation.
  - Follow-up prompt: Review deferred unit analytics-manager-scope-02d769ed598564be and close its stated proof gap. Paths: apps/analytics/crm_metrics.py.
- Notification investigator candidate awaiting parent validation of mutable delivery fields and worker authority.
  - Follow-up prompt: Review deferred unit notification-delivery-update-1e768233ec516b9d and close its stated proof gap. Paths: apps/notifications/serializers.py, apps/notifications/views.py, apps/notifications/services.py.
- Investigator candidate awaiting validation of format grammar and reachable prepare controls.
  - Follow-up prompt: Review deferred unit outreach-format-expansion-3dd212f6c94fe29e and close its stated proof gap. Paths: apps/outreach/services.py.
- Investigator candidate awaiting validation of status route authorization and returned personal data.
  - Follow-up prompt: Review deferred unit appointment-notification-status-46ca620668d571a6 and close its stated proof gap. Paths: apps/outreach/views.py.
- Potential AUD-22 sibling and independent missing AV control awaiting parent validation.
  - Follow-up prompt: Review deferred unit outreach-xlsx-sibling-286d9b066eb5a400 and close its stated proof gap. Paths: apps/outreach/imports.py.
- Investigator candidate awaiting parent validation of direct notes API versus linked record scopes.
  - Follow-up prompt: Review deferred unit note-linked-scope-b22dc44e445a3d68 and close its stated proof gap. Paths: apps/activities/views.py, apps/activities/serializers.py, apps/core/viewsets.py.
- Requires pre-upgrade unscoped browser sessionStorage; cross-account migration impact not yet independently validated.
  - Follow-up prompt: Review deferred unit legacy-inbox-draft-b0b5916bd80f1b09 and close its stated proof gap. Paths: frontend/src/features/inbox.
- Non-live callback secret/channel binding remains unresolved: need to establish realistic secret-holder capability and intended deployment before promotion.
  - Follow-up prompt: Review deferred unit discovery-0004-whatsapp-nonlive-binding and close its stated proof gap. Paths: apps/integrations/providers/whatsapp.py, apps/integrations/whatsapp/__init__.py.
- Legacy create_\* execution uses endpoint preliminary approval checks but lacks the crm_\* locked validator; concurrency/revocation semantics not fully established.
  - Follow-up prompt: Review deferred unit discovery-0004-legacy-ai-approval and close its stated proof gap. Paths: apps/ai_core/views.py, apps/ai_core/tool_registry.py.
- Inventory reconciliation: these paths were not fully security-audited by parent or investigators. Searches, architecture mapping and partial excerpts do not close review. This final worker result is not whole-repository certification.
  - Follow-up prompt: Review deferred unit discovery-0004-unreviewed-source and close its stated proof gap. Paths: docs/testing/project-risk-register-20261019.md, .agents/skills/zani-analyze-crm-product/SKILL.md, .agents/skills/zani-analyze-crm-product/agents/openai.yaml, .agents/skills/zani-analyze-crm-product/references/crm-mechanics.md, .agents/skills/zani-build-integration-reliability/SKILL.md, .agents/skills/zani-build-integration-reliability/agents/openai.yaml, .agents/skills/zani-build-integration-reliability/references/integration-checklist.md, .agents/skills/zani-change-crm-domain/SKILL.md, .agents/skills/zani-change-crm-domain/agents/openai.yaml, .agents/skills/zani-change-crm-domain/references/change-impact.md, .agents/skills/zani-evaluate-ai-grounding/SKILL.md, .agents/skills/zani-evaluate-ai-grounding/agents/openai.yaml, .agents/skills/zani-evaluate-ai-grounding/references/ai-checklist.md, .agents/skills/zani-handle-incident/SKILL.md, .agents/skills/zani-handle-incident/agents/openai.yaml, .agents/skills/zani-handle-incident/references/incident-runbook.md, .agents/skills/zani-plan-observability/SKILL.md, .agents/skills/zani-plan-observability/agents/openai.yaml, .agents/skills/zani-plan-observability/references/observability-checklist.md, .agents/skills/zani-review-access/SKILL.md, .agents/skills/zani-review-access/agents/openai.yaml, .agents/skills/zani-review-access/references/access-checklist.md, .agents/skills/zani-review-code/SKILL.md, .agents/skills/zani-review-code/agents/openai.yaml, .agents/skills/zani-review-code/references/review-checklist.md, .agents/skills/zani-review-frontend/SKILL.md, .agents/skills/zani-review-frontend/agents/openai.yaml, .agents/skills/zani-review-frontend/references/frontend-checklist.md, .agents/skills/zani-review-performance/SKILL.md, .agents/skills/zani-review-performance/agents/openai.yaml, .agents/skills/zani-review-performance/references/performance-checklist.md, .agents/skills/zani-run-verification/SKILL.md, .agents/skills/zani-run-verification/agents/openai.yaml, .agents/skills/zani-run-verification/references/verification-commands.md, .codex/continuity-hook.cjs, .codex/continuity-hook.test.cjs, .codex/hooks.json, .codex/project-session.json, .dockerignore, .env.example, .env.local.example, .env.production.example, .env.render.example, .env.staging.example, .github/workflows/ci.yml, .gitignore, .rgignore, AGENTS.md, README.md, STATUS.md, actual_docs/DEFECT_KNOWLEDGE_BASE.md, actual_docs/PROJECT_HANDOFF.md, actual_docs/README.md, actual_docs/UNIFIED_FALLBACK_INVENTORY.generated.md, apps/README.md, apps/__init__.py, apps/accounts/__init__.py, apps/accounts/admin.py, apps/accounts/apps.py, apps/accounts/email_change_views.py, apps/accounts/email_changes.py, apps/accounts/legal_documents.py, apps/accounts/management/__init__.py, apps/accounts/management/commands/__init__.py, apps/accounts/management/commands/prepare_e2e_smoke_data.py, apps/accounts/mfa.py, apps/accounts/migrations/0001_initial.py, apps/accounts/migrations/0002_update_user_roles.py, apps/accounts/migrations/0003_alter_user_role.py, apps/accounts/migrations/0004_socialidentity.py, apps/accounts/migrations/0005_userpreference.py, apps/accounts/migrations/0006_privileged_mfa.py, apps/accounts/migrations/0007_user_auth_epoch.py, apps/accounts/migrations/0008_useravatar.py, apps/accounts/migrations/0009_emailchangechallenge.py, apps/accounts/migrations/0010_accountsession.py, apps/accounts/migrations/0011_support_account_recovery.py, apps/accounts/migrations/__init__.py, apps/accounts/models.py, apps/accounts/passwords.py, apps/accounts/recovery_selectors.py, apps/accounts/serializers.py, apps/accounts/session_views.py, apps/accounts/tests.py, apps/accounts/tests_avatars.py, apps/accounts/tests_device_sessions.py, apps/accounts/tests_email_changes.py, apps/accounts/tests_legal_documents.py, apps/accounts/tests_mfa.py, apps/accounts/tests_recovery.py, apps/accounts/tests_session_policy.py, apps/activities/__init__.py, apps/activities/admin.py, apps/activities/apps.py, apps/activities/migrations/0001_initial.py, apps/activities/migrations/0002_segment_segmentfilter_and_more.py, apps/activities/migrations/0003_alter_taggedobject_options.py, apps/activities/migrations/0004_taggedobject_indexes.py, apps/activities/migrations/0005_remove_taggedobject_activities_tag_obj_bus_ent_tag_idx.py, apps/activities/migrations/__init__.py, apps/activities/models.py, apps/activities/segments.py, apps/activities/serializers.py, apps/activities/services.py, apps/activities/taxonomy.py, apps/activities/tests.py, apps/activities/tests_segments.py, apps/activities/tests_timeline_workspace.py, apps/activities/tests_write_boundaries.py, apps/activities/timeline_queries.py, apps/activities/views.py, apps/activities/write_validation.py, apps/ai_core/__init__.py, apps/ai_core/admin.py, apps/ai_core/agent_views.py, apps/ai_core/ai_client.py, apps/ai_core/analyst.py, apps/ai_core/apps.py, apps/ai_core/assistant.py, apps/ai_core/audit.py, apps/ai_core/context_service.py, apps/ai_core/conversation_copy.py, apps/ai_core/conversation_memory.py, apps/ai_core/conversation_preparation.py, apps/ai_core/conversation_router.py, apps/ai_core/crm_planner.py, apps/ai_core/crm_transitions.py, apps/ai_core/crm_views.py, apps/ai_core/crm_writes.py, apps/ai_core/grounding.py, apps/ai_core/history.py, apps/ai_core/inbox_runtime.py, apps/ai_core/knowledge.py, apps/ai_core/migrations/0001_initial.py, apps/ai_core/migrations/0002_agentprofile.py, apps/ai_core/migrations/0003_aitoolcalllog.py, apps/ai_core/migrations/0004_approvalrequest.py, apps/ai_core/migrations/0005_aitoolcalllog_attempts_aitoolcalllog_executed_at_and_more.py, apps/ai_core/migrations/0006_agent_knowledge_isolation.py, apps/ai_core/migrations/0007_agent_conversations.py, apps/ai_core/migrations/0008_customer_knowledge_visibility.py, apps/ai_core/migrations/__init__.py, apps/ai_core/models.py, apps/ai_core/prompt_service.py, apps/ai_core/providers/__init__.py, apps/ai_core/providers/base.py, apps/ai_core/providers/kimi.py, apps/ai_core/providers/mock.py, apps/ai_core/providers/openai.py, apps/ai_core/providers/openrouter.py, apps/ai_core/providers/registry.py, apps/ai_core/recommendations.py, apps/ai_core/runtime_policy.py, apps/ai_core/serializers.py, apps/ai_core/services.py, apps/ai_core/tasks.py, apps/ai_core/tests.py, apps/ai_core/tests_agent_runtime.py, apps/ai_core/tests_conversation_api.py, apps/ai_core/tests_conversation_execution.py, apps/ai_core/tests_conversation_memory.py, apps/ai_core/tests_conversation_state.py, apps/ai_core/tests_crm_planner.py, apps/ai_core/tests_crm_tools.py, apps/ai_core/tests_history.py, apps/ai_core/tests_history_answers.py, apps/ai_core/tests_inbox_continuity.py, apps/ai_core/tests_job_recovery.py, apps/ai_core/tests_knowledge_isolation.py, apps/ai_core/tests_prompt_preferences.py, apps/ai_core/tests_quality.py, apps/ai_core/tests_settings_certification.py, apps/ai_core/tests_workflows.py, apps/ai_core/views.py, apps/ai_core/workflows.py, apps/analytics/__init__.py, apps/analytics/admin.py, apps/analytics/apps.py, apps/analytics/crm_metrics.py, apps/analytics/financial_metrics.py, apps/analytics/manual_finance.py, apps/analytics/migrations/0001_initial.py, apps/analytics/migrations/0002_reportwidget_scheduledreport.py, apps/analytics/migrations/__init__.py, apps/analytics/models.py, apps/analytics/reports.py, apps/analytics/serializers.py, apps/analytics/tests.py, apps/analytics/tests_financial_sources.py, apps/analytics/tests_manual_finance.py, apps/analytics/tests_workspace.py, apps/analytics/views.py, apps/analytics/workspace.py, apps/analytics/workspace_export.py, apps/automations/__init__.py, apps/automations/action_validation.py, apps/automations/admin.py, apps/automations/apps.py, apps/automations/condition_fields.py, apps/automations/configuration.py, apps/automations/configuration_views.py, apps/automations/engine.py, apps/automations/management/__init__.py, apps/automations/management/commands/__init__.py, apps/automations/management/commands/queue_runtime_smoke.py, apps/automations/migrations/0001_initial.py, apps/automations/migrations/0002_alter_automationrule_trigger_type.py, apps/automations/migrations/0003_automationrun_action_results_automationrun_attempts_and_more.py, apps/automations/migrations/0004_alter_automationaction_action_type_and_more.py, apps/automations/migrations/0005_automationrun_current_action_index_and_more.py, apps/automations/migrations/__init__.py, apps/automations/models.py, apps/automations/permissions.py, apps/automations/serializers.py, apps/automations/tasks.py, apps/automations/tests.py, apps/automations/tests_action_validation.py, apps/automations/tests_claim_ownership.py, apps/automations/tests_configuration.py, apps/automations/tests_configuration_concurrency.py, apps/automations/tests_dispatch_commit.py, apps/automations/tests_follow_up_concurrency.py, apps/automations/tests_follow_up_policy.py, apps/automations/tests_queue_runtime.py, apps/automations/tests_rule_editor.py, apps/automations/views.py, apps/billing/__init__.py, apps/billing/admin.py, apps/billing/apps.py, apps/billing/commerce_selectors.py, apps/billing/entitlements.py, apps/billing/migrations/0001_initial.py, apps/billing/migrations/0002_seed_plans.py, apps/billing/migrations/0003_usagecounter.py, apps/billing/migrations/0004_update_default_entitlement_limits.py, apps/billing/migrations/0005_subscription_billing_controls.py, apps/billing/migrations/0006_billingoffer_billingorder_billingevent_and_more.py, apps/billing/migrations/__init__.py, apps/billing/storage.py, apps/billing/tests.py, apps/billing/tests_commerce.py, apps/billing/tests_commerce_concurrency.py, apps/billing/tests_settings_scope.py, apps/billing/usage.py, apps/bots/__init__.py, apps/bots/admin.py, apps/bots/ai.py, apps/bots/ai_settings.py, apps/bots/apps.py, apps/bots/automation_policy.py, apps/bots/channel_actions.py, apps/bots/configuration.py, apps/bots/customer_safety.py, apps/bots/deletion.py, apps/bots/handoff_notice.py, apps/bots/handoff_recovery.py, apps/bots/inbox_service.py, apps/bots/lifecycle.py, apps/bots/management/__init__.py, apps/bots/management/commands/__init__.py, apps/bots/management/commands/crm_pipeline_runtime_check.py, apps/bots/migrations/0001_initial.py, apps/bots/migrations/0002_public_widget_ids.py, apps/bots/migrations/0003_botconversation_assigned_to_and_more.py, apps/bots/migrations/0004_botconversation_deal.py, apps/bots/migrations/0005_botconversation_archive_reason_and_more.py, apps/bots/migrations/0006_botconversation_client_indexes.py, apps/bots/migrations/0007_remove_botconversation_bots_botconv_busi_client_arch_idx.py, apps/bots/migrations/0008_botmessage_unique_bot_message_external_delivery.py, apps/bots/migrations/0009_botconversation_bots_botcon_busines_81d379_idx_and_more.py, apps/bots/migrations/0010_botmessage_delivery_attempts_and_more.py, apps/bots/migrations/0011_botconversation_ai_safety_state.py, apps/bots/migrations/0012_answered_handoff_recovery.py, apps/bots/migrations/__init__.py, apps/bots/models.py, apps/bots/outbound_delivery.py, apps/bots/preview.py, apps/bots/runtime_configuration.py, apps/bots/safety_content.py, apps/bots/safety_policy.py, apps/bots/safety_state.py, apps/bots/sales_playbooks.py, apps/bots/scenarios.py, apps/bots/scheduling_context.py, apps/bots/serializers.py, apps/bots/services.py, apps/bots/tasks.py, apps/bots/tests.py, apps/bots/tests_automatic_booking.py, apps/bots/tests_configuration.py, apps/bots/tests_controlled_creation.py, apps/bots/tests_customer_knowledge.py, apps/bots/tests_customer_safety.py, apps/bots/tests_deletion.py, apps/bots/tests_handoff_notice.py, apps/bots/tests_handoff_recovery.py, apps/bots/tests_pause_inbound.py, apps/bots/tests_preview.py, apps/bots/tests_readiness.py, apps/bots/tests_runtime_configuration.py, apps/bots/tests_safety_migration.py, apps/bots/tests_safety_recovery.py, apps/bots/tests_safety_state.py, apps/bots/tests_scenarios.py, apps/bots/views.py, apps/branches/__init__.py, apps/branches/access.py, apps/branches/apps.py, apps/branches/bot_context.py, apps/branches/compatibility.py, apps/branches/config_serializers.py, apps/branches/config_views.py, apps/branches/configuration.py, apps/branches/migrations/0001_initial.py, apps/branches/migrations/0002_branchservice_branchtraveltime_scheduleday_and_more.py, apps/branches/migrations/__init__.py, apps/branches/models.py, apps/branches/schedule.py, apps/branches/serializers.py, apps/branches/services.py, apps/branches/staff_lifecycle.py, apps/branches/staff_views.py, apps/branches/tests_access.py, apps/branches/tests_bot.py, apps/branches/tests_compatibility.py, apps/branches/tests_concurrency.py, apps/branches/tests_scheduling.py, apps/branches/tests_staff.py, apps/branches/views.py, apps/businesses/__init__.py, apps/businesses/access.py, apps/businesses/activation.py, apps/businesses/admin.py, apps/businesses/apps.py, apps/businesses/assignment_notifications.py, apps/businesses/assignment_policy.py, apps/businesses/capabilities.py, apps/businesses/employee_access_selectors.py, apps/businesses/management/__init__.py, apps/businesses/management/commands/__init__.py, apps/businesses/management/commands/pilot_launch_quality_gate.py, apps/businesses/management/commands/prepare_pilot_demo.py, apps/businesses/management/commands/seed_pilot_demo.py, apps/businesses/migrations/0001_initial.py, apps/businesses/migrations/0002_rolepreset_alter_businessmember_role_businessrole_and_more.py, apps/businesses/migrations/0003_business_landing_domain_business_landing_id_and_more.py, apps/businesses/migrations/0004_businessinvitation.py, apps/businesses/migrations/0005_business_operational_settings.py, apps/businesses/migrations/0006_businessmember_availability_status_and_more.py, apps/businesses/migrations/0007_businessinvitation_team.py, apps/businesses/migrations/0008_alter_businessinvitation_role_and_more.py, apps/businesses/migrations/0009_routingpolicy_slaattention_and_more.py, apps/businesses/migrations/0010_alter_businessinvitation_role_and_more.py, apps/businesses/migrations/0011_financial_analysis_source.py, apps/businesses/migrations/0012_business_ownership_transfer.py, apps/businesses/migrations/0013_employee_access_repair.py, apps/businesses/migrations/__init__.py, apps/businesses/models.py, apps/businesses/ownership_selectors.py, apps/businesses/routing.py, apps/businesses/tasks.py, apps/businesses/tests_access.py, apps/businesses/tests_activation.py, apps/businesses/tests_demo_seed.py, apps/businesses/tests_employee_access.py, apps/businesses/tests_employee_access_concurrency.py, apps/businesses/tests_invitation_concurrency.py, apps/businesses/tests_member_deactivation.py, apps/businesses/tests_ownership.py, apps/businesses/tests_role_visibility.py, apps/businesses/tests_settings_team.py, apps/businesses/views.py, apps/clients/__init__.py, apps/clients/admin.py, apps/clients/apps.py, apps/clients/export_privacy.py, apps/clients/identity.py, apps/clients/lifecycle.py, apps/clients/migrations/0001_initial.py, apps/clients/migrations/0002_client_archive_reason_client_archived_at_and_more.py, apps/clients/migrations/0003_clientmergelog.py, apps/clients/migrations/0004_client_normalized_identity.py, apps/clients/migrations/0005_client_source_attribution.py, apps/clients/migrations/__init__.py, apps/clients/models.py, apps/clients/selectors.py, apps/clients/serializers.py, apps/clients/services.py, apps/clients/tests.py, apps/clients/tests_archive_dependencies.py, apps/clients/tests_sensitive_notes.py, apps/clients/tests_workspace_filters.py, apps/clients/views.py, apps/clients/workspace.py, apps/conversations/__init__.py, apps/conversations/admin.py, apps/conversations/ai_qualification.py, apps/conversations/apps.py, apps/conversations/auto_pipeline.py, apps/conversations/booking.py, apps/conversations/client_linking.py, apps/conversations/inbox_context.py, apps/conversations/inbox_helpers.py, apps/conversations/inbox_serializers.py, apps/conversations/inbox_views.py, apps/conversations/message_history.py, apps/conversations/migrations/0001_initial.py, apps/conversations/migrations/0002_conversation_archive_reason_conversation_archived_at_and_more.py, apps/conversations/migrations/0003_quickreplytemplate.py, apps/conversations/migrations/__init__.py, apps/conversations/models.py, apps/conversations/pipeline.py, apps/conversations/serializers.py, apps/conversations/services.py, apps/conversations/tests_ai_behavior_boundaries.py, apps/conversations/tests_ai_confirmation.py, apps/conversations/tests_client_linking.py, apps/conversations/tests_inbox_context.py, apps/conversations/tests_inbox_tasks.py, apps/conversations/tests_message_history.py, apps/conversations/tests_message_history_concurrency.py, apps/conversations/tests_quick_replies.py, apps/conversations/views.py, apps/core/__init__.py, apps/core/admin.py, apps/core/apps.py, apps/core/archive.py, apps/core/audit.py, apps/core/backup_readiness.py, apps/core/checks.py, apps/core/crm_cards.py, apps/core/crm_filters.py, apps/core/crm_mutations.py, apps/core/crm_read_scope.py, apps/core/csv_safety.py, apps/core/custom_field_views.py, apps/core/custom_fields.py, apps/core/date_ranges.py, apps/core/domain_errors.py, apps/core/exceptions.py, apps/core/idempotency.py, apps/core/import_export.py, apps/core/logging.py, apps/core/management/__init__.py, apps/core/management/commands/__init__.py, apps/core/management/commands/backup_restore_readiness_check.py, apps/core/management/commands/file_antivirus.py, apps/core/management/commands/observability_runtime_check.py, apps/core/management/commands/observe_service_status.py, apps/core/management/commands/paid_beta_gate_check.py, apps/core/management/commands/platform_operations_health_check.py, apps/core/management/commands/production_readiness_audit.py, apps/core/management/commands/storage_runtime_smoke.py, apps/core/management/commands/write_import_samples.py, apps/core/migrations/0001_initial.py, apps/core/migrations/0002_customfielddefinition_customfieldvalue_and_more.py, apps/core/migrations/0003_importjob.py, apps/core/migrations/0004_loginhistory_auditlog_category_auditlog_risk_level_and_more.py, apps/core/migrations/0005_fileattachment.py, apps/core/migrations/0006_alter_auditlog_action.py, apps/core/migrations/0007_importjob_errors_json_alter_importjob_entity_type.py, apps/core/migrations/0008_customfielddefinition_permissions_json.py, apps/core/migrations/0009_exportjob.py, apps/core/migrations/0010_crmcommandidempotency.py, apps/core/migrations/0011_file_security_scanning.py, apps/core/migrations/0012_service_component_state.py, apps/core/migrations/__init__.py, apps/core/models.py, apps/core/operational_dashboard.py, apps/core/operations_health.py, apps/core/paid_beta_gate.py, apps/core/pilot_views.py, apps/core/platform_connector_status.py, apps/core/platform_crm_children.py, apps/core/platform_crm_selectors.py, apps/core/platform_crm_views.py, apps/core/platform_details.py, apps/core/platform_details_views.py, apps/core/platform_overview.py, apps/core/platform_reads.py, apps/core/platform_selectors.py, apps/core/platform_serializers.py, apps/core/platform_views.py, apps/core/platform_worklists.py, apps/core/production_audit.py, apps/core/production_rules.py, apps/core/sanitization.py, apps/core/security_config.py, apps/core/security_views.py, apps/core/serializers.py, apps/core/service_status.py, apps/core/service_status_views.py, apps/core/tasks.py, apps/core/tests.py, apps/core/tests_api_contracts.py, apps/core/tests_api_exceptions.py, apps/core/tests_api_load_smoke.py, apps/core/tests_archive.py, apps/core/tests_b0_security.py, apps/core/tests_b101_capability_enforcement.py, apps/core/tests_b1_runtime.py, apps/core/tests_b2_roles_queues.py, apps/core/tests_b301_performance.py, apps/core/tests_b3_contracts.py, apps/core/tests_b4_capabilities.py, apps/core/tests_b5_performance.py, apps/core/tests_backup_readiness.py, apps/core/tests_business_flows_e2e.py, apps/core/tests_crm_cards.py, apps/core/tests_crm_projection_access.py, apps/core/tests_crm_server_concurrency.py, apps/core/tests_crm_server_scenarios.py, apps/core/tests_crm_workspace_filters.py, apps/core/tests_custom_fields.py, apps/core/tests_file_attachments.py, apps/core/tests_file_scanning.py, apps/core/tests_import_export.py, apps/core/tests_import_job_boundaries.py, apps/core/tests_import_job_concurrency.py, apps/core/tests_import_samples.py, apps/core/tests_mixed_membership_scope.py, apps/core/tests_observability.py, apps/core/tests_paid_beta_gate.py, apps/core/tests_platform_crm.py, apps/core/tests_platform_details.py, apps/core/tests_platform_operations.py, apps/core/tests_platform_overview.py, apps/core/tests_platform_rebuild.py, apps/core/tests_platform_s02.py, apps/core/tests_platform_worklists.py, apps/core/tests_production_audit.py, apps/core/tests_security.py, apps/core/tests_service_status.py, apps/core/tests_storage_runtime.py, apps/core/tests_tenant_isolation.py, apps/core/tests_work_queues.py, apps/core/tests_workspace_related_filters.py, apps/core/work_queues.py, apps/crm/__init__.py, apps/crm/admin.py, apps/crm/apps.py, apps/crm/migrations/0001_initial.py, apps/crm/migrations/0002_default_pipeline.py, apps/crm/migrations/0003_deal_lost_at_deal_lost_reason_deal_next_action_at_and_more.py, apps/crm/migrations/0004_deal_archive_reason_deal_archived_at_and_more.py, apps/crm/migrations/0005_deal_client_indexes.py, apps/crm/migrations/0006_remove_deal_crm_deal_busi_client_arch_idx.py, apps/crm/migrations/0007_dealstagehistory.py, apps/crm/migrations/0008_dealvaluehistory.py, apps/crm/migrations/0009_deal_crm_deal_busines_b4fdd1_idx.py, apps/crm/migrations/0010_pipeline_stage_canonicalization.py, apps/crm/migrations/__init__.py, apps/crm/models.py, apps/crm/pipeline_templates.py, apps/crm/selectors.py, apps/crm/serializers.py, apps/crm/services.py, apps/crm/tests.py, apps/crm/tests_pipeline_boundaries.py, apps/crm/tests_workspace_filters.py, apps/crm/views.py, apps/crm/workspace.py, apps/integrations/__init__.py, apps/integrations/admin.py, apps/integrations/apps.py, apps/integrations/bot_channel_credentials.py, apps/integrations/connectors.py, apps/integrations/credential_encryption.py, apps/integrations/crm_mapping.py, apps/integrations/financial_sources.py, apps/integrations/instagram.py, apps/integrations/kaspi/__init__.py, apps/integrations/kaspi/base.py, apps/integrations/kaspi/mock.py, apps/integrations/kaspi/provider_placeholder.py, apps/integrations/management/__init__.py, apps/integrations/management/commands/__init__.py, apps/integrations/management/commands/instagram_local_real_test_check.py, apps/integrations/management/commands/kaspi_local_real_test_check.py, apps/integrations/management/commands/moysklad_local_real_test_check.py, apps/integrations/management/commands/ozon_local_real_test_check.py, apps/integrations/management/commands/provider_rollout_readiness_check.py, apps/integrations/management/commands/rotate_connector_credentials.py, apps/integrations/management/commands/telegram_local_real_test_check.py, apps/integrations/management/commands/telegram_webhook_smoke.py, apps/integrations/management/commands/whatsapp_local_real_test_check.py, apps/integrations/management/commands/wildberries_local_real_test_check.py, apps/integrations/message_idempotency.py, apps/integrations/migrations/0001_initial.py, apps/integrations/migrations/0002_webhookendpoint_webhookdeliverylog_apitoken_and_more.py, apps/integrations/migrations/0003_businessconnector_businessevent_connectorcredential_and_more.py, apps/integrations/migrations/0004_add_pilot_connector_providers.py, apps/integrations/migrations/0005_alter_businessconnector_status.py, apps/integrations/migrations/0006_encrypt_plaintext_config_credentials.py, apps/integrations/migrations/__init__.py, apps/integrations/models.py, apps/integrations/moysklad/__init__.py, apps/integrations/moysklad/base.py, apps/integrations/moysklad/import_adapter.py, apps/integrations/moysklad/mock.py, apps/integrations/one_c/__init__.py, apps/integrations/one_c/base.py, apps/integrations/one_c/import_adapter.py, apps/integrations/one_c/mock.py, apps/integrations/ozon/__init__.py, apps/integrations/ozon/base.py, apps/integrations/ozon/mock.py, apps/integrations/provider_rollout.py, apps/integrations/providers/__init__.py, apps/integrations/providers/base.py, apps/integrations/providers/instagram.py, apps/integrations/providers/mock.py, apps/integrations/providers/registry.py, apps/integrations/providers/telegram.py, apps/integrations/providers/website.py, apps/integrations/providers/whatsapp.py, apps/integrations/public_api.py, apps/integrations/sanitization.py, apps/integrations/serializers.py, apps/integrations/services.py, apps/integrations/sync_service.py, apps/integrations/telegram.py, apps/integrations/tests.py, apps/integrations/tests_channel_ownership.py, apps/integrations/tests_channel_setup_consistency.py, apps/integrations/tests_connectors.py, apps/integrations/tests_credential_encryption.py, apps/integrations/tests_encrypted_config.py, apps/integrations/tests_provider_rollout.py, apps/integrations/tests_public_api.py, apps/integrations/view_actions.py, apps/integrations/views.py, apps/integrations/whatsapp/__init__.py, apps/integrations/whatsapp/base.py, apps/integrations/whatsapp/embedded_signup.py, apps/integrations/whatsapp/mock.py, apps/integrations/whatsapp/provider_placeholder.py, apps/integrations/wildberries/__init__.py, apps/integrations/wildberries/base.py, apps/integrations/wildberries/mock.py, apps/leads/__init__.py, apps/leads/admin.py, apps/leads/apps.py, apps/leads/form_assignment.py, apps/leads/migrations/0001_initial.py, apps/leads/migrations/0002_lead_archive_reason_lead_archived_at_and_more.py, apps/leads/migrations/0003_leadform_leadformfield_leadformsubmission_and_more.py, apps/leads/migrations/0004_leadformsubmissionerror_leadform_landing_domain_and_more.py, apps/leads/migrations/0005_lead_client_indexes.py, apps/leads/migrations/0006_lead_list_filter_indexes.py, apps/leads/migrations/0007_remove_lead_lead_lead_busi_client_arch_idx_and_more.py, apps/leads/migrations/0008_lead_leads_lead_busines_39f06b_idx.py, apps/leads/migrations/__init__.py, apps/leads/models.py, apps/leads/selectors.py, apps/leads/serializers.py, apps/leads/services.py, apps/leads/tests_assignment_patch.py, apps/leads/tests_crm_light.py, apps/leads/tests_form_write_boundaries.py, apps/leads/tests_forms.py, apps/leads/tests_workspace_filters.py, apps/leads/views.py, apps/leads/workspace.py, apps/notifications/__init__.py, apps/notifications/admin.py, apps/notifications/apps.py, apps/notifications/channels.py, apps/notifications/delivery.py, apps/notifications/email.py, apps/notifications/management/__init__.py, apps/notifications/management/commands/__init__.py, apps/notifications/management/commands/email_runtime_smoke.py, apps/notifications/management/commands/process_due_notifications.py, apps/notifications/migrations/0001_initial.py, apps/notifications/migrations/0002_alter_notification_options_notification_action_label_and_more.py, apps/notifications/migrations/0003_notification_recipient.py, apps/notifications/migrations/0004_notificationpreference.py, apps/notifications/migrations/0005_notification_attempts_notification_delivered_at_and_more.py, apps/notifications/migrations/__init__.py, apps/notifications/models.py, apps/notifications/routing.py, apps/notifications/serializers.py, apps/notifications/tasks.py, apps/notifications/tests.py, apps/notifications/tests_bell.py, apps/notifications/tests_email.py, apps/notifications/tests_settings_preferences.py, apps/onboarding/__init__.py, apps/onboarding/apps.py, apps/onboarding/serializers.py, apps/onboarding/services.py, apps/onboarding/templates.py, apps/onboarding/tests.py, apps/onboarding/views.py, apps/outreach/__init__.py, apps/outreach/admin.py, apps/outreach/apps.py, apps/outreach/migrations/0001_initial.py, apps/outreach/migrations/0002_production_safety.py, apps/outreach/migrations/0003_rename_outreach_ou_busines_2f6332_idx_outreach_ou_busines_5dee11_idx_and_more.py, apps/outreach/migrations/__init__.py, apps/outreach/models.py, apps/outreach/serializers.py, apps/outreach/services.py, apps/outreach/tests.py, apps/outreach/views.py, apps/payments/__init__.py, apps/payments/migrations/0001_initial.py, apps/payments/migrations/__init__.py, apps/payments/tests.py, apps/pricing/__init__.py, apps/pricing/admin.py, apps/pricing/apps.py, apps/pricing/management/__init__.py, apps/pricing/management/commands/__init__.py, apps/pricing/management/commands/kaspi_collect_competitor_offers.py, apps/pricing/management/commands/kaspi_pricing_cycle.py, apps/pricing/management/commands/kaspi_pricing_local_real_test_check.py, apps/pricing/management/commands/kaspi_pricing_readiness_check.py, apps/pricing/migrations/0001_initial.py, apps/pricing/migrations/0002_kaspipricingrule_autopilot_confirmed_at_and_more.py, apps/pricing/migrations/0003_pricingcatalogitem.py, apps/pricing/migrations/0004_kaspipricingcontrol_kaspipricingalert.py, apps/pricing/migrations/__init__.py, apps/pricing/models.py, apps/pricing/serializers.py, apps/pricing/services.py, apps/pricing/tasks.py, apps/pricing/tests.py, apps/pricing/views.py, apps/scheduling/__init__.py, apps/scheduling/admin.py, apps/scheduling/apps.py, apps/scheduling/availability.py, apps/scheduling/message_settings.py, apps/scheduling/migrations/0001_initial.py, apps/scheduling/migrations/0002_appointment_archive_reason_appointment_archived_at_and_more.py, apps/scheduling/migrations/0003_appointmentmessagesetting.py, apps/scheduling/migrations/0004_appointment_client_indexes.py, apps/scheduling/migrations/0005_remove_appointment_sched_appoint_busi_client_arch_idx.py, apps/scheduling/migrations/0006_resource_linked_user.py, apps/scheduling/migrations/0007_appointment_scheduling__busines_e1d6c2_idx_and_more.py, apps/scheduling/migrations/0008_specialist_schedule_exceptions.py, apps/scheduling/migrations/0009_appointment_booked_duration_minutes_and_more.py, apps/scheduling/migrations/__init__.py, apps/scheduling/models.py, apps/scheduling/resource_services.py, apps/scheduling/schedule_serializers.py, apps/scheduling/schedule_views.py, apps/scheduling/serializers.py, apps/scheduling/services.py, apps/scheduling/tests.py, apps/scheduling/tests_settings_delivery.py, apps/scheduling/tests_specialist_schedule.py, apps/scheduling/valuation.py, apps/scheduling/views.py, apps/services/__init__.py, apps/services/admin.py, apps/services/apps.py, apps/services/migrations/0001_initial.py, apps/services/migrations/0002_service_archive_fields.py, apps/services/migrations/__init__.py, apps/services/models.py, apps/services/serializers.py, apps/services/services.py, apps/services/tests.py, apps/services/views.py, apps/support/__init__.py, apps/support/access.py, apps/support/apps.py, apps/support/incidents.py, apps/support/messages.py, apps/support/migrations/0001_initial.py, apps/support/migrations/0002_incidentlink.py, apps/support/migrations/__init__.py, apps/support/models.py, apps/support/selectors.py, apps/support/serializers.py, apps/support/services.py, apps/support/tests_api.py, apps/support/tests_concurrency.py, apps/support/tests_domain.py, apps/support/tests_incidents.py, apps/support/urls.py, apps/support/views.py, apps/tasks/__init__.py, apps/tasks/admin.py, apps/tasks/apps.py, apps/tasks/escalation.py, apps/tasks/migrations/0001_initial.py, apps/tasks/migrations/0002_task_appointment_task_tasks_task_appoint_da66d2_idx.py, apps/tasks/migrations/0003_task_archive_reason_task_archived_at_and_more.py, apps/tasks/migrations/0004_taskcomment_task_completed_by_task_parent_task_and_more.py, apps/tasks/migrations/0005_task_client_indexes.py, apps/tasks/migrations/0006_remove_task_tasks_task_busi_client_arch_idx.py, apps/tasks/migrations/0007_task_cancel_reason_task_cancelled_at_and_more.py, apps/tasks/migrations/0008_task_tasks_task_busines_38b472_idx_and_more.py, apps/tasks/migrations/0009_task_conversation_task_tasks_task_convers_176087_idx.py, apps/tasks/migrations/0010_scheduled_reminder_delivery.py, apps/tasks/migrations/0011_task_specialist_task_waiting_reason_and_more.py, apps/tasks/migrations/__init__.py, apps/tasks/models.py, apps/tasks/mutations.py, apps/tasks/policy.py, apps/tasks/reminders.py, apps/tasks/selectors.py, apps/tasks/serializers.py, apps/tasks/services.py, apps/tasks/templates.py, apps/tasks/tests.py, apps/tasks/tests_concurrency.py, apps/tasks/tests_migrations.py, apps/tasks/tests_reminders.py, apps/tasks/tests_workspace.py, apps/tasks/views.py, archive_docs/2026-09-14/README.md, archive_docs/2026-09-14/docs/crm/CRM_AUDIT_REQUIRED_CHANGES.md, archive_docs/2026-09-14/docs/crm/CRM_IMPLEMENTATION_TASKS.md, archive_docs/2026-09-14/docs/frontend/ui-ux-polish-phase-10.md, archive_docs/2026-09-14/docs/integrations/providers/telegram-connector-mvp.md, archive_docs/2026-09-14/docs/pilot/block10-clean-pilot-package.md, archive_docs/2026-09-14/docs/pilot/block11-pilot-smoke-cleanup.md, archive_docs/2026-09-14/docs/pilot/block12-platform-operations-panel.md, archive_docs/2026-09-14/docs/pilot/block13-support-operator-workflow.md, archive_docs/2026-09-14/docs/pilot/block14-pilot-demo-launch.md, archive_docs/2026-09-14/docs/pilot/block5-unified-inbox.md, archive_docs/2026-09-14/docs/pilot/block7-mobile-owner-ux.md, archive_docs/2026-09-14/docs/pilot/block8-pilot-smoke-demo.md, archive_docs/2026-09-14/docs/pilot/block9-data-import-pilot.md, archive_docs/2026-09-14/docs/pilot/task3_task_calendar_flow_polish.md, archive_docs/2026-09-14/docs/pilot/task5_pilot_qa_polish_report.md, archive_docs/2026-09-14/docs/pilot/task6_pilot_readiness_checklist_report.md, archive_docs/2026-09-14/docs/pilot/task7_website_chat_connector_foundation_report.md, archive_docs/2026-09-14/docs/pilot/task8_inbox_polish_report.md, archive_docs/2026-09-14/docs/pilot/task9_integrations_status_polish_report.md, archive_docs/2026-09-14/docs/product/competitive-regression-report.md, archive_docs/2026-09-14/docs/production/staging/staging-render-execution-report.md, archive_docs/2026-09-14/docs/testing/regression-report.md, archive_docs/2026-09-14/plan/commit_pr_split_plan_2026_06_08.md, archive_docs/2026-09-14/plan/production_qa_2026_06_09.md, archive_docs/2026-09-14/plan/readiness_plan.md, archive_docs/2026-09-14/plan/stabilization_audit_2026_06_08.md, archive_docs/2026-10-07/AGENTS.snapshot.md, archive_docs/2026-10-07/CODEBASE_DEEP_AUDIT_2026-07-23.md, archive_docs/2026-10-07/MACDENT_PLATFORM_CRM_TECHNICAL_AUDIT_2026-09-18.md, archive_docs/2026-10-07/MACDENT_PRODUCT_UI_UX_AUDIT_2026-09-18.md, archive_docs/2026-10-07/README.md, archive_docs/2026-10-07/README.snapshot.md, archive_docs/2026-10-07/STATUS.md, archive_docs/2026-10-07/accounts/test_accounts.md, archive_docs/2026-10-07/actual_docs/APP_FUNCTIONAL_CERTIFICATION.md, archive_docs/2026-10-07/actual_docs/APP_FUNCTIONAL_CERTIFICATION_REPORT_2026-08-20.md, archive_docs/2026-10-07/actual_docs/BACKEND_AUDIT_REMEDIATION_PLAN.md, archive_docs/2026-10-07/actual_docs/CRM_WORKSPACE_UX_REFORM.md, archive_docs/2026-10-07/actual_docs/DEFECT_KNOWLEDGE_BASE.md, archive_docs/2026-10-07/actual_docs/PRE_PILOT_CODE_READINESS_MASTER.md, archive_docs/2026-10-07/actual_docs/PROJECT_HANDOFF.md, archive_docs/2026-10-07/actual_docs/README.md, archive_docs/2026-10-07/actual_docs/UNIFIED_FALLBACK_EXPERIENCE_PLAN.md, archive_docs/2026-10-07/apps/README.md, archive_docs/2026-10-07/archive_docs/README.md, archive_docs/2026-10-07/docs/README.md, archive_docs/2026-10-07/docs/WARM_PREMIUM_CRM_REDESIGN_BRIEF.md, archive_docs/2026-10-07/docs/ai/AI_ASSISTANT_RULES.md, archive_docs/2026-10-07/docs/analytics/analytics-reporting.md, archive_docs/2026-10-07/docs/api/API_ACTION_CONTRACT.md, archive_docs/2026-10-07/docs/architecture/realtime-strategy.md, archive_docs/2026-10-07/docs/auth/social-auth.md, archive_docs/2026-10-07/docs/automation/automation-runtime.md, archive_docs/2026-10-07/docs/billing/BILLING_DISCUSSION_DEFERRED_2026-09-25.md, archive_docs/2026-10-07/docs/billing/entitlements.md, archive_docs/2026-10-07/docs/crm/CRM_AUDIT_REQUIRED_CHANGES.md, archive_docs/2026-10-07/docs/crm/CRM_ENTITY_BEHAVIOR_CONTRACT.md, archive_docs/2026-10-07/docs/crm/CRM_IMPLEMENTATION_TASKS.md, archive_docs/2026-10-07/docs/crm/CRM_PRODUCTION_LAYER_PLAN.md, archive_docs/2026-10-07/docs/crm/client-payments.md, archive_docs/2026-10-07/docs/crm/specialist-scheduling.md, archive_docs/2026-10-07/docs/data-exports.md, archive_docs/2026-10-07/docs/frontend/archive/APP_UI_UX_REDESIGN_TASK.md, archive_docs/2026-10-07/docs/frontend/design-system.md, archive_docs/2026-10-07/docs/frontend/product-ui-reform.md, archive_docs/2026-10-07/docs/frontend/ui-ux-implementation-standard.md, archive_docs/2026-10-07/docs/frontend/ui-ux-polish-phase-10.md, archive_docs/2026-10-07/docs/integrations/CONNECTOR_BLUEPRINT.md, archive_docs/2026-10-07/docs/integrations/README.md, archive_docs/2026-10-07/docs/integrations/communication-onboarding.md, archive_docs/2026-10-07/docs/integrations/connector-credential-key-rotation.md, archive_docs/2026-10-07/docs/integrations/financial-source-contract.md, archive_docs/2026-10-07/docs/integrations/imports/data-imports.md, archive_docs/2026-10-07/docs/integrations/imports/excel-csv-real-import-mvp.md, archive_docs/2026-10-07/docs/integrations/integrations.md, archive_docs/2026-10-07/docs/integrations/lightweight-integrations-roadmap.md, archive_docs/2026-10-07/docs/integrations/live-connector-test-runbook.md, archive_docs/2026-10-07/docs/integrations/marketplace-integrations.md, archive_docs/2026-10-07/docs/integrations/marketplace-inventory-write-plan.md, archive_docs/2026-10-07/docs/integrations/marketplace-onboarding-runbook.md, archive_docs/2026-10-07/docs/integrations/marketplaces/kaspi-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/marketplaces/kaspi-pricing-agent.md, archive_docs/2026-10-07/docs/integrations/marketplaces/moysklad-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/marketplaces/ozon-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/marketplaces/wildberries-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/provider-rollout.md, archive_docs/2026-10-07/docs/integrations/providers/instagram-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/providers/telegram-connector-mvp.md, archive_docs/2026-10-07/docs/integrations/providers/telegram-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/providers/transactional-email.md, archive_docs/2026-10-07/docs/integrations/providers/whatsapp-merchant-connector.md, archive_docs/2026-10-07/docs/integrations/providers/widget-sdk.md, archive_docs/2026-10-07/docs/integrations/public-lead-capture.md, archive_docs/2026-10-07/docs/operations/internal-dev-tools-boundary.md, archive_docs/2026-10-07/docs/operations/platform-operations-health.md, archive_docs/2026-10-07/docs/operations/rebranding-2026-09-28.md, archive_docs/2026-10-07/docs/operations/technical-documentation-audit.md, archive_docs/2026-10-07/docs/pilot/backend-development-audit.md, archive_docs/2026-10-07/docs/pilot/backend-open-logic-register.md, archive_docs/2026-10-07/docs/pilot/block10-clean-pilot-package.md, archive_docs/2026-10-07/docs/pilot/block11-pilot-smoke-cleanup.md, archive_docs/2026-10-07/docs/pilot/block12-platform-operations-panel.md, archive_docs/2026-10-07/docs/pilot/block13-support-operator-workflow.md, archive_docs/2026-10-07/docs/pilot/block14-pilot-demo-launch.md, archive_docs/2026-10-07/docs/pilot/block5-unified-inbox.md, archive_docs/2026-10-07/docs/pilot/block7-mobile-owner-ux.md, archive_docs/2026-10-07/docs/pilot/block8-pilot-smoke-demo.md, archive_docs/2026-10-07/docs/pilot/block9-data-import-pilot.md, archive_docs/2026-10-07/docs/pilot/local-crm-completion.md, archive_docs/2026-10-07/docs/pilot/owner-questions-2026-09-28.md, archive_docs/2026-10-07/docs/pilot/pilot-production-qa-checklist.md, archive_docs/2026-10-07/docs/pilot/pilot-safe-promises.md, archive_docs/2026-10-07/docs/pilot/task3_task_calendar_flow_polish.md, archive_docs/2026-10-07/docs/pilot/task5_pilot_qa_polish_report.md, archive_docs/2026-10-07/docs/pilot/task6_pilot_readiness_checklist_report.md, archive_docs/2026-10-07/docs/pilot/task7_website_chat_connector_foundation_report.md, archive_docs/2026-10-07/docs/pilot/task8_inbox_polish_report.md, archive_docs/2026-10-07/docs/pilot/task9_integrations_status_polish_report.md, archive_docs/2026-10-07/docs/pre-production/README.md, archive_docs/2026-10-07/docs/pre-production/crm-ai-agent.md, archive_docs/2026-10-07/docs/pre-production/customer-ai-agent.md, archive_docs/2026-10-07/docs/pre-production/module-template.md, archive_docs/2026-10-07/docs/pre-production/project-state.md, archive_docs/2026-10-07/docs/product-capabilities.md, archive_docs/2026-10-07/docs/product/V1_PRODUCT_RULES.md, archive_docs/2026-10-07/docs/product/competitive-regression-report.md, archive_docs/2026-10-07/docs/product/landing-activation.md, archive_docs/2026-10-07/docs/production/backup-restore.md, archive_docs/2026-10-07/docs/production/celery-render-runtime.md, archive_docs/2026-10-07/docs/production/deployment.md, archive_docs/2026-10-07/docs/production/file-storage.md, archive_docs/2026-10-07/docs/production/monitoring-runbook.md, archive_docs/2026-10-07/docs/production/observability.md, archive_docs/2026-10-07/docs/production/paid-beta-gate.md, archive_docs/2026-10-07/docs/production/paid-beta-launch-runbook.md, archive_docs/2026-10-07/docs/production/production-readiness-10000-audit.md, archive_docs/2026-10-07/docs/production/production-readiness.md, archive_docs/2026-10-07/docs/production/staging/staging-ci-cd-checklist.md, archive_docs/2026-10-07/docs/production/staging/staging-provider-selection.md, archive_docs/2026-10-07/docs/production/staging/staging-render-execution-report.md, archive_docs/2026-10-07/docs/production/staging/staging-smoke-runbook.md, archive_docs/2026-10-07/docs/security/PERMISSION_MATRIX.md, archive_docs/2026-10-07/docs/security/aud027-crm-projections.md, archive_docs/2026-10-07/docs/security/file-antivirus.md, archive_docs/2026-10-07/docs/security/privileged-mfa.md, archive_docs/2026-10-07/docs/security/rate-limits.md, archive_docs/2026-10-07/docs/testing/CODEX_TASK_TEMPLATE.md, archive_docs/2026-10-07/docs/testing/SESSION_ROLLOVER.md, archive_docs/2026-10-07/docs/testing/ai-agent-continuity-20261006.md, archive_docs/2026-10-07/docs/testing/ai-agent-followup-20261005.md, archive_docs/2026-10-07/docs/testing/ai-agent-isolation-20261005.md, archive_docs/2026-10-07/docs/testing/ai-agent-reference-redesign-20261002.md, archive_docs/2026-10-07/docs/testing/ai-agent-scenarios-20261005.md, archive_docs/2026-10-07/docs/testing/ai-agents-behavior-20261006.md, archive_docs/2026-10-07/docs/testing/ai-agents-certification-20261006.md, archive_docs/2026-10-07/docs/testing/ai-agents-ux-20261005.md, archive_docs/2026-10-07/docs/testing/ai-crud-history-20261002.md, archive_docs/2026-10-07/docs/testing/ai-functional-20261002.md, archive_docs/2026-10-07/docs/testing/color-system-audit-20261002.md, archive_docs/2026-10-07/docs/testing/dependency-publication-20261006.md, archive_docs/2026-10-07/docs/testing/e2e-scale-baseline.md, archive_docs/2026-10-07/docs/testing/inbox-agent-safety-20261007.md, archive_docs/2026-10-07/docs/testing/regression-report.md, archive_docs/2026-10-07/docs/testing/task-state/CONSOLIDATION-2026-09-21.md, archive_docs/2026-10-07/docs/testing/task-state/PRIMARY-SESSION.md, archive_docs/2026-10-07/docs/testing/testing.md, archive_docs/2026-10-07/docs/testing/ui-feedback-20261005.md, archive_docs/2026-10-07/docs/testing/ui-feedback-inventory-20261005.md, archive_docs/2026-10-07/docs/testing/ui-loading-20261005.md, archive_docs/2026-10-07/docs/testing/ui-state-behavior-20261005.md, archive_docs/2026-10-07/docs/testing/ui-testing-toolkit.md, archive_docs/2026-10-07/frontend/README.md, archive_docs/2026-10-07/frontend/src/features/README.md, archive_docs/2026-10-07/frontend/src/features/deals/CHANGELOG.md, archive_docs/2026-10-07/frontend/src/features/deals/README.md, archive_docs/2026-10-07/manifest.json, archive_docs/2026-10-07/master_teh_plan.txt, archive_docs/2026-10-07/plan/README.md, archive_docs/2026-10-07/plan/clean_code_rules/zani_required_clean_code_rules.md, archive_docs/2026-10-07/plan/commit_pr_split_plan_2026_06_08.md, archive_docs/2026-10-07/plan/deals_reference_blueprint.md, archive_docs/2026-10-07/plan/production_qa_2026_06_09.md, archive_docs/2026-10-07/plan/readiness_plan.md, archive_docs/2026-10-07/plan/stabilization_audit_2026_06_08.md, archive_docs/2026-10-07/plan/ui_ux_design_system_reform.md, archive_docs/AGENTS.md, archive_docs/APP_2_PHASE_10_INTERACTION_WORKFLOW_QA_PLAN.md, archive_docs/APP_2_PHASE_9_UI_UX_POLISH_PLAN.md, archive_docs/APP_2_WORKBENCH_EXECUTION_ROADMAP.md, archive_docs/APP_UI_UX_REDESIGN_TASK.md, archive_docs/BROWSER_UI_UX_REMEDIATION_2026-07-31.md, archive_docs/CRM_CORE_WORKFLOW_AUDIT.md, archive_docs/CRM_IMPLEMENTATION_SPLIT/BACKEND_IMPLEMENTATION_PLAN.md, archive_docs/CRM_IMPLEMENTATION_SPLIT/BACKEND_RELIABILITY_EXECUTION_PLAN.md, archive_docs/CRM_PHASE_2A_HARDENING_EVIDENCE.md, archive_docs/CRM_TECHNICAL_MAP_AND_VERTICAL_MODES.md, archive_docs/POST_CERTIFICATION_EXECUTION_2026-08-02.md, archive_docs/PROJECT_EXECUTION_MASTER.md, archive_docs/README.md, archive_docs/X401_LOCAL_PILOT_READINESS_REPORT.md, config/__init__.py, config/asgi.py, config/celery.py, config/settings.py, config/urls.py, config/wsgi.py, deploy/clamav/clamd.conf, deploy/render.h1.example.yaml, docker-compose.yml, docs/README.md, docs/current/acceptance.md, docs/current/access.md, docs/current/ai.md, docs/current/crm.md, docs/current/engineering.md, docs/current/frontend.md, docs/current/integrations.md, docs/current/operations.md, docs/current/product.md, docs/current/roadmap.md, docs/documentation-index.json, docs/integrations/imports/samples/catalog_template.csv, docs/integrations/imports/samples/clients_template.csv, docs/integrations/imports/samples/deals_template.csv, docs/integrations/imports/samples/leads_template.csv, docs/integrations/imports/samples/sales_template.csv, docs/pre-production/README.md, docs/pre-production/capabilities.md, docs/pre-production/clients.md, docs/pre-production/crm-ai-agent.md, docs/pre-production/customer-ai-agent.md, docs/pre-production/data-lifecycle.md, docs/pre-production/files-antivirus.md, docs/pre-production/identity-access.md, docs/pre-production/inbox.md, docs/pre-production/integrations.md, docs/pre-production/leads-deals.md, docs/pre-production/module-template.md, docs/pre-production/money-analytics.md, docs/pre-production/operations.md, docs/pre-production/project-state.md, docs/pre-production/scheduling.md, docs/pre-production/settings-notifications.md, docs/pre-production/subscription-usage.md, docs/pre-production/tasks-automations.md, docs/testing/CODEX_TASK_TEMPLATE.md, docs/testing/SESSION_ROLLOVER.md, docs/testing/admin05-payments-partner-brief-20261016.txt, docs/testing/business-logic-questions-20261016.md, docs/testing/docs-reconciliation-20261016.md, docs/testing/inbox-live-acceptance-20261008.md, docs/testing/inbox-local-pilot-20261008.md, docs/testing/integrations-functional-review-20261008.md, docs/testing/platform-rebuild-spec-20261014.md, docs/testing/project-audit-20261017.md, docs/testing/settings-functional-20261008.md, docs/testing/settings-redesign-20261009.md, docs/testing/settings-workflow-20261009.md, docs/testing/task-state/PRIMARY-SESSION.md, docs/testing/testing.md, docs/testing/ui-operations-20261008.md, docs/testing/ui-testing-toolkit.md, frontend/.env.chromatic.example, frontend/.env.example, frontend/.env.production.example, frontend/.env.staging.example, frontend/.storybook/main.ts, frontend/.storybook/modes.ts, frontend/.storybook/preview.tsx, frontend/.storybook/serve.config.ts, frontend/.storybook/vite.config.ts, frontend/README.md, frontend/chromatic.config.json, frontend/e2e-ui-toolkit/catalog.spec.ts, frontend/e2e/accessibility-responsive.spec.ts, frontend/e2e/account-avatar.spec.ts, frontend/e2e/account-interface.spec.ts, frontend/e2e/account-mfa-qr-recovery.spec.ts, frontend/e2e/account-mfa-qr.spec.ts, frontend/e2e/account-section-nav.spec.ts, frontend/e2e/account-session-continuations.spec.ts, frontend/e2e/account-sessions.spec.ts, frontend/e2e/account-user-settings.spec.ts, frontend/e2e/action-color-roles.spec.ts, frontend/e2e/action-feedback.spec.ts, frontend/e2e/agent-header-picker.spec.ts, frontend/e2e/agent-reference-layout.spec.ts, frontend/e2e/agent-setup.spec.ts, frontend/e2e/ai-agent-analytics-certification.spec.ts, frontend/e2e/ai-agent-continuity.spec.ts, frontend/e2e/ai-agent-followup.spec.ts, frontend/e2e/ai-agent-isolation.spec.ts, frontend/e2e/ai-agent-scenarios.spec.ts, frontend/e2e/ai-agent-settings-certification.spec.ts, frontend/e2e/ai-agents-ux.spec.ts, frontend/e2e/ai-crm-history.spec.ts, frontend/e2e/ai-functional-settings.spec.ts, frontend/e2e/ai-inbox-memory.spec.ts, frontend/e2e/ai-job-recovery.spec.ts, frontend/e2e/billing-commerce.spec.ts, frontend/e2e/calendar-workspace.spec.ts, frontend/e2e/certification/action-outcome-contracts.mjs, frontend/e2e/certification/failure-certification-registry.mjs, frontend/e2e/certification/merchant-journey-registry.mjs, frontend/e2e/certification/route-action-registry.mjs, frontend/e2e/color-system-audit.spec.ts, frontend/e2e/color-system-details.spec.ts, frontend/e2e/connection-probe.spec.ts, frontend/e2e/connection-recovery.spec.ts, frontend/e2e/crm-toolbar-refinement.spec.ts, frontend/e2e/crm-unified-filters.spec.ts, frontend/e2e/crm-workspace-overlay.spec.ts, frontend/e2e/crm-workspaces-data.spec.ts, frontend/e2e/crm-workspaces-deals.spec.ts, frontend/e2e/crm-workspaces-reference.spec.ts, frontend/e2e/daily-workspaces.spec.ts, frontend/e2e/dashboard-data-loading.spec.ts, frontend/e2e/deals-empty-workspace.spec.ts, frontend/e2e/deals-kanban-density.spec.ts, frontend/e2e/deals-workspace-density.spec.ts, frontend/e2e/django-e2e.mjs, frontend/e2e/emerald-palette.spec.ts, frontend/e2e/entity-workspaces.spec.ts, frontend/e2e/failure-certification.spec.ts, frontend/e2e/fallback/fallback-registry.mjs, frontend/e2e/fixtures/action-color-roles.html, frontend/e2e/fixtures/action-color-roles.tsx, frontend/e2e/fixtures/error-boundaries.html, frontend/e2e/fixtures/error-boundaries.tsx, frontend/e2e/fixtures/failure-certification.html, frontend/e2e/fixtures/failure-certification.tsx, frontend/e2e/fixtures/fallback-surfaces.html, frontend/e2e/fixtures/fallback-surfaces.tsx, frontend/e2e/fixtures/feedback-catalog.html, frontend/e2e/fixtures/feedback-catalog.tsx, frontend/e2e/fixtures/state-behavior.html, frontend/e2e/fixtures/state-behavior.tsx, frontend/e2e/fixtures/widget-colors.html, frontend/e2e/functional-certification.spec.ts, frontend/e2e/handoff-recovery.spec.ts, frontend/e2e/header-search-width.spec.ts, frontend/e2e/inbox-agent-safety.spec.ts, frontend/e2e/inbox-client-relink.spec.ts, frontend/e2e/inbox-compact.spec.ts, frontend/e2e/inbox-inspector.spec.ts, frontend/e2e/inbox-local-pilot.spec.ts, frontend/e2e/inspector-interaction.spec.ts, frontend/e2e/kazakh-typography.spec.ts, frontend/e2e/leads-offline-isolation.spec.ts, frontend/e2e/legal-documents.spec.ts, frontend/e2e/merchant-journeys-certification.spec.ts, frontend/e2e/multibranch.spec.ts, frontend/e2e/neutral-terminology.spec.ts, frontend/e2e/pilot-actions.spec.ts, frontend/e2e/pilot-auth-security.spec.ts, frontend/e2e/pilot-auth.spec.ts, frontend/e2e/pilot-invitations.spec.ts, frontend/e2e/pilot-password-reset.spec.ts, frontend/e2e/pilot-record-content.spec.ts, frontend/e2e/pilot-staff-sales-cycle.spec.ts, frontend/e2e/platform-clinic-crm.spec.ts, frontend/e2e/platform-details.spec.ts, frontend/e2e/platform-employee-access.spec.ts, frontend/e2e/platform-operations.spec.ts, frontend/e2e/platform-overview.spec.ts, frontend/e2e/platform-ownership.spec.ts, frontend/e2e/platform-recovery.spec.ts, frontend/e2e/platform-s02.spec.ts, frontend/e2e/platform-shell.spec.ts, frontend/e2e/platform-support-incidents.spec.ts, frontend/e2e/platform-support.spec.ts, frontend/e2e/r01-daily-cycle.spec.ts, frontend/e2e/r01-inbox-task.spec.ts, frontend/e2e/runtime-maintainability.spec.ts, frontend/e2e/serve-isolated.py, frontend/e2e/service-error-feedback.spec.ts, frontend/e2e/service-s03.spec.ts, frontend/e2e/services-lifecycle.spec.ts, frontend/e2e/session-cache-isolation.spec.ts, frontend/e2e/session-persistence.spec.ts, frontend/e2e/settings-assignment.spec.ts, frontend/e2e/settings-functional.spec.ts, frontend/e2e/settings-redesign.spec.ts, frontend/e2e/settings-workflow.spec.ts, frontend/e2e/smoke.spec.ts, frontend/e2e/state-behavior.spec.ts, frontend/e2e/support/account-preferences.ts, frontend/e2e/support/crm-workspace.ts, frontend/e2e/tasks-redesign.spec.ts, frontend/e2e/ui-operations.spec.ts, frontend/e2e/widget-colors.spec.ts, frontend/index.html, frontend/lighthouserc.cjs, frontend/package-lock.json, frontend/package.json, frontend/playwright.action-colors.config.ts, frontend/playwright.config.ts, frontend/playwright.staging.config.ts, frontend/playwright.storybook.config.ts, frontend/postcss.config.js, frontend/public/backgrounds/ai-bots/almaty-dark-bg.webp, frontend/public/backgrounds/ai-bots/brick-bg.webp, frontend/public/backgrounds/ai-bots/monkey-bots.webp, frontend/public/backgrounds/ai-bots/monkey-phone-smile.webp, frontend/public/backgrounds/ai-bots/monkey-phone.webp, frontend/public/backgrounds/ai-bots/monkey-smile-mouth.webp, frontend/public/backgrounds/ai-bots/owner-monkey-smile.webp, frontend/public/backgrounds/ai-bots/speech-bubble.webp, frontend/public/backgrounds/hero/bgheromain-3840x1800.jpeg, frontend/public/backgrounds/hero/bgheromain.jpeg, frontend/public/backgrounds/hero/herobg1.png, frontend/public/backgrounds/hero/herobg2.png, frontend/public/backgrounds/hero/image.png, frontend/public/backgrounds/hero/layers/background.png, frontend/public/backgrounds/hero/layers/gold-trails-crop.png, frontend/public/backgrounds/hero/layers/gold-trails.png, frontend/public/backgrounds/hero/layers/hero-title.png, frontend/public/backgrounds/hero/layers/lead-instagram.png, frontend/public/backgrounds/hero/layers/lead-kaspi.png, frontend/public/backgrounds/hero/layers/lead-site.png, frontend/public/backgrounds/hero/layers/lead-telegram.png, frontend/public/backgrounds/hero/layers/lead-whatsapp.png, frontend/public/backgrounds/hero/layers/monkey-crop.png, frontend/public/backgrounds/hero/layers/monkey.png, frontend/public/backgrounds/hero/layers/particles-crop.png, frontend/public/backgrounds/hero/layers/particles.png, frontend/public/backgrounds/hero/layers/robot-base-crop.png, frontend/public/backgrounds/hero/layers/robot-base.png, frontend/public/backgrounds/hero/layers/wall-crop.png, frontend/public/backgrounds/hero/layers/wall.png, frontend/public/backgrounds/hero/photo_2026-06-16-15.08.08-master-3840x1800.jpg, frontend/public/backgrounds/hero/photo_2026-06-16-15.08.08.jpeg, frontend/public/backgrounds/hero/v2/berkut.webp, frontend/public/backgrounds/hero/v2/burst-finish.webp, frontend/public/backgrounds/hero/v2/burst-start.webp, frontend/public/backgrounds/hero/v2/energy-ring.webp, frontend/public/backgrounds/hero/v2/hero-scene-formatted.webp, frontend/public/backgrounds/hero/v2/hero-scene-wide.webp, frontend/public/backgrounds/hero/v2/hero-scene.webp, frontend/public/backgrounds/hero/v2/lead-instagram.webp, frontend/public/backgrounds/hero/v2/lead-kaspi.webp, frontend/public/backgrounds/hero/v2/lead-site.webp, frontend/public/backgrounds/hero/v2/lead-telegram.webp, frontend/public/backgrounds/hero/v2/lead-whatsapp.webp, frontend/public/backgrounds/hero/v2/result-deal.webp, frontend/public/backgrounds/hero/v2/result-money.webp, frontend/public/brand/platforma-crm-logo-transparent.png, frontend/public/brand/platforma-crm-logo.png, frontend/public/integrations_logos/1c.png, frontend/public/integrations_logos/instagram.png, frontend/public/integrations_logos/kaspi.png, frontend/public/integrations_logos/telegram.png, frontend/public/integrations_logos/whatsapp.png, frontend/public/integrations_logos/wildberries.png, frontend/public/landing/screens/deals.png, frontend/public/landing/screens/leads.png, frontend/public/landing/screens/messages.png, frontend/scripts/audit-color-system.mjs, frontend/scripts/check-bundle.mjs, frontend/scripts/check-failure-certification.mjs, frontend/scripts/check-fallback-inventory.mjs, frontend/scripts/check-functional-certification.mjs, frontend/scripts/check-i18n.mjs, frontend/scripts/check-merchant-journey-certification.mjs, frontend/scripts/chromatic-runtime.mjs, frontend/scripts/industry-terms.mjs, frontend/scripts/interaction-audit.mjs, frontend/scripts/run-chromatic.mjs, frontend/scripts/run-storybook.mjs, frontend/scripts/tests/action-color-policy.test.mjs, frontend/scripts/tests/action-feedback-policy.test.mjs, frontend/scripts/tests/app-error-normalization.test.mjs, frontend/scripts/tests/auth-return-path.test.mjs, frontend/scripts/tests/automation-editor.test.mjs, frontend/scripts/tests/bundle-budget.test.mjs, frontend/scripts/tests/calendar-period.test.mjs, frontend/scripts/tests/chromatic-runtime.test.mjs, frontend/scripts/tests/daily-workspaces-policy.test.mjs, frontend/scripts/tests/dashboard-appointment-dedupe.test.mjs, frontend/scripts/tests/error-boundary-policy.test.mjs, frontend/scripts/tests/failure-certification-registry.test.mjs, frontend/scripts/tests/fallback-inventory.test.mjs, frontend/scripts/tests/fallback-surface-policy.test.mjs, frontend/scripts/tests/functional-certification-registry.test.mjs, frontend/scripts/tests/gate-environment-policy.test.mjs, frontend/scripts/tests/inbox-delivery-policy.test.mjs, frontend/scripts/tests/industry-terms.test.mjs, frontend/scripts/tests/lead-csv-safety.test.mjs, frontend/scripts/tests/lead-offline-storage.test.mjs, frontend/scripts/tests/login-page-policy.test.mjs, frontend/scripts/tests/merchant-journey-certification.test.mjs, frontend/scripts/tests/notification-dedupe.test.mjs, frontend/scripts/tests/sidebar-navigation-policy.test.mjs, frontend/scripts/tests/task-workspace.test.mjs, frontend/scripts/tests/timeline-presentation.test.mjs, frontend/scripts/tests/ui-toolkit-policy.test.mjs, frontend/scripts/ui-toolkit-policy.mjs, frontend/scripts/visual-audit.mjs, frontend/src/api/activities.ts, frontend/src/api/ai.ts, frontend/src/api/aiCRM.ts, frontend/src/api/aiConversations.ts, frontend/src/api/analytics.ts, frontend/src/api/analyticsExports.ts, frontend/src/api/appError.ts, frontend/src/api/appErrorRegistry.ts, frontend/src/api/appointments.ts, frontend/src/api/auth.ts, frontend/src/api/automations.ts, frontend/src/api/billing.ts, frontend/src/api/billingCommerce.ts, frontend/src/api/bots.ts, frontend/src/api/branches.ts, frontend/src/api/businesses.ts, frontend/src/api/client.ts, frontend/src/api/clients.ts, frontend/src/api/connectivity.ts, frontend/src/api/connectors.ts, frontend/src/api/crmCards.ts, frontend/src/api/crud.ts, frontend/src/api/customFields.ts, frontend/src/api/deals.ts, frontend/src/api/developers.ts, frontend/src/api/employeeAccess.ts, frontend/src/api/fileAttachments.ts, frontend/src/api/importExport.ts, frontend/src/api/inbox.ts, frontend/src/api/leadForms.ts, frontend/src/api/leads.ts, frontend/src/api/notifications.ts, frontend/src/api/outreach.ts, frontend/src/api/ownership.ts, frontend/src/api/payments.ts, frontend/src/api/pilot.ts, frontend/src/api/platform.ts, frontend/src/api/platformClinic.ts, frontend/src/api/pricing.ts, frontend/src/api/quickReplies.ts, frontend/src/api/recovery.ts, frontend/src/api/resources.ts, frontend/src/api/security.ts, frontend/src/api/serviceStatus.ts, frontend/src/api/services.ts, frontend/src/api/sessionIdentity.ts, frontend/src/api/support.ts, frontend/src/api/taskRelations.ts, frontend/src/api/tasks.ts, frontend/src/api/team.ts, frontend/src/api/token.ts, frontend/src/api/workQueues.ts, frontend/src/api/workingHours.ts, frontend/src/app/providers.tsx, frontend/src/app/router.tsx, frontend/src/assets/platforma-crm-logo.png, frontend/src/components/actions/ActionConfirmProvider.tsx, frontend/src/components/actions/DraftGuard.tsx, frontend/src/components/actions/UndoToastProvider.tsx, frontend/src/components/actions/actionFeedbackPolicy.ts, frontend/src/components/actions/useActionFeedback.ts, frontend/src/components/actions/useRecoveryDelay.ts, frontend/src/components/ai/AiInsightCard.tsx, frontend/src/components/ai/AiNavigatorWidget.tsx, frontend/src/components/ai/PageAiHints.tsx, frontend/src/components/auth/PermissionGate.tsx, frontend/src/components/calendar/SimpleCalendar.tsx, frontend/src/components/crm/AttachmentScanStatus.tsx, frontend/src/components/crm/CrmActionBar.tsx, frontend/src/components/crm/CrmControlBar.tsx, frontend/src/components/crm/CrmDataTable.tsx, frontend/src/components/crm/CrmEmptyState.tsx, frontend/src/components/crm/CrmEntityDrawer.tsx, frontend/src/components/crm/CrmFilterChips.tsx, frontend/src/components/crm/CrmFilterControls.tsx, frontend/src/components/crm/CrmFilterFields.tsx, frontend/src/components/crm/CrmInspector.tsx, frontend/src/components/crm/CrmPagination.tsx, frontend/src/components/crm/CrmQuickFilters.tsx, frontend/src/components/crm/CrmTableSurface.tsx, frontend/src/components/crm/CrmWorkspacePage.tsx, frontend/src/components/crm/CrmWorkspacePopover.tsx, frontend/src/components/crm/CrmWorkspaceToolbar.tsx, frontend/src/components/crm/EntityWorkspace.tsx, frontend/src/components/crm/OperationalWorkspace.tsx, frontend/src/components/crm/drawers/AttachmentFilePicker.tsx, frontend/src/components/crm/drawers/appointment.tsx, frontend/src/components/crm/drawers/client.tsx, frontend/src/components/crm/drawers/config.ts, frontend/src/components/crm/drawers/deal.tsx, frontend/src/components/crm/drawers/fallback.tsx, frontend/src/components/crm/drawers/lead.tsx, frontend/src/components/crm/drawers/panels.tsx, frontend/src/components/crm/drawers/shared.tsx, frontend/src/components/crm/drawers/shell.tsx, frontend/src/components/crm/drawers/timeline.tsx, frontend/src/components/crm/drawers/timelineHelpers.ts, frontend/src/components/crm/drawers/types.ts, frontend/src/components/crm/index.ts, frontend/src/components/crm/tableLayout.ts, frontend/src/components/crm/useCrmFilters.ts, frontend/src/components/forms/AppointmentForm.tsx, frontend/src/components/forms/AppointmentRescheduleForm.tsx, frontend/src/components/forms/BusinessSettingsForm.tsx, frontend/src/components/forms/ClientForm.tsx, frontend/src/components/forms/LeadForm.tsx, frontend/src/components/forms/ResourceForm.tsx, frontend/src/components/forms/ServiceForm.tsx, frontend/src/components/forms/WorkingHoursForm.tsx, frontend/src/components/layout/AppLayout.tsx, frontend/src/components/layout/CommandPalette.tsx, frontend/src/components/layout/GlobalSearch.tsx, frontend/src/components/layout/Header.tsx, frontend/src/components/layout/HeaderAccountLink.tsx, frontend/src/components/layout/LanguageSelector.tsx, frontend/src/components/layout/MobileNav.tsx, frontend/src/components/layout/PageHeaderContext.tsx, frontend/src/components/layout/PlatformLayout.tsx, frontend/src/components/layout/PlatformPageHeading.tsx, frontend/src/components/layout/Sidebar.tsx, frontend/src/components/layout/WorkQueueLayout.tsx, frontend/src/components/layout/WorkbenchLayout.tsx, frontend/src/components/notifications/NotificationProvider.tsx, frontend/src/components/notifications/NotificationSoundWatcher.tsx, frontend/src/components/notifications/ServiceStatusNotice.tsx, frontend/src/components/notifications/UnreadMessagesNotice.tsx, frontend/src/components/notifications/notificationPolicy.ts, frontend/src/components/tables/DataTable.tsx, frontend/src/components/ui/ActionMenu.tsx, frontend/src/components/ui/AppErrorBoundary.tsx, frontend/src/components/ui/Badge.tsx, frontend/src/components/ui/Button.tsx, frontend/src/components/ui/Card.tsx, frontend/src/components/ui/ConnectivityBanner.tsx, frontend/src/components/ui/ConnectivityStatus.tsx, frontend/src/components/ui/DateRangePicker.tsx, frontend/src/components/ui/FallbackSurfaces.tsx, frontend/src/components/ui/FieldErrorSummary.tsx, frontend/src/components/ui/FilterBar.tsx, frontend/src/components/ui/Input.tsx, frontend/src/components/ui/LoadingIndicator.tsx, frontend/src/components/ui/MetricCard.tsx, frontend/src/components/ui/Modal.tsx, frontend/src/components/ui/Overlay.tsx, frontend/src/components/ui/PageHeader.tsx, frontend/src/components/ui/Primitives.tsx, frontend/src/components/ui/RecoveryDetails.tsx, frontend/src/components/ui/RouteErrorBoundary.tsx, frontend/src/components/ui/SearchableSelect.tsx, frontend/src/components/ui/Select.tsx, frontend/src/components/ui/StateViews.tsx, frontend/src/components/ui/StatusBadge.tsx, frontend/src/components/ui/StatusNotice.tsx, frontend/src/components/ui/Switch.tsx, frontend/src/components/ui/Tabs.tsx, frontend/src/components/ui/Textarea.tsx, frontend/src/components/ui/actionTone.ts, frontend/src/config/featureFlags.ts, frontend/src/features/account/AccountAccessSummary.tsx, frontend/src/features/account/AccountPage.tsx, frontend/src/features/account/AccountSectionNav.tsx, frontend/src/features/account/ActiveSessions.tsx, frontend/src/features/account/AvatarCropper.tsx, frontend/src/features/account/AvatarEditor.tsx, frontend/src/features/account/EmailSecurityRow.tsx, frontend/src/features/account/EmployeeAccessConfirmations.tsx, frontend/src/features/account/EmployeeAccessSummary.tsx, frontend/src/features/account/InterfaceSettingsCard.tsx, frontend/src/features/account/MfaSecurityCard.tsx, frontend/src/features/account/NotificationPreferencesCard.tsx, frontend/src/features/account/NotificationSoundControl.tsx, frontend/src/features/account/OwnershipConfirmations.tsx, frontend/src/features/account/OwnershipTransferSummary.tsx, frontend/src/features/account/RecoveryConfirmations.tsx, frontend/src/features/account/RecoverySummary.tsx, frontend/src/features/account/SecuritySettingRow.tsx, frontend/src/features/account/UserAvatar.tsx, frontend/src/features/account/accountPage.css, frontend/src/features/analytics/AnalyticsPage.tsx, frontend/src/features/analytics/FinancialSummary.tsx, frontend/src/features/analytics/WorkspaceSections.tsx, frontend/src/features/assistant/AIAgentsPage.tsx, frontend/src/features/assistant/CRMStaffAgentsPage.tsx, frontend/src/features/assistant/aiAgentsTypes.ts, frontend/src/features/assistant/aiAgentsUtils.ts, frontend/src/features/assistant/components/AIAgentActionsSection.tsx, frontend/src/features/assistant/components/AIAgentConfigSection.tsx, frontend/src/features/assistant/components/AIAgentEditorShell.tsx, frontend/src/features/assistant/components/AIAgentKnowledgeSection.tsx, frontend/src/features/assistant/components/AIAgentModals.tsx, frontend/src/features/assistant/components/AIAgentPreview.tsx, frontend/src/features/assistant/components/AIAgentProviderSetupSection.tsx, frontend/src/features/assistant/components/AIAgentRuntimeSection.tsx, frontend/src/features/assistant/components/AIAgentsSections.tsx, frontend/src/features/assistant/components/AIAgentsShared.tsx, frontend/src/features/assistant/components/AIAgentsWorkspace.tsx, frontend/src/features/assistant/components/AIHistoryPanel.tsx, frontend/src/features/assistant/components/AgentBranchScope.tsx, frontend/src/features/assistant/components/AgentConversationPanel.tsx, frontend/src/features/assistant/components/AgentDeleteControl.tsx, frontend/src/features/assistant/components/AgentNavigation.tsx, frontend/src/features/assistant/components/AgentScenarioCard.tsx, frontend/src/features/assistant/components/AgentTurnCard.tsx, frontend/src/features/assistant/components/CRMAgentRuntime.tsx, frontend/src/features/assistant/components/CRMAgentSettings.tsx, frontend/src/features/assistant/components/CRMCommandPanel.tsx, frontend/src/features/assistant/components/CustomerSafetySettings.tsx, frontend/src/features/assistant/components/SharedKnowledgePicker.tsx, frontend/src/features/assistant/useAIAgentEditorDrafts.ts, frontend/src/features/assistant/useCanonicalAIAgentRoute.ts, frontend/src/features/assistant/useMetaOAuthCallbackBridge.ts, frontend/src/features/auth/AccountRecoveryPage.tsx, frontend/src/features/auth/AuthExperienceShell.tsx, frontend/src/features/auth/AuthenticatorEnrollment.tsx, frontend/src/features/auth/ForgotPasswordPage.tsx, frontend/src/features/auth/InviteAcceptPage.tsx, frontend/src/features/auth/LoginPage.tsx, frontend/src/features/auth/MfaPage.tsx, frontend/src/features/auth/PasswordVisibilityToggle.tsx, frontend/src/features/auth/ResetPasswordPage.tsx, frontend/src/features/auth/SignupPage.tsx, frontend/src/features/auth/authExperience.css, frontend/src/features/auth/authExperienceMobileFix.css, frontend/src/features/auth/authLoginSerenity.css, frontend/src/features/auth/authReturnPath.ts, frontend/src/features/auth/useBrowserSessionActivity.ts, frontend/src/features/automations/AutomationActionFields.tsx, frontend/src/features/automations/AutomationsPage.tsx, frontend/src/features/automations/editorDraft.ts, frontend/src/features/billing/BillingOrderCard.tsx, frontend/src/features/billing/MerchantBilling.tsx, frontend/src/features/bots/BotDetailPage.tsx, frontend/src/features/bots/BotsPage.tsx, frontend/src/features/business/BranchesPage.tsx, frontend/src/features/business/components/BranchCatalogEditor.tsx, frontend/src/features/business/components/BranchEditor.tsx, frontend/src/features/business/components/BranchScheduleEditor.tsx, frontend/src/features/business/components/BusinessWorkspaceNav.tsx, frontend/src/features/calendar/AppointmentWorkspacePage.tsx, frontend/src/features/calendar/CalendarPage.tsx, frontend/src/features/calendar/appointmentAccess.ts, frontend/src/features/calendar/branchHours.ts, frontend/src/features/calendar/calendarConstants.ts, frontend/src/features/calendar/calendarTypes.ts, frontend/src/features/calendar/calendarUtils.ts, frontend/src/features/calendar/components/AppointmentDrawerPanel.tsx, frontend/src/features/calendar/components/CalendarAppointmentCards.tsx, frontend/src/features/calendar/components/CalendarBoard.tsx, frontend/src/features/calendar/components/CalendarDayInspector.tsx, frontend/src/features/calendar/components/CalendarFilters.tsx, frontend/src/features/calendar/components/CalendarPicker.tsx, frontend/src/features/calendar/components/CalendarToolbar.tsx, frontend/src/features/calendar/components/SearchableCalendarFilter.tsx, frontend/src/features/calendar/useCalendarCatalog.ts, frontend/src/features/clients/ClientWorkspacePage.tsx, frontend/src/features/clients/ClientsPage.tsx, frontend/src/features/clients/components/ClientInspector.tsx, frontend/src/features/clients/components/ClientPrimitives.tsx, frontend/src/features/clients/components/ClientQuickInspector.tsx, frontend/src/features/clients/components/ClientRow.tsx, frontend/src/features/clients/components/ClientWorkspaceSections.tsx, frontend/src/features/clients/components/ClientsFilters.tsx, frontend/src/features/clients/components/ClientsModals.tsx, frontend/src/features/clients/components/ClientsTable.tsx, frontend/src/features/clients/components/MobileClientCards.tsx, frontend/src/features/clients/hooks/useClientRows.ts, frontend/src/features/clients/hooks/useClientWorkspaceActions.ts, frontend/src/features/clients/hooks/useClientsPageHeader.ts, frontend/src/features/clients/hooks/useClientsWorkspace.ts, frontend/src/features/clients/types.ts, frontend/src/features/clients/utils.ts, frontend/src/features/conversations/ConversationsPage.tsx, frontend/src/features/conversations/components/ClientLinkConfirmation.tsx, frontend/src/features/conversations/components/ConversationComposer.tsx, frontend/src/features/conversations/components/ConversationItem.tsx, frontend/src/features/conversations/components/ConversationListPane.tsx, frontend/src/features/conversations/components/ConversationPrimitives.tsx, frontend/src/features/conversations/components/ConversationQueueFilters.tsx, frontend/src/features/conversations/components/ConversationThreadHeader.tsx, frontend/src/features/conversations/components/ConversationThreadPane.tsx, frontend/src/features/conversations/components/InboxCustomerContext.tsx, frontend/src/features/conversations/components/InboxMemoryControl.tsx, frontend/src/features/conversations/components/MessageBubble.tsx, frontend/src/features/conversations/components/MessageDeliveryDetails.tsx, frontend/src/features/conversations/components/PipelineConfirmationDialog.tsx, frontend/src/features/conversations/conversationConstants.ts, frontend/src/features/conversations/conversationTypes.ts, frontend/src/features/conversations/conversationUtils.ts, frontend/src/features/conversations/hooks/useConversationFilters.ts, frontend/src/features/conversations/hooks/useInboxDraft.ts, frontend/src/features/dashboard/DashboardPage.tsx, frontend/src/features/dashboard/OperationalDashboard.tsx, frontend/src/features/dashboard/OwnerDashboard.tsx, frontend/src/features/dashboard/dashboardUtils.ts, frontend/src/features/deals/DealWorkspacePage.tsx, frontend/src/features/deals/DealsPage.tsx, frontend/src/features/deals/components/DealDetailPanel.tsx, frontend/src/features/deals/components/DealListItem.tsx, frontend/src/features/deals/components/DealModals.tsx, frontend/src/features/deals/components/DealQuickInspector.tsx, frontend/src/features/deals/components/DealWorkspaceSections.tsx, frontend/src/features/deals/components/DealsFilters.tsx, frontend/src/features/deals/components/DealsList.tsx, frontend/src/features/deals/components/common/DealAmount.tsx, frontend/src/features/deals/components/common/DealRiskIndicator.tsx, frontend/src/features/deals/components/common/DealStageBadge.tsx, frontend/src/features/deals/components/common/DealTimeline.tsx, frontend/src/features/deals/hooks/useDealActions.ts, frontend/src/features/deals/hooks/useDealBoard.ts, frontend/src/features/deals/hooks/useDealFilters.ts, frontend/src/features/deals/hooks/useDealMetrics.ts, frontend/src/features/deals/hooks/useDealSelection.ts, frontend/src/features/deals/hooks/useDeals.ts, frontend/src/features/deals/types/index.ts, frontend/src/features/deals/utils/dealHelpers.ts, frontend/src/features/documents/DocumentLinks.tsx, frontend/src/features/documents/DocumentsPage.tsx, frontend/src/features/documents/documents.ts, frontend/src/features/integrations/IntegrationsPage.tsx, frontend/src/features/integrations/components/ConnectorCard.tsx, frontend/src/features/integrations/components/FinancialSourceSettings.tsx, frontend/src/features/integrations/components/ImportPanel.tsx, frontend/src/features/integrations/components/ProviderCard.tsx, frontend/src/features/integrations/components/setup/InstagramSetup.tsx, frontend/src/features/integrations/components/setup/IntegrationSetupUi.tsx, frontend/src/features/integrations/components/setup/KaspiPricingSetup.tsx, frontend/src/features/integrations/components/setup/KaspiSetup.tsx, frontend/src/features/integrations/components/setup/MoySkladSetup.tsx, frontend/src/features/integrations/components/setup/OzonSetup.tsx, frontend/src/features/integrations/components/setup/TelegramSetup.tsx, frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx, frontend/src/features/integrations/components/setup/WildberriesSetup.tsx, frontend/src/features/integrations/components/setup/metaCallbacks.ts, frontend/src/features/integrations/config/providerCatalog.ts, frontend/src/features/integrations/utils.ts, frontend/src/features/leads/LeadWorkspacePage.tsx, frontend/src/features/leads/LeadsPage.tsx, frontend/src/features/leads/components/LeadAppointmentModal.tsx, frontend/src/features/leads/components/LeadContextMenu.tsx, frontend/src/features/leads/components/LeadCreateModal.tsx, frontend/src/features/leads/components/LeadDetailPanel.tsx, frontend/src/features/leads/components/LeadDetailSections.tsx, frontend/src/features/leads/components/LeadLostModal.tsx, frontend/src/features/leads/components/LeadNextActionModal.tsx, frontend/src/features/leads/components/LeadQueueItem.tsx, frontend/src/features/leads/components/LeadQuickInspector.tsx, frontend/src/features/leads/components/LeadShortcutsModal.tsx, frontend/src/features/leads/components/LeadWorkspaceSections.tsx, frontend/src/features/leads/components/LeadsActionOverlays.tsx, frontend/src/features/leads/components/LeadsBulkBar.tsx, frontend/src/features/leads/components/LeadsModals.tsx, frontend/src/features/leads/components/LeadsPagination.tsx, frontend/src/features/leads/components/LeadsTable.tsx, frontend/src/features/leads/components/LeadsToolbar.tsx, frontend/src/features/leads/components/LeadsWorkspaceTable.tsx, frontend/src/features/leads/components/common/ActionDropdown.tsx, frontend/src/features/leads/components/common/MetricCard.tsx, frontend/src/features/leads/components/common/MetricTile.tsx, frontend/src/features/leads/components/common/SourceBadge.tsx, frontend/src/features/leads/components/common/SourceFilter.tsx, frontend/src/features/leads/components/common/ViewToggle.tsx, frontend/src/features/leads/hooks/useLeadAI.ts, frontend/src/features/leads/hooks/useLeadActionHistory.ts, frontend/src/features/leads/hooks/useLeadActions.ts, frontend/src/features/leads/hooks/useLeadBulkActions.ts, frontend/src/features/leads/hooks/useLeadFilters.ts, frontend/src/features/leads/hooks/useLeadInteractions.ts, frontend/src/features/leads/hooks/useLeadKeyboardShortcuts.ts, frontend/src/features/leads/hooks/useLeadOfflineQueue.ts, frontend/src/features/leads/hooks/useLeadRealtime.ts, frontend/src/features/leads/hooks/useLeadSelection.ts, frontend/src/features/leads/hooks/useLeadSelectionContext.ts, frontend/src/features/leads/hooks/useLeadView.ts, frontend/src/features/leads/hooks/useLeads.ts, frontend/src/features/leads/hooks/useLeadsPageHeader.ts, frontend/src/features/leads/hooks/useLeadsTableState.ts, frontend/src/features/leads/hooks/useLeadsWorkspaceData.ts, frontend/src/features/leads/hooks/useLeadsWorkspaceDisplay.ts, frontend/src/features/leads/index.ts, frontend/src/features/leads/types/index.ts, frontend/src/features/leads/utils/leadExport.ts, frontend/src/features/leads/utils/leadFilters.ts, frontend/src/features/leads/utils/leadFormat.tsx, frontend/src/features/leads/utils/leadMetrics.ts, frontend/src/features/leads/utils/leadStorage.ts, frontend/src/features/outreach/OutreachPage.tsx, frontend/src/features/payments/PaymentEntityPicker.tsx, frontend/src/features/payments/PaymentForm.tsx, frontend/src/features/payments/PaymentsButton.tsx, frontend/src/features/payments/PaymentsJournal.tsx, frontend/src/features/payments/usePaymentDraftGuard.ts, frontend/src/features/pilot/NotFoundPage.tsx, frontend/src/features/platform/BusinessBillingPanel.tsx, frontend/src/features/platform/BusinessDetailsForm.tsx, frontend/src/features/platform/BusinessEmployeeAccessPanel.tsx, frontend/src/features/platform/BusinessOwnershipPanel.tsx, frontend/src/features/platform/BusinessRecoveryPanel.tsx, frontend/src/features/platform/ClinicAccessHistory.tsx, frontend/src/features/platform/ClinicCrmBrowser.tsx, frontend/src/features/platform/ClinicReadUI.tsx, frontend/src/features/platform/EmployeeAccessDiagnostics.tsx, frontend/src/features/platform/OperationsInfrastructure.tsx, frontend/src/features/platform/OperationsWorklist.tsx, frontend/src/features/platform/OverviewAttention.tsx, frontend/src/features/platform/PlatformData.tsx, frontend/src/features/platform/PlatformMerchantDetailPage.tsx, frontend/src/features/platform/PlatformMerchantsPage.tsx, frontend/src/features/platform/PlatformOperationsPage.tsx, frontend/src/features/platform/PlatformOverviewPage.tsx, frontend/src/features/platform/PlatformPlaceholderPage.tsx, frontend/src/features/pricing/PricingPage.tsx, frontend/src/features/resources/ResourcesPage.tsx, frontend/src/features/resources/components/ResourceActionsMenu.tsx, frontend/src/features/resources/components/ResourceCreateForm.tsx, frontend/src/features/resources/components/ResourceEditModal.tsx, frontend/src/features/resources/components/ResourceStatusBadge.tsx, frontend/src/features/resources/components/ResourcesToolbar.tsx, frontend/src/features/resources/components/SpecialistLifecycle.tsx, frontend/src/features/services/ServicesPage.tsx, frontend/src/features/services/components/ServiceActionsMenu.tsx, frontend/src/features/services/components/ServiceEditModal.tsx, frontend/src/features/services/components/ServiceStatusBadge.tsx, frontend/src/features/settings/DevelopersSection.tsx, frontend/src/features/settings/SettingsPage.tsx, frontend/src/features/settings/WorkingHoursPage.tsx, frontend/src/features/settings/components/AbsenceAppointmentsModal.tsx, frontend/src/features/settings/components/CustomFieldAccessMatrix.tsx, frontend/src/features/settings/components/CustomFieldEditor.tsx, frontend/src/features/settings/components/CustomFieldRolePicker.tsx, frontend/src/features/settings/components/RoleAccessPreview.tsx, frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx, frontend/src/features/settings/components/SettingsLayout.tsx, frontend/src/features/settings/components/SettingsNavigation.tsx, frontend/src/features/settings/components/SettingsQueryState.tsx, frontend/src/features/settings/components/TeamAccessControl.tsx, frontend/src/features/settings/components/TeamBranchAccess.tsx, frontend/src/features/settings/components/WorkingHoursBusinessView.tsx, frontend/src/features/settings/components/WorkingHoursEditModal.tsx, frontend/src/features/settings/components/WorkingHoursResourcesView.tsx, frontend/src/features/settings/hooks/useSettingsSectionNavigation.ts, frontend/src/features/settings/roleAccess.ts, frontend/src/features/settings/sections/AppointmentMessagesSection.tsx, frontend/src/features/settings/sections/BillingSection.tsx, frontend/src/features/settings/sections/BusinessProfileSection.tsx, frontend/src/features/settings/sections/CustomFieldsSection.tsx, frontend/src/features/settings/sections/QuickRepliesSection.tsx, frontend/src/features/settings/sections/RolesSection.tsx, frontend/src/features/settings/sections/SecuritySection.tsx, frontend/src/features/settings/sections/TeamSection.tsx, frontend/src/features/settings/sections/UsageSection.tsx, frontend/src/features/settings/settingsConfig.ts, frontend/src/features/settings/settingsUtils.ts, frontend/src/features/settings/useSettingsModel.tsx, frontend/src/features/support/SupportActionDialog.tsx, frontend/src/features/support/SupportClinicPicker.tsx, frontend/src/features/support/SupportCreateDialog.tsx, frontend/src/features/support/SupportDetailPage.tsx, frontend/src/features/support/SupportIncidentPage.tsx, frontend/src/features/support/SupportIncidents.tsx, frontend/src/features/support/SupportListPage.tsx, frontend/src/features/support/SupportThread.tsx, frontend/src/features/support/SupportUI.tsx, frontend/src/features/tasks/TaskWorkspacePage.tsx, frontend/src/features/tasks/TasksPage.tsx, frontend/src/features/tasks/components/TaskDraftGuard.tsx, frontend/src/features/tasks/components/TaskDrawer.tsx, frontend/src/features/tasks/components/TaskEditor.tsx, frontend/src/features/tasks/components/TaskFormModal.tsx, frontend/src/features/tasks/components/TaskHeaderFilters.tsx, frontend/src/features/tasks/components/TaskInspector.tsx, frontend/src/features/tasks/components/TaskList.tsx, frontend/src/features/tasks/components/TaskQuickInspector.tsx, frontend/src/features/tasks/components/TaskRelationPicker.tsx, frontend/src/features/tasks/components/TaskStatus.tsx, frontend/src/features/tasks/components/TaskWorkloadPanel.tsx, frontend/src/features/tasks/hooks/useTaskActions.ts, frontend/src/features/tasks/hooks/useTaskFilters.ts, frontend/src/features/tasks/hooks/useTaskQueries.ts, frontend/src/features/tasks/taskFormUtils.ts, frontend/src/features/tasks/workspaceUtils.ts, frontend/src/features/timeline/TimelineActorFilter.tsx, frontend/src/features/timeline/TimelineDetails.tsx, frontend/src/features/timeline/TimelineEventTable.tsx, frontend/src/features/timeline/TimelinePage.tsx, frontend/src/features/timeline/TimelineToolbar.tsx, frontend/src/features/timeline/timelinePresentation.ts, frontend/src/features/timeline/useTimelineSearchParams.ts, frontend/src/hooks/useBodyScrollLock.ts, frontend/src/hooks/useBranchBooking.ts, frontend/src/hooks/useBusiness.ts, frontend/src/hooks/useClientCreateIntent.ts, frontend/src/hooks/useDebouncedValue.ts, frontend/src/hooks/useEntityData.ts, frontend/src/hooks/useMediaQuery.ts, frontend/src/lib/cn.ts, frontend/src/lib/customFields.ts, frontend/src/lib/format.ts, frontend/src/lib/i18n.tsx, frontend/src/lib/i18n/en.ts, frontend/src/lib/i18n/kk.ts, frontend/src/lib/i18n/ru.ts, frontend/src/lib/leadOfflineStorage.ts, frontend/src/lib/monitoring.ts, frontend/src/lib/notificationSound.ts, frontend/src/lib/permissions.ts, frontend/src/lib/prefetch.ts, frontend/src/lib/realtime.ts, frontend/src/lib/startPage.ts, frontend/src/main.tsx, frontend/src/styles.css, frontend/src/theme/semantic-tokens.json, frontend/src/types/analyticsWorkspace.ts, frontend/src/types/index.ts, frontend/src/types/platformOperations.ts, frontend/src/types/platformOverview.ts, frontend/src/types/support.ts, frontend/src/types/timeline.ts, frontend/src/ui-catalog/Buttons.stories.tsx, frontend/src/ui-catalog/CrmDrawer.stories.tsx, frontend/src/ui-catalog/Fields.stories.tsx, frontend/src/ui-catalog/Navigation.stories.tsx, frontend/src/ui-catalog/ServiceModal.stories.tsx, frontend/src/ui-catalog/ServiceModalExample.tsx, frontend/src/ui-catalog/ServiceTable.stories.tsx, frontend/src/ui-catalog/ServiceTableExample.tsx, frontend/src/ui-catalog/serviceFixtures.ts, frontend/src/vite-env.d.ts, frontend/tailwind.config.ts, frontend/tsconfig.app.json, frontend/tsconfig.json, frontend/tsconfig.node.json, frontend/tsconfig.storybook.json, frontend/vite.config.ts, frontend/widget/vite.config.ts, landing/assets/1212.png, landing/bgs/hero backgrond/herobg1.png, landing/bgs/hero backgrond/reference/7A6D241E-71F0-4C17-9B33-FE4EC38AF734.PNG, landing/refs/image.png, manage.py, pytest.ini, references/main_references/administrator_main_desktop+mobile.jpeg, references/main_references/analytics_mobile+desktop.jpeg, references/main_references/bussiness_settings_desktop+mobile.jpeg, references/main_references/calendar_desktop .jpeg, references/main_references/calendar_mobile.jpeg, references/main_references/clients_desktop.jpeg, references/main_references/clients_mobile.jpeg, references/main_references/crm-workspaces-20261001/clients.png, references/main_references/crm-workspaces-20261001/deals.png, references/main_references/crm-workspaces-20261001/leads.png, references/main_references/deals_desktop.jpeg, references/main_references/director_main_mobile.jpeg, references/main_references/inbox_desktop.jpeg, references/main_references/inbox_mobile.jpeg, references/main_references/integrations_desktop+mobile .jpeg, references/main_references/integrations_desktop+mobile 2.jpeg, references/main_references/kpi_desktop+mobile .jpeg, references/main_references/leads_desktop.jpeg, references/main_references/leads_mobile.jpeg, references/main_references/main_desktop.jpeg, requirements-dev.in, requirements-dev.txt, requirements.in, requirements.txt, scripts/ai_behavior/__init__.py, scripts/ai_behavior/action_cases.py, scripts/ai_behavior/continuity_cases.py, scripts/ai_behavior/customer_booking_cases.py, scripts/ai_behavior/customer_cases.py, scripts/ai_behavior/customer_pilot_cases.py, scripts/ai_behavior/customer_recovery_cases.py, scripts/ai_behavior/fixtures.py, scripts/ai_behavior/report.py, scripts/ai_behavior/run.py, scripts/ai_behavior/scope_cases.py, scripts/ai_behavior/suites.py, scripts/ai_behavior/test_transport.py, scripts/ai_behavior/transport.py, scripts/api_load_smoke.py, scripts/check_local_ci.sh, scripts/check_local_without_docker.sh, scripts/codex_verify.py, scripts/codex_verify.sh, scripts/instagram_local_real_test.sh, scripts/kaspi_local_real_test.sh, scripts/kaspi_pricing_cycle.sh, scripts/kaspi_pricing_local_real_test.sh, scripts/live_connectors_readiness.sh, scripts/make_clean_archive.sh, scripts/moysklad_local_real_test.sh, scripts/ozon_local_real_test.sh, scripts/paid_beta_launch_check.sh, scripts/pilot_recovery_drill.py, scripts/pilot_smoke_check.sh, scripts/platform_clinic_fixture.py, scripts/platform_diagnostics_fixture.py, scripts/predeploy_check.sh, scripts/production_release_check.sh, scripts/recovery_files.py, scripts/recovery_runtime.py, scripts/recovery_scenarios.py, scripts/recovery_test_mail.py, scripts/render_h1_queue_smoke.sh, scripts/render_h2_storage_smoke.sh, scripts/render_h3_observability_smoke.sh, scripts/render_h4_email_smoke.sh, scripts/render_h5_backup_readiness.sh, scripts/render_h6_load_baseline.sh, scripts/render_h7_provider_rollout_check.sh, scripts/security_dependency_audit.sh, scripts/setup_local_without_docker.sh, scripts/staging_smoke.sh, scripts/telegram_local_real_test.sh, scripts/tests/test_codex_verify.py, scripts/verify_billing_commerce.py, scripts/verify_connection_recovery.py, scripts/verify_handoff_recovery.py, scripts/verify_platform_admin_acceptance.py, scripts/verify_platform_details.py, scripts/verify_platform_employee_access.py, scripts/verify_platform_operations.py, scripts/verify_platform_ownership.py, scripts/verify_platform_recovery.py, scripts/verify_platform_s02.py, scripts/verify_platform_support.py, scripts/verify_recovery_s04.py, scripts/verify_service_s03.py, scripts/whatsapp_local_real_test.sh, scripts/wildberries_local_real_test.sh. Surfaces: remaining-source-review.
- Preserve existing AUD items without reclassifying documentation as validated security findings. AUD-07/08/09/10/11/12/19/20 and remaining AUD-V01 automation-actor/runtime questions were not fully revalidated; AUD-16/21 source counterevidence is recorded separately. Original consolidated register remains unchanged.
  - Follow-up prompt: Review deferred unit discovery-0004-aud-register-remainder and close its stated proof gap. Paths: docs/testing/project-risk-register-20261019.md, apps/automations/engine.py, apps/clients/services.py, apps/leads/views.py, apps/core/import_export.py. Surfaces: aud-reconciliation.
- Offline source-only authorization excludes validating actual deployment ingress, storage privacy, exposed service ports, scanner runtime, Windows ACLs and effective provider/MFA configuration.
  - Follow-up prompt: Review deferred unit discovery-0004-deployment-verification and close its stated proof gap. Paths: docker-compose.yml, config/settings.py, config/local_connector_keys.py, deploy/render.h1.example.yaml, .env.render.example. Surfaces: deployment-boundary.
- No concrete standalone exhaustion finding established for recursive public-form normalization or chat message size. Effective request-body and nesting limits require further source/runtime evidence.
  - Follow-up prompt: Review deferred unit discovery-0004-public-resource-limits and close its stated proof gap. Paths: apps/leads/forms_service.py, apps/bots/serializers.py.
- Scan canceled; saved findings and pending review were preserved.
  - Follow-up prompt: Review deferred unit scan-stopped and close its stated proof gap.
