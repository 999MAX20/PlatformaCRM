import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { appointmentMessageSettingsApi } from "../../api/appointments";
import { billingApi } from "../../api/billing";
import { businessesApi } from "../../api/businesses";
import { customFieldsApi } from "../../api/customFields";
import { notificationsApi } from "../../api/notifications";
import { quickRepliesApi } from "../../api/quickReplies";
import { securityApi } from "../../api/security";
import { teamApi } from "../../api/team";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import {
  canonicalBusinessRole,
  hasPermission
} from "../../lib/permissions";
import type {
  AppointmentMessageSetting,
  Business,
  BusinessInvitation,
  BusinessMembershipSummary,
  CustomFieldDefinition,
  Id,
  Notification,
  NotificationPreference,
  QuickReplyTemplate
} from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { useSettingsSectionNavigation } from "./hooks/useSettingsSectionNavigation";
import {
  settingsGroupOrder,
  settingsSectionGroupFallback,
  settingsSections,
  teamRoleOptions
} from "./settingsConfig";

export function useSettingsModel() {
  const { t, language } = useI18n();

  const confirmAction = useActionConfirm();

  const queryClient = useQueryClient();

  const { business, isLoading } = useActiveBusiness();

  const { user } = useAuth();

  const canViewBilling = hasPermission(user, business?.id, "billing", "view");

  const canManageBilling = hasPermission(
    user,
    business?.id,
    "billing",
    "manage",
  );

  const canViewTeam = hasPermission(user, business?.id, "team", "view");

  const canManageTeam = hasPermission(user, business?.id, "team", "manage");

  const canViewAudit = hasPermission(user, business?.id, "audit_logs", "view");

  const canManageSettings = hasPermission(
    user,
    business?.id,
    "settings",
    "update",
  );

  const canViewNotifications = hasPermission(
    user,
    business?.id,
    "notifications",
    "view",
  );

  const canManageConversations = hasPermission(
    user,
    business?.id,
    "conversations",
    "manage",
  );

  const canUpdateNotifications = hasPermission(user, business?.id, "notifications", "update");

  async function confirmDelete(label: string, action = "settings.delete") {
    const result = await confirmAction({
      title: t(action),
      description: label
        ? `${t(action)}: ${label}`
        : t(action),
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
        if (section.id === "notification-preferences")
          return canViewNotifications;
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
      canViewNotifications,
      canViewTeam,
      user,
    ],
  );

  const {
    activeSettingsSection,
    allowedSettingsSectionIds,
    setActiveSettingsSection,
  } = useSettingsSectionNavigation(allowedSettingsSections);

  const subscription = useQuery({
    queryKey: ["current-subscription", business?.id],
    queryFn: () => billingApi.currentSubscription(business!.id),
    enabled: Boolean(business && canViewBilling),
  });

  const plans = useQuery({
    queryKey: ["billing-plans"],
    queryFn: billingApi.plans,
    enabled: Boolean(canViewBilling),
  });

  const entitlements = useQuery({
    queryKey: ["billing-entitlements", business?.id],
    queryFn: () => billingApi.entitlements(business!.id),
    enabled: Boolean(business && canViewBilling),
  });

  const customFields = useQuery({
    queryKey: ["custom-fields", business?.id],
    queryFn: () => customFieldsApi.listAll({ business: business?.id }),
    enabled: Boolean(
      business &&
      canManageSettings &&
      allowedSettingsSectionIds.has("custom-fields"),
    ),
  });

  const teamMembers = useQuery({
    queryKey: ["team-members", business?.id],
    queryFn: () => teamApi.allMembers(business?.id),
    enabled: Boolean(business && canViewTeam),
  });

  const teamRoles = useQuery({
    queryKey: ["team-roles", business?.id],
    queryFn: () => teamApi.allRoles(business?.id),
    enabled: Boolean(business && canViewTeam),
  });

  const invitations = useQuery({
    queryKey: ["team-invitations", business?.id],
    queryFn: () => teamApi.allInvitations(business?.id),
    enabled: Boolean(business && canManageTeam),
  });

  const [inviteForm, setInviteForm] = useState({
    email: "",
    phone: "",
    telegram: "",
    full_name: "",
    role: "operator" as BusinessMembershipSummary["role"],
    delivery_channel: "whatsapp" as
      "email" | "whatsapp" | "telegram" | "manual",
  });

  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);

  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);

  const [copiedInviteId, setCopiedInviteId] = useState<number | null>(null);

  const [copyInviteError, setCopyInviteError] = useState("");

  const [lastCreatedInvite, setLastCreatedInvite] =
    useState<BusinessInvitation | null>(null);

  const departments = useQuery({
    queryKey: ["team-departments", business?.id],
    queryFn: () => teamApi.allDepartments(business?.id),
    enabled: Boolean(business && canViewTeam),
  });

  const [departmentName, setDepartmentName] = useState("");

  const [quickReplyForm, setQuickReplyForm] = useState({
    title: "",
    text: "",
    category: "",
    channel: "all",
  });

  const [appointmentMessageDrafts, setAppointmentMessageDrafts] = useState<
    Record<number, Partial<AppointmentMessageSetting>>
  >({});

  const [billingSettingsForm, setBillingSettingsForm] = useState({
    billing_email: "",
    payment_method: "",
    invoice_name: "",
    invoice_tax_id: "",
    invoice_address: "",
  });

  const [selectedPlanId, setSelectedPlanId] = useState("");

  const securityRisk = useQuery({
    queryKey: ["security-risk", business?.id],
    queryFn: () => securityApi.riskSummary(business?.id),
    enabled: Boolean(business && canViewAudit),
    retry: false,
  });

  const auditLogs = useQuery({
    queryKey: ["security-audit", business?.id],
    queryFn: () => securityApi.audit({ business: business?.id }),
    enabled: Boolean(business && canViewAudit),
    retry: false,
  });

  const loginHistory = useQuery({
    queryKey: ["security-login-history", business?.id],
    queryFn: () => securityApi.loginHistory({ business: business?.id }),
    enabled: Boolean(business && canViewAudit),
    retry: false,
  });

  const supportGrants = useQuery({
    queryKey: ["security-support-grants", business?.id],
    queryFn: () => securityApi.supportGrants.listAll({ business: business?.id }),
    enabled: Boolean(business && canViewAudit),
    retry: false,
  });

  const appointmentMessageSettings = useQuery({
    queryKey: ["appointment-message-settings", business?.id],
    queryFn: () =>
      appointmentMessageSettingsApi.list({ business: business?.id }),
    enabled: Boolean(business?.id && canManageSettings),
  });

  const notificationPreferences = useQuery({
    queryKey: ["notification-preferences", business?.id, user?.id],
    queryFn: () => notificationsApi.preferences.listAll({ business: business?.id, user: "me" }),
    enabled: Boolean(business?.id && user?.id && canViewNotifications),
  });

  const preferenceByCategory = useMemo(
    () =>
      new Map(
        (notificationPreferences.data || []).map((preference) => [
          preference.category,
          preference,
        ]),
      ),
    [notificationPreferences.data],
  );

  useEffect(() => {
    const current = subscription.data;
    if (!current) return;
    const details = current.invoice_details_json || {};
    setBillingSettingsForm({
      billing_email: current.billing_email || "",
      payment_method: current.payment_method || "",
      invoice_name: String(details.name || ""),
      invoice_tax_id: String(details.tax_id || ""),
      invoice_address: String(details.address || ""),
    });
    setSelectedPlanId(
      current.requested_plan
        ? String(current.requested_plan)
        : current.plan?.id
          ? String(current.plan.id)
          : "",
    );
  }, [subscription.data?.id]);

  const [editingQuickReplyId, setEditingQuickReplyId] = useState<number | null>(
    null,
  );

  const [quickReplyEditForm, setQuickReplyEditForm] = useState({
    title: "",
    text: "",
    category: "",
    channel: "all" as QuickReplyTemplate["channel"],
    is_active: true,
  });

  const quickReplies = useQuery({
    queryKey: ["quick-replies", business?.id],
    queryFn: () => quickRepliesApi.listAll({ business: business?.id }),
    enabled: Boolean(business && canManageConversations),
  });

  const notificationPreferenceMutation = useMutation({
    mutationFn: ({
      category,
      enabled,
    }: {
      category: Notification["category"];
      enabled: boolean;
    }) => {
      if (!business || !user) throw new Error(t("account.businessRequired"));
      const existing = (notificationPreferences.data || []).find(
        (preference) => preference.category === category,
      );
      const payload: Partial<NotificationPreference> = {
        business: business.id,
        user: user.id,
        category,
        in_app_enabled: enabled,
      };
      if (existing)
        return notificationsApi.preferences.update({
          id: existing.id,
          payload,
        });
      return notificationsApi.preferences.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
    },
  });

  const mutation = useMutation({
    mutationFn: (payload: Partial<Business>) =>
      business
        ? businessesApi.update({ id: business.id, payload })
        : businessesApi.create(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["businesses"] }),
  });

  const updateCustomFieldMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: Id;
      payload: Partial<CustomFieldDefinition>;
    }) => customFieldsApi.update({ id, payload }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
    },
  });

  const removeCustomFieldMutation = useMutation({
    mutationFn: (id: Id) => customFieldsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
    },
  });

  const updateMemberMutation = useMutation({
    mutationFn: teamApi.updateMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team-members"] });
      queryClient.invalidateQueries({ queryKey: ["auth-me"] });
    },
  });

  const inviteMutation = useMutation({
    mutationFn: () => {
      if (!business) throw new Error("Business is required.");
      return teamApi.createInvitation({
        business: business.id,
        email: inviteForm.email,
        phone: inviteForm.phone,
        telegram: inviteForm.telegram,
        full_name: inviteForm.full_name,
        role: inviteForm.role,
        delivery_channel: inviteForm.delivery_channel,
      });
    },
    onSuccess: (invitation) => {
      setLastCreatedInvite(invitation);
      setInviteForm({
        email: "",
        phone: "",
        telegram: "",
        full_name: "",
        role: "operator",
        delivery_channel: "whatsapp",
      });
      queryClient.invalidateQueries({ queryKey: ["team-invitations"] });
    },
  });

  const revokeInvitationMutation = useMutation({
    mutationFn: teamApi.revokeInvitation,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["team-invitations"] }),
  });

  const departmentMutation = useMutation({
    mutationFn: () => {
      if (!business) throw new Error("Business is required.");
      return teamApi.createDepartment({
        business: business.id,
        name: departmentName,
        description: "",
      });
    },
    onSuccess: () => {
      setDepartmentName("");
      queryClient.invalidateQueries({ queryKey: ["team-departments"] });
    },
  });

  const quickReplyMutation = useMutation({
    mutationFn: () => {
      if (!business) throw new Error("Business is required.");
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.create({
        business: business.id,
        title: quickReplyForm.title,
        text: quickReplyForm.text,
        category: quickReplyForm.category,
        channel: quickReplyForm.channel as QuickReplyTemplate["channel"],
        sort_order: 0,
        is_active: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      setQuickReplyForm({ title: "", text: "", category: "", channel: "all" });
    },
  });

  const updateQuickReplyMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<QuickReplyTemplate>;
    }) => {
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.update({
        id,
        payload,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      setEditingQuickReplyId(null);
    },
  });

  const removeQuickReplyMutation = useMutation({
    mutationFn: (id: number) => {
      if (!canManageConversations)
        throw new Error(
          t("permissions.forbidden", {
            action: t("permissions.action.manage"),
            resource: t("permissions.resource.conversations"),
          }),
        );
      return quickRepliesApi.remove(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quick-replies"] });
      if (editingQuickReplyId) setEditingQuickReplyId(null);
    },
  });

  const appointmentMessageMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<AppointmentMessageSetting>;
    }) => appointmentMessageSettingsApi.update({ id, payload }),
    onSuccess: (saved, { id, payload }) => {
      queryClient.setQueryData<AppointmentMessageSetting[]>(["appointment-message-settings", business?.id], (rows) => rows?.map((row) => Number(row.id) === id ? saved : row));
      setAppointmentMessageDrafts((current) => {
        const remaining = { ...current[id] };
        for (const key of Object.keys(payload) as Array<keyof AppointmentMessageSetting>) {
          if (remaining[key] === payload[key]) delete remaining[key];
        }
        const next = { ...current };
        if (Object.keys(remaining).length) next[id] = remaining;
        else delete next[id];
        return next;
      });
      queryClient.invalidateQueries({
        queryKey: ["appointment-message-settings"],
      });
    },
  });

  const billingSettingsMutation = useMutation({
    mutationFn: () =>
      billingApi.updateSettings({
        business: business!.id,
        billing_email: billingSettingsForm.billing_email,
        invoice_details_json: {
          ...subscription.data?.invoice_details_json,
          name: billingSettingsForm.invoice_name,
          tax_id: billingSettingsForm.invoice_tax_id,
          address: billingSettingsForm.invoice_address,
        },
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["current-subscription"] }),
  });

  const planChangeMutation = useMutation({
    mutationFn: (plan: Id) => billingApi.requestPlanChange(plan, business!.id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["current-subscription"] }),
  });

  function startEditingQuickReply(template: QuickReplyTemplate) {
    setEditingQuickReplyId(Number(template.id));
    setQuickReplyEditForm({
      title: template.title,
      text: template.text,
      category: template.category || "",
      channel: template.channel,
      is_active: template.is_active,
    });
  }

  const currentPlan = subscription.data?.plan;

  const members = teamMembers.data || [];

  const roles = teamRoles.data || [];

  const canonicalRoleKeys = new Set(teamRoleOptions.map((option) => option.value));

  const visibleRoles = roles.filter(
    (role) => !role.is_system || canonicalRoleKeys.has(role.preset_key as BusinessMembershipSummary["role"]),
  );

  const selectedMember =
    members.find((member) => Number(member.id) === selectedMemberId) ||
    members[0];

  const selectedMemberRole = canonicalBusinessRole(
    selectedMember?.role,
  ) as BusinessMembershipSummary["role"];

  const selectedRole =
    roles.find((role) => Number(role.id) === selectedRoleId) ||
    roles.find(
      (role) => Number(role.id) === Number(selectedMember?.business_role),
    ) ||
    roles.find((role) => role.preset_key === selectedMemberRole) ||
    roles.find((role) => role.preset_key === "specialist") ||
    visibleRoles[0];

  const translatedTeamRoleOptions = teamRoleOptions.map((option) => ({
    ...option,
    label: t(`settings.role.${option.value}`),
  }));

  const editableTeamRoleOptions = translatedTeamRoleOptions.filter(
    (option) => option.value !== "owner",
  );

  const translatedSettingsSections = allowedSettingsSections.map((section) => ({
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

  const quickReplyChannelOptions = [
    { value: "all", label: t("settings.channel.all") },
    { value: "website", label: t("settings.channel.website") },
    { value: "telegram", label: "Telegram" },
    { value: "whatsapp", label: "WhatsApp" },
    { value: "instagram", label: "Instagram" },
    { value: "manual", label: t("settings.channel.manual") },
  ];

  const locale =
    language === "kk" ? "kk-KZ" : language === "en" ? "en-US" : "ru-RU";

  const appointmentMessages = appointmentMessageSettings.data || [];

  const appointmentMessageValue = <K extends keyof AppointmentMessageSetting>(
    setting: AppointmentMessageSetting,
    key: K,
  ): AppointmentMessageSetting[K] => {
    return (
      (appointmentMessageDrafts[Number(setting.id)]?.[key] as
        AppointmentMessageSetting[K] | undefined) ?? setting[key]
    );
  };

  function inviteUrl(path: string) {
    return `${window.location.origin}${path}`;
  }

  function inviteMessage(path: string) {
    return t("settings.inviteMessage", { url: inviteUrl(path) });
  }

  function inviteShareUrl(invitation: {
    invite_path: string;
    email: string;
    phone?: string;
    telegram?: string;
    delivery_channel?: string;
  }) {
    const message = encodeURIComponent(inviteMessage(invitation.invite_path));
    if (invitation.delivery_channel === "email") {
      return `mailto:${invitation.email}?subject=${encodeURIComponent(t("settings.inviteSubject"))}&body=${message}`;
    }
    if (invitation.delivery_channel === "whatsapp" && invitation.phone) {
      const phone = invitation.phone.replace(/\D/g, "");
      return `https://wa.me/${phone}?text=${message}`;
    }
    if (invitation.delivery_channel === "telegram") {
      return `https://t.me/share/url?url=${encodeURIComponent(inviteUrl(invitation.invite_path))}&text=${encodeURIComponent(t("settings.inviteSubject"))}`;
    }
    return inviteUrl(invitation.invite_path);
  }

  async function copyInvitation(invitation: {
    id: number;
    invite_path: string;
  }) {
    setCopyInviteError("");
    try {
      if (!navigator.clipboard?.writeText) throw new Error(t("settings.copyUnavailable"));
      await navigator.clipboard.writeText(inviteMessage(invitation.invite_path));
    } catch {
      setCopyInviteError(t("settings.copyUnavailable"));
      return;
    }
    setCopiedInviteId(invitation.id);
    window.setTimeout(
      () =>
        setCopiedInviteId((current) =>
          current === invitation.id ? null : current,
        ),
      1800,
    );
  }
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
    billingSettingsForm,
    billingSettingsMutation,
    business,
    canManageBilling,
    canManageTeam,
    canUpdateNotifications,
    confirmDelete,
    copiedInviteId,
    copyInvitation,
    copyInviteError,
    currentPlan,
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
    notificationPreferenceMutation,
    notificationPreferences,
    planChangeMutation,
    plans,
    preferenceByCategory,
    quickReplies,
    quickReplyChannelOptions,
    quickReplyEditForm,
    quickReplyForm,
    quickReplyMutation,
    removeCustomFieldMutation,
    removeQuickReplyMutation,
    revokeInvitationMutation,
    roles,
    securityRisk,
    selectedMember,
    selectedMemberRole,
    selectedPlanId,
    selectedRole,
    setActiveSettingsSection,
    setAppointmentMessageDrafts,
    setBillingSettingsForm,
    setCopyInviteError,
    setDepartmentName,
    setEditingQuickReplyId,
    setInviteForm,
    setLastCreatedInvite,
    setQuickReplyEditForm,
    setQuickReplyForm,
    setSelectedMemberId,
    setSelectedPlanId,
    setSelectedRoleId,
    startEditingQuickReply,
    subscription,
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
