import { useI18n } from "../../../lib/i18n";
import { ActionMenu } from "../../../components/ui/ActionMenu";
import { CrmWorkspacePopover } from "../../../components/crm/CrmWorkspacePopover";
import { CrmFilterControls } from "../../../components/crm/CrmFilterControls";
import { Columns3, Download, ArrowDownWideNarrow, Share2, Upload } from "lucide-react";
import type { TeamMember } from "../../../types";
import type { LeadColumnKey, LeadFilter } from "../types";
type LeadFilterTab = { value: LeadFilter; label: string; count?: number };
export function LeadsToolbar({ filters, sourceOptions, teamList, moreMenuOpen, columnOrder, visibleColumns, labels, onToggleMoreMenu, onToggleColumn, onToggleSortByAi, onExportCsv, onExportExcel, onShareView, onOpenImport }: {
  filters: LeadFilterTab[];
  teamList: TeamMember[];
  sourceOptions: { value: string; label: string }[];
  moreMenuOpen: boolean;
  columnOrder: LeadColumnKey[];
  visibleColumns: Record<LeadColumnKey, boolean>;
  labels: {
    search: string;
    columns: string;
    exportCsv: string;
    exportExcel: string;
    import: string;
    shareView: string;
    column: (column: LeadColumnKey) => string;
  };
  onToggleMoreMenu: () => void;
  onToggleColumn: (column: LeadColumnKey) => void;
  onToggleSortByAi: () => void;
  onExportCsv: () => void;
  onExportExcel: () => void;
  onShareView: () => void;
  onOpenImport: () => void;
}) {
  const { t } = useI18n();
  return <div data-testid="leads-filter-toolbar"><CrmFilterControls kind="leads" searchLabel={labels.search}
    counts={Object.fromEntries(filters.map(item => [item.value === "all" ? "total" : item.value, item.count]))}
    options={{ source: sourceOptions, assignees: teamList.filter(member => member.is_active).map(member => ({ value: member.user.id, label: member.user.full_name || member.user.email })) }}
    actions={<>
      <CrmWorkspacePopover label={labels.columns} icon={<Columns3 size={16} />} open={moreMenuOpen} onToggle={onToggleMoreMenu}>
        {columnOrder.map(column => <label key={column} className="flex min-h-11 items-center gap-3 rounded-control px-2 text-sm hover:bg-surface-hover"><input type="checkbox" checked={visibleColumns[column]} disabled={column === "lead"} onChange={() => onToggleColumn(column)} />{labels.column(column)}</label>)}
      </CrmWorkspacePopover>
      <ActionMenu label={t("leads.moreActions")} items={[
        { key: "import", label: labels.import, icon: Upload, onSelect: onOpenImport },
        { key: "csv", label: labels.exportCsv, icon: Download, onSelect: onExportCsv },
        { key: "excel", label: labels.exportExcel, icon: Download, onSelect: onExportExcel },
        { key: "sort", label: t("crmFilters.sortActivity"), icon: ArrowDownWideNarrow, onSelect: onToggleSortByAi },
        { key: "share", label: labels.shareView, icon: Share2, onSelect: onShareView },
      ]} />
    </>} /></div>;
}
