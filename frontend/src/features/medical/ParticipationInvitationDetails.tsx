import type { Participation } from "../../api/medicalParticipation";
import { useI18n } from "../../lib/i18n";

export function ParticipationInvitationDetails({ item }: { item: Participation }) {
  const { t, language } = useI18n();
  const planned = item.planned_work_date;
  const locale = language === "kk" ? "kk-KZ" : language === "en" ? "en-GB" : "ru-RU";
  return <div className="space-y-1 break-words text-sm" data-testid="participation-invitation-details">
    <p>{t("medical.participation.initiator")}: {item.proposer_name || t("medical.clinical.authorUnknown")}</p>
    {item.work_direction ? <p className="whitespace-pre-wrap">{t("medical.participation.workDirection")}: {item.work_direction}</p> : null}
    {planned ? <p>{t("medical.participation.plannedWorkDate")}: <time dateTime={planned}>{new Intl.DateTimeFormat(locale, {
      day: "numeric", month: language === "kk" ? "numeric" : "long", year: "numeric", timeZone: "UTC",
    }).format(new Date(`${planned}T12:00:00Z`))}</time></p> : null}
  </div>;
}
