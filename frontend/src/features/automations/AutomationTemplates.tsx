import { useAutomationRules } from "./useAutomationRules";

import { ClipboardCheck, Play } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { Card, CardBody } from "../../components/ui/Card";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  templates: ReturnType<typeof useAutomationRules>["templates"];
  triggers: { value: string; label: string }[];
  canCreate: boolean;
  applyTemplateMutation: ReturnType<
    typeof useAutomationRules
  >["applyTemplateMutation"];
};
export function AutomationTemplates({
  t,
  templates,
  triggers,
  canCreate,
  applyTemplateMutation,
}: Props) {
  return (
    <div className="mb-6">
      <div className="mb-3 flex items-center gap-2">
        <ClipboardCheck size={20} className="text-brand-700" />
        <h2 className="text-xl font-bold text-platforma-text">
          {t("automations.templatesTitle")}
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(templates.data || []).map((template) => (
          <Card key={template.key}>
            <CardBody>
              <div className="mb-4 flex items-center justify-between gap-3">
                <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">
                  {triggers.find((item) => item.value === template.trigger_type)
                    ?.label || template.trigger_type}
                </span>
                <span className="text-xs font-bold text-platforma-faint">
                  {t("automations.actionCount", {
                    count: template.actions.length,
                  })}
                </span>
              </div>
              <h3 className="text-lg font-bold text-platforma-text">
                {template.name}
              </h3>
              <p className="mt-2 text-sm leading-6 text-platforma-subtle">
                {template.description}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  disabled={!canCreate}
                  onClick={() =>
                    applyTemplateMutation.mutate({
                      templateKey: template.key,
                      isActive: false,
                    })
                  }
                  isLoading={applyTemplateMutation.isPending}
                >
                  {t("automations.addDraft")}
                </Button>
                <Button
                  disabled={!canCreate}
                  onClick={() =>
                    applyTemplateMutation.mutate({
                      templateKey: template.key,
                      isActive: true,
                    })
                  }
                  isLoading={applyTemplateMutation.isPending}
                >
                  <Play size={16} /> {t("automations.enable")}
                </Button>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
