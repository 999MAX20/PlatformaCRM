import { useCallback, useEffect, useRef, useState } from "react";
import { medicalRolesApi as api, type MedicalRoleContext } from "../../../api/medicalRoles";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { MedicalRoleAssignmentForm, MedicalRoleRevokeForm } from "./MedicalRoleAssignmentForm";
import type { RoleDraftState } from "./MedicalRoleCommand";
import { MedicalRolePageStatus } from "./MedicalRolePageStatus";
import { medicalRoleDenied, useMedicalRolePage } from "./useMedicalRolePage";

export function MedicalRoleMemberPanel({ businessId, memberId, guard, onDraft, onDenied }: {
  businessId: number; memberId: number; guard: { current: RoleDraftState };
  onDraft: (state: RoleDraftState) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const [context, setContext] = useState<MedicalRoleContext | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  const [mode, setMode] = useState<"assign" | "revoke" | null>(null);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    setContext(null); setError(null);
    void api.context({ business_id: businessId, member_id: memberId }, controller.signal).then(value => {
      if (!controller.signal.aborted) setContext(value);
    }).catch(cause => { if (!controller.signal.aborted) { if (medicalRoleDenied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [businessId, memberId, version, onDenied]);
  useEffect(() => { if (context) title.current?.focus(); }, [context]);
  function refresh() {
    guard.current = { dirty: false, pending: false }; onDraft(guard.current);
    setMode(null); setVersion(value => value + 1);
  }
  function cancelForm() {
    if (guard.current.pending || (guard.current.dirty && !window.confirm(t("medical.clinical.discard")))) return;
    guard.current.dirty = false; onDraft(guard.current); setMode(null); title.current?.focus();
  }
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={refresh}>{t("common.retry")}</Button>} />;
  if (!context) return <LoadingState />;
  const control = { guard, onDraft, onSaved: refresh, onDenied };
  return <div className="space-y-4" data-testid="medical-role-member-panel">
    <h3 ref={title} tabIndex={-1} className="platforma-focus-ring break-words text-base font-semibold">{context.member.name || t("medical.roles.memberFallback", { id: memberId })}</h3>
    {!context.member.is_active || !context.member.account_active ? <p className="text-sm text-platforma-subtle">{t("medical.roles.inactive")}</p> : null}
    {context.assignment ? <div className="space-y-2 text-sm" data-testid="medical-role-current">
      <p className="break-words font-medium">{context.role_name} · {t(`medical.roles.kind.${context.assignment.kind}`)}</p>
      <p role="status">{t(context.assignment.revoked_at ? "medical.roles.revoked" : "medical.roles.assigned")}</p>
      {context.role_active === false ? <p>{t("medical.roles.inactiveRole")}</p> : null}
      {context.assignment.all_branches ? <p>{t("branches.allFuture")}</p> : <ul>{context.assigned_branches.map(branch => <li className="break-words" key={branch.id}>
        {branch.name}{!branch.is_active ? ` · ${t("medical.roles.inactive")}` : ""}
      </li>)}</ul>}
    </div> : <p className="text-sm text-platforma-subtle">{t("medical.roles.notAssigned")}</p>}
    {mode ? <>
      <Button variant="secondary" onClick={cancelForm}>{t("common.back")}</Button>
      {mode === "assign" ? <MedicalRoleAssignmentForm businessId={businessId} context={context} control={control} /> :
        <MedicalRoleRevokeForm businessId={businessId} context={context} control={control} />}
    </> : <div className="flex flex-wrap gap-2">
      <Button disabled={!context.can_assign} onClick={() => setMode("assign")}>{t("medical.roles.assign")}</Button>
      <Button variant="secondary" disabled={!context.can_revoke} onClick={() => setMode("revoke")}>{t("medical.roles.revoke")}</Button>
    </div>}
    {!context.can_assign ? <p className="text-sm text-platforma-subtle">{t("medical.roles.assignmentUnavailable")}</p> : null}
    {!mode ? <RoleHistory key={version} businessId={businessId} memberId={memberId} onDenied={onDenied} /> : null}
  </div>;
}

function RoleHistory({ businessId, memberId, onDenied }: { businessId: number; memberId: number; onDenied: (cause: unknown) => void }) {
  const { t, language } = useI18n();
  const read = useCallback((after_id: number | undefined, signal: AbortSignal) => api.history({ business_id: businessId, member_id: memberId, after_id }, signal), [businessId, memberId]);
  const page = useMedicalRolePage(read, onDenied);
  return <section className="space-y-3 border-t border-platforma-border pt-4" aria-label={t("medical.roles.history")}>
    <h3 className="text-base font-semibold">{t("medical.roles.history")}</h3>
    <ol className="divide-y divide-platforma-border">{page.rows.map(row => <li key={row.id} className="space-y-1 py-3 text-sm">
      <p className="font-medium">{t(`medical.roles.decision.${row.action}`)}</p>
      <p className="break-words text-platforma-subtle">{row.actor_name || t("medical.clinical.authorUnknown")} · <time dateTime={row.created_at}>{formatDateTime(row.created_at, undefined, true, language)}</time></p>
      <p className="break-words whitespace-pre-wrap">{row.reason}</p>
    </li>)}</ol>
    <MedicalRolePageStatus page={page} empty={t("medical.roles.noHistory")} />
  </section>;
}
