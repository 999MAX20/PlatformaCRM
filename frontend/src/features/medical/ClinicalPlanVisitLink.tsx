import { useEffect, useLayoutEffect, useRef, useState } from "react";
import axios from "axios";
import { medicalClinicalApi, type ClinicalPlanAccess, type ClinicalVisitStep } from "../../api/medicalClinical";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export function ClinicalVisitStepLabel({ step }: { step: ClinicalVisitStep }) {
  const { t } = useI18n();
  return <p className="break-words text-sm">{t("medical.plan.visitStep", {
    service: step.service_name, position: step.position, plan: step.plan_id,
  })}</p>;
}

export function ClinicalPlanVisitLink({ value, access, onChange, disabled, readOnly }: {
  value?: ClinicalVisitStep; access?: ClinicalPlanAccess; onChange: (value?: ClinicalVisitStep) => void;
  disabled: boolean; readOnly: boolean;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState<number | undefined>();
  const [attempt, setAttempt] = useState(0);
  const [data, setData] = useState<{ results: ClinicalVisitStep[]; next_before_id: number | null } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState("");
  const toggle = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  useLayoutEffect(() => {
    if (wasOpen.current && !open) toggle.current?.focus();
    wasOpen.current = open;
  }, [open]);
  const scopeKey = access ? JSON.stringify(access.scope) : "";
  useEffect(() => {
    if (!open || !access) return;
    const controller = new AbortController();
    setData(null); setError(null);
    void medicalClinicalApi.visitSteps({ ...access.scope, before_id: cursor }, controller.signal).then(result => {
      if (!controller.signal.aborted) setData(result);
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (axios.isAxiosError(cause) && [401, 403].includes(cause.response?.status ?? 0)) access.onDenied(cause);
      else setError(cause);
    });
    return () => controller.abort();
  }, [open, scopeKey, cursor, attempt]);
  const chosen = data?.results.find(item => String(item.id) === selected);
  return <div className="space-y-2" data-testid="clinical-visit-link">
    {value ? <ClinicalVisitStepLabel step={value} /> : null}
    {!readOnly && access ? <>
      <div className="flex flex-wrap gap-2">
        <Button ref={toggle} type="button" size="lg" variant="secondary" disabled={disabled} onClick={() => {
          setOpen(current => !current); setCursor(undefined); setSelected("");
        }}>{t(open ? "common.cancel" : value ? "medical.plan.changeVisit" : "medical.plan.linkVisit")}</Button>
        {value ? <Button type="button" size="lg" variant="ghost" disabled={disabled} onClick={() => {
          if (window.confirm(t("medical.plan.confirmUnlink"))) { onChange(undefined); setOpen(false); }
        }}>{t("medical.plan.unlinkVisit")}</Button> : null}
      </div>
      {open ? <div className="space-y-3 border-l-2 border-platforma-border pl-3">
        {error ? <ErrorState message={getApiErrorMessage(error)} action={<Button type="button" size="lg" variant="secondary"
          disabled={disabled} onClick={() => setAttempt(value => value + 1)}>{t("common.retry")}</Button>} /> : !data ? <LoadingState /> : <>
          {!data.results.length ? <p className="text-sm text-platforma-subtle">{t("medical.plan.noVisitSteps")}</p> : <>
            <Select portal label={t("medical.plan.selectVisit")} value={selected} disabled={disabled}
              onChange={event => setSelected(event.target.value)} options={[
                { value: "", label: t("medical.plan.selectVisit") }, ...data.results.map(item => ({ value: item.id,
                  label: t("medical.plan.visitStep", { service: item.service_name, position: item.position, plan: item.plan_id }) })),
              ]} />
            <Button type="button" size="lg" variant="secondary" disabled={disabled || !chosen} onClick={() => {
              if (chosen) { onChange(chosen); setOpen(false); }
            }}>{t("medical.plan.applyVisit")}</Button>
          </>}
          <div className="flex flex-wrap gap-2">
            {cursor ? <Button type="button" size="lg" variant="ghost" disabled={disabled} onClick={() => {
              setCursor(undefined); setSelected("");
            }}>{t("medical.clinical.newest")}</Button> : null}
            {data.next_before_id ? <Button type="button" size="lg" variant="ghost" disabled={disabled} onClick={() => {
              setCursor(data.next_before_id!); setSelected("");
            }}>{t("medical.clinical.older")}</Button> : null}
          </div>
        </>}
      </div> : null}
    </> : null}
  </div>;
}
