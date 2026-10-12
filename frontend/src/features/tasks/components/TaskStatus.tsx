import { Badge, type BadgeVariant } from "../../../components/ui/Badge";
import { useI18n } from "../../../lib/i18n";
import type { Task } from "../../../types";

const tones: Record<Task["status"], BadgeVariant> = { open: "neutral", in_progress: "info", waiting: "warning", done: "success", cancelled: "neutral" };
export function TaskStatus({ status }: { status: Task["status"] }) {
  const { t } = useI18n();
  return <Badge size="sm" variant={tones[status]}>{t(`taskWorkspace.status.${status}`)}</Badge>;
}
