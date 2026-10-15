import { useSearchParams } from "react-router";
import { Tabs } from "../../components/ui/Tabs";
import { useI18n } from "../../lib/i18n";
import { OperationsWorklist } from "./OperationsWorklist";
import { OperationsInfrastructure } from "./OperationsInfrastructure";

const sections = ["incidents", "connectors", "history", "infrastructure"] as const;
export function PlatformOperationsPage() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const section = sections.find(value => value === params.get("section")) || "incidents";
  function update(values: Record<string, string>) {
    setParams(current => { const next = new URLSearchParams(current); for (const [key, value] of Object.entries(values)) { if (value) next.set(key, value); else next.delete(key); } return next; }, { replace: true });
  }
  return <div className="space-y-4" data-testid="platform-operations-ready">
    <Tabs value={section} options={sections.map(value => ({ value, label: t(`operationsWorkspace.${value}`) }))} ariaLabel={t("platform.operations.title")} idPrefix="operations" appearance="underline"
      onChange={value => update({ section: value, page: "", component: "", freshness: "", date_from: "", date_to: "" })} />
    <section role="tabpanel" id={`operations-panel-${section}`} aria-labelledby={`operations-tab-${section}`}>
      {section === "infrastructure" ? <OperationsInfrastructure /> : <OperationsWorklist key={section} section={section} params={params} update={update} />}
    </section>
  </div>;
}
