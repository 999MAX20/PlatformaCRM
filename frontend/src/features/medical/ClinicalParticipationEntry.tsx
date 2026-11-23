import { useCallback, useEffect, useId, useImperativeHandle, useMemo, useRef, useState, type Ref } from "react";
import { Tabs } from "../../components/ui/Tabs";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import type { ClinicalEntryHandle } from "./ClinicalAppointmentEntry";
import { ParticipationClinicalOverview } from "./ClinicalOverview";
import { ParticipationClinicalHistory } from "./ClinicalHistory";
import { ParticipationToothChart } from "./ToothChart";
import { ClinicalViewNavigationProvider } from "./clinicalViewNavigation";
import type { HistoryMemory } from "./clinicalHistoryNavigation";
import { MedicalFilesWorkspace, type MedicalFilesNavigation, type MedicalFilesState } from "./files/MedicalFilesWorkspace";

type Tab = "overview" | "history" | "teeth" | "files";

export function ClinicalParticipationEntry({ businessId, patientId, participationId, navigationRef, onDirtyChange, onDenied }: {
  businessId: number; patientId: number; participationId: number; navigationRef: Ref<ClinicalEntryHandle>;
  onDirtyChange?: (dirty: boolean) => void; onDenied: (cause: unknown) => void;
}) {
  const { t } = useI18n();
  const prefix = useId();
  const [tab, setTab] = useState<Tab>("overview");
  const [fileState, setFileState] = useState<MedicalFilesState>({ dirty: false, pending: false });
  const guard = useRef(fileState);
  const [fileReset, setFileReset] = useState(0);
  const files = useRef<MedicalFilesNavigation>(null);
  const history: HistoryMemory = useRef(new Map());
  const scope = useMemo(() => ({ business_id: businessId, patient_id: patientId, participation_id: participationId }),
    [businessId, patientId, participationId]);
  const changed = useCallback((state: MedicalFilesState) => { guard.current = state; setFileState(state); }, []);
  const beforeLeave = useCallback(() => !guard.current.pending && (!guard.current.dirty || window.confirm(t("medical.clinical.discard"))), [t]);
  useImperativeHandle(navigationRef, () => ({ beforeLeave: async () => beforeLeave() }), [beforeLeave]);
  useUnsavedEntryWarning(fileState.dirty || fileState.pending);
  useEffect(() => { onDirtyChange?.(fileState.dirty || fileState.pending); }, [fileState, onDirtyChange]);
  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);
  function navigate(next: Tab) {
    if (next === tab || !beforeLeave()) return;
    if (guard.current.dirty) setFileReset(value => value + 1);
    setTab(next);
  }
  const props = { businessId, patientId, participationId, onDenied };
  return <ClinicalViewNavigationProvider><section className="min-w-0 space-y-4" data-testid="participation-card">
    <Tabs value={tab} onChange={navigate} idPrefix={prefix} ariaLabel={t("medical.clinical.title")}
      appearance="underline" className="[&_[role=tab]]:min-h-11" options={[
        { value: "overview", label: t("medical.overview.title") }, { value: "history", label: t("medical.clinical.history") },
        { value: "teeth", label: t("medical.tooth.title") }, { value: "files", label: t("medical.files.title") },
      ]} />
    <div role="tabpanel" id={`${prefix}-panel-overview`} aria-labelledby={`${prefix}-tab-overview`} hidden={tab !== "overview"}>
      {tab === "overview" ? <ParticipationClinicalOverview {...props} onHistory={() => {
        navigate("history"); requestAnimationFrame(() => document.getElementById(`${prefix}-tab-history`)?.focus());
      }} /> : null}
    </div>
    <div role="tabpanel" id={`${prefix}-panel-history`} aria-labelledby={`${prefix}-tab-history`} hidden={tab !== "history"}>
      {tab === "history" ? <ParticipationClinicalHistory {...props} memory={history} /> : null}
    </div>
    <div role="tabpanel" id={`${prefix}-panel-teeth`} aria-labelledby={`${prefix}-tab-teeth`} hidden={tab !== "teeth"}>
      {tab === "teeth" ? <ParticipationToothChart {...props} onFiles={tooth => {
        if (files.current?.openTooth(tooth)) { setTab("files"); requestAnimationFrame(() => document.getElementById(`${prefix}-tab-files`)?.focus()); }
      }} /> : null}
    </div>
    <div role="tabpanel" id={`${prefix}-panel-files`} aria-labelledby={`${prefix}-tab-files`} hidden={tab !== "files"}>
      <MedicalFilesWorkspace key={fileReset} scope={scope} active={tab === "files"} onState={changed} onDenied={onDenied} navigationRef={files} />
    </div>
  </section></ClinicalViewNavigationProvider>;
}
