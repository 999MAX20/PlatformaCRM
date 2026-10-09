import type { BusinessRole, RolePermission } from "../../types";
import type { Translate } from "./settingsUtils";

const scopes = new Set(["none", "own", "team", "business"]);
function scopeValue(value: unknown): RolePermission["scope"] | null {
  return typeof value === "string" && scopes.has(value) ? value as RolePermission["scope"] : null;
}
function presetAction(value: unknown, action: string) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const actions = value as Record<string, unknown>;
  return scopeValue(actions[action]) || scopeValue(actions.manage);
}

// Mirrors the existing explicit -> manage -> preset lookup, without claiming
// object-level/capability access. Custom memberships can have a separate base role.
export function configuredRoleScope(role: BusinessRole, resource: string, action: string, baseRole?: BusinessRole): RolePermission["scope"] | null {
  if ((role.is_system && role.preset_key === "owner") || (baseRole?.is_system && baseRole.preset_key === "owner")) return "business";
  const permission = role.permissions.find(item => item.resource === resource && item.action === action)
    || role.permissions.find(item => item.resource === resource && item.action === "manage");
  if (role.is_active && permission) return permission.is_allowed ? permission.scope : "none";
  const preset = role.is_system ? role : baseRole?.is_system ? baseRole : undefined;
  return preset ? presetAction(preset.permissions_json["*"], action)
    || presetAction(preset.permissions_json[resource], action) || "none" : null;
}

export function settingsRoleName(role: BusinessRole, t: Translate) {
  return role.is_system && ["owner", "admin", "manager", "operator", "specialist"].includes(role.preset_key)
    ? t(`settings.role.${role.preset_key}`) : role.name;
}

export function roleActionLabel(action: string, t: Translate) {
  const key = "settings.redesign.action." + action;
  const label = t(key);
  return label === key ? action : label;
}
