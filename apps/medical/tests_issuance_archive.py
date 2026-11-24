import hashlib,io,json,zipfile
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied,ValidationError
from apps.businesses.models import Business
from .tests_document_issuance import DocumentIssuanceTests as Fixture
from .tests_patient_services import key
from .issuance_archive import portal_archive
from .issuance_portal import portal_pdf,portal_documents
from .models import MedicalDocumentGrantEvent
from .identity_crypto import MedicalDataUnavailable
from .audit import MedicalAuditUnavailable

@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8),
    USE_S3=False,MEDICAL_SYNTHETIC_SIGNING_ENABLED=True,MEDICAL_SYNTHETIC_ISSUANCE_ENABLED=True,ENVIRONMENT="test")
class PortalArchiveTests(TestCase):
    setUpTestData=classmethod(Fixture.setUpTestData.__func__)
    setUp,prepare,rules,save,change,confirm,render,finalize=Fixture.setUp,Fixture.prepare,Fixture.rules,Fixture.save,Fixture.change,Fixture.confirm,Fixture.render,Fixture.finalize
    create,activate,login=Fixture.create,Fixture.activate,Fixture.login
    def ready(self):
        self.finalize();grant,code,_=self.create();grant,_=self.activate(grant);token,_=self.login(code)
        return grant,dict(business_slug=self.business.slug,token=token)
    def test_exact_pdf_manifest_portable_paths_and_audit(self):
        grant,scope=self.ready()
        public_id=portal_documents(**scope)["documents"][0]["id"]
        pdf=portal_pdf(**scope,public_id=public_id)
        data=portal_archive(**scope)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest=json.loads(archive.read("manifest.json"));item=manifest["documents"][0]
            self.assertEqual(set(archive.namelist()),{"index.html","manifest.json",f"documents/{public_id}.pdf"})
            self.assertEqual(archive.read(item["path"]),pdf)
            self.assertEqual(item["sha256"],hashlib.sha256(pdf).hexdigest())
            self.assertEqual(item["revision"],self.version.revision)
            self.assertIn(item["path"].encode(),archive.read("index.html"))
        self.assertEqual(MedicalDocumentGrantEvent.objects.filter(grant=grant,action="downloaded").count(),1)
    def test_anonymous_foreign_revoked_expired_and_private_http(self):
        grant,scope=self.ready();api=APIClient();url=f"/api/medical/portal/{self.business.slug}/archive/"
        self.assertEqual(api.get(url).status_code,403)
        api.cookies["medical_document_session"]=scope["token"]
        response=api.get(url);self.assertEqual(response.status_code,200,response.content[:100])
        self.assertEqual(response["Content-Type"],"application/zip");self.assertEqual(response["Cache-Control"],"no-store, private")
        other=Business.objects.create(owner=self.owner,name="Other archive",slug="other-archive")
        with self.assertRaises(PermissionDenied):portal_archive(**(scope|{"business_slug":other.slug}))
        with patch("django.utils.timezone.now",return_value=grant.expires_at):
            with self.assertRaises(PermissionDenied):portal_archive(**scope)
        self.activate(grant,action="revoke",reason="Synthetic revoke",idempotency_key="revoke")
        self.assertEqual(api.get(url).status_code,403)
    def test_unavailable_material_and_audit_failure_never_return_partial_archive(self):
        grant,scope=self.ready()
        with patch("apps.medical.issuance_archive._material",side_effect=MedicalDataUnavailable):
            with self.assertRaises(MedicalDataUnavailable):portal_archive(**scope)
        with patch("apps.medical.issuance_archive.grant_event",side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):portal_archive(**scope)
        self.assertFalse(MedicalDocumentGrantEvent.objects.filter(grant=grant,action="downloaded").exists())
    def test_limit_and_expiry_rechecked_before_return(self):
        grant,scope=self.ready()
        with patch("apps.medical.issuance_archive.MAX_ARCHIVE_BYTES",1),patch("apps.medical.issuance_archive._material") as material:
            with self.assertRaises(ValidationError):portal_archive(**scope)
            material.assert_not_called()
        from .issuance_portal import session_grant
        original=session_grant
        calls=0
        def expire(slug,token):
            nonlocal calls
            calls+=1
            if calls==2:raise PermissionDenied()
            return original(slug,token)
        with patch("apps.medical.issuance_archive.session_grant",side_effect=expire):
            with self.assertRaises(PermissionDenied):portal_archive(**scope)
        self.assertFalse(MedicalDocumentGrantEvent.objects.filter(grant=grant,action="downloaded").exists())

    def test_multiple_exact_versions_and_readable_index_escape(self):
        from apps.core.models import FileAttachment
        self.finalize();first=self.version
        self.version=self.save(idempotency_key="second-document")
        self.change(idempotency_key="second-submit")
        self.confirm(idempotency_key="second-head")
        self.change(target="reviewed",expected_state_revision=2,idempotency_key="second-primary")
        self.artifact,_=self.render()
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean",scan_sha256=self.artifact.sha256)
        self.finalize(idempotency_key="second-finalize")
        grant,code,_=self.create(version_ids=[first.pk,self.version.pk]);self.activate(grant);token,_=self.login(code)
        scope=dict(business_slug=self.business.slug,token=token)
        from .document_content import read_document_revision
        def hostile_title(version):
            result=read_document_revision(version)
            result["template"]["title"]='<script>alert(1)</script> ../../outside.pdf'
            return result
        with patch("apps.medical.issuance_archive.read_document_revision",side_effect=hostile_title),patch("tempfile.NamedTemporaryFile",side_effect=AssertionError("Archive must stay in memory")):
            data=portal_archive(**scope)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest=json.loads(archive.read("manifest.json"))
            self.assertEqual(len(manifest["documents"]),2)
            self.assertEqual(len(archive.namelist()),4)
            index=archive.read("index.html")
            self.assertNotIn(b"<script>",index);self.assertIn(b"&lt;script&gt;",index)
            self.assertFalse(any(".." in path for path in archive.namelist()))
            for item in manifest["documents"]:
                self.assertEqual(item["sha256"],hashlib.sha256(archive.read(item["path"])).hexdigest())
