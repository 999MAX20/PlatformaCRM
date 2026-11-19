import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, KeyRound } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router";
import { z } from "zod";

import { confirmPasswordReset } from "../../api/auth";
import { getApiErrorMessage, getApiFieldErrors } from "../../api/client";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import "./authLoginSerenity.css";

type FormValues = {
  password: string;
  password_confirm: string;
};

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const { uid = "", token = "" } = useParams();
  const { t } = useI18n();
  const schema = z.object({
    password: z.string().min(8, t("validation.passwordMin")),
    password_confirm: z.string().min(8, t("passwordReset.repeatPasswordRequired")),
  }).refine((values) => values.password === values.password_confirm, {
    path: ["password_confirm"],
    message: t("passwordReset.passwordMismatch"),
  });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [invalidLink, setInvalidLink] = useState(false);
  const { register, handleSubmit, setError: setFieldError, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      await confirmPasswordReset({ uid, token, password: values.password });
      setDone(true);
      window.setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      const fieldErrors = getApiFieldErrors(err);
      if (fieldErrors.password?.length) {
        setFieldError("password", { type: "server", message: fieldErrors.password.join(" ") }, { shouldFocus: true });
      } else {
        setInvalidLink(normalizeAppError(err).code === "password_reset_link_invalid");
        setError(getApiErrorMessage(err));
      }
    }
  }

  return (
    <main className="serenity-login serenity-login--signal-field serenity-login--password-reset">
      <div className="serenity-login__ambient" aria-hidden="true">
        <span /><span /><span /><span /><span />
      </div>
      <section className="glass-panel w-full max-w-lg rounded-[2rem] p-6 sm:p-8">
        <div className="mb-7">
          <div className="mb-4 grid h-14 w-14 place-items-center rounded-3xl bg-brand-500 text-white shadow-glow">
            {done ? <CheckCircle2 size={25} /> : <KeyRound size={25} />}
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-midnight">
            {done ? t("passwordReset.doneTitle") : t("passwordReset.newTitle")}
          </h1>
          <p className="mt-2 text-sm leading-6 text-platforma-faint">
            {done ? t("passwordReset.doneText") : t("passwordReset.newText")}
          </p>
        </div>

        {error ? <div className="mb-5"><ErrorState message={error} /></div> : null}

        {invalidLink ? <Link className="platforma-focus-ring mb-5 inline-flex min-h-11 items-center font-bold text-brand-700 underline" to="/forgot-password">{t("passwordReset.getLink")}</Link> : null}

        {!done && !invalidLink ? (
          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <Input label={t("invite.newPassword")} type="password" autoComplete="new-password" error={errors.password?.message} {...register("password")} />
            <Input label={t("passwordReset.repeatPassword")} type="password" autoComplete="new-password" error={errors.password_confirm?.message} {...register("password_confirm")} />
            <Button variant="primary" className="w-full" type="submit" isLoading={isSubmitting}>
              {t("passwordReset.savePassword")}
            </Button>
          </form>
        ) : null}

        <p className="mt-5 text-center text-sm text-platforma-faint">
          <Link className="font-bold text-brand-700 hover:text-brand-800" to="/login">
            {t("passwordReset.backToLogin")}
          </Link>
        </p>
      </section>
    </main>
  );
}
