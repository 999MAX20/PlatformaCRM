import { QRCodeSVG } from "qrcode.react";

import type { MfaEnrollment } from "../../api/auth";
import { useI18n } from "../../lib/i18n";

export function AuthenticatorEnrollment({ enrollment }: { enrollment: MfaEnrollment }) {
  const { t } = useI18n();
  return (
    <div className="grid min-w-0 gap-3">
      <p className="text-sm text-platforma-subtle">{t("mfa.scanQr")}</p>
      <QRCodeSVG value={enrollment.otpauth_uri} size={240} marginSize={4} level="M"
        role="img" aria-label={t("mfa.qrLabel")} className="mx-auto h-auto max-w-full"
        data-testid="authenticator-qr" />
      <details className="min-w-0 text-center text-sm">
        <summary className="mx-auto w-fit cursor-pointer font-semibold">{t("mfa.manualFallback")}</summary>
        <code className="mx-auto mt-2 block w-fit max-w-full break-all rounded-xl bg-surface-muted p-3">{enrollment.manual_key}</code>
      </details>
    </div>
  );
}
