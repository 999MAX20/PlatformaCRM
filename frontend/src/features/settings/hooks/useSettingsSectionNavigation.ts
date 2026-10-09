import { useEffect, useMemo, useState } from "react";
import type { SettingsSectionConfig } from "../settingsConfig";

export function useSettingsSectionNavigation(allowedSettingsSections: SettingsSectionConfig[]) {
  const [activeSettingsSection, setActiveSettingsSection] = useState(() => window.location.hash.replace("#", "") || "business-profile");
  const allowedSettingsSectionIds = useMemo(() => new Set(allowedSettingsSections.map(section => section.id)), [allowedSettingsSections]);

  useEffect(() => {
    function handleHashChange() {
      setActiveSettingsSection(window.location.hash.replace("#", "") || "business-profile");
      window.setTimeout(() => window.scrollTo({ top: 0, behavior: "instant" }), 0);
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    if (!allowedSettingsSections.length || allowedSettingsSectionIds.has(activeSettingsSection)) return;
    const next = allowedSettingsSections[0].id;
    setActiveSettingsSection(next);
    window.history.replaceState(window.history.state, "", "#" + next);
  }, [activeSettingsSection, allowedSettingsSectionIds, allowedSettingsSections]);

  return { activeSettingsSection, allowedSettingsSectionIds, setActiveSettingsSection };
}
