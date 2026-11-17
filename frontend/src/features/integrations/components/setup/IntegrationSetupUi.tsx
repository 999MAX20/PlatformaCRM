import { providerCatalog } from "../../config/providerCatalog";
import { Badge, type BadgeVariant } from "../../../../components/ui/Badge";
import { ToggleSwitch } from "../../../../components/ui/Switch";
import { cn } from "../../../../lib/cn";
import { useI18n } from "../../../../lib/i18n";
import { Link } from "react-router";
import { AppWindow, Link2, Phone, UserRound } from "lucide-react";
import { createContext, useContext, useId, type ComponentProps, type ReactNode } from "react";
import { LoadingState } from "../../../../components/ui/StateViews";
import { Modal } from "../../../../components/ui/Modal";

const SetupDialogContext = createContext(false);

export function MessengerSetupDialog({ title, logo, ...props }: Omit<ComponentProps<typeof Modal>, "title"> & { title: string; logo?: string }) {
  return <Modal {...props} bodyClassName="bg-surface-card! p-4 sm:p-6"
    className="[&>header]:h-auto [&>header]:min-h-16 [&>header]:py-3 sm:[&>header]:px-6 [&>header>h2]:overflow-visible [&>header>h2]:whitespace-normal"
    title={<span className="flex items-center gap-3 text-xl font-bold sm:text-2xl"><ChannelLogo logo={logo} title={title} /><span className="min-w-0 break-words">{title}</span></span>}>
    <SetupDialogContext.Provider value>{props.children}</SetupDialogContext.Provider>
  </Modal>;
}

function ChannelLogo({ logo, title }: { logo?: string; title: string }) {
  return logo ? <span className="shrink-0 [&>img]:h-[44px] [&>img]:w-[44px]"><LogoMark logo={logo} label={title} /></span> :
    <span className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-control bg-surface-muted text-brand-700"><AppWindow size={28} aria-hidden="true" /></span>;
}

export function SetupInstructions({ steps, note }: { steps: string[]; note?: string }) {
  const { t } = useI18n();
  return <section className="space-y-2">
    <h3 className="text-base font-bold text-platforma-text">{t("integrations.setup.howToConnect")}</h3>
    <ol className="list-decimal space-y-1 pl-5 text-sm leading-6 text-platforma-text">
      {steps.map(step => <li key={step} className="pl-1">{step}</li>)}
    </ol>
    {note ? <p className="text-sm leading-5 text-platforma-subtle">{note}</p> : null}
  </section>;
}

export function AccountSelectionHint({ kind, label, hint }: { kind: "phone" | "account"; label: string; hint: string }) {
  const { t } = useI18n();
  const Icon = kind === "phone" ? Phone : UserRound;
  return <div className="space-y-2">
    <p className="text-sm font-semibold text-platforma-text">{label}</p>
    <p className="flex min-h-11 items-center gap-3 rounded-control border border-platforma-border bg-surface-muted px-3 py-2 text-sm text-platforma-subtle">
      <Icon size={20} className="shrink-0" aria-hidden="true" />{t("integrations.setup.chooseInWindow")}
    </p>
    <p className="text-sm leading-5 text-platforma-subtle">{hint}</p>
  </div>;
}

const providerLogos = new Set(
  providerCatalog
    .map((item) => item.logo)
    .filter(Boolean),
);

export function LogoMark({ logo, label, compact = false }: { logo?: string; label: string; compact?: boolean }) {
  const containerClassName = compact ? "h-9 w-9 rounded-control" : "h-11 w-11 rounded-control";

  if (logo && providerLogos.has(logo)) {
    return (
      <img src={logo} alt="" width={compact ? 36 : 44} height={compact ? 36 : 44}
        className={cn("shrink-0 object-contain", compact ? "h-9 w-9" : "h-11 w-11")} />
    );
  }
  return (
    <div className={cn("grid shrink-0 place-items-center bg-brand-500 font-bold text-white", compact ? "text-xs" : "text-sm", containerClassName)}>
      {label.slice(0, 2).toUpperCase()}
    </div>
  );
}

export { ToggleSwitch };


export function MessengerSetupShell({
  logo,
  title,
  description,
  status,
  statusTone = "neutral",
  error,
  children,
  actions,
  instructions,
  advanced,
  advancedOpen,
  advancedLabel,
  onToggleAdvanced,
  channelEnabled,
  channelToggleVisible,
  channelToggleLoading,
  canManage,
  inboxChannel,
  onToggleChannel,
  loading = false,
}: {
  logo?: string;
  title: string;
  description: string;
  status: string;
  statusTone?: "neutral" | "progress" | "success" | "warning";
  error?: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  instructions?: ReactNode;
  advanced?: ReactNode;
  advancedOpen?: boolean;
  advancedLabel?: string;
  onToggleAdvanced?: () => void;
  channelEnabled?: boolean;
  channelToggleVisible?: boolean;
  channelToggleLoading?: boolean;
  canManage: boolean;
  inboxChannel: string;
  onToggleChannel?: (checked: boolean) => void;
  loading?: boolean;
}) {
  const { t } = useI18n();
  const inDialog = useContext(SetupDialogContext);
  const advancedId = useId();
  const resolvedAdvancedLabel = advancedLabel || t("integrations.setup.needHelp");
  const statusVariant: Record<NonNullable<typeof statusTone>, BadgeVariant> = {
    neutral: "neutral",
    progress: "info",
    success: "success",
    warning: "warning",
  };

  return (
    <div className="w-full min-w-0 space-y-5">
      {!inDialog ? <div className="flex items-center gap-3 border-b border-platforma-border pb-4">
        <ChannelLogo logo={logo} title={title} /><h2 className="text-xl font-bold text-platforma-text">{title}</h2>
      </div> : null}
      {description ? <p className="text-sm leading-6 text-platforma-text">{description}</p> : null}
      {error}
      {loading ? <LoadingState /> : children}
      {!loading ? instructions : null}

      {!loading && advanced ? (
        <div>
          <button type="button" className="platforma-focus-ring min-h-11 text-sm font-bold text-brand-700" aria-expanded={Boolean(advancedOpen)} aria-controls={advancedId} onClick={onToggleAdvanced}>
            {advancedOpen ? t("integrations.setup.hideManualSetup") : resolvedAdvancedLabel}
          </button>
          {advancedOpen ? <div id={advancedId} className="mt-3 rounded-card border border-platforma-border bg-surface-muted p-4">{advanced}</div> : null}
        </div>
      ) : null}

      {!loading ? <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-t border-platforma-border pt-4">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={statusVariant[statusTone]}>{status}</Badge>
        {!loading && channelToggleVisible && onToggleChannel ? (
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-platforma-text">{t("integrations.setup.channelEnabled")}</span>
            <ToggleSwitch
              checked={Boolean(channelEnabled)}
              disabled={!canManage}
              isLoading={channelToggleLoading}
              label={t("integrations.setup.toggleChannel", { title })}
              onChange={onToggleChannel}
            />
          </div>
        ) : null}
        {channelToggleVisible ? <Link className="platforma-focus-ring inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-platforma-subtle hover:text-platforma-text" to={`/app/conversations?channel=${inboxChannel}`}>
          <Link2 size={16} aria-hidden="true" />{t("integrations.setup.openMessages")}
        </Link> : null}
        </div>
        {actions ? <div className="ml-auto flex flex-wrap justify-end gap-2 [&_button]:min-h-11">{actions}</div> : null}
      </div> : null}
    </div>
  );
}
