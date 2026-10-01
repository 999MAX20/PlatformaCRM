import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { Archive, Trash2 } from "lucide-react";

import { Button } from "../../src/components/ui/Button";
import { Input } from "../../src/components/ui/Input";
import { Textarea } from "../../src/components/ui/Textarea";
import { Select } from "../../src/components/ui/Select";
import { Switch } from "../../src/components/ui/Switch";
import { Tabs } from "../../src/components/ui/Tabs";
import { WorkbenchMetric } from "../../src/components/layout/WorkbenchLayout";
import { Tooltip } from "../../src/features/conversations/components/ConversationPrimitives";
import { ActionMenu } from "../../src/components/ui/ActionMenu";
import { ConversationComposer } from "../../src/features/conversations/components/ConversationComposer";
import type { InboxConversation } from "../../src/api/inbox";
import {
  buttonVariantForActionTone,
  type ActionTone,
} from "../../src/components/ui/actionTone";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../../src/styles.css";

const roles: Array<{ tone: ActionTone; label: string; example: string }> = [
  { tone: "brand", label: "Brand", example: "Create" },
  { tone: "neutral", label: "Neutral", example: "Edit" },
  { tone: "warning", label: "Warning", example: "Archive" },
  { tone: "danger", label: "Danger", example: "Delete" },
  { tone: "ai", label: "AI", example: "Generate" },
];

function ActionColorRolesFixture() {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(false);
  const [tab, setTab] = useState("first");
  const [choice, setChoice] = useState("first");
  return (
    <main className="min-h-screen bg-platforma-page p-6 text-platforma-text sm:p-10">
      <section className="mx-auto max-w-4xl rounded-card border border-platforma-border bg-surface-card p-5 shadow-panel sm:p-8">
        <h1 className="text-2xl font-bold text-platforma-ink">Action color roles</h1>
        <p className="mt-2 text-sm text-platforma-subtle">Semantic role matrix for default, focus, hover, pressed and disabled verification.</p>
        <div className="mt-6 grid gap-3" data-testid="action-color-matrix">
          {roles.map((role) => (
            <div key={role.tone} className="grid gap-3 rounded-card border border-platforma-border bg-surface-warm p-4 sm:grid-cols-[120px_1fr_1fr] sm:items-center">
              <strong>{role.label}</strong>
              <Button data-testid={`tone-${role.tone}`} variant={buttonVariantForActionTone(role.tone)}>
                {role.example}
              </Button>
              <Button data-testid={`tone-${role.tone}-disabled`} variant={buttonVariantForActionTone(role.tone)} disabled>
                {role.example} disabled
              </Button>
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-4" data-testid="control-color-matrix">
          <Button data-testid="loading-button" isLoading>Create</Button>
          <Input label="Editable field" placeholder="Enter a name" />
          <Input label="Disabled field" disabled defaultValue="Disabled" />
          <Input label="Read-only field" readOnly defaultValue="Read only" />
          <Input label="Invalid field" error="Enter a valid value" />
          <Textarea label="Notes" />
          <Select label="Selected option" value={choice} onChange={(event) => setChoice(event.target.value)} options={[{ value: "first", label: "First" }, { value: "second", label: "Second" }]} />
          <Select label="Disabled select" disabled options={[{ value: "first", label: "First" }]} />
          <label className="flex items-center gap-2"><input type="checkbox" />Select record</label>
          <label className="flex items-center gap-2"><input type="radio" name="choice" />Select radio</label>
          <Switch label="Enabled preference" checked={enabled} onChange={setEnabled} />
          <Switch label="Disabled preference" checked disabled onChange={() => {}} />
          <Tabs value={tab} onChange={setTab} ariaLabel="Workspace view" options={[{ value: "first", label: "First view" }, { value: "second", label: "Second view" }]} />
          {(["neutral", "brand", "success", "warning", "danger", "ai"] as const).map(tone => <WorkbenchMetric key={tone} label={`${tone} metric`} value="12" detail="Readable detail" tone={tone} />)}
          <div data-testid="warning-alpha" className="bg-platforma-warningSoft/[0.45]">Warning surface</div>
          <div data-testid="danger-alpha" className="bg-platforma-dangerSoft/60">Danger surface</div>
          <Tooltip label="Tooltip content"><Button variant="secondary">Tooltip trigger</Button></Tooltip>
          <ActionMenu label="Record actions" items={[
            { key: "archive", label: "Archive record", icon: Archive, tone: "warning", onSelect: () => {} },
            { key: "delete", label: "Delete unavailable", icon: Trash2, tone: "danger", disabled: true, onSelect: () => {} },
          ]} />
          <ConversationComposer selected={{ status: "closed" } as InboxConversation} draft="" composerRef={null} sendPending={false} onDraftChange={() => {}} onResizeComposer={() => {}} onOpenQuickReplies={() => {}} onSendReply={() => {}} t={t} />
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <ActionColorRolesFixture />
    </I18nProvider>
  </React.StrictMode>,
);
