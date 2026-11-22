import { useCallback, useEffect, useRef, useState } from "react";
import { medicalCredentialsApi as api, type CredentialAccess, type CredentialProfile } from "../../../api/medicalCredentials";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { RoleDraftState } from "../roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";
import { CredentialEditor } from "./CredentialEditor";
import { CredentialMembers, CredentialHistory } from "./CredentialLists";

export function CredentialWorkspace({ businessId, active, onDraft }: {
  businessId: number; active: boolean; onDraft: (state: RoleDraftState) => void;
}) {
  const { t, language } = useI18n();
  const [access, setAccess] = useState<CredentialAccess | null>(null);
  const [member, setMember] = useState<number | null>(null);
  const [versionId, setVersionId] = useState<number | undefined>();
  const [profile, setProfile] = useState<CredentialProfile | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [editing, setEditing] = useState(false);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const denied = useCallback((cause: unknown) => {
    setAccess(null); setProfile(null); setEditing(false); setError(cause);
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
  }, [onDraft]);
  useEffect(() => {
    if (!active || guard.current.dirty || guard.current.pending) return;
    const controller = new AbortController(); setError(null); setProfile(null);
    void (async () => {
      try {
        const permission = await api.access(businessId, controller.signal);
        const target = permission.kind === "doctor" ? permission.member_id : member;
        const value = await api.profile(businessId, target, versionId, controller.signal);
        if (!controller.signal.aborted) { setAccess(permission); setProfile(value); }
      } catch (cause) { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) denied(cause); else setError(cause); } }
    })();
    return () => controller.abort();
  }, [active, businessId, member, versionId, attempt, denied]);
  function reload() { setVersionId(undefined); setAttempt(value => value + 1); }
  function close() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current = { dirty: false, pending: false }; onDraft(guard.current); setEditing(false);
  }
  const version = profile?.version;
  if (!active) return null;
  return <div className="space-y-4" data-testid="medical-credential-workspace">
    {access?.kind === "head" ? <CredentialMembers businessId={businessId} value={member} onChange={value => {
      setMember(value); setVersionId(undefined); setProfile(null);
    }} onDenied={denied} /> : null}
    <Button variant="secondary" onClick={reload}>{t("medical.clinical.reload")}</Button>
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !profile ? <LoadingState /> : <>
      {version ? <section className="space-y-3" aria-label={t("medical.credentials.current")}>
        <h2 className="text-base font-semibold">{t("medical.templates.version", { revision: version.revision })}</h2>
        <p className="text-sm text-platforma-subtle">{version.confirmed_at
          ? t("medical.credentials.confirmed", { date: new Date(version.confirmed_at).toLocaleString(language), id: version.confirmed_by_id ?? "" })
          : t("medical.credentials.unconfirmed")}</p>
        <dl className="space-y-3">{Object.entries(version.content).map(([field, value]) => <div key={field}>
          <dt className="text-sm text-platforma-subtle">{t(credentialLabels[field as keyof typeof credentialLabels])}</dt>
          <dd className="whitespace-pre-wrap break-words text-sm">{value || t("medical.credentials.notSet")}</dd>
        </div>)}</dl>
        {version.reason ? <p className="whitespace-pre-wrap break-words text-sm">{t("medical.templates.reason")}: {version.reason}</p> : null}
      </section> : <p className="text-sm text-platforma-subtle">{t("medical.credentials.empty")}</p>}
      {access?.actions.confirm && (!version || version.revision === profile.current_revision)
        ? <Button id="medical-credential-edit" onClick={() => setEditing(true)}>{t("medical.credentials.edit")}</Button> : null}
      <CredentialHistory key={`${profile.member_id}-${attempt}`} businessId={businessId} memberId={profile.member_id}
        onSelect={setVersionId} onDenied={denied} />
    </>}
    <Modal open={editing} onClose={close} closeOnBackdrop={false} size="lg" focusReturnId="medical-credential-edit" title={t("medical.credentials.edit")}>
      {editing && profile ? <CredentialEditor businessId={businessId} profile={profile}
        control={{ guard, onDraft, onDenied: denied, onSaved: () => { setEditing(false); reload(); } }} /> : null}
    </Modal>
  </div>;
}

const credentialLabels = { license: "medical.credentials.license", specialty: "medical.credentials.specialty",
  position: "medical.credentials.position", qualification: "medical.credentials.qualification" } as const;
