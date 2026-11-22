import axios from "axios";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { getApiErrorMessage } from "../../../api/client";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "./useMedicalRolePage";

export type RoleDraftState = { dirty: boolean; pending: boolean };
export type RoleFormControl = { guard: { current: RoleDraftState }; onDraft: (state: RoleDraftState) => void;
  onSaved: () => void; onDenied: (cause: unknown) => void };

export function MedicalRoleCommand<T extends object>({ payload, dirty, submit, label, control, children }: {
  payload: T | null; dirty: boolean; submit: (payload: T, key: string) => Promise<unknown>; label: string;
  control: RoleFormControl; children: ReactNode;
}) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [conflict, setConflict] = useState(false);
  const retry = useRef<{ fingerprint: string; key: string } | null>(null);
  control.guard.current.dirty = dirty;
  useEffect(() => { control.onDraft({ dirty, pending }); }, [dirty, pending, control.onDraft]);
  useEffect(() => () => { control.guard.current = { dirty: false, pending: false }; control.onDraft({ dirty: false, pending: false }); }, [control.guard, control.onDraft]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!payload || conflict || control.guard.current.pending) return;
    control.guard.current.pending = true; setPending(true); setError(null);
    const fingerprint = JSON.stringify(payload);
    if (retry.current?.fingerprint !== fingerprint) retry.current = { fingerprint, key: crypto.randomUUID() };
    try {
      await submit(payload, retry.current.key);
      control.guard.current = { dirty: false, pending: false };
      control.onDraft({ dirty: false, pending: false }); control.onSaved();
    } catch (cause) {
      if (medicalRoleDenied(cause)) control.onDenied(cause);
      else { setError(cause); if (axios.isAxiosError(cause) && cause.response?.status === 409) setConflict(true); }
    } finally { control.guard.current.pending = false; setPending(false); }
  }
  return <form onSubmit={event => void save(event)} className="space-y-4" data-testid="medical-role-command">
    <fieldset disabled={pending || conflict} className="min-w-0 space-y-4">{children}</fieldset>
    {error ? <ErrorState message={conflict ? t("medical.clinical.conflict") : getApiErrorMessage(error)} /> : null}
    <div className="flex flex-wrap gap-2">
      {conflict ? <Button type="button" variant="secondary" onClick={() => {
        if (window.confirm(t("medical.clinical.discard"))) control.onSaved();
      }}>{t("medical.clinical.reload")}</Button> : null}
      <Button type="submit" size="lg" isLoading={pending} disabled={!payload || conflict}>{label}</Button>
    </div>
  </form>;
}
