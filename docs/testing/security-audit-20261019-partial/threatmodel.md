# Threat Model

PlatformaCRM is a multi-tenant React/Django REST CRM with tenant records, scheduling, messaging, file upload/import/export, AI tools, integrations and platform administration (config/urls.py:133,182,200). Docker runs migrations, collectstatic and Gunicorn; Compose adds PostgreSQL, Redis, Celery and ClamAV (Dockerfile:19; docker-compose.yml:1-145). The Render blueprint is an example, not deployment evidence. Model generated from an independent architecture review and parent checks; mapping alone is not completed source-audit coverage.

## Assets

- Tenant CRM records and linked entities; business membership and resource/record-scoped permissions protect ownership (apps/core/permissions.py:25; apps/core/viewsets.py:138,215).
- User identity, access JWTs, HttpOnly refresh cookies, device sessions and auth epochs (config/settings.py:263; apps/accounts/authentication.py:12; apps/accounts/auth_views.py:23).
- Attachments stored as private/attachments/business-{id}/{uuid}{ext} under default storage, with scan state and digest-verified byte snapshots (apps/core/models.py:20,183; apps/core/file_scanning.py:88).
- Avatar originals are transient; normalized fresh 256x256 JPEG is stored as UserAvatar database binary (apps/accounts/avatars.py:23-61).
- Imports and export results are default-storage FileFields with imports/YYYY/MM/DD and exports/YYYY/MM/DD keys (apps/core/models.py:301,344).
- Connector AES-GCM envelopes and separately provisioned encryption keys; database and broker authority; audit records (apps/integrations/credential_encryption.py:42; config/settings.py:44,69,174,315).
- Distinct platform-support grants, AI approvals, scoped API tokens and outbound provider authority (apps/core/permissions.py:10; apps/ai_core/crm_approval.py:9; apps/integrations/views.py:426).

## Trust Boundaries

- Browser/API -> Django: JWT and IsAuthenticated defaults; independent CORS/CSRF/security middleware; public endpoint overrides. Middleware alone does not protect CSRF-exempt DRF views (config/settings.py:142-151,261-268).
- User -> tenant: ownership, active membership and unexpired support grants form accessible_businesses; global platform-admin access depends on SUPPORT_REQUIRES_GRANT; querysets and mutations apply separate policy (apps/core/permissions.py:10-52; apps/core/viewsets.py:130-235).
- Caller -> attachment: target entity resolved inside business, UPDATE for upload and VIEW for download; quota and scanner checks independent (apps/core/file_attachments.py:23; apps/core/file_attachment_views.py:48,75).
- Untrusted bytes -> parsers: extension/MIME/size/signature checks, tokenized scan leases, clean-only release, immutable size/hash-checked snapshot; avatar byte/pixel/frame limits and re-encoding (apps/core/file_validation.py:28; apps/core/file_scanning.py:35,88; apps/accounts/avatars.py:23).
- Backend -> storage: local writes use MEDIA_ROOT/private/attachments; legacy local route checks PRIVATE_MEDIA_ROOT/path then opens FileField storage; S3 disables that route. Host/bucket policy must prevent direct-access bypass (config/settings.py:194-195,233-257; apps/core/file_views.py:19-46).
- Web/workers -> Redis/ClamAV: queue names route jobs but do not isolate equal-privilege processes sharing environment and media. Scanner is unauthenticated internal INSTREAM with no published scanner port (docker-compose.yml:30-114; config/settings.py:315-327).
- External API client -> public clients API: separate bearer token scope clients:read and token.business filter; token issuance/rotation stores hashes and returns raw value once (apps/integrations/views.py:431,445,521).
- Webhook destination -> transport: address filtering, pinned TLS, bounded redirects and per-hop validation belong to webhook transport; provider adapters require separate review (apps/integrations/webhooks.py:25-167).
- AI proposal -> execution: locked approval binds business, log, requester, action type and fingerprint, status/expiry and current approver permission; mutation paths for that approval must preserve binding (apps/ai_core/crm_approval.py:9-23).
- Operator -> deployment: startup holds database schema and environment credential authority (Dockerfile:19; config/settings.py:37).

## Attacker Capabilities

- Unauthenticated callers can submit public login/intake/webhook/API requests when deployed publicly; no assumed filesystem, database, broker or signing-key access.
- Authenticated tenant members control permitted form fields, filenames/MIME/bytes and record identifiers, but not unrelated businesses or objects outside their role scope.
- Integration managers can configure permitted outbound destinations; internal-network access is not an intended webhook capability.
- Provider payloads and AI-generated content are untrusted. Provider secrets, API tokens and approval artifacts grant distinct limited capabilities.
- Runtime environment, mount and key-file operators already have privileged deployment authority; require a lower-privilege boundary before claiming additional security impact.

## Security Objectives

- Enforce tenant/record/linked-resource authorization consistently across API, bulk operations, exports and jobs.
- Reject revoked identities and independently enforce support grants, API scopes and exact AI command approval.
- Fail closed on scanning; serve the exact scanned bytes only to currently authorized users; do not persist avatar originals.
- Bound file/archive/image/tabular decoding and shared-resource consumption; default attachment maximum 10 MiB, avatar 5 MiB/16 million pixels/one frame, separate import/export/report bounds (config/settings.py:198-209; apps/accounts/avatars.py:13-14).
- Keep provider credentials and encryption key material confidential, and redact errors.
- Constrain outbound HTTP targets and bind approved input to actual side effect.
- User-context priorities: SQL injection; HTTP/API/session/CSRF/SSRF; attachments/avatars, active content, MIME/origin/storage/download protection. These priorities are not findings.

## Assumptions

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
- Effective avatar resource: UserAvatar DB binary, fresh 256x256 JPEG <=128 KiB; own account API/database are recipients, original input not persisted (apps/accounts/avatar_views.py:24; apps/accounts/avatars.py:23-61).
- Effective scanner: Compose web/file worker CLAMD_HOST/PORT -> clamav:3310; clamav_data:/var/lib/clamav and deploy/clamav/clamd.conf read-only. No published port, daemon resource limits and application timeout/clean-only release (docker-compose.yml:86-104; config/settings.py:199-203).
- Effective connector key resource: explicit CONNECTOR_CREDENTIAL_LOCAL_KEY_FILE, else %LOCALAPPDATA%/Zani/connector-credential-key.json, else ~/.zani/connector-credential-key.json, only in development without env keys. Exclusive mode 0600 creation/chmod; same host user recipients, Windows ACL unknown. Production/staging requires environment keyring/active ID without automatic local fallback (config/local_connector_keys.py:23-51; config/settings.py:44-55; apps/integrations/credential_encryption.py:42).

---

## Saved Model Context

- Source: scan
- Scan: 220130aa-3d20-4bcf-9415-8d794f1087e3
- Target: PlatformaCRM
- Revision: df2b9708401a3075e590b3e5e97bc5369383c34a
- Snapshot: codex-security-snapshot/v1:sha256:230fd7f877f6e3107caa575f3753bc767d91a70bab6b85ca6597845c29f1eda3
- Result status: canceled
- Model origin: recovered
- Model scope: not recorded
- Scan scope: .

This is a provisional model saved before successful completion.
