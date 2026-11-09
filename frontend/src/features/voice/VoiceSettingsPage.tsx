import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { VoiceSettings } from "../settings/sections/VoiceInputSection";
import { Card } from "../../components/ui/Card";

export default function VoiceSettingsPage() {
  const { user } = useAuth(); const { business } = useActiveBusiness(); const { t } = useI18n();
  return <Card className="max-w-2xl"><h1 className="border-b border-platforma-border p-5 text-xl font-semibold">{t("voice.title")}</h1>
    {user && business && <VoiceSettings key={`${user.id}:${business.id}`} userId={user.id} />}</Card>;
}
