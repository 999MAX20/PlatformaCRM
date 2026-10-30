import { useSettingsTeam } from "./useSettingsTeam";
import { useSettingsMessages } from "./useSettingsMessages";
import { useSettingsQuickReplies } from "./useSettingsQuickReplies";
import { useSettingsCustomFields } from "./useSettingsCustomFields";
import { useSettingsSecurity } from "./useSettingsSecurity";
import { useSettingsBilling } from "./useSettingsBilling";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

import { businessesApi } from "../../api/businesses";

import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import type { Business } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { useSettingsSectionNavigation } from "./hooks/useSettingsSectionNavigation";
import {
  settingsGroupOrder,
  settingsSectionGroupFallback,
  settingsSections,
} from "./settingsConfig";

export function useSettingsModel() {
  const { t, language } = useI18n();

  const confirmAction = useActionConfirm();

  const queryClient = useQueryClient();

  const { business, isLoading } = useActiveBusiness();

  const { user } = useAuth();

  const canViewBilling = hasPermission(user, business?.id, "billing", "view");

  const canViewTeam = hasPermission(user, business?.id, "team", "view");

  const canManageTeam = hasPermission(user, business?.id, "team", "manage");

  const canViewAudit = hasPermission(user, business?.id, "audit_logs", "view");

  const canManageSettings = hasPermission(
    user,
    business?.id,
    "settings",
    "update",
  );

  const canManageConversations = hasPermission(
    user,
    business?.id,
    "conversations",
    "manage",
  );

  async function confirmDelete(label: string, action = "settings.delete") {
    const result = await confirmAction({
      title: t(action),
      description: label ? `${t(action)}: ${label}` : t(action),
      confirmLabel: t(action),
      tone: "danger",
    });
    return result.confirmed;
  }

  const allowedSettingsSections = useMemo(
    () =>
      settingsSections.filter((section) => {
        if (
          section.id === "business-profile" ||
          section.id === "appointment-messages" ||
          section.id === "custom-fields"
        )
          return canManageSettings;
        if (section.id === "team-access") return canViewTeam;
        if (section.id === "roles") return canManageTeam;
        if (section.id === "security-center") return canViewAudit;
        if (section.id === "quick-replies") return canManageConversations;
        if (section.id === "billing" || section.id === "usage")
          return canViewBilling;
        return hasPermission(
          user,
          business?.id,
          section.resource,
          section.action || "view",
        );
      }),
    [
      business?.id,
      canManageConversations,
      canManageSettings,
      canManageTeam,
      canViewAudit,
      canViewBilling,
      canViewTeam,
      user,
    ],
  );

  const {
    activeSettingsSection,
    allowedSettingsSectionIds,
    setActiveSettingsSection,
  } = useSettingsSectionNavigation(allowedSettingsSections);

  const {
    teamMembers,
    teamRoles,
    invitations,
    inviteForm,
    setInviteForm,
    selectedMemberId,
    setSelectedMemberId,
    selectedRoleId,
    setSelectedRoleId,
    roleEditorSource,
    setRoleEditorSource,
    copiedInviteId,
    setCopiedInviteId,
    copyInviteError,
    setCopyInviteError,
    lastCreatedInvite,
    setLastCreatedInvite,
    departments,
    departmentName,
    setDepartmentName,
    updateMemberMutation,
    inviteMutation,
    revokeInvitationMutation,
    departmentMutation,
    members,
    roles,
    canonicalRoleKeys,
    visibleRoles,
    selectedMember,
    selectedMemberRole,
    selectedRole,
    translatedTeamRoleOptions,
    editableTeamRoleOptions,
    inviteUrl,
    inviteMessage,
    inviteShareUrl,
    copyInvitation,
  } = useSettingsTeam({
    business,
    canViewTeam,
    canManageTeam,
    activeSettingsSection,
    queryClient,
    t,
  });
  const {
    appointmentMessageDrafts,
    setAppointmentMessageDrafts,
    appointmentMessageSettings,
    appointmentMessageMutation,
    appointmentMessages,
    appointmentMessageValue,
  } = useSettingsMessages({
    business,
    canManageSettings,
    activeSettingsSection,
    queryClient,
  });
  const {
    quickReplyForm,
    setQuickReplyForm,
    editingQuickReplyId,
    setEditingQuickReplyId,
    quickReplyEditForm,
    setQuickReplyEditForm,
    quickReplies,
    quickReplyMutation,
    updateQuickReplyMutation,
    removeQuickReplyMutation,
    startEditingQuickReply,
    quickReplyChannelOptions,
  } = useSettingsQuickReplies({
    business,
    canManageConversations,
    activeSettingsSection,
    queryClient,
    t,
  });
  const { customFields, updateCustomFieldMutation, removeCustomFieldMutation } =
    useSettingsCustomFields({
      business,
      canManageSettings,
      activeSettingsSection,
      allowedSettingsSectionIds,
      queryClient,
    });
  const { auditLogs, loginHistory, supportGrants } = useSettingsSecurity({
    business,
    canViewAudit,
    activeSettingsSection,
  });
  const { entitlements } = useSettingsBilling({
    business,
    canViewBilling,
    activeSettingsSection,
  });
  const mutation = useMutation({
    mutationFn: (payload: Partial<Business>) =>
      business
        ? businessesApi.update({ id: business.id, payload })
        : businessesApi.create(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["businesses"] }),
  });

  const translatedSettingsSections = allowedSettingsSections
    .filter((section) => section.id !== "roles")
    .map((section) => ({
      ...section,
      label: t(`settings.section.${section.id}`),
      group:
        section.group || settingsSectionGroupFallback[section.id] || "advanced",
    }));

  const translatedSettingsGroups = settingsGroupOrder
    .map((groupKey) => ({
      key: groupKey,
      label: t(`settings.group.${groupKey}`),
      sections: translatedSettingsSections.filter(
        (section) => section.group === groupKey,
      ),
    }))
    .filter((item) => item.sections.length);

  const locale =
    language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";

  return {
    activeSettingsSection,
    allowedSettingsSectionIds,
    allowedSettingsSections,
    appointmentMessageDrafts,
    appointmentMessageMutation,
    appointmentMessageSettings,
    appointmentMessageValue,
    appointmentMessages,
    auditLogs,
    business,
    canManageTeam,
    confirmDelete,
    copiedInviteId,
    copyInvitation,
    copyInviteError,
    customFields,
    departmentMutation,
    departmentName,
    departments,
    editableTeamRoleOptions,
    editingQuickReplyId,
    entitlements,
    invitations,
    inviteForm,
    inviteMutation,
    inviteShareUrl,
    isLoading,
    lastCreatedInvite,
    locale,
    loginHistory,
    members,
    mutation,
    quickReplies,
    quickReplyChannelOptions,
    quickReplyEditForm,
    quickReplyForm,
    quickReplyMutation,
    removeCustomFieldMutation,
    removeQuickReplyMutation,
    revokeInvitationMutation,
    roles,
    selectedMember,
    selectedMemberRole,
    selectedRole,
    roleEditorSource,
    setRoleEditorSource,
    setActiveSettingsSection,
    setAppointmentMessageDrafts,
    setCopyInviteError,
    setDepartmentName,
    setEditingQuickReplyId,
    setInviteForm,
    setLastCreatedInvite,
    setQuickReplyEditForm,
    setQuickReplyForm,
    setSelectedMemberId,
    setSelectedRoleId,
    startEditingQuickReply,
    supportGrants,
    t,
    teamMembers,
    teamRoles,
    translatedSettingsGroups,
    translatedSettingsSections,
    updateCustomFieldMutation,
    updateMemberMutation,
    updateQuickReplyMutation,
    visibleRoles,
  };
}
export type SettingsModel = ReturnType<typeof useSettingsModel>;
