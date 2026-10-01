import { Link } from "react-router";
import { useI18n } from "../../lib/i18n";
import { documentPath, legalDocuments } from "./documents";

export function DocumentLinks() {
  const { t } = useI18n();
  return <footer data-testid="account-documents" className="border-t border-platforma-border px-1 py-5 text-xs text-platforma-subtle">
    <Link to="/documents" target="_blank" rel="noopener noreferrer" className="platforma-focus-ring rounded font-semibold underline underline-offset-4">{t("documents.title")}</Link>
    <nav aria-label={t("documents.title")} className="mt-3 flex flex-wrap gap-x-5 gap-y-3">
      {legalDocuments.map(document => <Link key={document.id} to={documentPath(document.id)} target="_blank" rel="noopener noreferrer" className="platforma-focus-ring rounded underline underline-offset-4">{t(document.titleKey)}</Link>)}
    </nav>
  </footer>;
}
