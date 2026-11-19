import { Check, ChevronRight, Copy, Plus, Search } from "lucide-react";
import { useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Dialog } from "../../../components/ui/Overlay";
import type { BusinessInvitation, BusinessMembershipSummary } from "../../../types";
import { RoleAccessPreview } from "../components/RoleAccessPreview";
import { SettingsDrawer, SettingsFeedback, SettingsSaveBar, SettingsSection, SettingsTabs } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { TeamAccessControl } from "../components/TeamAccessControl";
import { settingsRoleName } from "../roleAccess";
import type { SettingsModel } from "../useSettingsModel";

export function TeamSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, canManageTeam, teamMembers, teamRoles, invitations, departments, members, roles, selectedMember, selectedMemberRole, setSelectedMemberId, editableTeamRoleOptions,
    inviteForm, setInviteForm, inviteMutation, lastCreatedInvite, setLastCreatedInvite, updateMemberMutation, departmentName, setDepartmentName, departmentMutation } = model;
  const [tab, setTab] = useState<"members" | "invitations" | "departments">("members");
  const [search, setSearch] = useState("");
  const [drawer, setDrawer] = useState<"invite" | "member" | null>(null);
  const [roleDrafts, setRoleDrafts] = useState<Record<number, BusinessMembershipSummary["role"]>>({});
  const [copyTarget, setCopyTarget] = useState<number | null>(null);
  const inviteRole = roles.find(role => role.preset_key === inviteForm.role);
  const createdInvite = invitations.data?.find(invitation => invitation.id === lastCreatedInvite?.id) || lastCreatedInvite;
  const assignedRole = roles.find(role => String(role.id) === String(selectedMember?.business_role));
  const memberDraft = selectedMember ? roleDrafts[Number(selectedMember.id)] || selectedMemberRole : selectedMemberRole;
  const memberRole = selectedMember && memberDraft === selectedMemberRole
    ? assignedRole || roles.find(role => role.preset_key === memberDraft)
    : roles.find(role => role.preset_key === memberDraft);
  const inviteErrors = getApiFieldErrors(inviteMutation.error);
  const inviteHasFieldErrors = ["email", "full_name", "role", "delivery_channel", "phone", "telegram"].some(key => inviteErrors[key]?.length);
  const filtered = members.filter(member => (member.user.full_name + " " + member.user.email).toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  function openInvitation() {
    inviteMutation.reset(); setLastCreatedInvite(null); model.setCopyInviteError(""); setDrawer("invite");
  }
  function configureRole(roleId?: string | number) {
    if (!roleId) return;
    model.setSelectedRoleId(Number(roleId)); model.setRoleEditorSource(drawer);
    model.setActiveSettingsSection("roles"); window.location.hash = "roles";
  }
  function invitationActions(invitation: BusinessInvitation) {
    const id = Number(invitation.id);
    const canResend = invitation.status === "pending" || invitation.status === "expired";
    if (!canResend) {
      const completedAt = invitation.accepted_at || invitation.revoked_at;
      return completedAt ? <time className="text-xs text-platforma-subtle" dateTime={completedAt}>{new Date(completedAt).toLocaleString(model.locale, { dateStyle: "medium", timeStyle: "short" })}</time> : null;
    }
    const delivery = invitation.delivery_status || "not_requested";
    return <div className="space-y-2">
      <p role="status" className={delivery === "accepted" ? "inline-flex items-center gap-2 rounded-control bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700" : "text-sm text-platforma-subtle"}>{delivery === "accepted" && <Check size={16} aria-hidden="true" />}{t(`invite.delivery.${delivery}`)}</p>
      {delivery === "failed" && <p className="text-sm text-platforma-danger">{t("invite.deliveryHelp")}</p>}
      <p className="text-xs text-platforma-subtle">{t("invite.expires", { date: new Date(invitation.expires_at).toLocaleString(model.locale, { dateStyle: "medium", timeStyle: "short" }) })}</p>
      <div className="flex flex-wrap gap-2">
        {invitation.status === "pending" && new Date(invitation.expires_at).getTime() > Date.now() && <Button type="button" variant="secondary"
          onClick={() => { setCopyTarget(id); void model.copyInvitation({ id, invite_path: invitation.invite_path }); }}><Copy size={16} />{model.copiedInviteId === id ? t("settings.copied") : t("settings.copy")}</Button>}
        {canResend && <Button type="button" variant="secondary" disabled={model.resendInvitationMutation.isPending || model.revokeInvitationMutation.isPending}
          onClick={() => model.resendInvitationMutation.mutate({ id, revision: invitation.updated_at })}>{t("invite.resend")}</Button>}
        {canResend && <Button type="button" variant="ghost" className="text-platforma-danger" disabled={model.revokeInvitationMutation.isPending || model.resendInvitationMutation.isPending} onClick={async () => {
          if (await model.confirmDelete(invitation.full_name || invitation.email, "settings.revoke")) model.revokeInvitationMutation.mutate(invitation.id);
        }}>{t("settings.revoke")}</Button>}
      </div>
      <p className="text-xs text-platforma-subtle">{t("invite.resendHelp")}</p>
      {copyTarget === id && model.copyInviteError && <SettingsFeedback error={new Error(model.copyInviteError)} />}
      {model.resendInvitationMutation.variables?.id === id && <SettingsFeedback error={model.resendInvitationMutation.error} />}
      {model.revokeInvitationMutation.variables === invitation.id && <SettingsFeedback error={model.revokeInvitationMutation.error} />}
    </div>;
  }
  const memberChanged = Boolean(selectedMember && selectedMember.role !== "owner" && memberRole && (
    memberDraft !== selectedMemberRole || String(selectedMember.business_role) !== String(memberRole.id)
  ));
  return <SettingsSection id="team-access" active={activeSettingsSection} title={t("settings.section.team-access")}
    actions={canManageTeam && <Button type="button" onClick={openInvitation}><Plus size={16} />{t("settings.redesign.invite")}</Button>}>
    <div className="space-y-4 p-4 sm:p-5">
      <SettingsTabs value={tab} onChange={setTab} label={t("settings.section.team-access")} items={[
        { value: "members", label: t("settings.redesign.employees") },
        ...(canManageTeam ? [{ value: "invitations" as const, label: t("settings.redesign.invitations") }] : []),
        { value: "departments", label: t("settings.departments") },
      ]} />
      {tab === "members" && <>
        <Input label={t("common.search")} placeholder={t("settings.redesign.searchEmployees")} leftIcon={<Search size={16} />} value={search} onChange={event => setSearch(event.target.value)} />
        <SettingsQueryState queries={[teamMembers]} />
        {!teamMembers.isLoading && !teamMembers.isError && <div>
          <div className="hidden grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,0.6fr)_24px] gap-4 border-b border-platforma-border bg-surface-muted px-3 py-3 text-xs text-platforma-subtle md:grid">
            <span>{t("settings.redesign.employee")}</span><span>{t("settings.role")}</span><span>{t("settings.redesign.loginAccess")}</span><span />
          </div>
          {filtered.map(member => <button key={member.id} type="button" onClick={() => { setSelectedMemberId(Number(member.id)); updateMemberMutation.reset(); setDrawer("member"); }}
            className="platforma-focus-ring grid w-full gap-2 border-b border-platforma-border px-3 py-4 text-left text-sm hover:bg-surface-hover md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,0.6fr)_24px] md:items-center md:gap-4">
            <span className="min-w-0"><span className="block font-semibold">{member.user.full_name || member.user.email}</span><span className="mt-1 block break-all text-xs text-platforma-subtle">{member.user.email}</span></span>
            <span>{member.business_role_name || t(`settings.role.${member.role}`)}</span>
            <span className={member.is_active ? "text-platforma-success" : "text-platforma-subtle"}>{t(member.is_active ? "settings.active" : "settings.inactive")}</span>
            <ChevronRight aria-hidden="true" className="hidden text-platforma-subtle md:block" size={16} />
          </button>)}
          {!filtered.length && <p className="py-8 text-center text-sm text-platforma-subtle">{t(search.trim() ? "settings.redesign.noMatches" : "settings.teamEmpty")}</p>}
        </div>}
      </>}
      {tab === "invitations" && canManageTeam && <>
        <SettingsQueryState queries={[invitations]} />
        {!invitations.isError && <div className="divide-y divide-platforma-border">
          {(invitations.data || []).map(invitation => <div key={invitation.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div className="min-w-0"><p className="text-sm font-semibold">{invitation.full_name || invitation.email}</p><p className="mt-1 break-all text-xs text-platforma-subtle">{invitation.email} · {t(`settings.role.${invitation.role}`)} · {t(`status.${invitation.status}`)}</p></div>
            {invitationActions(invitation)}
          </div>)}
          {invitations.isSuccess && !invitations.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noInvites")}</p>}
        </div>}
      </>}
      {tab === "departments" && <>
        <SettingsQueryState queries={[departments]} />
        {canManageTeam && <form onSubmit={event => { event.preventDefault(); if (departmentName.trim()) departmentMutation.mutate(); }} className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-0 flex-1"><Input label={t("settings.redesign.name")} value={departmentName} disabled={departmentMutation.isPending} required onChange={event => { setDepartmentName(event.target.value); departmentMutation.reset(); }} /></div>
            <Button type="submit" isLoading={departmentMutation.isPending}>{t("settings.add")}</Button>
          </div>
          <SettingsFeedback error={departmentMutation.error} saved={departmentMutation.isSuccess} />
        </form>}
        {!departments.isError && <div className="divide-y divide-platforma-border">{(departments.data || []).map(department => <div key={department.id} className="flex items-center justify-between gap-3 py-4 text-sm"><span className="font-semibold">{department.name}</span><span className="text-platforma-subtle">{department.members_count || 0} {t("settings.members")}</span></div>)}</div>}
        {departments.isSuccess && !departments.data?.length && <p className="py-4 text-sm text-platforma-subtle">{t("settings.noDepartments")}</p>}
      </>}
    </div>
    <Dialog size="lg" className="sm:!max-w-[960px]" mobileFullScreen backdropClassName="p-0 sm:p-5 !bg-black/25" backdropBlur={false} closeOnBackdrop={false} testId="invitation-dialog" open={drawer === "invite" && activeSettingsSection === "team-access"} onClose={() => { if (!inviteMutation.isPending) setDrawer(null); }} title={t("settings.redesign.invite")}
      footer={<div className="flex flex-wrap items-center justify-end gap-3">
        <div className="w-full"><SettingsFeedback error={!inviteHasFieldErrors ? inviteMutation.error : undefined} /></div>
        <Button type="button" variant="secondary" disabled={inviteMutation.isPending} onClick={() => setDrawer(null)}>{t(lastCreatedInvite ? "common.close" : "common.cancel")}</Button>
        {!lastCreatedInvite && <Button type="submit" form="settings-invitation-form" isLoading={inviteMutation.isPending} disabled={!canManageTeam || teamRoles.isLoading || teamRoles.isError}>{t("invite.send")}</Button>}
      </div>}>
      {createdInvite ? <div className="space-y-4"><p role="status" className="text-base font-semibold text-platforma-success">{t("settings.inviteCreatedTitle")}</p><p className="break-all text-sm">{createdInvite.email} · {t(`settings.role.${createdInvite.role}`)} · {t(`status.${createdInvite.status}`)}</p>{invitationActions(createdInvite)}</div> : <form id="settings-invitation-form" onSubmit={event => { event.preventDefault(); inviteMutation.mutate(undefined, { onError: () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-invitation-form [aria-invalid="true"]')?.focus()) }); }}>
        <fieldset disabled={!canManageTeam || inviteMutation.isPending} className="grid items-start gap-6 md:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <div className="min-w-0 space-y-4">
          <Input label={t("settings.fullName")} name="full_name" value={inviteForm.full_name} error={inviteErrors.full_name?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, full_name: event.target.value })} />
          <Input label={t("settings.loginEmail")} type="email" name="email" required value={inviteForm.email} error={inviteErrors.email?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, email: event.target.value })} />
          <SettingsQueryState queries={[teamRoles]} />
          <Select label={t("settings.role")} value={inviteForm.role} error={inviteErrors.role?.join(" ")} options={editableTeamRoleOptions} onChange={event => setInviteForm({ ...inviteForm, role: event.target.value as BusinessMembershipSummary["role"] })} />
          <p className="text-sm leading-6 text-platforma-subtle">{t("invite.emailHelp")}</p>
          </div>
          <div className="min-w-0 border-t border-platforma-border pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold">{t("settings.redesign.rolePreview")}</h3><Button variant="ghost" type="button" disabled={!inviteRole} onClick={() => configureRole(inviteRole?.id)}>{t("invite.configureSharedRole")}</Button></div>
            <p className="mb-3 text-xs leading-5 text-platforma-subtle">{t("invite.sharedRoleHelp")}</p>
            {!teamRoles.isLoading && !teamRoles.isError && <RoleAccessPreview role={inviteRole} />}
          </div>
        </fieldset>
      </form>}
    </Dialog>
    <SettingsDrawer open={drawer === "member" && activeSettingsSection === "team-access" && Boolean(selectedMember)} onClose={() => { if (!updateMemberMutation.isPending) setDrawer(null); }}
      title={selectedMember?.user.full_name || selectedMember?.user.email || t("settings.redesign.employee")}
      footer={<SettingsSaveBar drawer feedback={<SettingsFeedback error={updateMemberMutation.error} saved={updateMemberMutation.isSuccess && !memberChanged} />}>
        <Button type="button" variant="secondary" disabled={updateMemberMutation.isPending} onClick={() => { if (selectedMember) setRoleDrafts(current => { const next = { ...current }; delete next[Number(selectedMember.id)]; return next; }); setDrawer(null); }}>{t("common.cancel")}</Button>
        {canManageTeam && selectedMember?.role !== "owner" && <Button type="button" isLoading={updateMemberMutation.isPending} disabled={!memberChanged || !memberRole || teamRoles.isError} onClick={() => {
          if (!selectedMember || !memberRole) return;
          updateMemberMutation.mutate({ id: selectedMember.id, payload: { role: memberDraft, business_role: memberRole.id } }, { onSuccess: () => setRoleDrafts(current => { const next = { ...current }; delete next[Number(selectedMember.id)]; return next; }) });
        }}>{t("common.save")}</Button>}
      </SettingsSaveBar>}>
      {selectedMember && <div className="space-y-4">
        <p className="break-all text-sm text-platforma-subtle">{selectedMember.user.email}</p>
        <TeamAccessControl key={selectedMember.id} member={selectedMember} canManage={canManageTeam} />
        <SettingsQueryState queries={[teamRoles]} />
        <Select data-testid="team-role-select" label={t("settings.role")} value={memberDraft} disabled={!canManageTeam || selectedMember.role === "owner" || updateMemberMutation.isPending || teamRoles.isError}
          options={selectedMember.role === "owner" ? [{ value: "owner", label: t("settings.role.owner") }] : editableTeamRoleOptions.map(option => assignedRole && !assignedRole.is_system && option.value === selectedMemberRole ? { ...option, label: settingsRoleName(assignedRole, t) } : option)}
          onChange={event => { setRoleDrafts(current => ({ ...current, [Number(selectedMember.id)]: event.target.value as BusinessMembershipSummary["role"] })); updateMemberMutation.reset(); }} />
        {canManageTeam && selectedMember.role !== "owner" && <Button type="button" variant="secondary" disabled={memberChanged || !memberRole || teamRoles.isLoading || teamRoles.isError || updateMemberMutation.isPending}
          onClick={() => configureRole(memberRole?.id)}>{t("settings.workflow.editRolePermissions")}</Button>}
        {memberChanged ? <p role="status" className="text-sm text-platforma-subtle">{t("settings.workflow.saveRoleFirst")}</p>
          : !teamRoles.isLoading && !teamRoles.isError && <RoleAccessPreview role={memberRole} baseRole={roles.find(role => role.preset_key === memberDraft)} />}
      </div>}
    </SettingsDrawer>
  </SettingsSection>;
}
