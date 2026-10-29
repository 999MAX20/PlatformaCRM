import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { clientsApi } from "../../api/clients";
import { useClientSearch } from "../../hooks/useClientSearch";
import { useI18n } from "../../lib/i18n";
import { SearchableSelect } from "../ui/SearchableSelect";
import { ErrorState } from "../ui/StateViews";
import { Button } from "../ui/Button";
import type { Client } from "../../types";

const option = (client: Client) => ({ value: String(client.id), label: client.full_name, description: [client.phone, client.email].filter(Boolean).join(" · ") });

export function ClientPicker({ value, onChange, businessId, error, label, placeholder, createAction }: {
  value: string; onChange: (value: string) => void; businessId?: number;
  error?: string; label?: string; placeholder?: string; createAction?: ReactNode;
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const search = useClientSearch(query, open, businessId);
  const selected = useQuery({
    queryKey: ["clients", "picker-value", search.businessId, search.userId, value],
    queryFn: () => clientsApi.get(Number(value)),
    enabled: Boolean(value && search.allowed), retry: false,
  });
  const selectedClient = search.allowed && !selected.isError && selected.data?.business === search.businessId ? selected.data : undefined;
  return <div>
    <SearchableSelect emptyAction={createAction} error={error} label={label || t("common.client")} value={value} onChange={onChange}
      placeholder={placeholder || t("appointment.selectClient")} disabled={!search.allowed}
      options={search.clients.map(option)} selectedOption={selectedClient ? option(selectedClient) : undefined}
      remote={{ onSearch: setQuery, onOpen: setOpen, loading: search.loading, error: search.error,
        retry: () => { void search.refetch(); }, hasMore: Boolean(search.hasNextPage),
        loadMore: () => { void search.fetchNextPage(); }, loadingMore: search.isFetchingNextPage }} />
    {value && selected.isPending && search.allowed ? <p role="status">{t("common.loading")}</p> : null}
    {selected.isError && search.allowed ? <ErrorState error={selected.error} action={<Button type="button" onClick={() => void selected.refetch()}>{t("common.retry")}</Button>} /> : null}
  </div>;
}
