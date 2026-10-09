import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import type { QuickReplyTemplate } from "../../../types";
import { SettingsDrawer, SettingsFeedback, SettingsSaveBar, SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import type { SettingsModel } from "../useSettingsModel";

export function QuickRepliesSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, quickReplies, quickReplyMutation, updateQuickReplyMutation, removeQuickReplyMutation, quickReplyForm, setQuickReplyForm, quickReplyChannelOptions, editingQuickReplyId, quickReplyEditForm, setQuickReplyEditForm, setEditingQuickReplyId, startEditingQuickReply, confirmDelete } = model;
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");
  const editing = editingQuickReplyId !== null;
  const value = editing ? quickReplyEditForm : quickReplyForm;
  const mutation = editing ? updateQuickReplyMutation : quickReplyMutation;
  const errors = getApiFieldErrors(mutation.error);
  const hasFieldErrors = ["title", "text", "category", "channel", "is_active"].some(key => errors[key]?.length);
  const pending = quickReplyMutation.isPending || updateQuickReplyMutation.isPending || removeQuickReplyMutation.isPending;
  function change(patch: Partial<typeof quickReplyEditForm>) {
    if (editing) setQuickReplyEditForm(current => ({ ...current, ...patch }));
    else setQuickReplyForm(current => ({ ...current, ...patch }));
    mutation.reset();
  }
  function close() { if (!pending) { setCreating(false); setEditingQuickReplyId(null); } }
  const rows = (quickReplies.data || []).filter(row => (row.title + " " + row.category + " " + row.text).toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  return <SettingsSection id="quick-replies" active={activeSettingsSection} title={t("settings.section.quick-replies")}
    actions={<Button type="button" disabled={pending} onClick={() => { setEditingQuickReplyId(null); quickReplyMutation.reset(); setCreating(true); }}><Plus size={16} />{t("settings.redesign.newReply")}</Button>}>
    <div className="space-y-4 p-4 sm:p-5">
      <Input label={t("common.search")} value={search} leftIcon={<Search size={16} />} onChange={event => setSearch(event.target.value)} />
      <SettingsQueryState queries={[quickReplies]} />
      {quickReplies.isSuccess && <div className="divide-y divide-platforma-border">
        {rows.map(row => <div key={row.id} className="space-y-3 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1"><p className="text-sm font-bold">{row.title}</p><p className="mt-1 text-xs text-platforma-subtle">{quickReplyChannelOptions.find(option => option.value === row.channel)?.label || row.channel}{row.category ? " · " + row.category : ""} · {t(row.is_active ? "settings.active" : "settings.inactive")}</p><p className="mt-2 line-clamp-2 whitespace-pre-wrap text-sm leading-6 text-platforma-subtle">{row.text}</p></div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" disabled={pending} onClick={() => { setCreating(false); updateQuickReplyMutation.reset(); startEditingQuickReply(row); }}>{t("settings.edit")}</Button>
              <Button type="button" variant={row.is_active ? "warning" : "secondary"} disabled={pending}
                onClick={() => updateQuickReplyMutation.mutate({ id: Number(row.id), payload: { is_active: !row.is_active } })}>{t(row.is_active ? "settings.disable" : "settings.enable")}</Button>
              <Button type="button" variant="danger" disabled={pending} onClick={async () => { if (await confirmDelete(row.title)) removeQuickReplyMutation.mutate(Number(row.id)); }}>{t("settings.delete")}</Button>
            </div>
          </div>
          {!editing && updateQuickReplyMutation.variables?.id === Number(row.id) && <SettingsFeedback error={updateQuickReplyMutation.error} saved={updateQuickReplyMutation.isSuccess} />}
          {removeQuickReplyMutation.variables === Number(row.id) && <SettingsFeedback error={removeQuickReplyMutation.error} />}
        </div>)}
        {!rows.length && <p className="py-8 text-center text-sm text-platforma-subtle">{t(search.trim() ? "settings.redesign.noMatches" : "settings.noQuickReplies")}</p>}
      </div>}
    </div>
    <SettingsDrawer open={(creating || editing) && activeSettingsSection === "quick-replies"} onClose={close} title={t(editing ? "settings.edit" : "settings.redesign.newReply")}
      footer={<SettingsSaveBar drawer feedback={<SettingsFeedback error={!hasFieldErrors ? mutation.error : undefined} />}>
        <Button type="button" variant="secondary" disabled={pending} onClick={close}>{t("common.cancel")}</Button>
        <Button type="submit" form="settings-quick-reply-form" isLoading={mutation.isPending} disabled={pending}>{t(editing ? "common.save" : "settings.add")}</Button>
      </SettingsSaveBar>}>
      <form id="settings-quick-reply-form" onSubmit={event => {
        event.preventDefault();
        const onError = () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-quick-reply-form [aria-invalid="true"]')?.focus());
        if (editing && editingQuickReplyId !== null) updateQuickReplyMutation.mutate({ id: editingQuickReplyId, payload: quickReplyEditForm }, { onError });
        else quickReplyMutation.mutate(undefined, { onSuccess: () => setCreating(false), onError });
      }}>
        <fieldset disabled={pending} className="space-y-4">
          <Input label={t("settings.templateTitle")} required value={value.title} error={errors.title?.join(" ")} onChange={event => change({ title: event.target.value })} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label={t("settings.channel")} value={value.channel} error={errors.channel?.join(" ")} onChange={event => change({ channel: event.target.value as QuickReplyTemplate["channel"] })} options={quickReplyChannelOptions.filter(option => option.value !== "manual" || value.channel === "manual")} />
            <Input label={t("settings.category")} value={value.category} error={errors.category?.join(" ")} onChange={event => change({ category: event.target.value })} />
          </div>
          <Textarea label={t("settings.templateText")} rows={9} required value={value.text} error={errors.text?.join(" ")} onChange={event => change({ text: event.target.value })} />
          {editing && <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" className="h-5 w-5 accent-brand-500" checked={quickReplyEditForm.is_active} onChange={event => change({ is_active: event.target.checked })} />{t("settings.active")}</label>}
          {errors.is_active && <p role="alert" className="text-sm text-platforma-danger">{errors.is_active.join(" ")}</p>}
        </fieldset>
      </form>
    </SettingsDrawer>
  </SettingsSection>;
}
