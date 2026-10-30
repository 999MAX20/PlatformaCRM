import { AutomationEditorDialog } from "./AutomationEditorDialog";
import { AutomationCreateDialog } from "./AutomationCreateDialog";
import { AutomationRunDetails } from "./AutomationRunDetails";
import { AutomationRunList } from "./AutomationRunList";
import { AutomationTemplates } from "./AutomationTemplates";
import {
  triggerKeys,
  actionOptionKeys,
  localeByLanguage,
} from "./automationPresentation";
import { useAutomationRules } from "./useAutomationRules";
import { useAutomationRuns } from "./useAutomationRuns";
import { useAutomationEditor } from "./useAutomationEditor";
import { Plus, Settings2, Workflow } from "lucide-react";

import { Link } from "react-router";

import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, CardBody, Surface } from "../../components/ui/Card";

import { PageHeader } from "../../components/ui/PageHeader";

import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/ui/StateViews";

import { useActiveBusiness } from "../../hooks/useBusiness";

import { useI18n } from "../../lib/i18n";

export function AutomationsPage() {
  const { t, language } = useI18n();

  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const canCreate = hasPermission(user, business?.id, "automations", "create");
  const canUpdate = hasPermission(user, business?.id, "automations", "update");
  const { automationRules, templates, applyTemplateMutation, toggleMutation } =
    useAutomationRules(business);
  const {
    runs,
    filters,
    updateFilters,
    selectedRun,
    setSelectedRun,
    retryRunMutation,
    cancelRunMutation,
  } = useAutomationRuns(business?.id, user?.id);
  const {
    createOpen,
    setCreateOpen,
    advancedOpen,
    editorSession,
    editingRuleId,
    editorLoading,
    editorLoadError,
    form,
    setForm,
    advancedForm,
    setAdvancedForm,
    conditions,
    setConditions,
    actions,
    setActions,
    setPreview,
    actionErrors,
    setActionErrors,
    members,
    draftSignature,
    validPreview,
    advancedError,
    setAdvancedError,
    mutation,
    previewMutation,
    createManualMutation,
    openEditor,
    closeEditor,
    buildManualPayload,
  } = useAutomationEditor(business, canUpdate);

  const triggers = triggerKeys.map((item) => ({
    value: item.value,
    label: t(item.labelKey),
  }));
  const actionOptions = actionOptionKeys.map((item) => ({
    value: item.value,
    label: t(item.labelKey),
  }));
  const locale = localeByLanguage[language];
  const ruleList = automationRules.data?.results || [];
  const ruleSummary = automationRules.isError ? undefined : automationRules.data?.summary;
  const runSummary = runs.isError ? undefined : runs.data?.summary;

  if (!business) return <ErrorState message={t("automations.noBusiness")} />;
  if (automationRules.isLoading || templates.isLoading)
    return <LoadingState scope="page" />;

  return (
    <>
      <PageHeader
        title={t("automations.title")}
        description={t("automations.description")}
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="/app/settings#automations">
              <Button type="button" variant="secondary">
                {t("automations.backToSettings")}
              </Button>
            </Link>
            <Button disabled={!canCreate} onClick={() => setCreateOpen(true)}>
              <Plus size={18} />
              {t("automations.createRule")}
            </Button>
          </div>
        }
      />
      {applyTemplateMutation.error ||
      toggleMutation.error ||
      mutation.error ||
      createManualMutation.error ? (
        <div className="mb-4">
          <ErrorState message={t("automations.saveError")} />
        </div>
      ) : null}

      <section className="mb-5 grid gap-3 sm:grid-cols-3">
        <Surface padding="sm" variant="muted">
          <p className="text-xs font-semibold text-platforma-faint">
            {t("automations.rulesTitle")}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-platforma-text">
            {ruleSummary ? `${ruleSummary.active}/${ruleSummary.total}` : "—"}
          </p>
        </Surface>
        <Surface padding="sm" variant="muted">
          <p className="text-xs font-semibold text-platforma-faint">
            {t("automations.runsTitle")}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-platforma-text">
            {runSummary?.total ?? "—"}
          </p>
        </Surface>
        <Surface padding="sm" variant={runSummary?.failed ? "danger" : "muted"}>
          <p className="text-xs font-semibold text-platforma-faint">
            {t("automations.retry")}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-platforma-text">
            {runSummary?.retryable ?? "—"}
          </p>
        </Surface>
      </section>

      {automationRules.isError ? <ErrorState error={automationRules.error}
        action={<Button variant="secondary" onClick={() => void automationRules.refetch()}>{t("common.retry")}</Button>} /> : null}

      <details className="mb-6 rounded-card border border-platforma-border bg-surface-card p-4 shadow-card">
        <summary className="cursor-pointer text-sm font-bold uppercase tracking-[0.14em] text-platforma-subtle">
          {t("automations.advancedTitle")}
        </summary>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-6 text-platforma-subtle">
            {t("automations.advancedText")}
          </p>
          <Button
            type="button"
            variant="secondary"
            disabled={!canCreate}
            onClick={() => void openEditor()}
          >
            <Settings2 size={18} />
            {t("automations.advancedBuilder")}
          </Button>
        </div>
      </details>

      <AutomationTemplates
        t={t}
        templates={templates}
        triggers={triggers}
        canCreate={canCreate}
        applyTemplateMutation={applyTemplateMutation}
      />

      <div className="mb-3 flex items-center gap-2">
        <Workflow size={20} className="text-brand-700" />
        <h2 className="text-xl font-bold text-platforma-text">
          {t("automations.rulesTitle")}
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {ruleList.map((rule) => (
          <Card key={rule.id}>
            <CardBody>
              <div className="mb-5 flex items-center justify-between">
                <div className="grid h-12 w-12 place-items-center rounded-control bg-surface-muted text-brand-700">
                  <Workflow size={22} />
                </div>
                <Badge variant={rule.is_active ? "success" : "neutral"}>
                  {rule.is_active ? t("status.active") : t("status.draft")}
                </Badge>
              </div>
              <h2 className="text-lg font-semibold text-platforma-text">
                {rule.name}
              </h2>
              <p className="mt-2 text-sm leading-6 text-platforma-subtle">
                {triggers.find((item) => item.value === rule.trigger_type)
                  ?.label || rule.trigger_type}
              </p>
              {rule.description ? (
                <p className="mt-3 text-sm leading-6 text-platforma-subtle">
                  {rule.description}
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                {canUpdate ? (
                  <Button
                    variant="secondary"
                    onClick={() => void openEditor(rule.id)}
                  >
                    {t("common.edit")}
                  </Button>
                ) : null}
                <Button
                  disabled={
                    !canUpdate || (!rule.is_active && !rule.actions?.length)
                  }
                  variant={rule.is_active ? "warning" : "primary"}
                  onClick={() =>
                    toggleMutation.mutate({ rule, isActive: !rule.is_active })
                  }
                  isLoading={toggleMutation.isPending}
                >
                  {rule.is_active
                    ? t("automations.disable")
                    : t("automations.enable")}
                </Button>
              </div>
            </CardBody>
          </Card>
        ))}
        {!automationRules.isError && !ruleList.length ? (
          <EmptyState
            title={t("automations.emptyTitle")}
            description={t("automations.emptyDescription")}
            action={
              canCreate ? (
                <Button variant="secondary" onClick={() => setCreateOpen(true)}>
                  <Plus size={16} />
                  {t("automations.createRule")}
                </Button>
              ) : undefined
            }
          />
        ) : null}
      </div>

      <AutomationRunList
        t={t}
        runs={runs}
        filters={filters}
        updateFilters={updateFilters}
        canManage={hasPermission(user, business?.id, "automations", "manage")}
        triggers={[...triggers,
          { value: "client_inactive", label: t("automations.trigger.clientInactive") },
          { value: "tag_added", label: t("automations.trigger.tagAdded") },
          { value: "tag_removed", label: t("automations.trigger.tagRemoved") },
        ]}
        locale={locale}
        setSelectedRun={setSelectedRun}
        retryRunMutation={retryRunMutation}
        cancelRunMutation={cancelRunMutation}
      />

      <AutomationRunDetails
        t={t}
        selectedRun={selectedRun}
        setSelectedRun={setSelectedRun}
        locale={locale}
        retryRunMutation={retryRunMutation}
        cancelRunMutation={cancelRunMutation}
        canManage={hasPermission(user, business?.id, "automations", "manage")}
      />

      <AutomationCreateDialog
        t={t}
        createOpen={createOpen}
        setCreateOpen={setCreateOpen}
        mutation={mutation}
        business={business}
        form={form}
        setForm={setForm}
        triggers={triggers}
      />

      <AutomationEditorDialog
        editingRuleId={editingRuleId}
        t={t}
        advancedOpen={advancedOpen}
        closeEditor={closeEditor}
        editorLoading={editorLoading}
        editorLoadError={editorLoadError}
        openEditor={openEditor}
        validPreview={validPreview}
        setAdvancedError={setAdvancedError}
        createManualMutation={createManualMutation}
        buildManualPayload={buildManualPayload}
        editorSession={editorSession}
        advancedError={advancedError}
        advancedForm={advancedForm}
        setAdvancedForm={setAdvancedForm}
        triggers={triggers}
        setConditions={setConditions}
        conditions={conditions}
        members={members}
        setActions={setActions}
        actions={actions}
        actionErrors={actionErrors}
        actionOptions={actionOptions}
        setPreview={setPreview}
        setActionErrors={setActionErrors}
        previewMutation={previewMutation}
        draftSignature={draftSignature}
      />
    </>
  );
}
