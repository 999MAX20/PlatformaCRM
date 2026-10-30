import { conditionOperators } from "./automationPresentation";

import { useAutomationEditor } from "./useAutomationEditor";
import { Plus, Trash2 } from "lucide-react";

import { AutomationActionFields } from "./AutomationActionFields";
import { editedConditionValue } from "./editorDraft";

import { getApiErrorMessage } from "../../api/client";

import { Button } from "../../components/ui/Button";
import { Surface } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";

import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { Textarea } from "../../components/ui/Textarea";

import { useI18n } from "../../lib/i18n";
import type {
  AutomationActionDraft,
  AutomationConditionDraft,
} from "../../types";

type Props = {
  editingRuleId: ReturnType<typeof useAutomationEditor>["editingRuleId"];
  t: ReturnType<typeof useI18n>["t"];
  advancedOpen: ReturnType<typeof useAutomationEditor>["advancedOpen"];
  closeEditor: ReturnType<typeof useAutomationEditor>["closeEditor"];
  editorLoading: ReturnType<typeof useAutomationEditor>["editorLoading"];
  editorLoadError: ReturnType<typeof useAutomationEditor>["editorLoadError"];
  openEditor: ReturnType<typeof useAutomationEditor>["openEditor"];
  validPreview: ReturnType<typeof useAutomationEditor>["validPreview"];
  setAdvancedError: ReturnType<typeof useAutomationEditor>["setAdvancedError"];
  createManualMutation: ReturnType<
    typeof useAutomationEditor
  >["createManualMutation"];
  buildManualPayload: ReturnType<
    typeof useAutomationEditor
  >["buildManualPayload"];
  editorSession: ReturnType<typeof useAutomationEditor>["editorSession"];
  advancedError: ReturnType<typeof useAutomationEditor>["advancedError"];
  advancedForm: ReturnType<typeof useAutomationEditor>["advancedForm"];
  setAdvancedForm: ReturnType<typeof useAutomationEditor>["setAdvancedForm"];
  triggers: { value: string; label: string }[];
  setConditions: ReturnType<typeof useAutomationEditor>["setConditions"];
  conditions: ReturnType<typeof useAutomationEditor>["conditions"];
  members: ReturnType<typeof useAutomationEditor>["members"];
  setActions: ReturnType<typeof useAutomationEditor>["setActions"];
  actions: ReturnType<typeof useAutomationEditor>["actions"];
  actionErrors: ReturnType<typeof useAutomationEditor>["actionErrors"];
  actionOptions: { value: string; label: string }[];
  setPreview: ReturnType<typeof useAutomationEditor>["setPreview"];
  setActionErrors: ReturnType<typeof useAutomationEditor>["setActionErrors"];
  previewMutation: ReturnType<typeof useAutomationEditor>["previewMutation"];
  draftSignature: ReturnType<typeof useAutomationEditor>["draftSignature"];
};
export function AutomationEditorDialog({
  editingRuleId,
  t,
  advancedOpen,
  closeEditor,
  editorLoading,
  editorLoadError,
  openEditor,
  validPreview,
  setAdvancedError,
  createManualMutation,
  buildManualPayload,
  editorSession,
  advancedError,
  advancedForm,
  setAdvancedForm,
  triggers,
  setConditions,
  conditions,
  members,
  setActions,
  actions,
  actionErrors,
  actionOptions,
  setPreview,
  setActionErrors,
  previewMutation,
  draftSignature,
}: Props) {
  return (
    <Modal
      title={
        editingRuleId ? t("common.edit") : t("automations.advancedBuilder")
      }
      open={advancedOpen}
      onClose={closeEditor}
    >
      {editorLoading ? (
        <LoadingState />
      ) : editorLoadError ? (
        <div className="space-y-3">
          <ErrorState message={getApiErrorMessage(editorLoadError, t)} />
          <Button onClick={() => void openEditor(editingRuleId)}>
            {t("common.retry")}
          </Button>
        </div>
      ) : (
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (!validPreview) {
              setAdvancedError(t("automations.previewRequired"));
              return;
            }
            createManualMutation.mutate({
              id: editingRuleId,
              payload: buildManualPayload(),
              session: editorSession.current,
            });
          }}
        >
          <fieldset
            disabled={createManualMutation.isPending}
            className="min-w-0 space-y-5"
          >
            {advancedError ? <ErrorState message={advancedError} /> : null}
            <div className="grid gap-3 md:grid-cols-2">
              <Input
                label={t("automations.name")}
                value={advancedForm.name}
                onChange={(event) =>
                  setAdvancedForm({ ...advancedForm, name: event.target.value })
                }
                required
              />
              <Select
                label={t("automations.trigger")}
                value={advancedForm.trigger_type}
                onChange={(event) =>
                  setAdvancedForm({
                    ...advancedForm,
                    trigger_type: event.target.value,
                  })
                }
                options={triggers}
              />
            </div>
            <Textarea
              label={t("automations.descriptionLabel")}
              value={advancedForm.description}
              onChange={(event) =>
                setAdvancedForm({
                  ...advancedForm,
                  description: event.target.value,
                })
              }
            />
            <div className="grid gap-3 md:grid-cols-[1fr_130px]">
              <Input
                label={t("automations.priority")}
                type="number"
                value={advancedForm.priority}
                onChange={(event) =>
                  setAdvancedForm({
                    ...advancedForm,
                    priority: Number(event.target.value),
                  })
                }
              />
              <label className="flex items-end gap-2 pb-3 text-sm font-semibold text-platforma-subtle">
                <input
                  type="checkbox"
                  checked={advancedForm.is_active}
                  onChange={(event) =>
                    setAdvancedForm({
                      ...advancedForm,
                      is_active: event.target.checked,
                    })
                  }
                />
                {t("automations.enableAfterSave")}
              </label>
            </div>

            <Surface variant="muted" className="p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="font-bold text-platforma-ink">
                  {t("automations.conditions")}
                </h3>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    setConditions([
                      ...conditions,
                      {
                        field: "source",
                        operator: "eq",
                        rawValue: "",
                        value: { value: "" },
                      },
                    ])
                  }
                >
                  <Plus size={16} /> {t("automations.addCondition")}
                </Button>
              </div>
              <div className="space-y-3">
                {conditions.map((condition, index) => (
                  <div
                    key={index}
                    className="grid gap-2 md:grid-cols-[1fr_120px_1fr_auto]"
                  >
                    <Input
                      placeholder={t("automations.fieldPlaceholder")}
                      value={condition.field}
                      onChange={(event) =>
                        setConditions(
                          conditions.map((item, itemIndex) =>
                            itemIndex === index
                              ? { ...item, field: event.target.value }
                              : item,
                          ),
                        )
                      }
                    />
                    <Select
                      value={condition.operator}
                      onChange={(event) =>
                        setConditions(
                          conditions.map((item, itemIndex) =>
                            itemIndex === index
                              ? {
                                  ...item,
                                  operator: event.target
                                    .value as AutomationConditionDraft["operator"],
                                }
                              : item,
                          ),
                        )
                      }
                      options={conditionOperators}
                    />
                    <Input
                      placeholder={t("automations.expectedValue")}
                      value={condition.rawValue}
                      onChange={(event) =>
                        setConditions(
                          conditions.map((item, itemIndex) =>
                            itemIndex === index
                              ? {
                                  ...item,
                                  rawValue: event.target.value,
                                  value: editedConditionValue(
                                    event.target.value,
                                  ),
                                }
                              : item,
                          ),
                        )
                      }
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      className="px-3"
                      aria-label={t("automations.removeCondition")}
                      onClick={() =>
                        setConditions(
                          conditions.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        )
                      }
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ))}
                {!conditions.length ? (
                  <p className="text-sm text-platforma-subtle">
                    {t("automations.noConditionsHint")}
                  </p>
                ) : null}
              </div>
            </Surface>

            {members.isError ? (
              <div role="alert">
                <ErrorState message={getApiErrorMessage(members.error, t)} />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => members.refetch()}
                >
                  {t("common.retry")}
                </Button>
              </div>
            ) : null}
            <Surface variant="muted" className="p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="font-bold text-platforma-ink">
                  {t("automations.actions")}
                </h3>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    setActions([
                      ...actions,
                      { action_type: "wait", config: {}, delay_seconds: 300 },
                    ])
                  }
                >
                  <Plus size={16} /> {t("automations.addAction")}
                </Button>
              </div>
              <div className="space-y-3">
                {actions.map((action, index) => (
                  <div
                    key={index}
                    className="rounded-card border border-platforma-border bg-surface-card p-3"
                  >
                    <div className="grid gap-2 md:grid-cols-[1fr_150px_auto]">
                      <Select
                        label={t("automations.actionType")}
                        error={
                          actionErrors[index]?.includes("action_type")
                            ? t("automations.triggerActionInvalid")
                            : undefined
                        }
                        value={action.action_type}
                        onChange={(event) =>
                          setActions(
                            actions.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    action_type: event.target
                                      .value as AutomationActionDraft["action_type"],
                                    config: {},
                                    delay_seconds:
                                      event.target.value === "wait" ? 300 : 0,
                                  }
                                : item,
                            ),
                          )
                        }
                        options={actionOptions}
                      />
                      <Input
                        type="number"
                        label={t("automations.delaySeconds")}
                        min={action.action_type === "wait" ? 1 : 0}
                        step={1}
                        error={
                          actionErrors[index]?.includes("delay_seconds")
                            ? t("automations.fieldInvalid")
                            : undefined
                        }
                        value={action.delay_seconds}
                        onChange={(event) =>
                          setActions(
                            actions.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    delay_seconds: Number(event.target.value),
                                  }
                                : item,
                            ),
                          )
                        }
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        className="px-3"
                        aria-label={t("automations.removeAction")}
                        onClick={() =>
                          setActions(
                            actions.filter(
                              (_, itemIndex) => itemIndex !== index,
                            ),
                          )
                        }
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                    <AutomationActionFields
                      action={action}
                      members={members.data || []}
                      membersLoading={members.isLoading}
                      invalidFields={actionErrors[index]}
                      onChange={(config) => {
                        setPreview(null);
                        setActionErrors({});
                        setActions(
                          actions.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, config } : item,
                          ),
                        );
                      }}
                    />
                  </div>
                ))}
              </div>
            </Surface>

            {validPreview ? (
              <div className="rounded-card border border-platforma-success/20 bg-[var(--platforma-success-soft)] p-4 text-sm text-platforma-success">
                <p className="font-bold">
                  {t("automations.previewOk", { name: validPreview.name })}
                </p>

                <p className="mt-2 font-semibold">
                  {t("automations.previewMeta", {
                    conditions: validPreview.conditions_count,
                    actions: validPreview.actions_count,
                  })}
                </p>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={(event) => {
                  if (event.currentTarget.form?.reportValidity())
                    previewMutation.mutate({
                      payload: buildManualPayload(),
                      signature: draftSignature,
                      id: editingRuleId,
                      session: editorSession.current,
                    });
                }}
                isLoading={previewMutation.isPending}
              >
                {t("automations.testPreview")}
              </Button>
              <Button type="submit" isLoading={createManualMutation.isPending}>
                {t("automations.saveRule")}
              </Button>
            </div>
          </fieldset>
        </form>
      )}
    </Modal>
  );
}
