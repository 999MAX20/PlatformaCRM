import { ArrowUpRight, ChevronRight, Copy, Plus, Search } from "lucide-react";
import { useState } from "react";
import { getApiFieldErrors } from "../../../api/client";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
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
    const pending = invitation.status === "pending" && new Date(invitation.expires_at).getTime() > Date.now();
    return <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {pending && <>
          <a href={model.inviteShareUrl(invitation)} target="_blank" rel="noreferrer"
            className="platforma-focus-ring inline-flex min-h-11 items-center justify-center gap-2 rounded-control border border-platforma-border px-3 text-sm font-semibold text-brand-700 hover:bg-brand-50">{t("settings.send")}<ArrowUpRight aria-hidden="true" size={16} /></a>
          <Button type="button" variant="secondary" onClick={() => { setCopyTarget(id); void model.copyInvitation({ id, invite_path: invitation.invite_path }); }}><Copy size={16} />{model.copiedInviteId === id ? t("settings.copied") : t("settings.copy")}</Button>
          <Button type="button" variant="danger" disabled={model.revokeInvitationMutation.isPending} onClick={async () => {
            if (await model.confirmDelete(invitation.full_name || invitation.email, "settings.revoke")) model.revokeInvitationMutation.mutate(invitation.id);
          }}>{t("settings.revoke")}</Button>
        </>}
      </div>
      {copyTarget === id && model.copyInviteError && <SettingsFeedback error={new Error(model.copyInviteError)} />}
      {model.revokeInvitationMutation.variables === invitation.id && <SettingsFeedback error={model.revokeInvitationMutation.error} />}
    </div>;
  }
  const memberChanged = Boolean(selectedMember && memberDraft !== selectedMemberRole);
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
    <SettingsDrawer open={drawer === "invite" && activeSettingsSection === "team-access"} onClose={() => { if (!inviteMutation.isPending) setDrawer(null); }} title={t("settings.redesign.invite")}
      footer={<SettingsSaveBar drawer feedback={<SettingsFeedback error={!inviteHasFieldErrors ? inviteMutation.error : undefined} />}>
        <Button type="button" variant="secondary" disabled={inviteMutation.isPending} onClick={() => setDrawer(null)}>{t(lastCreatedInvite ? "common.close" : "common.cancel")}</Button>
        {!lastCreatedInvite && <Button type="submit" form="settings-invitation-form" isLoading={inviteMutation.isPending} disabled={!canManageTeam || teamRoles.isLoading || teamRoles.isError}>{t("settings.createInvite")}</Button>}
      </SettingsSaveBar>}>
      {createdInvite ? <div className="space-y-4"><p role="status" className="text-base font-semibold text-platforma-success">{t("settings.inviteCreatedTitle")}</p><p className="break-all text-sm">{createdInvite.email} · {t(`settings.role.${createdInvite.role}`)} · {t(`status.${createdInvite.status}`)}</p>{invitationActions(createdInvite)}</div> : <form id="settings-invitation-form" onSubmit={event => { event.preventDefault(); inviteMutation.mutate(undefined, { onError: () => window.requestAnimationFrame(() => document.querySelector<HTMLElement>('#settings-invitation-form [aria-invalid="true"]')?.focus()) }); }}>
        <fieldset disabled={!canManageTeam || inviteMutation.isPending} className="space-y-4">
          <Input label={t("settings.fullName")} name="full_name" value={inviteForm.full_name} error={inviteErrors.full_name?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, full_name: event.target.value })} />
          <Input label={t("settings.loginEmail")} type="email" name="email" required value={inviteForm.email} error={inviteErrors.email?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, email: event.target.value })} />
          <SettingsQueryState queries={[teamRoles]} />
          <Select label={t("settings.role")} value={inviteForm.role} error={inviteErrors.role?.join(" ")} options={editableTeamRoleOptions} onChange={event => setInviteForm({ ...inviteForm, role: event.target.value as BusinessMembershipSummary["role"] })} />
          <Select label={t("settings.delivery")} value={inviteForm.delivery_channel} error={inviteErrors.delivery_channel?.join(" ")} options={[{ value: "manual", label: t("settings.copyLink") }, { value: "email", label: "Email" }, { value: "whatsapp", label: "WhatsApp" }, { value: "telegram", label: "Telegram" }]}
            onChange={event => setInviteForm({ ...inviteForm, delivery_channel: event.target.value as typeof inviteForm.delivery_channel })} />
          {inviteForm.delivery_channel === "whatsapp" && <Input label={t("settings.whatsappPhone")} name="phone" type="tel" required value={inviteForm.phone} error={inviteErrors.phone?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, phone: event.target.value })} />}
          {inviteForm.delivery_channel === "telegram" && <Input label="Telegram" name="telegram" required value={inviteForm.telegram} error={inviteErrors.telegram?.join(" ")} onChange={event => setInviteForm({ ...inviteForm, telegram: event.target.value })} />}
          <p className="text-xs leading-5 text-platforma-subtle">{t(`settings.deliveryHelp.${inviteForm.delivery_channel}`)}</p>
          <div className="border-t border-platforma-border pt-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-bold">{t("settings.redesign.rolePreview")}</h3><Button variant="ghost" type="button" disabled={!inviteRole} onClick={() => configureRole(inviteRole?.id)}>{t("settings.redesign.configureRole")}</Button></div>
            {!teamRoles.isLoading && !teamRoles.isError && <RoleAccessPreview role={inviteRole} />}
          </div>
        </fieldset>
      </form>}
    </SettingsDrawer>
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
        <SettingsQueryState queries={[teamRoles]} />
        <Select data-testid="team-role-select" label={t("settings.role")} value={memberDraft} disabled={!canManageTeam || selectedMember.role === "owner" || updateMemberMutation.isPending || teamRoles.isError}
          options={selectedMember.role === "owner" ? [{ value: "owner", label: t("settings.role.owner") }] : editableTeamRoleOptions.map(option => assignedRole && !assignedRole.is_system && option.value === selectedMemberRole ? { ...option, label: settingsRoleName(assignedRole, t) } : option)}
          onChange={event => { setRoleDrafts(current => ({ ...current, [Number(selectedMember.id)]: event.target.value as BusinessMembershipSummary["role"] })); updateMemberMutation.reset(); }} />
        {canManageTeam && selectedMember.role !== "owner" && <Button type="button" variant="secondary" disabled={!memberRole || teamRoles.isLoading || teamRoles.isError || updateMemberMutation.isPending}
          onClick={() => configureRole(memberRole?.id)}>{t("settings.workflow.editRolePermissions")}</Button>}
        {!teamRoles.isLoading && !teamRoles.isError && <RoleAccessPreview role={memberRole} baseRole={roles.find(role => role.preset_key === memberDraft)} />}
        <TeamAccessControl key={selectedMember.id} member={selectedMember} canManage={canManageTeam} />
      </div>}
    </SettingsDrawer>
  </SettingsSection>;
}
