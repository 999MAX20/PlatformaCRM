import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { agentProfilesApi } from "../../../api/ai";
import { getApiErrorMessage } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { ToggleSwitch } from "../../../components/ui/Switch";
import { useI18n } from "../../../lib/i18n";
import type { AgentProfile, Id } from "../../../types";

const sources = ["clients", "leads", "deals", "tasks", "appointments", "knowledge"];
const tools = ["summarize_conversation", "qualify_lead", "create_lead", "create_task", "crm_read", "crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"];

export function InternalAgentSettings({ businessId, profiles, canManage }: { businessId: Id; profiles: AgentProfile[]; canManage: boolean }) {
  const { t } = useI18n();
  return <div className="mx-auto mb-4 w-full max-w-[960px] space-y-2">
    {(["employee", "analyst"] as const).map(scenario => {
      const profile = profiles.filter(item => item.business === businessId && item.bot === null && item.rules_json.scenario === scenario).sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];
      return <details key={scenario} className="rounded-control border border-platforma-border bg-surface-card px-4">
        <summary className="platforma-focus-ring cursor-pointer py-3 text-sm font-semibold">{t(`aiWorkflow.${scenario}`)}</summary>
        <ScenarioForm key={`${businessId}-${scenario}-${profile?.updated_at || "new"}`} {...{ businessId, scenario, profile, canManage }} />
      </details>;
    })}
  </div>;
}

function ScenarioForm({ businessId, scenario, profile, canManage }: { businessId: Id; scenario: "employee" | "analyst"; profile?: AgentProfile; canManage: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(profile?.is_active ?? true);
  const [language, setLanguage] = useState(profile?.language || "ru");
  const [tone, setTone] = useState(profile?.tone || "expert");
  const [instructions, setInstructions] = useState(profile?.system_prompt || "");
  const [selectedSources, setSources] = useState<string[]>((profile?.rules_json.sources as string[]) || sources);
  const [selectedTools, setTools] = useState<string[]>((profile?.allowed_tools_json.tools as string[]) || (scenario === "employee" ? tools : []));
  const [saved, setSaved] = useState(false);
  const save = useMutation({
    mutationFn: () => {
      const payload = { business: businessId, bot: null, name: t(`aiWorkflow.${scenario}`), is_active: enabled, language, tone,
        system_prompt: instructions, rules_json: { scenario, sources: scenario === "analyst" ? sources : selectedSources },
        allowed_tools_json: { tools: scenario === "analyst" ? [] : selectedTools } };
      return profile ? agentProfilesApi.update({ id: profile.id, payload }) : agentProfilesApi.create(payload);
    },
    onSuccess: async () => { setSaved(true); await queryClient.invalidateQueries({ queryKey: ["ai-agent-profiles"] }); },
  });
  const toggle = (values: string[], value: string, on: boolean) => on ? [...new Set([...values, value])] : values.filter(item => item !== value);
  return <form className="space-y-4 pb-4" onChange={() => setSaved(false)} onSubmit={event => { event.preventDefault(); save.mutate(); }}>
    <p className="text-sm text-platforma-subtle">{t(`aiWorkflow.${scenario}Scope`)}</p>
    <div className="flex items-center justify-between gap-4"><span>{t("aiWorkflow.enabled")}</span><ToggleSwitch checked={enabled} onChange={setEnabled} disabled={!canManage || save.isPending} label={t("aiWorkflow.enabled")} /></div>
    <div className="grid gap-3 sm:grid-cols-2">
      <Select label={t("common.language")} value={language} disabled={!canManage || save.isPending} onChange={event => setLanguage(event.target.value)} options={[{ value: "ru", label: "Русский" }, { value: "kk", label: "Қазақша" }, { value: "en", label: "English" }]} />
      <Select label={t("aiWorkflow.tone")} value={tone} disabled={!canManage || save.isPending} onChange={event => setTone(event.target.value as AgentProfile["tone"])} options={["friendly", "expert", "formal", "sales", "support"].map(value => ({ value, label: t(`aiAgents.tone.${value}`) }))} />
    </div>
    <Textarea label={t("aiWorkflow.instructions")} value={instructions} disabled={!canManage || save.isPending} onChange={event => setInstructions(event.target.value)} />
    {scenario === "employee" && <>
      <fieldset className="grid gap-2 sm:grid-cols-2"><legend className="mb-2 text-sm font-semibold">{t("aiWorkflow.sources")}</legend>
        {sources.map(source => <label key={source} className="flex min-h-9 items-center gap-2 text-sm"><input type="checkbox" checked={selectedSources.includes(source)} disabled={!canManage || save.isPending} onChange={event => setSources(toggle(selectedSources, source, event.target.checked))} />{t(`aiWorkflow.source.${source}`)}</label>)}
      </fieldset>
      <fieldset className="grid gap-2 sm:grid-cols-2"><legend className="mb-2 text-sm font-semibold">{t("aiWorkflow.actions")}</legend>
        {tools.map(tool => <label key={tool} className="flex min-h-9 items-center gap-2 text-sm"><input type="checkbox" checked={selectedTools.includes(tool)} disabled={!canManage || save.isPending} onChange={event => setTools(toggle(selectedTools, tool, event.target.checked))} />{t(`aiWorkflow.tool.${tool}`)}</label>)}
      </fieldset>
    </>}
    {save.error && <p role="alert" className="text-sm text-platforma-danger">{getApiErrorMessage(save.error)}</p>}
    <div className="flex flex-wrap items-center gap-3"><Button type="submit" disabled={!canManage} isLoading={save.isPending}>{t("common.save")}</Button><Link className="platforma-focus-ring text-sm underline" to="/app/ai-assistant">{t("aiWorkflow.open")}</Link>{saved && <span role="status">{t("common.saved")}</span>}</div>
  </form>;
}
