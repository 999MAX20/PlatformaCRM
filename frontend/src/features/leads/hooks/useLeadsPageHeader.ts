import { useEffect } from "react";
import { Plus } from "lucide-react";

import type { Translate } from "../types";
import { usePageHeader } from "../../../components/layout/PageHeaderContext";

export function useLeadsPageHeader({
  t,
  onCreateLead,
}: {
  t: Translate;
  onCreateLead: () => void;
}) {
  const { setPageHeader } = usePageHeader();

  useEffect(() => {
    setPageHeader({
      title: t("nav.leads"),
      primaryAction: {
        label: t("leads.create"),
        icon: Plus,
        onClick: onCreateLead,
      },
    });
    return () => setPageHeader(null);
  }, [onCreateLead, setPageHeader, t]);
}
