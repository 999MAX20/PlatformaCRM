import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, BriefcaseBusiness, UsersRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { getApiErrorMessage } from "../../api/client";
import { isMfaPendingResponse } from "../../api/auth";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { LanguageSelector } from "../../components/layout/LanguageSelector";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "./AuthProvider";
import { useUnsavedEntryWarning } from "./useUnsavedEntryWarning";
import { PasswordVisibilityToggle } from "./PasswordVisibilityToggle";
import { GoogleSignInButton } from "./GoogleSignInButton";
import { isGooglePending } from "../../api/token";
import { getPostAuthReturnPath } from "./authReturnPath";
import { legalDocuments } from "../documents/documents";
import "./authLoginSerenity.css";

type FormValues = {
  full_name: string;
  email: string;
  password: string;
  password_confirm: string;
  business_name: string;
};

export function SignupPage() {
  const navigate = useNavigate();
  const { signupOwner, loginWithGoogle } = useAuth();
  const [googleLoading, setGoogleLoading] = useState(false);
  const { t } = useI18n();
  const schema = z.object({
    full_name: z.string().min(2, t("validation.name")),
    email: z.string().email(t("validation.email")),
    password: z.string()
      .min(8, t("signup.passwordMinCheck"))
      .regex(/^(?=.*\p{L})(?=.*\d).+$/u, t("signup.passwordLettersNumbersCheck"))
      .refine((value) => !/\s/.test(value), t("signup.passwordNoSpacesCheck")),
    password_confirm: z.string().min(1, t("passwordReset.repeatPasswordRequired")),
    business_name: z.string().min(2, t("validation.businessName")),
  }).refine((values) => values.password === values.password_confirm, {
    message: t("passwordReset.passwordMismatch"),
    path: ["password_confirm"],
  });
  const [error, setError] = useState<string | null>(null);
  const [isPasswordVisible, setPasswordVisible] = useState(false);
  const [isPasswordConfirmVisible, setPasswordConfirmVisible] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", business_name: "", password: "", password_confirm: "" },
  });
  useUnsavedEntryWarning(isDirty || isSubmitting);

  async function onSubmit(values: FormValues) {
    if (googleLoading) return;
    setError(null);
    try {
      const response = await signupOwner({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        business_name: values.business_name,
        business_type: "other",
        accepted_documents: legalDocuments.map(document => document.id),
        acceptance_method: "signup_submit",
      });
      if (isMfaPendingResponse(response)) {
        sessionStorage.setItem("zani_mfa_pending", JSON.stringify(response));
        navigate("/mfa", { replace: true });
        return;
      }
      navigate("/app");
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  }

  async function completeGoogleSignup(idToken: string) {
    setError(null);
    setGoogleLoading(true);
    try {
      const result = await loginWithGoogle(idToken);
      if (isGooglePending(result)) {
        navigate("/google/complete");
      } else if (isMfaPendingResponse(result)) {
        sessionStorage.setItem("zani_mfa_pending", JSON.stringify(result));
        navigate("/mfa", { replace: true });
      } else {
        navigate(getPostAuthReturnPath(result.is_platform_user), { replace: true });
      }
      return true;
    } catch (err) {
      setError(getApiErrorMessage(err));
      return false;
    } finally {
      setGoogleLoading(false);
    }
  }

  return (
    <main className="serenity-login serenity-login--signal-field serenity-login--signup">
      <div className="serenity-login__ambient" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>

      <header className="serenity-login__header">
        <Link className="serenity-login__brand" to="/login">
          <img className="serenity-login__brand-logo" src="/brand/platforma-crm-logo-transparent.png" alt="PlatformaCRM" width={2170} height={725} />
        </Link>

        <div className="serenity-login__header-actions">
          <span>{t("auth.alreadyHaveAccount")}</span>
          <Link className="serenity-login__signup-link" to="/login">
            {t("auth.submit")}
          </Link>
          <LanguageSelector className="serenity-login__language" />
        </div>
      </header>

      <div className="serenity-login__layout">
        <section className="serenity-login__story" aria-label={t("auth.heroAria")}>
          <h1>{t("signup.headline")}</h1>

          <div className="serenity-login__benefits">
            <article>
              <span aria-hidden="true"><BriefcaseBusiness size={19} /></span>
              <div>
                <h2>{t("signup.businessSection")}</h2>
                <p>{t("signup.createCompanyText")}</p>
              </div>
            </article>
            <article>
              <span aria-hidden="true"><UsersRound size={19} /></span>
              <div>
                <h2>{t("signup.accountSection")}</h2>
                <p>{t("signup.afterSignInHelper")}</p>
              </div>
            </article>
          </div>
        </section>

        <section className="serenity-login__form-area" aria-label={t("auth.create")}>
          <div className="serenity-login__card serenity-login__card--signup">
            <h2>{t("signup.createCompanyTitle")}</h2>

            {error ? (
              <div className="serenity-login__error" role="alert" aria-live="polite">
                {error}
              </div>
            ) : null}

            {import.meta.env.VITE_GOOGLE_CLIENT_ID ? <>
              <div className="serenity-login__social-row">
                <GoogleSignInButton text="signup_with" disabled={isSubmitting || googleLoading} onCredential={completeGoogleSignup} />
              </div>
              <div className="serenity-login__divider"><span>{t("googleAuth.signupEmailDivider")}</span></div>
            </> : null}

            <form className="serenity-login__form serenity-login__form--signup" noValidate onSubmit={handleSubmit(onSubmit)}>
              <div className="serenity-login__field-grid">
                <Input label={t("signup.yourName")} autoComplete="name" placeholder={t("signup.namePlaceholder")} error={errors.full_name?.message} {...register("full_name")} />
                <Input label={t("auth.email")} type="email" autoComplete="email" placeholder={t("auth.emailPlaceholder")} error={errors.email?.message} {...register("email")} />
              </div>
              <Input label={t("signup.businessName")} autoComplete="organization" placeholder={t("signup.businessNamePlaceholder")} error={errors.business_name?.message} {...register("business_name")} />
              <div className="serenity-login__field-grid">
                <Input
                  label={t("auth.password")}
                  type={isPasswordVisible ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder={t("signup.passwordPlaceholder")}
                  error={errors.password?.message}
                  rightIcon={
                    <PasswordVisibilityToggle
                      visible={isPasswordVisible}
                      onToggle={() => setPasswordVisible((visible) => !visible)}
                    />
                  }
                  {...register("password")}
                />
                <Input
                  label={t("signup.passwordConfirm")}
                  type={isPasswordConfirmVisible ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder={t("passwordReset.repeatPassword")}
                  error={errors.password_confirm?.message}
                  rightIcon={
                    <PasswordVisibilityToggle
                      visible={isPasswordConfirmVisible}
                      onToggle={() => setPasswordConfirmVisible((visible) => !visible)}
                    />
                  }
                  {...register("password_confirm")}
                />
              </div>
              <Button className="serenity-login__primary" type="submit" aria-describedby="signup-consent-notice" disabled={googleLoading} isLoading={isSubmitting}>
                {t("signup.freeSubmit")}
                <ArrowRight size={18} />
              </Button>
              <p id="signup-consent-notice" className="serenity-login__consent-notice" data-testid="signup-documents">
                {t("signup.consentPrefix")} {" "}
                <Link to="/documents" target="_blank" rel="noopener noreferrer" className="platforma-focus-ring rounded-sm underline underline-offset-4">{t("signup.consentLink")}</Link>
                {t("signup.consentSuffix")}
              </p>
            </form>

          </div>
        </section>
      </div>
    </main>
  );
}
