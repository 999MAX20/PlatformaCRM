import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, Search } from "lucide-react";
import { useState } from "react";
import { teamApi } from "../../../api/team";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { permissionResourceLabel } from "../../../lib/permissions";
import type { BusinessRole, Id, RolePermission } from "../../../types";
import { SettingsFeedback, SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { configuredRoleScope, roleActionLabel, settingsRoleName } from "../roleAccess";
import { translatedVisibilityLabel } from "../settingsUtils";
import type { SettingsModel } from "../useSettingsModel";

type PermissionDraft = Pick<RolePermission, "scope" | "is_allowed">;
type SavePermission = { key: string; roleId: Id; permissionId?: Id; resource: string; action: string; draft: PermissionDraft; };

export function RolesSection({ model }: { model: SettingsModel; }) {
  const { t, business, visibleRoles, selectedRole, setSelectedRoleId, teamRoles, canManageTeam, activeSettingsSection } = model;
  const [search, setSearch] = useState("");
  const [drafts, setDrafts] = useState<Record<string, PermissionDraft>>({});
  const cache = useQueryClient();
  const catalog = useQuery({ queryKey: ["team-permission-catalog"], queryFn: teamApi.catalog, staleTime: 300_000 });
  const save = useMutation({
    mutationFn: (value: SavePermission) => value.permissionId
      ? teamApi.updatePermission({ id: value.permissionId, payload: value.draft })
      : teamApi.createPermission({ business_role: value.roleId, resource: value.resource, action: value.action, ...value.draft }),
    onSuccess: (permission, value) => {
      cache.setQueryData<BusinessRole[]>(["team-roles", business?.id], roles => roles?.map(role => String(role.id) !== String(value.roleId) ? role : {
        ...role, permissions: [...role.permissions.filter(item => String(item.id) !== String(permission.id)), permission],
      }));
      setDrafts(current => { const next = { ...current }; delete next[value.key]; return next; });
      void cache.invalidateQueries({ queryKey: ["team-roles", business?.id] });
      void cache.invalidateQueries({ queryKey: ["auth-me"] });
    },
  });
  const owner = selectedRole?.is_system && selectedRole.preset_key === "owner";
  const filter = search.trim().toLocaleLowerCase();
  const resources = (catalog.data?.resources || []).map(item => ({
    ...item, actions: item.actions.filter(action => !filter || (permissionResourceLabel(item.resource, t) + " " + roleActionLabel(action, t)).toLocaleLowerCase().includes(filter)),
  })).filter(item => item.actions.length);
  return <SettingsSection id="roles" active={activeSettingsSection} title={t("settings.section.roles")} actions={<Button type="button" variant="ghost" disabled={save.isPending}
      onClick={() => { model.setActiveSettingsSection("team-access"); window.location.hash = "team-access"; }}>
      <ArrowLeft size={16} />{t(model.roleEditorSource === "invite" ? "settings.workflow.backToInvitation" : model.roleEditorSource === "member" ? "settings.workflow.backToEmployee" : "settings.section.team-access")}
    </Button>}>
    <div className="space-y-4 p-4 sm:p-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <Select label={t("settings.role")} value={selectedRole ? String(selectedRole.id) : ""} disabled={save.isPending || !visibleRoles.length}
          onChange={event => setSelectedRoleId(Number(event.target.value))}
          options={visibleRoles.map(role => ({ value: String(role.id), label: settingsRoleName(role, t) }))} />
        <Input label={t("common.search")} leftIcon={<Search size={16} />} placeholder={t("settings.redesign.permissionSearch")} value={search} onChange={event => setSearch(event.target.value)} />
      </div>
      <SettingsQueryState queries={[teamRoles, catalog]} />
      {teamRoles.isSuccess && !visibleRoles.length && <p className="text-sm text-platforma-subtle">{t("settings.noRoles")}</p>}
      {selectedRole && !teamRoles.isError && !catalog.isError && <>
        <p className="text-sm text-platforma-subtle">{t(owner ? "settings.redesign.ownerAccess" : "settings.redesign.roleApplies")}</p>
        <div className="divide-y divide-platforma-border rounded-card border border-platforma-border">
          {resources.map(({ resource, actions }, resourceIndex) => <details key={String(selectedRole.id) + resource} open={filter || resourceIndex === 0 ? true : undefined} className="group" name={filter ? undefined : "role-resource-" + selectedRole.id}>
            <summary className="platforma-focus-ring flex min-h-12 cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-bold text-platforma-text">
              <span className="min-w-0 flex-1">{permissionResourceLabel(resource, t)}</span>
              <span className="hidden text-xs font-medium text-platforma-subtle sm:inline">{[...new Set(actions.map(action => {
                const scope = configuredRoleScope(selectedRole, resource, action);
                return scope === null ? t("settings.redesign.permissionInherited") : scope !== "none" ? roleActionLabel(action, t) : null;
              }).filter(Boolean))].join(" · ") || translatedVisibilityLabel("none", t)}</span>
              <ChevronDown aria-hidden="true" size={16} className="shrink-0 text-platforma-subtle group-open:rotate-180" />
            </summary>
            <div className="border-t border-platforma-border px-3 sm:px-4">
              <div className="hidden grid-cols-[minmax(0,1.2fr)_72px_minmax(120px,1fr)_minmax(100px,0.8fr)] gap-3 border-b border-platforma-border py-2 text-xs text-platforma-subtle md:grid">
                <span>{t("settings.redesign.action")}</span><span>{t("settings.redesign.access")}</span><span>{t("settings.redesign.scope")}</span><span />
              </div>
              {actions.map(action => {
                const key = String(selectedRole.id) + ":" + resource + ":" + action;
                const permission = selectedRole.permissions.find(item => item.resource === resource && item.action === action);
                const inheritedScope = configuredRoleScope(selectedRole, resource, action);
                const baseline: PermissionDraft = permission ? { scope: permission.scope, is_allowed: permission.is_allowed } : { scope: inheritedScope || "none", is_allowed: Boolean(inheritedScope && inheritedScope !== "none") };
                const value = drafts[key] || baseline;
                const enabled = value.is_allowed && value.scope !== "none";
                const inheritedUnknown = !permission && inheritedScope === null;
                const dirty = Boolean(drafts[key] && (inheritedUnknown || value.is_allowed !== baseline.is_allowed || value.scope !== baseline.scope));
                const thisSave = save.variables?.key === key;
                const label = permissionResourceLabel(resource, t) + " · " + roleActionLabel(action, t);
                function change(next: PermissionDraft) { setDrafts(current => ({ ...current, [key]: next })); if (thisSave) save.reset(); }
                return <div key={action} className="border-b border-platforma-border py-3 last:border-b-0">
                  <div className="grid items-center gap-3 md:grid-cols-[minmax(0,1.2fr)_72px_minmax(120px,1fr)_minmax(100px,0.8fr)]">
                    <div><p className="text-sm font-semibold">{roleActionLabel(action, t)}</p>{!permission && !owner && <p className="mt-1 text-xs text-platforma-subtle">{t("settings.redesign.permissionInherited")}</p>}</div>
                    <label className="flex min-h-11 items-center gap-2 text-sm">
                      <input type="checkbox" aria-label={label + " · " + t("settings.redesign.access")} className="h-5 w-5 accent-brand-500"
                        checked={owner || enabled} disabled={owner || !canManageTeam || save.isPending}
                        ref={input => { if (input) input.indeterminate = inheritedUnknown && !drafts[key]; }}
                        onChange={event => change({ is_allowed: event.target.checked, scope: event.target.checked && value.scope === "none" ? "own" : value.scope })} />
                      <span className="md:sr-only">{t("settings.redesign.access")}</span>
                    </label>
                    <Select aria-label={label + " · " + t("settings.redesign.scope")} value={owner ? "business" : inheritedUnknown && !drafts[key] ? "" : value.scope}
                      disabled={owner || !canManageTeam || !enabled || save.isPending}
                      options={[...(inheritedUnknown && !drafts[key] ? [{ value: "", label: t("settings.redesign.permissionInherited") }] : []), ...(value.scope === "none" ? ["none", "own", "team", "business"] : ["own", "team", "business"]).map(scope => ({ value: scope, label: translatedVisibilityLabel(scope, t) }))]}
                      onChange={event => change({ ...value, scope: event.target.value as RolePermission["scope"] })} />
                    <div className="flex flex-wrap gap-2">
                      {dirty && <>
                        <Button type="button" size="sm" isLoading={thisSave && save.isPending} disabled={save.isPending || !canManageTeam}
                          aria-label={t("common.save") + " · " + label}
                          onClick={() => save.mutate({ key, roleId: selectedRole.id, permissionId: permission?.id, resource, action, draft: value })}>{t("common.save")}</Button>
                        <Button type="button" size="sm" variant="ghost" disabled={save.isPending} aria-label={t("common.cancel") + " · " + label}
                          onClick={() => { setDrafts(current => { const next = { ...current }; delete next[key]; return next; }); if (thisSave) save.reset(); }}>{t("common.cancel")}</Button>
                      </>}
                      {thisSave && save.isSuccess && <SettingsFeedback saved />}
                    </div>
                  </div>
                  {thisSave && save.error && <div className="mt-3"><SettingsFeedback error={save.error} /></div>}
                </div>;
              })}
            </div>
          </details>)}
        </div>
        {!resources.length && catalog.isSuccess && <p className="py-4 text-sm text-platforma-subtle">{t("settings.redesign.noMatches")}</p>}
        <p className="text-xs leading-5 text-platforma-subtle">{t("settings.redesign.roleScopeNote")}</p>
      </>}
    </div>
  </SettingsSection>;
}
