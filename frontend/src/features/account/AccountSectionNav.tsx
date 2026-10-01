import { Bell, Settings2, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";

import { useI18n } from "../../lib/i18n";

const sections = [
  { id: "profile", label: "account.profileEyebrow", icon: UserRound },
  { id: "interface", label: "account.interfaceTitle", icon: Settings2 },
  { id: "security", label: "account.loginHistoryEyebrow", icon: ShieldCheck },
  { id: "notifications", label: "account.notificationsEyebrow", icon: Bell },
] as const;

export function AccountSectionNav() {
  const { t } = useI18n();
  const [active, setActive] = useState<string>("profile");

  useEffect(() => {
    let frame = 0;
    function update() {
      frame = 0;
      const threshold = window.innerWidth >= 1280 ? 100 : 152;
      let current: string = sections[0].id;
      for (const section of sections) {
        if ((document.getElementById(section.id)?.getBoundingClientRect().top ?? Infinity) <= threshold) current = section.id;
      }
      if (window.scrollY > 0 && window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) current = sections.at(-1)!.id;
      setActive(current);
    }
    function schedule() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    const observer = new ResizeObserver(schedule);
    for (const section of sections) {
      const element = document.getElementById(section.id);
      if (element) observer.observe(element);
    }
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    schedule();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, []);

  return (
    <div className="account-section-nav-rail">
    <nav aria-label={t("account.sectionNavigation")} className="grid grid-cols-4 gap-1 rounded-card border border-platforma-border bg-surface-card p-2 shadow-soft xl:sticky xl:top-20 xl:mx-auto xl:w-14 xl:grid-cols-1 2xl:w-48">
      {sections.map(({ id, label, icon: Icon }) => (
        <a key={id} href={`#${id}`} title={t(label)} aria-current={active === id ? "location" : undefined}
          className={`platforma-focus-ring flex min-h-11 items-center justify-center gap-2 rounded-control px-1 py-2 text-center text-xs font-semibold 2xl:justify-start 2xl:text-left 2xl:text-sm ${active === id ? "bg-brand-50 text-brand-700" : "text-platforma-subtle hover:bg-surface-hover"}`}>
          <Icon size={17} className="hidden shrink-0 xl:block" aria-hidden="true" />
          <span className="xl:sr-only 2xl:not-sr-only">{t(label)}</span>
        </a>
      ))}
    </nav>
    </div>
  );
}
