import { ArrowLeft, BarChart3, Bot, BriefcaseBusiness, Cloud, Gift, MessageSquareText, ShieldCheck, ShoppingCart, Sparkles, UsersRound } from "lucide-react";
import { Link } from "react-router";

import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { useI18n } from "../../lib/i18n";

type AuthExperienceShellProps = {
  children: React.ReactNode;
  mode: "signup" | "login";
};

const features = [
  {
    icon: Gift,
    titleKey: "auth.featureCrmTitle",
    textKey: "auth.featureCrmText",
  },
  {
    icon: Sparkles,
    titleKey: "auth.featureAiTitle",
    textKey: "auth.featureAiText",
  },
  {
    icon: MessageSquareText,
    titleKey: "auth.featureBotsTitle",
    textKey: "auth.featureBotsText",
  },
  {
    icon: ShoppingCart,
    titleKey: "auth.featureIntegrationsTitle",
    textKey: "auth.featureIntegrationsText",
  },
];

export function AuthExperienceShell({ children, mode }: AuthExperienceShellProps) {
  const { t } = useI18n();
  const isSignup = mode === "signup";

  return (
    <main className={`platforma-auth-experience ${isSignup ? "is-signup" : "is-login"}`}>
      <div className="platforma-auth-noise" />
      <header className="platforma-auth-topbar">
        <Link className="platforma-auth-back" to="/">
          <ArrowLeft size={18} />
          {t("auth.backToSite")}
        </Link>
        <Link className="platforma-auth-brand" to="/">
          <span>Платформа CRM</span>
          <i />
          <em>{t("auth.brandTagline")}</em>
        </Link>
        <div className="platforma-auth-switch">
          <span>{isSignup ? t("auth.alreadyHaveAccount") : t("auth.noAccount")}</span>
          <Link to={isSignup ? "/login" : "/signup"}>{isSignup ? t("auth.submit") : t("auth.create")}</Link>
          <LanguageSelector className="platforma-auth-language" />
        </div>
      </header>

      <div className="platforma-auth-grid">
        <section className="platforma-auth-hero" aria-label={t("auth.heroAria")}>
          <h1>
            {isSignup ? (
              <>{t("auth.signupHeroPrefix")} <strong>{t("auth.signupHeroTime")}</strong></>
            ) : (
              <>{t("auth.loginHeroPrefix")} <strong>{t("auth.loginHeroTime")}</strong></>
            )}
          </h1>
          <p className="platforma-auth-lead">
            {isSignup ? t("auth.signupHeroText") : t("auth.loginHeroText")}
          </p>

          <div className="platforma-auth-feature-list">
            {features.map((feature) => (
              <article key={feature.titleKey} className="platforma-auth-feature">
                <span>
                  <feature.icon size={22} />
                </span>
                <div>
                  <h2>{t(feature.titleKey)}</h2>
                  <p>{t(feature.textKey)}</p>
                </div>
              </article>
            ))}
          </div>

          <div className="platforma-auth-proof">
            <div className="platforma-auth-avatars" aria-hidden="true">
              {["A", "M", "D", "S"].map((item) => (
                <span key={item}>{item}</span>
              ))}
              <b>+2K</b>
            </div>
            <p>{t("auth.proofText")}</p>
          </div>

          <div className="platforma-auth-trust">
            <span>
              <ShieldCheck size={18} />
              {t("auth.trustSecurity")}
            </span>
            <span>
              <Cloud size={18} />
              {t("auth.trustServers")}
            </span>
          </div>

          <DashboardPreview />
        </section>

        <section className="platforma-auth-card-wrap">{children}</section>
      </div>
    </main>
  );
}

function DashboardPreview() {
  const { t } = useI18n();
  return (
    <div className="platforma-auth-dashboard" aria-hidden="true">
      <div className="platforma-auth-dashboard-sidebar">
        <b>Платформа CRM</b>
        {[t("nav.dashboard"), t("nav.clients"), t("nav.deals"), t("nav.bots"), t("nav.analytics")].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      <div className="platforma-auth-dashboard-main">
        <div className="platforma-auth-dashboard-title">
          <div>
            <p>{t("auth.previewWelcome")}</p>
            <small>{t("auth.previewScanned")}</small>
          </div>
          <UsersRound size={18} />
        </div>
        <div className="platforma-auth-metrics">
          {[
            [t("auth.previewNewLeads"), "248", "+24%"],
            [t("auth.previewBookings"), "32", "+18%"],
            [t("auth.previewRevenue"), "2 450 800 ₸", "+32%"],
          ].map(([label, value, delta]) => (
            <div key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
              <i>{delta}</i>
            </div>
          ))}
        </div>
        <div className="platforma-auth-pipeline">
          <div>
            <BriefcaseBusiness size={15} />
            {t("auth.previewPipeline")}
          </div>
          <span />
          <span />
          <span />
        </div>
        <div className="platforma-auth-dashboard-bottom">
          <div>
            <Bot size={16} />
            {t("auth.previewAiTip")}
          </div>
          <div>
            <BarChart3 size={16} />
            {t("auth.previewConversion")}
          </div>
        </div>
      </div>
    </div>
  );
}
