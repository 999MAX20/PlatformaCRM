import { useNavigate } from "react-router";
import { WalletCards } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { hasPermission } from "../../lib/permissions";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";

export function PaymentsButton({ client }: { client: { id: number; full_name: string } }) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  if (!hasPermission(user, business?.id, "payments") || !hasPermission(user, business?.id, "clients")) return null;
  return <>
    <Button type="button" variant="secondary" onClick={() => void navigate(`/app/payments?client=${client.id}`)} data-testid="client-payments-open"><WalletCards size={18} aria-hidden />{t("payments.title")}</Button>
  </>;
}
