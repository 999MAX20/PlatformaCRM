import { useEffect } from "react";
import { Plus } from "lucide-react";

import { usePageHeader } from "../../../components/layout/PageHeaderContext";
import type { Translate } from "../types";

export function useClientsPageHeader({
  t,
  onCreateClient,
  onCloseClientCard,
  onPayments,
}: {
  t: Translate;
  onCreateClient?: () => void;
  onCloseClientCard: () => void;
  onPayments?: () => void;
}) {
  const { setPageHeader } = usePageHeader();

  useEffect(() => {
    setPageHeader({
      title: t("clients.title"),
      secondaryActions: onPayments ? [{ label: t("payments.title"), title: t("payments.title"), onClick: onPayments, presentation: "label", focusReturnId: "clients-payments" }] : [],

      primaryAction: onCreateClient ? {
        label: t("clients.create"),
        icon: Plus,
        onClick: onCreateClient,
      } : undefined,
    });
    return () => setPageHeader(null);
  }, [onCreateClient, onPayments, setPageHeader, t]);

  useEffect(() => {
    function handleHotkeys(event: KeyboardEvent) {
      if (event.defaultPrevented || document.querySelector('[role="dialog"][aria-modal="true"]')) return;
      const isCommand = event.metaKey || event.ctrlKey;
      if (isCommand && event.key.toLowerCase() === "n" && onCreateClient) {
        event.preventDefault();
        onCreateClient();
      }
      if (event.key === "Escape") onCloseClientCard();
    }

    window.addEventListener("keydown", handleHotkeys);
    return () => window.removeEventListener("keydown", handleHotkeys);
  }, [onCloseClientCard, onCreateClient]);
}
