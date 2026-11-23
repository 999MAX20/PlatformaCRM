import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { clientsApi } from "../../api/clients";
import type { AppointmentCreatePayload } from "../../api/appointments";
import { medicalReceptionApi, type ReceptionRequest } from "../../api/medicalReception";
import { getApiErrorMessage } from "../../api/client";
import type { Client } from "../../types";
import { AppointmentForm } from "../../components/forms/AppointmentForm";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { useCalendarCatalog } from "../calendar/useCalendarCatalog";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { useI18n } from "../../lib/i18n";

export function ReceptionBookingForm({ businessId, row, onDirty, onPending, onDenied, onDone }: {
  businessId: number; row: ReceptionRequest; onDirty: (value: boolean) => void;
  onPending: (value: boolean) => void; onDenied: (cause: unknown) => void; onDone: () => void;
}) {
  const { t } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const cache = useQueryClient();
  const catalog = useCalendarCatalog(businessId, user?.id, false, false);
  const [client, setClient] = useState<Client | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [conflict, setConflict] = useState(false);
  const controller = useRef(new AbortController());
  const pending = useRef(false);
  const request = useRef<{ fingerprint: string; key: string } | null>(null);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    setClient(null); setError(null);
    clientsApi.get(row.client_id).then(value => {
      if (!active.signal.aborted) {
        if (value.business !== businessId) onDenied(new Error("Reception booking scope changed.")); else setClient(value);
      }
    }).catch(cause => {
      if (!active.signal.aborted) {
        if (axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0)) onDenied(cause); else setError(cause);
      }
    });
    return () => active.abort();
  }, [businessId, row.client_id, attempt, onDenied]);
  const catalogError = catalog.services.error || catalog.resources.error;
  useEffect(() => {
    if (axios.isAxiosError(catalogError) && [401, 403, 404].includes(catalogError.response?.status ?? 0)) onDenied(catalogError);
  }, [catalogError, onDenied]);
  async function book(payload: AppointmentCreatePayload) {
    if (pending.current) return;
    if (conflict || payload.client !== row.client_id || payload.service !== row.service_id || payload.branch !== row.branch_id ||
        !payload.resource || !payload.start_at || !payload.expected_duration_minutes || payload.expected_price === undefined) {
      throw new Error(t("medical.plan.reviewBooking"));
    }
    if (!window.confirm(t("medical.plan.confirmBooking"))) return;
    const command = { business_id: businessId, expected_revision: row.revision, resource_id: payload.resource,
      start_at: payload.start_at, expected_price: payload.expected_price,
      expected_duration_minutes: payload.expected_duration_minutes, confirmed: true as const };
    const fingerprint = JSON.stringify(command);
    if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, key: crypto.randomUUID() };
    pending.current = true; onPending(true);
    try {
      await medicalReceptionApi.book(row.id, command, request.current.key, controller.current.signal);
      if (!controller.current.signal.aborted) { onDirty(false); void refreshAppointmentQueries(cache); onDone(); }
    } catch (cause) {
      if (!controller.current.signal.aborted) {
        const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 401 || status === 403 || status === 404) onDenied(cause);
        else if (status === 409) setConflict(true);
      }
      throw cause;
    } finally { pending.current = false; onPending(false); }
  }
  if (error || catalogError) return <ErrorState message={getApiErrorMessage(error || catalogError)} action={<Button size="lg" variant="secondary" onClick={() => {
    setAttempt(value => value + 1); void catalog.services.refetch(); void catalog.resources.refetch();
  }}>{t("common.retry")}</Button>} />;
  if (!client || catalog.services.isPending || catalog.resources.isPending) return <LoadingState />;
  if (business?.id !== businessId) return null;
  return <div className="space-y-4" data-testid="reception-booking">
    <p>{row.recommended_from} — {row.recommended_until}{row.duration_minutes ? ` · ${row.duration_minutes} ${t("appointment.minutes")}` : ""}</p>
    <AppointmentForm businessId={businessId} clients={[client]} services={catalog.services.data || []} resources={catalog.resources.data || []}
      leads={[]} recordFirst fixedClient fixedContext fixedBranch hideNotes currency={business.currency} timeZone={business.timezone}
      onDirtyChange={onDirty} onSubmit={book} prefill={{ client: row.client_id, branch: row.branch_id,
        service: row.service_id, resource: row.preferred_resource_id, responsible_user: user?.id }} />
    {conflict ? <Button size="lg" variant="secondary" onClick={() => {
      if (window.confirm(t("medical.clinical.discard"))) { onDirty(false); onDone(); }
    }}>{t("medical.clinical.reload")}</Button> : null}
  </div>;
}
