import { CrmPagination } from "../../../components/crm";

export function LeadsPagination({ page, pageSize, total, shown, label, pageSizeLabel, previousLabel, nextLabel, onPageChange, onPageSizeChange }: {
  page: number;
  pageSize: number;
  total: number;
  shown: number;
  label: string;
  pageSizeLabel: string;
  previousLabel: string;
  nextLabel: string;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  return <CrmPagination numbered page={page} pageSize={pageSize} total={total} shown={shown} rangeLabel={label}
    pageSizeAriaLabel={pageSizeLabel} pageSizeLabel={(size) => `${pageSizeLabel} ${size}`} previousLabel={previousLabel} nextLabel={nextLabel}
    onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />;
}
