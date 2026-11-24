import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";
import axios from "axios";
import { medicalPortalApi as api, type PortalDocuments } from "../../api/medicalIssuance";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export function DocumentPortalPage() {
  const { businessSlug = "" } = useParams();
  return <Portal key={businessSlug} slug={businessSlug} />;
}

function Portal({ slug }: { slug: string }) {
  const { t, language: locale } = useI18n();
  const [documents, setDocuments] = useState<PortalDocuments | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<"unavailable" | "retry" | "throttled" | "archiveUnavailable" | null>(null);
  const controller = useRef(new AbortController());
  const currentDocuments = useRef(documents); currentDocuments.current = documents;
  const downloads = useRef(new Set<string>());
  useEffect(() => () => { downloads.current.forEach(url => URL.revokeObjectURL(url)); downloads.current.clear(); }, []);
  const busy = useRef(false);
  const unavailable = (cause: unknown) => axios.isAxiosError(cause) && [401, 403, 404].includes(cause.response?.status ?? 0);
  useEffect(() => {
    const active = new AbortController(); controller.current = active;
    api.documents(slug, active.signal).then(value => { if (!active.signal.aborted) setDocuments(value); })
      .catch(cause => { if (!active.signal.aborted && !unavailable(cause)) setError("retry"); })
      .finally(() => { if (!active.signal.aborted) setLoading(false); });
    return () => active.abort();
  }, [slug]);
  useEffect(() => {
    if (!documents) return;
    const expiry = window.setTimeout(() => { setDocuments(null); setError("unavailable"); }, Math.max(0, Math.min(Date.parse(documents.expires_at), Date.parse(documents.session_expires_at)) - Date.now()));
    return () => window.clearTimeout(expiry);
  }, [documents]);
  async function run(action: "login" | "refresh" | "logout" | "archive") {
    if (busy.current) return;
    busy.current = true; setPending(true); setError(null);
    const signal = controller.current.signal;
    try {
      if (action === "archive") {
        const expected = currentDocuments.current;
        if (!expected) return;
        const blob = await api.archive(slug, signal);
        if (!signal.aborted && currentDocuments.current === expected && Math.min(Date.parse(expected.expires_at), Date.parse(expected.session_expires_at)) > Date.now()) {
          const url = URL.createObjectURL(blob); downloads.current.add(url);
          const link = document.createElement("a"); link.href = url; link.download = "documents.zip";
          document.body.appendChild(link); link.click(); link.remove();
          window.setTimeout(() => { URL.revokeObjectURL(url); downloads.current.delete(url); }, 10_000);
        }
      }
      else if (action === "logout") { await api.logout(slug, signal); if (!signal.aborted) { setDocuments(null); setCode(""); } }
      else {
        if (action === "login") await api.login(slug, code, signal);
        const result = await api.documents(slug, signal);
        if (!signal.aborted) { setDocuments(result); setCode(""); }
      }
    } catch (cause) {
      if (!signal.aborted) {
        if (unavailable(cause)) { setDocuments(null); setError("unavailable"); }
        else setError(axios.isAxiosError(cause) && cause.response?.status === 429 ? "throttled" : action === "archive" ? "archiveUnavailable" : "retry");
      }
    } finally { busy.current = false; if (!signal.aborted) setPending(false); }
  }
  return <main className="min-h-screen bg-platforma-bg px-4 py-8 text-platforma-text sm:px-6" data-testid="medical-document-portal">
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2"><p className="text-sm font-semibold">PlatformaCRM</p><h1 className="text-2xl font-semibold">{t("medical.issue.portalTitle")}</h1></header>
      {loading ? <LoadingState /> : documents ? <section className="space-y-4" aria-label={t("medical.issue.portalTitle")}>
        <p className="text-sm text-platforma-subtle">{t("medical.issue.until", { date: new Date(documents.expires_at).toLocaleString(locale) })}</p>
        {documents.synthetic ? <p className="text-sm">{t("medical.issue.synthetic")}</p> : null}
        <Button size="lg" disabled={pending || !documents.documents.length} isLoading={pending} onClick={() => void run("archive")}>{t("medical.issue.archive")}</Button>
        <ul className="divide-y divide-platforma-border rounded-xl border border-platforma-border bg-platforma-surface">
          {documents.documents.map(item => <li key={item.id} className="space-y-3 p-4">
            <div><h2 className="break-words font-semibold">{item.title}</h2><p className="text-sm text-platforma-subtle">{t("medical.issue.version", { revision: item.revision })}</p></div>
            {item.has_correction ? <p className="text-sm">{t("medical.issue.corrected")}</p> : null}
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <a className="inline-flex min-h-11 items-center font-medium text-platforma-primary underline focus-visible:outline" href={api.fileUrl(slug, item.id)} target="_blank" rel="noopener noreferrer">{t("medical.issue.view")}</a>
              <a className="inline-flex min-h-11 items-center font-medium text-platforma-primary underline focus-visible:outline" href={api.fileUrl(slug, item.id, true)} target="_blank" rel="noopener noreferrer">{t("medical.issue.download")}</a>
            </div>
          </li>)}
        </ul>
        <div className="flex flex-wrap gap-2"><Button size="lg" variant="secondary" disabled={pending} onClick={() => void run("refresh")}>{t("common.refresh")}</Button><Button size="lg" variant="secondary" disabled={pending} onClick={() => void run("logout")}>{t("medical.issue.logout")}</Button></div>
      </section> : <form className="space-y-4 rounded-xl border border-platforma-border bg-platforma-surface p-5" onSubmit={event => { event.preventDefault(); void run("login"); }}>
        <p className="text-sm text-platforma-subtle">{t("medical.issue.codeHint")}</p>
        <Input label={t("medical.issue.code")} value={code} required maxLength={40} autoComplete="off" spellCheck={false} disabled={pending} onChange={event => setCode(event.target.value)} />
        <Button type="submit" size="lg" isLoading={pending} disabled={!code.trim()}>{t("medical.issue.open")}</Button>
      </form>}
      {error ? <ErrorState message={t(`medical.issue.${error}`)} action={documents && ["retry", "archiveUnavailable"].includes(error) ? <Button onClick={() => void run(error === "archiveUnavailable" ? "archive" : "refresh")}>{t("common.retry")}</Button> : undefined} /> : null}
    </div>
  </main>;
}
