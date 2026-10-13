import { SearchableSelect } from "../../../components/ui/SearchableSelect";
import type { SearchableCalendarFilterOption } from "../calendarTypes";

export function SearchableCalendarFilter({ value, options, allLabel, disabled, onChange }: {
  value: string; options: SearchableCalendarFilterOption[]; allLabel: string;
  searchPlaceholder: string; emptyLabel: string; disabled?: boolean; onChange: (value: string) => void;
}) {
  return <div onKeyDown={event => {
    // The first Escape belongs to the select, the next to its containing dialog.
    if (event.key === "Escape" && event.currentTarget.querySelector('[aria-expanded="true"]')) event.stopPropagation();
  }}><SearchableSelect value={value} options={options} placeholder={allLabel} emptyLabel={allLabel} disabled={disabled} onChange={onChange} /></div>;
}
