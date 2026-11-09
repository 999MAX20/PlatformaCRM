import type { Branch } from "../../../api/branches";
import { Badge } from "../../../components/ui/Badge";
import { useI18n } from "../../../lib/i18n";

export function BranchStatusBadge({ branch }: { branch: Branch }) {
  const { t } = useI18n();
  const key = branch.archived_at ? "archived" : !branch.is_active ? "paused" : branch.setup_state === "configured" ? "configured" : "notConfigured";
  return <Badge size="sm" variant={key === "configured" ? "success" : key === "notConfigured" ? "warning" : "neutral"}>{t(`branches.${key}`)}</Badge>;
}
