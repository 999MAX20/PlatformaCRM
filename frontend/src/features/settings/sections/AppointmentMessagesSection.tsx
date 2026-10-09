import { CalendarCheck2, CalendarClock, MessageSquare } from "lucide-react";
import { useRef, useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Switch } from "../../../components/ui/Switch";
import { Textarea } from "../../../components/ui/Textarea";
import type { AppointmentMessageSetting } from "../../../types";
import { SettingsFeedback, SettingsSaveBar, SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { appointmentChannelOptions, appointmentScenarioLabels } from "../settingsConfig";
import type { SettingsModel } from "../useSettingsModel";

const variableNames = ["client_name", "service_name", "date", "time", "business_name", "address_text"] as const;
const scenarioIcons = { confirmation: CalendarCheck2, reminder: CalendarClock, thank_you: MessageSquare };

export function AppointmentMessagesSection({ model }: { model: SettingsModel; }) {
  const { t, business, activeSettingsSection, appointmentMessageSettings, appointmentMessages, appointmentMessageValue, appointmentMessageDrafts, setAppointmentMessageDrafts, appointmentMessageMutation } = model;
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const setting = appointmentMessages.find(item => Number(item.id) === selectedId) || appointmentMessages[0];
  const id = Number(setting?.id);
  const meta = setting ? appointmentScenarioLabels[setting.scenario] : undefined;
  const currentMutation = appointmentMessageMutation.variables?.id === id;
  const error = currentMutation ? appointmentMessageMutation.error : null;
  const fieldErrors = getApiFieldErrors(error);
  const enabled = setting ? Boolean(appointmentMessageValue(setting, "is_enabled")) : false;
  const draft = appointmentMessageDrafts[id];
  const text = setting ? String(appointmentMessageValue(setting, "template_text")) : "";
  const channel = setting ? String(appointmentMessageValue(setting, "channel_policy")) : "";
  const available = setting?.available_channels || ["auto", "system"];
  const choices = appointmentChannelOptions.filter(option => available.includes(option.value) || option.value === channel).map(option => ({
    value: option.value, label: available.includes(option.value) ? t(option.labelKey) : t("settings.appointmentMessages.unavailableChannel", { channel: t(option.labelKey) }),
  }));
  if (channel && !choices.some(option => option.value === channel)) choices.push({ value: channel, label: t("settings.appointmentMessages.unavailableChannel", { channel: channel === "sms" ? "SMS" : channel }) });
  function update(values: Partial<AppointmentMessageSetting>) {
    setAppointmentMessageDrafts(current => ({ ...current, [id]: { ...current[id], ...values } }));
    if (currentMutation && !appointmentMessageMutation.isPending) appointmentMessageMutation.reset();
  }
  function insertVariable(name: string) {
    const start = textarea.current?.selectionStart ?? text.length;
    const end = textarea.current?.selectionEnd ?? start;
    const token = "{" + name + "}";
    update({ template_text: text.slice(0, start) + token + text.slice(end) });
    window.requestAnimationFrame(() => { textarea.current?.focus(); textarea.current?.setSelectionRange(start + token.length, start + token.length); });
  }
  const preview = text.split(/(\{[^{}]+\})/g).map((part, index) => {
    if (!part.startsWith("{") || !part.endsWith("}")) return part;
    const name = part.slice(1, -1);
    if (name === "business_name") return business?.name || part;
    if (name === "address") return business?.address || part;
    const label = name === "resource_text" || name === "resource_name" ? t("appointment.resource")
      : variableNames.includes(name as typeof variableNames[number]) ? t(`settings.redesign.variable.${name}`) : part;
    return <span key={index} className="rounded bg-brand-50 px-1 py-0.5 text-brand-700">{label}</span>;
  });
  const hasFieldError = ["offset_minutes", "channel_policy", "template_text", "is_enabled"].some(key => fieldErrors[key]?.length);
  return <SettingsSection id="appointment-messages" active={activeSettingsSection} title={t("settings.section.appointment-messages")}>
    {!appointmentMessageSettings.isSuccess && <div className="p-4 sm:p-5"><SettingsQueryState queries={[appointmentMessageSettings]} /></div>}
    {appointmentMessageSettings.isSuccess && !appointmentMessages.length && <p className="px-5 pb-8 text-sm text-platforma-subtle">{t("settings.redesign.noScenarios")}</p>}
    {setting && meta && !appointmentMessageSettings.isError && <div>
      <div className="grid min-w-0 gap-5 p-4 sm:p-5 xl:grid-cols-[200px_minmax(0,1fr)]">
        <nav aria-label={t("settings.appointmentMessagesTitle")} className="flex flex-wrap gap-2 xl:block xl:space-y-2 xl:border-r xl:border-platforma-border xl:pr-4">
          {appointmentMessages.map(item => {
            const Icon = scenarioIcons[item.scenario];
            const active = Number(item.id) === id;
            return <button key={item.id} type="button" aria-pressed={active} disabled={appointmentMessageMutation.isPending}
              onClick={() => setSelectedId(Number(item.id))}
              className={"platforma-focus-ring flex min-h-14 items-center gap-3 rounded-control p-3 text-left text-sm xl:w-full " + (active ? "bg-brand-50 text-brand-700" : "text-platforma-subtle hover:bg-surface-hover")}>
              <Icon aria-hidden="true" size={18} className="shrink-0" />
              <span><span className="block font-semibold">{t(appointmentScenarioLabels[item.scenario].titleKey)}</span><span className="mt-1 block text-xs">{t(item.is_enabled ? "settings.enabled" : "settings.paused")}{appointmentMessageDrafts[Number(item.id)] ? " · " + t("settings.redesign.unsaved") : ""}</span></span>
            </button>;
          })}
        </nav>
        <div className="min-w-0">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-base font-bold">{t(meta.titleKey)}</h2>
            <div className="flex min-h-11 items-center gap-3"><span className="text-sm text-platforma-subtle">{t(enabled ? "settings.enabled" : "settings.paused")}</span><Switch checked={enabled} label={t(meta.titleKey)} isLoading={appointmentMessageMutation.isPending}
              onChange={is_enabled => appointmentMessageMutation.mutate({ id, payload: { is_enabled } })} /></div>
          </div>
          {fieldErrors.is_enabled && <p role="alert" className="mb-3 text-sm text-platforma-danger">{fieldErrors.is_enabled.join(" ")}</p>}
          <div className="grid min-w-0 grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,1fr)_240px]">
            <form id="settings-message-form" className="min-w-0" onSubmit={event => {
              event.preventDefault(); if (draft) appointmentMessageMutation.mutate({ id, payload: draft }, { onError: () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-message-form [aria-invalid="true"]')?.focus()) });
            }}>
              <fieldset disabled={appointmentMessageMutation.isPending} className="min-w-0 space-y-4">
                <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
                  <Input label={t(setting.scenario === "thank_you" ? "settings.appointmentMessages.offsetAfter" : "settings.appointmentMessages.offsetBefore")}
                    type="number" min={setting.scenario === "thank_you" ? 0 : 1} max={43200} required step={1}
                    value={Math.abs(Number(appointmentMessageValue(setting, "offset_minutes")))} error={fieldErrors.offset_minutes?.join(" ")}
                    onChange={event => update({ offset_minutes: (setting.scenario === "thank_you" ? 1 : -1) * Math.abs(Number(event.target.value || 0)) })} />
                  <Select label={t("settings.appointmentMessages.deliveryChannel")} value={channel} options={choices} error={fieldErrors.channel_policy?.join(" ")}
                    onChange={event => update({ channel_policy: event.target.value as AppointmentMessageSetting["channel_policy"] })} />
                </div>
                <p className="text-xs leading-5 text-platforma-subtle">{t("settings.appointmentMessages.channelStatus")}</p>
                <Textarea ref={textarea} label={t("settings.appointmentMessages.templateText")} rows={7} value={text} error={fieldErrors.template_text?.join(" ")} onChange={event => update({ template_text: event.target.value })} />
                <div><p className="mb-2 text-xs text-platforma-subtle">{t("settings.redesign.insertVariable")}</p><div className="flex flex-wrap gap-2">{variableNames.map(name => <Button key={name} variant="secondary" size="sm" type="button" onClick={() => insertVariable(name)}>{t(`settings.redesign.variable.${name}`)}</Button>)}</div></div>
              </fieldset>
            </form>
            <aside className="min-w-0 space-y-3 border-t border-platforma-border pt-4 2xl:border-l 2xl:border-t-0 2xl:pl-4 2xl:pt-0">
              <h3 className="text-sm font-bold">{t("settings.redesign.preview")}</h3>
              <p className="whitespace-pre-wrap break-words rounded-card bg-surface-muted p-4 text-sm leading-6">{preview || "—"}</p>
              <p className="text-xs leading-5 text-platforma-subtle">{t("settings.redesign.templatePreviewNote")}</p>
            </aside>
          </div>
        </div>
      </div>
      <SettingsSaveBar feedback={error && !hasFieldError ? <SettingsFeedback error={error} /> : draft ? <p className="text-sm text-platforma-subtle">{t("settings.redesign.unsaved")}</p> : <SettingsFeedback saved={currentMutation && appointmentMessageMutation.isSuccess} />}>
        <Button variant="secondary" type="button" disabled={!draft || appointmentMessageMutation.isPending} onClick={() => { setAppointmentMessageDrafts(current => { const next = { ...current }; delete next[id]; return next; }); if (currentMutation) appointmentMessageMutation.reset(); }}>{t("common.cancel")}</Button>
        <Button type="submit" form="settings-message-form" disabled={!draft} isLoading={appointmentMessageMutation.isPending}>{t("settings.appointmentMessages.saveScenario")}</Button>
      </SettingsSaveBar>
    </div>}
  </SettingsSection>;
}
