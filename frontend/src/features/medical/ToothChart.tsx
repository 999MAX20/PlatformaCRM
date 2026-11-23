import { useToothNavigation } from "./clinicalViewNavigation";
import { ToothShape } from "./ToothShape";
import { historyScopeKey } from "./clinicalHistoryNavigation";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import type { AppointmentClinicalContext, ClinicalReadScope } from "../../api/medicalClinical";
import { medicalToothApi, type ToothObservation, type ToothHistory, type ToothSnapshot } from "../../api/medicalTooth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";
import { localeByLanguage } from "../calendar/calendarConstants";

import { ToothEditor } from "./ToothEditor";
import { ToothPlanSteps } from "./ToothPlanSteps";
import type { ClinicalDraftControl } from "./ClinicalDraftForm";

type Denied = (cause: unknown) => void;
function denied(cause: unknown) { return axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0); }

export function ToothChart({ context, onDenied, onFiles }: { context: AppointmentClinicalContext; onDenied: Denied; onFiles?: (tooth: number) => void }) {
  const scope = useMemo(() => ({ business_id: context.business_id, patient_id: context.patient.id,
    appointment_id: context.appointment.id }), [context]);
  return <ToothChartRead key={historyScopeKey(scope)} scope={scope} context={context} onDenied={onDenied} onFiles={onFiles} />;
}

export function ParticipationToothChart({ businessId, patientId, participationId, onDenied, onFiles }: {
  businessId: number; patientId: number; participationId: number; onDenied: Denied; onFiles?: (tooth: number) => void;
}) {
  const scope = useMemo(() => ({ business_id: businessId, patient_id: patientId, participation_id: participationId }),
    [businessId, patientId, participationId]);
  return <ToothChartRead key={historyScopeKey(scope)} scope={scope} onDenied={onDenied} onFiles={onFiles} />;
}

function ToothChartRead({ scope, context, onDenied, onFiles }: {
  scope: ClinicalReadScope; context?: AppointmentClinicalContext; onDenied: Denied;
  onFiles?: (tooth: number) => void;
}) {
  const { t } = useI18n();
  const [navigation, setNavigation] = useToothNavigation(scope);
  const { date, asOf } = navigation;
  return <section className="space-y-4" data-testid="tooth-chart">
    <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); if (date) setNavigation({ ...navigation, asOf: new Date(date).toISOString() }); }}>
      <Input type="datetime-local" label={t("medical.tooth.asOf")} value={date} onChange={event => setNavigation({ ...navigation, date: event.target.value })} />
      <Button type="submit" size="lg" variant="secondary" disabled={!date}>{t("medical.tooth.show")}</Button>
      {asOf ? <Button size="lg" variant="secondary" onClick={() => { setNavigation({ ...navigation, date: "", asOf: undefined }); }}>{t("medical.tooth.current")}</Button> : null}
    </form>
    <ChartData navigation={navigation} onNavigation={setNavigation} key={asOf ?? "current"} scope={scope} context={context} asOf={asOf} onDenied={onDenied} onFiles={onFiles} />
  </section>;
}

function ChartData({ scope, context, asOf, onDenied, navigation, onNavigation, onFiles }: {
  scope: ClinicalReadScope; context?: AppointmentClinicalContext; asOf?: string; onDenied: Denied;
  navigation: ReturnType<typeof useToothNavigation>[0]; onNavigation: ReturnType<typeof useToothNavigation>[1];
  onFiles?: (tooth: number) => void;
}) {
  const { t } = useI18n();
  const [rows, setRows] = useState<ToothSnapshot["observations"] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const { mode, quadrant } = navigation;
  const [selected, setSelected] = useState<number | null>(null);
  const editor = useRef<ClinicalDraftControl>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const focusAfterReload = useRef<number | null>(navigation.focusedTooth ?? null);
  const [confirmClose, setConfirmClose] = useState(false);
  const [closeFailed, setCloseFailed] = useState(false);
  const [closing, setClosing] = useState(false);
  const closePending = useRef(false);
  const filesDestination = useRef<number | null>(null);
  const finish = () => {
    const tooth = filesDestination.current; filesDestination.current = null;
    setConfirmClose(false); setSelected(null);
    if (tooth !== null) onFiles?.(tooth);
  };
  const reload = () => { focusAfterReload.current = selected; finish(); setAttempt(x => x + 1); };
  const close = () => {
    if (closePending.current || editor.current?.isPending()) return;
    if (editor.current?.isDirty()) { setCloseFailed(false); setConfirmClose(true); } else finish();
  };
  async function saveAndClose() {
    if (closePending.current) return;
    closePending.current = true; setClosing(true); setCloseFailed(false);
    try { if (await editor.current?.save()) finish(); else setCloseFailed(true); }
    finally { closePending.current = false; setClosing(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    setRows(null); setError(null);
    async function load() {
      const collected: ToothSnapshot["observations"] = [];
      let cursor: number | undefined;
      let cutoff = asOf;
      do {
        const page = await medicalToothApi.snapshot({ ...scope, as_of: cutoff, after_state_id: cursor }, controller.signal);
        collected.push(...page.observations);
        cutoff = page.as_of;
        const next = page.next_after_state_id;
        if (next !== null && next <= (cursor ?? 0)) throw new Error("Invalid medical pagination cursor.");
        cursor = next ?? undefined;
      } while (cursor !== undefined && !controller.signal.aborted);
      if (!controller.signal.aborted) setRows(collected);
    }
    void load().catch(cause => { if (!controller.signal.aborted) { if (denied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope, asOf, attempt, onDenied]);
  useLayoutEffect(() => {
    if (!rows || focusAfterReload.current === null) return;
    const button = chartRef.current?.querySelector<HTMLButtonElement>(`[data-focus-return-id="tooth-${focusAfterReload.current}"]`);
    if (button) { button.focus({ preventScroll: true }); focusAfterReload.current = null; }
  }, [rows]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} />;
  if (!rows) return <LoadingState />;
  const quadrants = [1, 2, 4, 3];
  return <div ref={chartRef} className="space-y-4">
    <Select label={t("medical.tooth.title")} value={mode} onChange={event => { onNavigation({ ...navigation, mode: event.target.value, focusedTooth: undefined }); setSelected(null); }}
      options={["permanent", "primary", "mixed"].map(value => ({ value, label: t(`medical.tooth.${value}`) }))} />
    <p className="hidden text-sm text-platforma-subtle md:block">{t("medical.tooth.orientation")}</p>
    <div className="md:hidden"><Select label={t("medical.tooth.orientation")} value={quadrant} onChange={event => onNavigation({ ...navigation, quadrant: Number(event.target.value), focusedTooth: undefined })}
      options={quadrants.map(value => ({ value, label: t(`medical.tooth.q${value}`) }))} /></div>
    <div className="grid min-w-0 gap-4 md:grid-cols-2">
      {quadrants.map(q => <section key={q} className={q === quadrant ? "min-w-0 space-y-2" : "hidden min-w-0 space-y-2 md:block"}>
        <h3 className="text-sm font-medium">{t(`medical.tooth.q${q}`)}</h3>
        {(mode === "mixed" ? [false, true] : [mode === "primary"]).map(primary => {
          const numbers = Array.from({ length: primary ? 5 : 8 }, (_, index) => (q + (primary ? 4 : 0)) * 10 + index + 1);
          if (q === 1 || q === 4) numbers.reverse();
          return <div key={String(primary)} className="space-y-2">
            {mode === "mixed" ? <p className="text-xs text-platforma-subtle">{t(primary ? "medical.tooth.primary" : "medical.tooth.permanent")}</p> : null}
            <div className="flex overflow-x-auto pb-2">{numbers.map(tooth => {
              const observed = rows.some(row => row.tooth === tooth);
              return <button type="button" key={tooth} className={`platforma-focus-ring flex min-h-11 min-w-11 shrink-0 cursor-pointer flex-col items-center rounded-control px-0.5 py-2 transition-colors hover:bg-surface-hover ${observed ? "bg-brand-50 text-brand-700" : "text-platforma-subtle"}`}
                aria-label={`${t("medical.tooth.tooth")} ${tooth}: ${t(observed ? "medical.tooth.observed" : "medical.tooth.empty")}`}
                data-focus-return-id={`tooth-${tooth}`} onClick={() => { onNavigation({ ...navigation, focusedTooth: tooth }); setSelected(tooth); }}>
                <ToothShape tooth={tooth} />
                <span className="text-sm font-semibold tabular-nums">{tooth}{observed ? " •" : ""}</span>
              </button>;
            })}</div>
          </div>;
        })}
      </section>)}
    </div>
    <p className="text-sm text-platforma-subtle">{t("medical.tooth.select")}</p>
    <Modal open={selected !== null} onClose={close} closeOnBackdrop={false} size="lg" title={`${t("medical.tooth.tooth")} ${selected ?? ""}`}
      focusReturnId={`tooth-${selected}`} testId="tooth-inspector">
      {selected !== null ? <div className="space-y-4">
        {onFiles && !asOf ? <Button size="lg" variant="secondary" onClick={() => {
          if (closePending.current || editor.current?.isPending()) return;
          filesDestination.current = selected; close();
        }}>{t("medical.files.title")}</Button> : null}
        <ToothPlanSteps key={`${selected}-${asOf ?? "current"}`} scope={scope} tooth={selected} asOf={asOf} onDenied={onDenied} />
        {asOf || !context ? <p className="text-sm text-platforma-subtle">{t("medical.tooth.readOnly")}</p> : null}
        {!rows.some(row => row.tooth === selected) ? <p>{t("medical.tooth.empty")}</p> : rows.filter(row => row.tooth === selected).map(row =>
          <Observation key={row.history_id} row={row} scope={scope} onDenied={onDenied} />)}
        {!asOf && context ? <ToothEditor key={selected} context={context} tooth={selected}
          revisions={new Map(rows.filter(row => row.tooth === selected).map(row => [row.surface, row.current_revision]))}
          control={editor} onSaved={reload} onReload={reload} onDenied={onDenied} /> : null}
      </div> : null}
    </Modal>
    <Modal open={confirmClose && selected !== null} onClose={() => { if (!closePending.current) { filesDestination.current = null; setConfirmClose(false); } }}
      closeOnBackdrop={false} size="sm" title={t("medical.clinical.unsavedTitle")} testId="tooth-unsaved">
      <div className="space-y-4">
        {closeFailed ? <p role="alert">{t("medical.clinical.closeFailed")}</p> : null}
        <div className="flex flex-wrap gap-3">
          <Button size="lg" isLoading={closing} onClick={() => void saveAndClose()}>{t("medical.clinical.saveClose")}</Button>
          <Button size="lg" variant="secondary" disabled={closing} onClick={() => { filesDestination.current = null; setConfirmClose(false); }}>{t("medical.clinical.continueEditing")}</Button>
          <Button size="lg" variant="secondary" disabled={closing} onClick={finish}>{t("medical.clinical.leaveUnsaved")}</Button>
        </div>
      </div>
    </Modal>
  </div>;
}

function Observation({ row, scope, onDenied }: { row: ToothObservation; scope: ClinicalReadScope; onDenied: Denied }) {
  const { t, language } = useI18n();
  const [history, setHistory] = useState<ToothHistory | null>(null);
  const [selectedId, setSelectedId] = useState(row.history_id);
  const [error, setError] = useState<unknown>(null);
  const [cursor, setCursor] = useState<number | undefined>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setHistory(null); setError(null);
    medicalToothApi.history({ ...scope, tooth_state_id: row.tooth_state_id, before_revision: cursor }, controller.signal)
      .then(data => { if (!controller.signal.aborted) setHistory(data); })
      .catch(cause => { if (!controller.signal.aborted) { if (denied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [scope, row.tooth_state_id, cursor, attempt, onDenied]);
  return <section className="space-y-3 border-t border-platforma-border pt-3">
    <h3 className="font-medium">{row.surface || t("medical.tooth.whole")}</h3>
    <ToothVersion key={selectedId} id={selectedId} scope={scope} onDenied={onDenied} />
    {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} /> : !history ? <LoadingState /> : <>
      <h4 className="text-sm font-medium">{t("medical.clinical.revisions")}</h4>
      <div className="flex flex-wrap gap-2">{history.versions.map(item => <Button key={item.history_id} size="lg" variant="secondary"
        aria-pressed={selectedId === item.history_id} onClick={() => setSelectedId(item.history_id)}>
        {item.revision} · {formatDateTime(item.observed_at, undefined, true, localeByLanguage[language])}
      </Button>)}</div>
      {cursor ? <Button size="lg" variant="secondary" onClick={() => setCursor(undefined)}>{t("medical.clinical.newest")}</Button> : null}
      {history.next_before_revision ? <Button size="lg" variant="secondary" onClick={() => setCursor(history.next_before_revision!)}>{t("medical.clinical.older")}</Button> : null}
    </>}
  </section>;
}

function ToothVersion({ id, scope, onDenied }: { id: number; scope: ClinicalReadScope; onDenied: Denied }) {
  const { t, language } = useI18n();
  const [version, setVersion] = useState<ToothObservation | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setVersion(null); setError(null);
    medicalToothApi.version(id, scope, controller.signal)
      .then(value => { if (!controller.signal.aborted) setVersion(value); })
      .catch(cause => { if (!controller.signal.aborted) { if (denied(cause)) onDenied(cause); else setError(cause); } });
    return () => controller.abort();
  }, [id, scope, onDenied, attempt]);
  if (error) return <ErrorState message={getApiErrorMessage(error)} action={<Button size="lg" variant="secondary" onClick={() => setAttempt(x => x + 1)}>{t("common.retry")}</Button>} />;
  if (!version) return <LoadingState />;
  return <div className="space-y-2" data-testid="tooth-version">
    <p className="whitespace-pre-wrap break-words text-sm">{version.observation}</p>
    <p className="break-words text-sm text-platforma-subtle">{version.author_name} · {formatDateTime(version.observed_at, undefined, true, localeByLanguage[language])}</p>
    {version.reason ? <p className="whitespace-pre-wrap break-words text-sm">{version.reason}</p> : null}
  </div>;
}
