import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, Send } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { z } from "zod";

import { requestPasswordReset } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { ErrorState } from "../../components/ui/StateViews";
import { StatusNotice } from "../../components/ui/StatusNotice";
import { useI18n } from "../../lib/i18n";

type FormValues = {
  email: string;
};

export function ForgotPasswordPage() {
  const { t } = useI18n();
  const schema = z.object({
    email: z.string().email(t("validation.email")),
  });
  const [error, setError] = useState<string | null>(null);
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });
  async function onSubmit(values: FormValues) {
    setError(null);
    setRequestMessage(null);
    try {
      const response = await requestPasswordReset({ ...values, delivery_channel: "email" });
      setRequestMessage(response.message);
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-soft-mesh px-4 py-8">
      <section className="glass-panel w-full max-w-lg rounded-[2rem] p-6 sm:p-8">
        <div className="mb-7">
          <div className="mb-4 grid h-14 w-14 place-items-center rounded-3xl bg-ai-gradient text-white shadow-glow">
            <KeyRound size={25} />
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-midnight">{t("passwordReset.requestTitle")}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            {t("passwordReset.requestText")}
          </p>
        </div>

        {error ? <div className="mb-5"><ErrorState message={error} /></div> : null}
        {requestMessage ? <StatusNotice className="mb-5" tone="success" title={requestMessage} /> : null}

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <Input label={t("common.email")} type="email" error={errors.email?.message} {...register("email")} />
          <Button variant="primary" className="w-full" type="submit" isLoading={isSubmitting}>
            {t("passwordReset.getLink")}
            <Send size={18} />
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          {t("passwordReset.remembered")}{" "}
          <Link className="font-bold text-brand-700 hover:text-brand-800" to="/login">
            {t("auth.submit")}
          </Link>
        </p>
      </section>
    </main>
  );
}
