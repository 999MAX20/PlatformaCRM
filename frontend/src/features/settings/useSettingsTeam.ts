import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { teamApi } from "../../api/team";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { canonicalBusinessRole } from "../../lib/permissions";
import type { BusinessInvitation, BusinessMembershipSummary } from "../../types";

import { teamRoleOptions } from "./settingsConfig";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canViewTeam: boolean;
  canManageTeam: boolean;
  activeSettingsSection: string;
  queryClient: ReturnType<typeof useQueryClient>;
  t: ReturnType<typeof useI18n>["t"];
};

export function useSettingsTeam({ business, canViewTeam, canManageTeam, activeSettingsSection, queryClient, t }: Context) {
const teamMembers = useQuery({
    queryKey: ["team-members", business?.id],
    queryFn: () => teamApi.allMembers(business?.id),
    enabled: (activeSettingsSection === "team-access" || activeSettingsSection === "roles") && Boolean(business && canViewTeam),
  });

const teamRoles = useQuery({
    queryKey: ["team-roles", business?.id],
    queryFn: () => teamApi.allRoles(business?.id),
    enabled: (activeSettingsSection === "team-access" || activeSettingsSection === "roles") && Boolean(business && canViewTeam),
  });

const invitations = useQuery({
    queryKey: ["team-invitations", business?.id],
    queryFn: () => teamApi.allInvitations(business?.id),
    enabled: (activeSettingsSection === "team-access" || activeSettingsSection === "roles") && Boolean(business && canManageTeam),
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

const [roleEditorSource, setRoleEditorSource] = useState<"member" | "invite" | null>(null);

const [copiedInviteId, setCopiedInviteId] = useState<number | null>(null);

const [copyInviteError, setCopyInviteError] = useState("");

const [lastCreatedInvite, setLastCreatedInvite] =
    useState<BusinessInvitation | null>(null);

const departments = useQuery({
    queryKey: ["team-departments", business?.id],
    queryFn: () => teamApi.allDepartments(business?.id),
    enabled: (activeSettingsSection === "team-access" || activeSettingsSection === "roles") && Boolean(business && canViewTeam),
  });

const [departmentName, setDepartmentName] = useState("");

const updateMemberMutation = useMutation({
    mutationFn: teamApi.updateMember,
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ["team-members"] }),
      queryClient.invalidateQueries({ queryKey: ["auth-me"] }),
    ]),
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
return { teamMembers, teamRoles, invitations, inviteForm, setInviteForm, selectedMemberId, setSelectedMemberId, selectedRoleId, setSelectedRoleId, roleEditorSource, setRoleEditorSource, copiedInviteId, setCopiedInviteId, copyInviteError, setCopyInviteError, lastCreatedInvite, setLastCreatedInvite, departments, departmentName, setDepartmentName, updateMemberMutation, inviteMutation, revokeInvitationMutation, departmentMutation, members, roles, canonicalRoleKeys, visibleRoles, selectedMember, selectedMemberRole, selectedRole, translatedTeamRoleOptions, editableTeamRoleOptions, inviteUrl, inviteMessage, inviteShareUrl, copyInvitation };
}
