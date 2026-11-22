import { useCallback, useEffect, useRef, useState } from "react";
import { medicalRolesApi as api, type MedicalRoleAccess } from "../../../api/medicalRoles";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { MedicalRoleDefinitionForm } from "./MedicalRoleDefinitionForm";
import { MedicalRoleMemberPanel } from "./MedicalRoleMemberPanel";
import { MedicalRolePageStatus } from "./MedicalRolePageStatus";
import { useMedicalRolePage } from "./useMedicalRolePage";
import type { RoleDraftState } from "./MedicalRoleCommand";

export function MedicalRoleWorkspace({ businessId, active, onDraft }: { businessId: number; active: boolean; onDraft: (state: RoleDraftState) => void }) {
  const { t } = useI18n();
  const [access, setAccess] = useState<MedicalRoleAccess | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<"create" | number | null>(null);
  const [version, setVersion] = useState(0);
  const guard = useRef<RoleDraftState>({ dirty: false, pending: false });
  const focusReturn = useRef("medical-role-create");
  const denied = useCallback((cause: unknown) => {
    setAccess(null); setError(cause); setDialog(null);
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
  }, [onDraft]);
  useEffect(() => {
    if (!active || guard.current.dirty || guard.current.pending) return;
    const controller = new AbortController();
    setAccess(null); setError(null);
    void api.access(businessId, controller.signal).then(value => { if (!controller.signal.aborted) setAccess(value); })
      .catch(cause => { if (!controller.signal.aborted) denied(cause); });
    return () => controller.abort();
  }, [active, businessId, attempt, denied]);
  function close() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current = { dirty: false, pending: false }; onDraft(guard.current); setDialog(null);
  }
  function saved() { setDialog(null); setVersion(value => value + 1); }
  function openDialog(value: "create" | number) {
    focusReturn.current = value === "create" ? "medical-role-create" : `medical-role-member-${value}`;
    setDialog(value);
  }
  if (!active && !access) return null;
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} />;
  if (!access) return <LoadingState />;
  return <div className="space-y-5" data-testid="medical-role-workspace">
    {!access.can_assign ? <p role="status" className="text-sm text-platforma-subtle">{t("medical.roles.moduleDisabled")}</p> : null}
    <div className="flex flex-wrap gap-2">
      <Button id="medical-role-create" disabled={!access.can_assign} onClick={() => openDialog("create")}>{t("medical.roles.create")}</Button>
      <Button variant="secondary" onClick={() => setAttempt(value => value + 1)}>{t("medical.clinical.reload")}</Button>
    </div>
    <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); setQuery(search.trim()); }}>
      <div className="min-w-0 flex-1"><Input label={t("medical.roles.searchMember")} value={search} maxLength={100} onChange={event => setSearch(event.target.value)} /></div>
      <Button type="submit" variant="secondary">{t("common.search")}</Button>
    </form>
    <MemberList key={`${query}:${version}`} businessId={businessId} query={query} onDenied={denied} onSelect={openDialog} />
    <RoleList key={version} businessId={businessId} onDenied={denied} />
    <Modal title={t(dialog === "create" ? "medical.roles.create" : "medical.roles.memberAccess")} open={dialog !== null}
      onClose={close} closeOnBackdrop={false} size="lg" focusReturnId={focusReturn.current}>
      {dialog === "create" ? <MedicalRoleDefinitionForm businessId={businessId} access={access}
        control={{ guard, onDraft, onSaved: saved, onDenied: denied }} /> : typeof dialog === "number" ?
        <MedicalRoleMemberPanel businessId={businessId} memberId={dialog} guard={guard} onDraft={onDraft} onDenied={denied} /> : null}
    </Modal>
  </div>;
}

function MemberList({ businessId, query, onDenied, onSelect }: { businessId: number; query: string;
  onDenied: (cause: unknown) => void; onSelect: (id: number) => void }) {
  const { t } = useI18n();
  const read = useCallback((after_id: number | undefined, signal: AbortSignal) => api.members({ business_id: businessId, query, after_id }, signal), [businessId, query]);
  const page = useMedicalRolePage(read, onDenied);
  return <section className="space-y-3" aria-label={t("medical.roles.members")}>
    <h2 className="text-base font-semibold">{t("medical.roles.members")}</h2>
    <ul className="divide-y divide-platforma-border">{page.rows.map(member => <li key={member.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0 flex-1 break-words"><p className="font-medium">{member.name || t("medical.roles.memberFallback", { id: member.id })}</p>
        {!member.is_active || !member.account_active ? <p className="text-sm text-platforma-subtle">{t("medical.roles.inactive")}</p> : null}</div>
      <Button id={`medical-role-member-${member.id}`} variant="secondary" onClick={() => onSelect(member.id)}>{t("medical.roles.memberAccess")}</Button>
    </li>)}</ul>
    <MedicalRolePageStatus page={page} empty={t("medical.roles.noMembers")} />
  </section>;
}

function RoleList({ businessId, onDenied }: { businessId: number; onDenied: (cause: unknown) => void }) {
  const { t } = useI18n();
  const read = useCallback((after_id: number | undefined, signal: AbortSignal) => api.roles({ business_id: businessId, after_id }, signal), [businessId]);
  const page = useMedicalRolePage(read, onDenied);
  return <section className="space-y-3" aria-label={t("medical.roles.definitions")}>
    <h2 className="text-base font-semibold">{t("medical.roles.definitions")}</h2>
    <div className="divide-y divide-platforma-border">{page.rows.map(role => <details key={role.id} className="py-2">
      <summary className="platforma-focus-ring min-h-11 cursor-pointer break-words py-2 font-medium">{role.name} · {t(`medical.roles.kind.${role.kind}`)}{!role.is_active ? ` · ${t("medical.roles.inactive")}` : ""}</summary>
      <ul className="space-y-1 py-2 text-sm">{role.permissions.filter(rule => rule.is_allowed).map(rule => <li key={`${rule.resource}:${rule.action}`} className="break-words">
        {t(`medical.roles.resource.${rule.resource}`)} · {t(`medical.roles.action.${rule.action}`)} · {t(`settings.visibility.${rule.scope}`)}
      </li>)}</ul>
    </details>)}</div>
    <MedicalRolePageStatus page={page} empty={t("medical.roles.noRoles")} />
  </section>;
}
