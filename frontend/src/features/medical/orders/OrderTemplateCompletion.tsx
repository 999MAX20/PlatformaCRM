import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { medicalOrdersApi, type OrderPreview, type OrderScope } from "../../../api/medicalOrders";
import { Button } from "../../../components/ui/Button";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function OrderTemplateCompletion({ scope, orderId, hint, text, onChange, onAccept, onDismiss, onDenied, isSaving }: {
  scope: OrderScope; orderId?: number; hint: OrderPreview | null; text: string;
  onChange: (text: string) => void; onAccept: (preview: OrderPreview) => void;
  onDismiss: () => void; onDenied: (cause: unknown) => void; isSaving: () => boolean;
}) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const active = useRef<AbortController | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const [overlay, setOverlay] = useState<CSSProperties | null>(null);
  const [scroll, setScroll] = useState({ left: 0, top: 0 });
  function dismiss() { active.current?.abort(); onDismiss(); input.current?.focus(); }
  const current = useRef({ text, hint, onAccept, isSaving });
  current.current = { text, hint, onAccept, isSaving };
  const scopeKey = JSON.stringify(scope);
  const suffix = hint?.document_text.startsWith(text) ? hint.document_text.slice(text.length) : "";
  useLayoutEffect(() => {
    const element = input.current;
    if (!element) return;
    const measure = () => {
      const style = getComputedStyle(element);
      setOverlay({ left: element.offsetLeft + element.clientLeft, top: element.offsetTop + element.clientTop,
        width: element.clientWidth, height: element.clientHeight, padding: style.padding,
        fontFamily: style.fontFamily, fontSize: style.fontSize, fontWeight: style.fontWeight,
        lineHeight: style.lineHeight, letterSpacing: style.letterSpacing, boxSizing: "border-box" });
      setScroll({ left: element.scrollLeft, top: element.scrollTop });
    };
    measure(); const observer = new ResizeObserver(measure); observer.observe(element);
    return () => observer.disconnect();
  }, [scopeKey, text, hint]);
  useEffect(() => {
    active.current?.abort(); setPending(false); setFailed(false);
    return () => active.current?.abort();
  }, [scopeKey, orderId, text, hint]);

  async function accept() {
    if (!hint || !suffix || pending || isSaving()) return;
    const controller = new AbortController(); active.current = controller;
    setPending(true); setFailed(false);
    try {
      const fresh = await medicalOrdersApi.preview(scope, hint.template_source.approval.version_id, orderId, controller.signal);
      if (controller.signal.aborted || current.current.text !== text || current.current.hint !== hint || current.current.isSaving()) return;
      if (fresh.template_source.source_digest !== hint.template_source.source_digest || fresh.document_text !== hint.document_text ||
          fresh.patient_revision !== hint.patient_revision || fresh.encounter_revision !== hint.encounter_revision ||
          fresh.missing_fields.length || fresh.unknown_fields.length) {
        setFailed(true); return;
      }
      current.current.onAccept(fresh); input.current?.focus();
    } catch (cause) {
      if (!controller.signal.aborted) {
        if (medicalRoleDenied(cause)) onDenied(cause); else setFailed(true);
      }
    } finally { if (!controller.signal.aborted) setPending(false); }
  }
  return <div className="space-y-2" data-testid="order-template-completion">
    <div className="relative">
    <Textarea ref={input} label={t("medical.orders.text")} value={text} maxLength={32768} rows={6}
      onChange={event => onChange(event.target.value)}
      onScroll={event => setScroll({ left: event.currentTarget.scrollLeft, top: event.currentTarget.scrollTop })}
      onKeyDown={event => {
        if (event.key === "Escape" && hint) { event.preventDefault(); event.stopPropagation(); dismiss(); }
        else if (event.key === "Tab" && !event.shiftKey && suffix && !pending) { event.preventDefault(); void accept(); }
      }} />
    {suffix && overlay ? <div aria-hidden="true" data-testid="order-template-ghost"
      className="pointer-events-none absolute overflow-hidden whitespace-pre-wrap break-words" style={overlay}>
      <div style={{ transform: `translate(${-scroll.left}px, ${-scroll.top}px)` }}><span className="text-transparent">{text}</span><span className="text-platforma-subtle">{suffix}</span></div>
    </div> : null}
    </div>
    {hint ? <div className="space-y-2 rounded-card border border-platforma-border p-3">
      <p className="break-words text-sm">{hint.template_source.template.title} · {t("medical.templates.version", { revision: hint.template_source.approval.revision })}</p>
      {suffix ? <p className="sr-only" role="status">{suffix}</p> : <p className="text-sm text-platforma-subtle">{t("medical.assistance.noContinuation")}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="lg" disabled={!suffix || pending} isLoading={pending} onClick={() => void accept()}>{t("medical.assistance.accept")}</Button>
        <Button type="button" size="lg" variant="secondary" onClick={dismiss}>{t("medical.assistance.dismiss")}</Button>
      </div>
    </div> : null}
    {failed ? <p role="alert" className="text-sm">{t("medical.assistance.templateChanged")}</p> : null}
  </div>;
}
