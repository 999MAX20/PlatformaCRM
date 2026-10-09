import { Select } from "../../../components/ui/Select";
import type { SettingsGroupKey } from "../settingsConfig";

type Section = { id: string; label: string; };
type Props = {
  activeSettingsSection: string;
  setActiveSettingsSection: (id: string) => void;
  translatedSettingsGroups: { key: SettingsGroupKey; label: string; sections: Section[]; }[];
  translatedSettingsSections: Section[];
  navigationTitle: string;
};

export function SettingsNavigation({ activeSettingsSection, setActiveSettingsSection, translatedSettingsGroups, translatedSettingsSections, navigationTitle }: Props) {
  return <aside className="min-w-0 lg:sticky lg:top-20 lg:max-h-[calc(100dvh-96px)] lg:self-start lg:overflow-y-auto">
    <div className="lg:hidden"><Select label={navigationTitle} value={activeSettingsSection === "roles" ? "team-access" : activeSettingsSection}
      onChange={event => { setActiveSettingsSection(event.target.value); window.location.hash = event.target.value; }}
      options={translatedSettingsSections.map(section => ({ value: section.id, label: section.label }))} /></div>
    <nav aria-label={navigationTitle} className="hidden space-y-3 py-1 lg:block">
      {translatedSettingsGroups.map(group => <div key={group.key}>
        <p className="mb-1 text-xs font-bold uppercase text-platforma-subtle">{group.label}</p>
        <div className="space-y-1">
          {group.sections.map(section => <a key={section.id} href={"#" + section.id}
            aria-current={(activeSettingsSection === section.id || activeSettingsSection === "roles" && section.id === "team-access") ? "page" : undefined}
            className={"platforma-focus-ring flex min-h-11 items-center rounded-control px-3 py-2 text-sm font-semibold transition-colors " + ((activeSettingsSection === section.id || activeSettingsSection === "roles" && section.id === "team-access") ? "bg-brand-50 text-brand-700" : "text-platforma-subtle hover:bg-surface-hover hover:text-platforma-text")}
            onClick={event => { if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) setActiveSettingsSection(section.id); }}>
            {section.label}
          </a>)}
        </div>
      </div>)}
    </nav>
  </aside>;
}
