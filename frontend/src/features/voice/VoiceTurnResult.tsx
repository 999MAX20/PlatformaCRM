import { Link } from "react-router";
import type { AgentTurn } from "../../api/aiConversations";
import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";
import { formatDateTime } from "../../lib/format";

const paths: Record<string, [string, string]> = { clients: ["clients", "client"], tasks: ["tasks", "task"], appointments: ["calendar", "appointment"] };
const object = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const printable = (value: unknown) => value == null || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);

export function VoiceTurnResult({ turn, busy, canExecute, onAction, readOnly = false }: {
  turn: AgentTurn; busy: boolean; canExecute: boolean; onAction: (kind: "confirm" | "cancel" | "retry") => void; readOnly?: boolean;
}) {
  const { t, language } = useI18n();
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";
  const visitLabel = (record: Record<string, unknown>) => [record.service_name, record.resource_name, record.branch_name,
    typeof record.start_at === "string" ? formatDateTime(record.start_at, undefined, true, locale) : null].filter(Boolean).join(" · ");
  const fieldValue = (field: string, value: unknown) => field === "start_at" && typeof value === "string"
    ? formatDateTime(value, undefined, true, locale) : printable(value);
  if (turn.redacted) return <p role="status" className="text-sm text-platforma-subtle">{t("agentChat.redacted")}</p>;
  const pending = turn.status === "awaiting_confirmation";
  const identityReview = pending && turn.actions.some(action => action.tool_name === "crm_create" && action.input_json.entity === "clients"
    || action.tool_name === "crm_schedule" && !object(object(action.input_json.values).client).id);
  const taskReview = pending && turn.actions.some(action => action.tool_name === "crm_create" && action.input_json.entity === "tasks");
  const processing = ["preparing", "executing"].includes(turn.status);
  return <div className="space-y-3 text-sm" aria-live="polite">
    <p role="status" className="whitespace-pre-wrap break-words leading-6">{processing ? t(`agentChat.status.${turn.status}`)
      : pending ? t(identityReview ? "voice.reviewIdentity" : taskReview ? "voice.reviewTask" : "voice.review") : turn.status === "completed" && turn.actions.length ? t("voice.completed") : turn.response}</p>
    {turn.actions.map(action => {
      const fields = object(action.input_json.values); const before = object(action.input_json.before);
      const record = object(action.output_json.record); const entity = String(action.output_json.entity || action.input_json.entity || "");
      const target = action.output_json.entity_id || action.input_json.entity_id; const route = paths[entity];
      if (action.tool_name === "crm_schedule") {
        const rows = Array.isArray(action.output_json.records) ? action.output_json.records.map(object) : [];
        const preview = object(action.input_json.preview);
        return <section key={action.id} className="space-y-3 border-l-2 border-platforma-border pl-3" aria-label={t("voice.results")}>
          <p className="font-medium">{t(fields.plan ? "voice.planCreated" : "voice.booking")}</p>
          {action.status === "executed" ? <ul className="space-y-3">{rows.map(row => {
            const record = object(row.record); const path = paths[String(row.entity)]; const id = row.entity_id;
            if (!path || typeof id !== "number") return null;
            return <li key={`${row.entity}:${id}`} className="space-y-1">
              <p className="text-xs text-platforma-subtle">{t(row.entity === "appointments" ? "aiCRM.field.appointment" : "aiCRM.field.client")} · {t(row.created ? "voice.created" : "voice.existing")}</p>
              <Link className="platforma-focus-ring block break-words underline underline-offset-4" to={`/app/${path[0]}?${path[1]}=${id}`}>
                {String(record.full_name || visitLabel(record) || `#${id}`)}</Link>
            </li>;
          })}</ul> : <><dl className="space-y-1">
            <div className="flex flex-wrap gap-x-2"><dt className="text-platforma-subtle">{t("aiCRM.field.full_name")}:</dt><dd className="min-w-0 break-words">{String(preview.client_name || "")}</dd></div>
            {!object(fields.client).id && <div className="flex flex-wrap gap-x-2"><dt className="text-platforma-subtle">{t("aiCRM.field.phone")}:</dt><dd className="min-w-0 break-words">{printable(object(fields.client).phone)}</dd></div>}
          </dl>
            <ul className="space-y-2">{(Array.isArray(preview.visits) ? preview.visits : []).map((visit, index) => <li key={index}>{visitLabel(object(visit))}</li>)}</ul></>}
          {typeof action.output_json.visit_plan_id === "number" && <Link className="platforma-focus-ring inline-flex min-h-9 items-center underline underline-offset-4"
            to={`/app/appointments?view=plans&plan=${action.output_json.visit_plan_id}`}>{t("plans.plan")} #{action.output_json.visit_plan_id}</Link>}
        </section>;
      }
      return <section key={action.id} className="space-y-2 border-l-2 border-platforma-border pl-3" aria-label={t("aiCRM.review")}>
        <p className="font-medium">{t(`aiWorkflow.tool.${action.tool_name}`)} · {t(`aiWorkflow.source.${entity}`)}</p>
        {pending && action.tool_name === "crm_transition" && entity === "appointments" && <p className="break-words">
          {String(object(action.input_json.preview).client_name || "")} · {visitLabel(object(action.input_json.preview))}
          {typeof target === "number" && <Link className="platforma-focus-ring ml-2 underline" to={`/app/calendar?appointment=${target}`}>#{target}</Link>}
        </p>}
        {action.status === "executed" && route && typeof target === "number" ? <Link className="platforma-focus-ring break-words underline"
          to={`/app/${route[0]}?${route[1]}=${target}`}>{String(record.full_name || record.title || record.message || `#${target}`)}</Link>
          : <dl className="space-y-1">{Object.entries(fields).map(([field, value]) => <div key={field} className="flex flex-wrap gap-x-2">
            <dt className="text-platforma-subtle">{t(`aiCRM.field.${field}`)}:</dt><dd className="min-w-0 break-words">{field in before ? `${fieldValue(field, before[field])} → ` : ""}{fieldValue(field, value)}</dd>
          </div>)}</dl>}
        {action.tool_name === "crm_transition" && action.input_json.action ? <p>{t(`aiCRM.action.${String(action.input_json.action)}`)}</p> : null}
        {action.input_json.reason ? <p className="break-words">{printable(action.input_json.reason)}</p> : null}
      </section>;
    })}
    {turn.sources.length > 0 && <details><summary className="platforma-focus-ring cursor-pointer text-xs text-platforma-subtle">{t("aiScenario.sources")}</summary>
      <ul className="mt-2 space-y-1 text-xs">{turn.sources.map(source => <li key={source.id}>{source.label}</li>)}</ul></details>}
    {turn.status === "failed" && <p role="alert" className="text-platforma-danger">{t(["voice_action_unavailable", "voice_one_operation"].includes(turn.error_code) ? `voice.error.${turn.error_code}` : turn.error_code === "access_changed" ? "agentChat.accessDenied" : "agentChat.failedText")}</p>}
    {!readOnly && (pending || processing || turn.status === "failed") && <div className="flex flex-wrap gap-2">
      {pending && <><Button disabled={busy || !canExecute || !turn.actions.some(action => action.status === "suggested")} onClick={() => onAction("confirm")}>{t("agentChat.confirm")}</Button>
        <Button variant="ghost" disabled={busy} onClick={() => onAction("cancel")}>{t("aiCRM.discard")}</Button></>}
      {processing && <Button variant="ghost" disabled={busy} onClick={() => onAction("cancel")}>{t("agentChat.stop")}</Button>}
      {turn.status === "failed" && turn.error_code !== "access_changed" && <Button variant="secondary" disabled={busy} onClick={() => onAction("retry")}>{t("agentChat.retryRemaining")}</Button>}
    </div>}
  </div>;
}
