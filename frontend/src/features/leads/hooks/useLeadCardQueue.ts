import { useMemo } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { useNotification } from "../../../components/notifications/NotificationProvider";
import { useI18n } from "../../../lib/i18n";
import { leadOfflineScope } from "../../../lib/leadOfflineStorage";
import { useLeadOfflineQueue } from "./useLeadOfflineQueue";
import type { Id, Lead } from "../../../types";

const noRows: Lead[] = [];
export function useLeadCardQueue(businessId?: Id) {
  const { user } = useAuth();
  const { t } = useI18n();
  const notify = useNotification();
  const scope = useMemo(() => leadOfflineScope(user, businessId), [user, businessId]);
  return useLeadOfflineQueue({ scope, onlineLeads: noRows, hasFreshData: false, accessDenied: false, t,
    onNotice: message => { if (message) notify({ message, tone: "info" }); },
    onWarning: message => notify({ message, tone: "warning" }),
  });
}
