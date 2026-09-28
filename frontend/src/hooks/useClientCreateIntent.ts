import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";

import { getApiErrorMessage } from "../api/client";
import { clientsApi } from "../api/clients";
import { useI18n } from "../lib/i18n";
import type { Client, Id } from "../types";

/** Consume the existing CRM-card create link without trusting its client ID. */
export function useClientCreateIntent({ businessId, allowed, onOpen }: {
  businessId?: Id;
  allowed: boolean;
  onOpen: (client: Client | null) => void;
}) {
  const { t } = useI18n();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const requested = params.get("create") === "1";
  const rawClient = params.get("client");
  const clientId = Number(rawClient);
  const validId = Boolean(rawClient && /^\d+$/.test(rawClient) && Number.isSafeInteger(clientId) && clientId > 0);
  const [linkedClient, setLinkedClient] = useState<Client | null>(null);
  const handled = useRef("");
  const clientQuery = useQuery({
    queryKey: ["clients", "create-context", businessId, clientId],
    queryFn: () => clientsApi.get(clientId),
    enabled: requested && allowed && Boolean(businessId) && validId,
    retry: false,
  });
  const wrongBusiness = Boolean(clientQuery.data && String(clientQuery.data.business) !== String(businessId));
  const error = requested && (!allowed || (rawClient && !validId) || wrongBusiness)
    ? t("actions.errorForbidden")
    : requested && clientQuery.error ? getApiErrorMessage(clientQuery.error) : null;
  const isLoading = requested && allowed && validId && clientQuery.isPending;

  useEffect(() => {
    if (!requested) {
      handled.current = "";
      return;
    }
    if (!businessId || !allowed || error || isLoading || handled.current === location.key) return;
    handled.current = location.key;
    const client = validId ? clientQuery.data ?? null : null;
    setLinkedClient(client);
    onOpen(client);
    setParams(current => {
      const next = new URLSearchParams(current);
      next.delete("create");
      next.delete("client");
      return next;
    }, { replace: true });
  }, [allowed, businessId, clientQuery.data, error, isLoading, location.key, onOpen, requested, setParams, validId]);

  const client = linkedClient && String(linkedClient.business) === String(businessId) ? linkedClient : null;
  return {
    error,
    isLoading,
    client,
    includeClient: (clients: Client[]) => client ? [client, ...clients.filter(item => item.id !== client.id)] : clients,
  };
}
