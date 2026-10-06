import { CheckCircle2, CircleAlert, Bot, UserRound } from "lucide-react";
import { Link } from "react-router";
import type { AgentTurn } from "../../../api/aiConversations";
import { Button } from "../../../components/ui/Button";
import { useI18n } from "../../../lib/i18n";

const paths: Record<string, [string, string]> = { clients: ["clients", "client"], leads: ["leads", "lead"], deals: ["deals", "deal"], tasks: ["tasks", "task"], appointments: ["calendar", "appointment"] };
const printable = (value: unknown) => value === null || value === undefined || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);
const object = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

export function AgentTurnCard({ turn, busy, canExecute, isLatest, onConfirm, onCancel, onRetry }: {
  turn: AgentTurn; busy: boolean; canExecute: boolean; isLatest: boolean;
  onConfirm: () => void; onCancel: () => void; onRetry: () => void;
}) {
  const { t } = useI18n();
  if (turn.redacted) return <p role="status" className="rounded-xl border border-platforma-border p-4 text-sm text-platforma-subtle">{t("agentChat.redacted")}</p>;
  const pending = turn.status === "awaiting_confirmation";
  return <article className="space-y-3">
    <div className="ml-auto flex max-w-[95%] items-start gap-3 rounded-2xl bg-surface-muted p-4 sm:max-w-[85%]">
      <UserRound size={18} className="mt-0.5 shrink-0 text-platforma-subtle" aria-hidden="true" />
      <p className="min-w-0 whitespace-pre-wrap break-words text-sm leading-6">{turn.message}</p>
    </div>
    <div className="flex min-w-0 items-start gap-3">
      <Bot size={20} className="mt-1 shrink-0 text-ai-600" aria-hidden="true" />
      <div className="min-w-0 flex-1 space-y-3">
        {turn.response && <p className="whitespace-pre-wrap break-words text-sm leading-6">{turn.response}</p>}
        <div className="flex flex-wrap items-center gap-2 text-xs text-platforma-subtle" role="status">
          {turn.status === "completed" && <CheckCircle2 size={14} aria-hidden="true" />}
          {turn.status === "failed" && <CircleAlert size={14} aria-hidden="true" />}
          <span>{t(`agentChat.status.${turn.status}`)}</span>
          {turn.total_steps > 0 && <span>{t("agentChat.progress", { done: turn.completed_steps, total: turn.total_steps })}</span>}
          {turn.provider_state === "mock" && <span>{t("aiQuality.mock")}</span>}
        </div>
        {turn.actions.map(action => {
          const fields = object(action.input_json.values);
          const before = object(action.input_json.before);
          const record = object(action.output_json.record);
          const entity = String(action.output_json.entity || action.input_json.entity || "");
          const target = action.output_json.entity_id || action.input_json.entity_id;
          const route = paths[entity];
          return <section key={action.id} className="space-y-2 rounded-xl border border-platforma-border bg-surface-card p-3 sm:p-4" aria-label={t("aiCRM.review")}>
            <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold">{t(`aiWorkflow.tool.${action.tool_name}`)} · {t(`aiWorkflow.source.${entity}`)}</h3>
              {action.status === "executed" && <span className="text-xs text-platforma-success">{t("aiCRM.executed")}</span>}</div>
            {route && typeof target === "number" && <Link className="inline-block text-sm underline" to={`/app/${route[0]}?${route[1]}=${target}`}>{String(record.full_name || record.title || record.message || `#${target}`)}</Link>}
            {Object.keys(fields).length > 0 && <div className="overflow-x-auto" tabIndex={0}><table className="w-full text-left text-sm">
              <thead><tr><th className="p-2">{t("aiCRM.field")}</th><th className="p-2">{t("aiCRM.before")}</th><th className="p-2">{t("aiCRM.after")}</th></tr></thead>
              <tbody>{Object.entries(fields).map(([key, value]) => <tr key={key} className="border-t border-platforma-border"><th className="p-2 font-medium">{t(`aiCRM.field.${key}`)}</th><td className="max-w-64 break-words p-2">{printable(before[key])}</td><td className="max-w-64 break-words p-2">{printable(value)}</td></tr>)}</tbody>
            </table></div>}
            {action.input_json.action ? <p className="text-sm">{t(`aiCRM.action.${String(action.input_json.action)}`)}</p> : null}
            {action.input_json.reason ? <p className="break-words text-sm">{printable(action.input_json.reason)}</p> : null}
          </section>;
        })}
        {turn.sources.length > 0 && <details><summary className="cursor-pointer text-xs text-platforma-subtle">{t("aiScenario.sources")}</summary><ul className="mt-2 space-y-1 text-xs text-platforma-subtle">{turn.sources.map(source => <li key={source.id}>{source.label}</li>)}</ul></details>}
        {turn.status === "failed" && <p className="text-sm text-platforma-danger">{t("agentChat.failedText")}</p>}
        {isLatest && <div className="flex flex-wrap gap-2">
          {pending && <Button disabled={busy || !canExecute || !turn.actions.some(item => item.status === "suggested")} onClick={onConfirm}>{t("agentChat.confirm")}</Button>}
          {pending && <Button variant="secondary" disabled={busy} onClick={onCancel}>{t("aiCRM.discard")}</Button>}
          {turn.status === "failed" && <Button variant="secondary" disabled={busy} onClick={onRetry}>{t("agentChat.retryRemaining")}</Button>}
        </div>}
      </div>
    </div>
  </article>;
}
