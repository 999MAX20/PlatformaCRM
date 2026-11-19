import { useEffect, useId, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input, type InputProps } from "../../../../components/ui/Input";
import { useI18n } from "../../../../lib/i18n";

/** Keep connector secrets out of the browser's username/password form pairing. */
export function CredentialInput({ revealable = false, ...props }: Omit<InputProps, "type" | "autoComplete" | "name"> & { revealable?: boolean }) {
  const id = useId();
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);
  useEffect(() => { if (!props.value) setVisible(false); }, [props.value]);
  return <form autoComplete="off" onSubmit={event => event.preventDefault()}>
    <Input {...props} passwordReveal={false} name={`connector-credential-${id}`} type={visible ? "text" : "password"} autoComplete="new-password"
      rightIcon={revealable ? <button type="button" className="platforma-focus-ring -mr-3 flex h-11 w-11 items-center justify-center rounded-control hover:bg-surface-hover disabled:cursor-not-allowed"
        aria-label={t(visible ? "integrations.setup.hideKey" : "integrations.setup.showKey")} aria-pressed={visible}
        disabled={props.disabled} onClick={() => setVisible(value => !value)}>
        {visible ? <EyeOff size={20} aria-hidden="true" /> : <Eye size={20} aria-hidden="true" />}
      </button> : props.rightIcon}
      onChange={event => {
        // Saved CRM passwords are never intentional connector credentials.
        if (event.currentTarget.matches(":-webkit-autofill")) {
          event.currentTarget.value = String(props.value ?? "");
          return;
        }
        props.onChange?.(event);
      }} />
  </form>;
}
