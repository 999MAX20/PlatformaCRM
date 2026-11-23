import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { googleIntegrationsApi } from "../../api/googleIntegrations";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

export default function GoogleCallback() {
  const { t } = useI18n();
  const cache = useQueryClient();
  const started = useRef(false);
  const [status, setStatus] = useState<"loading" | "success" | "cancelled" | "failed">("loading");
  const [error, setError] = useState<unknown>();
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    window.history.replaceState(window.history.state, "", window.location.pathname);
    const code = params.get("code"), state = params.get("state");
    if (params.has("error") || !code || !state) { setStatus("cancelled"); return; }
    void googleIntegrationsApi.complete(code, state).then(async () => {
      await cache.invalidateQueries({ queryKey: ["google-connection"] });
      await cache.invalidateQueries({ queryKey: ["google-calendar"] });
      setStatus("success");
    }).catch(reason => { setError(reason); setStatus("failed"); });
  }, [cache]);
  return <div className="mx-auto w-full max-w-2xl space-y-4 p-4">
    <h1 className="text-xl font-semibold">Google</h1>
    {status === "loading" ? <LoadingState /> : <>
      {status === "failed" ? <ErrorState error={error} /> : <p role="status">{t(`googleSheets.callback.${status}`)}</p>}
      <Link to="/app/settings#integrations" className="text-brand-700 underline">{t("googleSheets.back")}</Link>
    </>}
  </div>;
}
