import palette from "../../src/theme/semantic-tokens.json";

type PlatformaCRMWidgetOptions = {
  publicToken: string;
  apiUrl?: string;
  position?: "right" | "left";
};

type ConversationResponse = {
  conversation_id: string;
  message_id: number;
  status: string;
};

declare global {
  interface Window {
    /** Compatibility for existing embedded widgets. */
    ZaniWidget?: { init: (options: PlatformaCRMWidgetOptions) => void };
    PlatformaCRMWidget?: {
      init: (options: PlatformaCRMWidgetOptions) => void;
    };
  }
}

const colorVariables = Object.entries(palette.tokens).map(([name, value]) => `--color-${name.replaceAll(".", "-")}:${value}`).join(";");

const styles = `
.platforma-widget-root{${colorVariables};position:fixed;z-index:2147483000;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--color-text-primary)}
.platforma-widget-root[data-position="right"]{right:22px;bottom:22px}
.platforma-widget-root[data-position="left"]{left:22px;bottom:22px}
.platforma-bubble{display:grid;place-items:center;width:64px;height:64px;border:0;border-radius:24px;background:var(--color-brand-default);color:var(--color-text-inverse);box-shadow:0 18px 45px var(--color-focus-halo);cursor:pointer;transition:transform .18s ease,box-shadow .18s ease}
.platforma-bubble:hover{transform:translateY(-2px);background:var(--color-brand-hover);box-shadow:0 22px 60px var(--color-focus-halo)}
.platforma-panel{position:absolute;right:0;bottom:78px;width:min(380px,calc(100vw - 32px));overflow:hidden;border:1px solid var(--color-border-default);border-radius:28px;background:var(--color-surface-default);box-shadow:0 28px 90px color-mix(in srgb,var(--color-text-primary) 22%,transparent);backdrop-filter:blur(18px)}
.platforma-widget-root[data-position="left"] .platforma-panel{left:0;right:auto}
.platforma-panel[hidden]{display:none}
.platforma-header{padding:18px 18px 14px;background:var(--color-brand-pressed);color:var(--color-text-inverse)}
.platforma-title{margin:0;font-size:16px;font-weight:800}
.platforma-subtitle{margin:4px 0 0;font-size:13px;color:var(--color-text-inverse)}
.platforma-body{display:grid;gap:10px;max-height:360px;overflow:auto;padding:16px;background:var(--color-surface-canvas)}
.platforma-message{max-width:86%;border-radius:18px;padding:10px 12px;font-size:13px;line-height:1.45}
.platforma-message.system{background:var(--color-info-soft);color:var(--color-info-content)}
.platforma-message.user{justify-self:end;background:var(--color-brand-default);color:var(--color-text-inverse)}
.platforma-message.status{background:var(--color-surface-subtle);color:var(--color-text-secondary)}
.platforma-form{display:grid;gap:8px;padding:14px;border-top:1px solid var(--color-border-default);background:var(--color-surface-default)}
.platforma-input{min-height:42px;border:1px solid var(--color-border-control);border-radius:16px;padding:0 12px;font:inherit;font-size:14px;background:var(--color-surface-default);color:var(--color-text-primary);outline:none}
.platforma-input::placeholder{color:var(--color-text-muted)}
.platforma-input:hover{border-color:var(--color-brand-default)}
.platforma-input:focus{border-color:var(--color-focus-ring);box-shadow:0 0 0 4px var(--color-focus-halo)}
.platforma-actions{display:flex;gap:8px}
.platforma-actions .platforma-input{flex:1}
.platforma-send{min-width:92px;border:0;border-radius:16px;background:var(--color-brand-default);color:var(--color-text-inverse);font-weight:800;cursor:pointer}
.platforma-send:hover{background:var(--color-brand-hover)}
.platforma-send:active,.platforma-bubble:active{background:var(--color-brand-pressed)}
.platforma-send:focus-visible,.platforma-bubble:focus-visible,.platforma-input:focus-visible{outline:2px solid var(--color-focus-ring);outline-offset:2px}
.platforma-send:disabled{background:var(--color-disabled-surface);color:var(--color-disabled-content);box-shadow:inset 0 0 0 1px var(--color-disabled-border);opacity:1;cursor:not-allowed}
`;

class PlatformaCRMWidgetController {
  private options: PlatformaCRMWidgetOptions;
  private conversationId: string | null = null;
  private root: HTMLDivElement;
  private panel: HTMLDivElement;
  private body: HTMLDivElement;
  private input: HTMLInputElement;
  private nameInput: HTMLInputElement;
  private phoneInput: HTMLInputElement;
  private sendButton: HTMLButtonElement;

  constructor(options: PlatformaCRMWidgetOptions) {
    this.options = options;
    this.root = document.createElement("div");
    this.panel = document.createElement("div");
    this.body = document.createElement("div");
    this.input = document.createElement("input");
    this.nameInput = document.createElement("input");
    this.phoneInput = document.createElement("input");
    this.sendButton = document.createElement("button");
    this.mount();
  }

  private mount() {
    injectStyles();
    this.root.className = "platforma-widget-root";
    this.root.dataset.position = this.options.position || "right";

    const bubble = document.createElement("button");
    bubble.className = "platforma-bubble";
    bubble.type = "button";
    bubble.innerHTML = "✦";
    bubble.ariaLabel = "Open PlatformaCRM chat";

    this.panel.className = "platforma-panel";
    this.panel.hidden = true;
    this.panel.innerHTML = `
      <div class="platforma-header">
        <p class="platforma-title">PlatformaCRM chat</p>
        <p class="platforma-subtitle">Напишите нам, и менеджер увидит сообщение в CRM.</p>
      </div>
    `;

    this.body.className = "platforma-body";
    this.panel.appendChild(this.body);
    this.addMessage("system", "Здравствуйте! Чем можем помочь?");

    const form = document.createElement("form");
    form.className = "platforma-form";
    this.nameInput.className = "platforma-input";
    this.nameInput.placeholder = "Ваше имя";
    this.phoneInput.className = "platforma-input";
    this.phoneInput.placeholder = "Телефон";
    this.input.className = "platforma-input";
    this.input.placeholder = "Сообщение...";
    this.sendButton.className = "platforma-send";
    this.sendButton.type = "submit";
    this.sendButton.textContent = "Send";

    const actions = document.createElement("div");
    actions.className = "platforma-actions";
    actions.append(this.input, this.sendButton);
    form.append(this.nameInput, this.phoneInput, actions);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.send();
    });
    this.panel.appendChild(form);

    bubble.addEventListener("click", () => {
      this.panel.hidden = !this.panel.hidden;
      if (!this.panel.hidden) this.input.focus();
    });

    this.root.append(this.panel, bubble);
    document.body.appendChild(this.root);
  }

  private async send() {
    const text = this.input.value.trim();
    if (!text || this.sendButton.disabled) return;
    this.sendButton.disabled = true;
    this.addMessage("user", text);
    this.input.value = "";

    try {
      const response = this.conversationId ? await this.appendMessage(text) : await this.createConversation(text);
      this.conversationId = response.conversation_id;
      this.addMessage("status", "Сообщение отправлено. Мы скоро ответим.");
    } catch (error) {
      this.addMessage("status", "Не удалось отправить сообщение. Попробуйте позже.");
    } finally {
      this.sendButton.disabled = false;
    }
  }

  private async createConversation(message: string) {
    return this.request<ConversationResponse>(`/api/public/website-chat/${this.options.publicToken}/conversations/`, {
      full_name: this.nameInput.value.trim(),
      phone: this.phoneInput.value.trim(),
      message,
      external_user_id: getVisitorId(),
    });
  }

  private async appendMessage(message: string) {
    return this.request<ConversationResponse>(
      `/api/public/website-chat/${this.options.publicToken}/conversations/${this.conversationId}/messages/`,
      { message, external_user_id: getVisitorId() },
    );
  }

  private async request<T>(path: string, payload: Record<string, unknown>) {
    const response = await fetch(`${this.apiUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`PlatformaCRM widget request failed: ${response.status}`);
    return response.json() as Promise<T>;
  }

  private apiUrl() {
    return (this.options.apiUrl || "").replace(/\/$/, "");
  }

  private addMessage(type: "system" | "user" | "status", text: string) {
    const node = document.createElement("div");
    node.className = `platforma-message ${type}`;
    node.textContent = text;
    this.body.appendChild(node);
    this.body.scrollTop = this.body.scrollHeight;
  }
}

function injectStyles() {
  if (document.getElementById("platforma-widget-styles")) return;
  const style = document.createElement("style");
  style.id = "platforma-widget-styles";
  style.textContent = styles;
  document.head.appendChild(style);
}

function getVisitorId() {
  const key = "zani_widget_visitor_id";
  const current = localStorage.getItem(key);
  if (current) return current;
  const value = crypto.randomUUID ? crypto.randomUUID() : `visitor-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(key, value);
  return value;
}

function init(options: PlatformaCRMWidgetOptions) {
  if (!options.publicToken) {
    console.warn("PlatformaCRMWidget: publicToken is required.");
    return;
  }
  new PlatformaCRMWidgetController(options);
}

window.PlatformaCRMWidget = { init };
window.ZaniWidget = window.PlatformaCRMWidget;

const currentScript = document.currentScript as HTMLScriptElement | null;
const token = (currentScript?.dataset.platformaToken || currentScript?.dataset.zaniToken);
if (token) {
  init({
    publicToken: token,
    apiUrl: currentScript?.dataset.platformaApi || currentScript?.dataset.zaniApi || "",
    position: (currentScript?.dataset.platformaPosition || currentScript?.dataset.zaniPosition) === "left" ? "left" : "right",
  });
}
