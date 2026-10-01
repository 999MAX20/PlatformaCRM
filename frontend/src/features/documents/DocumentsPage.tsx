import { Link, useParams } from "react-router";
import { useI18n } from "../../lib/i18n";
import { NotFoundPage } from "../pilot/NotFoundPage";
import { documentPath, legalDocuments } from "./documents";

export function DocumentsPage() {
  const { documentId } = useParams();
  const { t } = useI18n();
  const document = legalDocuments.find(item => item.id === documentId);
  if (documentId && !document) return <NotFoundPage />;
  return <main className="mx-auto min-h-screen max-w-4xl px-5 py-10 sm:px-8">
    {document ? <Link to="/documents" className="platforma-focus-ring mb-6 inline-block rounded text-sm underline underline-offset-4">{t("documents.title")}</Link> : null}
    <h1 className="text-2xl font-bold text-platforma-text">{document ? t(document.titleKey) : t("documents.title")}</h1>
    {document ? <article data-document-body className="mt-8" /> : <nav aria-label={t("documents.title")} className="mt-6 flex flex-col items-start gap-4">
      {legalDocuments.map(item => <Link key={item.id} className="platforma-focus-ring rounded text-sm underline underline-offset-4" to={documentPath(item.id)}>{t(item.titleKey)}</Link>)}
    </nav>}
  </main>;
}
