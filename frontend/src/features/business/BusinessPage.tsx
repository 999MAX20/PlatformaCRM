import { useEffect } from "react";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useI18n } from "../../lib/i18n";

export function BusinessPage() {
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => {
    setPageHeader({ title: t("nav.business") });
    return () => setPageHeader(null);
  }, [setPageHeader, t]);
  return null;
}
