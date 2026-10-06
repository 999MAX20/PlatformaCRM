import { CRMStaffAgentsPage } from "./CRMStaffAgentsPage";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { agentProfilesApi, businessKnowledgeApi } from "../../api/ai";
import { botChannelsApi, botLifecycleApi, botsApi, ensureBotChannel, saveAgentConfiguration } from "../../api/bots";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useEntityData } from "../../hooks/useEntityData";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import type { AgentProfile, Bot as BotType, BotChannel, BusinessKnowledgeItem } from "../../types";
import { AIAgentsWorkspace } from "./components/AIAgentsWorkspace";
import { AgentNavigation } from "./components/AgentNavigation";
import { AgentDeleteControl } from "./components/AgentDeleteControl";
import { jsonFromLines } from "./aiAgentsUtils";
import { useAIAgentEditorDrafts } from "./useAIAgentEditorDrafts";
import { useCanonicalAIAgentRoute } from "./useCanonicalAIAgentRoute";
import { useMetaOAuthCallbackBridge } from "./useMetaOAuthCallbackBridge";

export function AIAgentsPage() {
  const { user } = useAuth();
  const { business, isLoading } = useActiveBusiness();
  if (isLoading) return <LoadingState scope="page" />;
  return hasPermission(user, business?.id, "ai_automation", "view") ? <CustomerAgentsPage /> : <CRMStaffAgentsPage />;
}

function CustomerAgentsPage() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  const { user } = useAuth();
  const { business, isLoading: isBusinessLoading } = useActiveBusiness();
  const canManage = hasPermission(user, business?.id, "ai_automation", "manage");
  const canDelete = hasPermission(user, business?.id, "ai_automation", "delete");
  const canViewChannels = hasPermission(user, business?.id, "integrations", "view");
  const canManageChannels = hasPermission(user, business?.id, "integrations", "manage");
  const canSuggest = hasPermission(user, business?.id, "ai_assistant", "suggest");
  const queryClient = useQueryClient();
  const { bots } = useEntityData({
    bots: true,
  });
  const profiles = useQuery<AgentProfile[]>({ queryKey: ["ai-agent-profiles"], queryFn: () => agentProfilesApi.list() });
  const [createOpen, setCreateOpen] = useState(false);
  const [newAgentScenario, setNewAgentScenario] = useState<"inbox" | "crm" | null>(null);
  const [newAgentName, setNewAgentName] = useState(() => t("aiAgents.defaultNewAgentName"));
  useMetaOAuthCallbackBridge();

  const botList = useMemo(() => (bots.data || []).filter(bot => bot.business === business?.id), [bots.data, business?.id]);
  const profileList = useMemo(() => (profiles.data || []).filter(profile => profile.business === business?.id), [profiles.data, business?.id]);
  const isPageLoading = isBusinessLoading
    || bots.isLoading
    || profiles.isLoading;
  const { activeSection, canonicalRoute, selectedBot } = useCanonicalAIAgentRoute({
    bots: botList,
    hasBusiness: Boolean(business),
    isPageLoading,
  });
  const knowledge = useQuery<BusinessKnowledgeItem[]>({
    queryKey: ["ai-knowledge-items", business?.id, selectedBot?.id],
    queryFn: () => businessKnowledgeApi.listAll({ agent: selectedBot?.id }),
    enabled: Boolean(business && selectedBot),
  });

  const selectedProfile = useMemo(
    () => (profiles.data || []).filter((profile) => profile.bot === selectedBot?.id).sort((a, b) => Number(b.is_active) - Number(a.is_active) || b.updated_at.localeCompare(a.updated_at))[0] || null,
    [profiles.data, selectedBot?.id],
  );
  const [isSavingEditor, setIsSavingEditor] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const loadChannels = Boolean(business && canViewChannels && ["channels", "test"].includes(activeSection));
  const botChannels = useQuery<BotChannel[]>({
    queryKey: ["bot-channels"],
    queryFn: () => botChannelsApi.list(),
    enabled: loadChannels,
  });
  useEffect(() => {
    if (!botChannels.dataUpdatedAt) return;
    void queryClient.invalidateQueries({ queryKey: ["bots"] });
  }, [botChannels.dataUpdatedAt, queryClient]);
  const {
    botDraft,
    discardDeletedAgent,
    editorDirty,
    hasUserEdits,
    markBotSaved,
    markProfileSaved,
    navigationBlocker,
    profileForm,
    resetEditorDrafts,
    saveState,
    setBotDraft,
    setProfileForm,
    setSaveState,
  } = useAIAgentEditorDrafts({ selectedBot, selectedProfile, t });

  const createBot = useMutation({
    mutationFn: () =>
      botsApi.create({
        business: Number(business?.id),
        name: newAgentName.trim() || t("aiAgents.defaultNewAgentName"),
        scenario: newAgentScenario || "inbox",
        status: "draft",
        default_language: "ru",
        settings_json: {},
      }),
    onSuccess: async (bot) => {
      await queryClient.invalidateQueries({ queryKey: ["bots"] });
      setCreateOpen(false);
      setNewAgentScenario(null);
      await queryClient.invalidateQueries({ queryKey: ["ai-agent-profiles"] });
      setNewAgentName(t("aiAgents.defaultNewAgentName"));
      navigate(`/app/ai-agents/${bot.id}/profile`);
    },
  });

  const saveConfiguration = useMutation({
    mutationFn: () => {
      if (!selectedBot) throw new Error("Agent is not selected.");
      return saveAgentConfiguration(selectedBot.id, {
        bot: { name: botDraft.name.trim(), default_language: botDraft.default_language, settings_json: botDraft.settings_json },
        profile: {
          ...(profileForm.id ? { id: profileForm.id } : {}),
          name: botDraft.name.trim(), role_description: profileForm.role_description,
          tone: profileForm.tone, is_active: true, system_prompt: profileForm.system_prompt,
          rules_json: { ...selectedProfile?.rules_json, ...jsonFromLines(profileForm.rules_text),
            ...(selectedBot.scenario === "crm" ? { sources: profileForm.sources, analyst_enabled: profileForm.analyst_enabled } : {}) },
          allowed_tools_json: { tools: profileForm.allowed_tools },
          escalation_rules_json: jsonFromLines(profileForm.escalation_text),
        },
      });
    },
    onSuccess: async ({ bot, profile }) => {
      markBotSaved(bot);
      markProfileSaved(profile);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ai-agent-profiles"] }),
        queryClient.invalidateQueries({ queryKey: ["bots"] }),
      ]);
    },
  });

  const addChannel = useMutation({
    mutationFn: ({ botId, channel }: { botId: number; channel: BotChannel["channel"] }) =>
      ensureBotChannel({ botId, channel }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] }),
      queryClient.invalidateQueries({ queryKey: ["bots"] }),
    ]),
  });

  const toggleChannel = useMutation({
    mutationFn: ({ channel, status }: { channel: BotChannel; status: BotChannel["status"] }) =>
      botChannelsApi.update({ id: channel.id, payload: { status } }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] }),
      queryClient.invalidateQueries({ queryKey: ["bots"] }),
    ]),
  });

  const toggleBotStatus = useMutation({
    mutationFn: (active: boolean) => {
      if (!selectedBot) throw new Error("Agent is not selected.");
      return active ? botLifecycleApi.activate(selectedBot.id) : botLifecycleApi.pause(selectedBot.id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bots"] }),
  });

  const saveEditorDrafts = useCallback(async () => {
    if (!selectedBot || !canManage || !botDraft.name.trim()) return false;
    setIsSavingEditor(true);
    try {
      await saveConfiguration.mutateAsync();
      setSaveState("saved");
      return true;
    } finally {
      setIsSavingEditor(false);
    }
  }, [botDraft, canManage, profileForm.name, saveConfiguration, selectedBot, setSaveState]);

  useEffect(() => {
    setPageHeader({ title: t("nav.aiAgents") });
    return () => setPageHeader(null);
  }, [setPageHeader, t]);

  const navigation = (
    <AgentNavigation
      bots={botList} profiles={profileList} selectedBot={selectedBot}
      isLoading={isPageLoading || Boolean(canonicalRoute) || isDeleting} error={bots.error || profiles.error}
      canCreate={canManage} dirty={hasUserEdits} onCreate={() => setCreateOpen(true)}
      onRetry={() => void Promise.all([bots.refetch(), profiles.refetch()])}
      onSelect={id => navigate(`/app/ai-agents/${id}/profile`)}
    />
  );

  if (isPageLoading) {
    return <>{navigation}<LoadingState scope="page" /></>;
  }

  if (!business) return <ErrorState message={t("aiAgents.noBusiness")} />;

  if (canonicalRoute) {
    return <>{navigation}<LoadingState scope="page" /></>;
  }

  const pageError = bots.error || profiles.error;
  const sectionError = activeSection === "channels"
    ? botChannels.error
    : activeSection === "knowledge"
      ? knowledge.error
      : activeSection === "test"
        ? botChannels.error || knowledge.error
        : null;
  const sectionLoading = activeSection === "channels"
    ? botChannels.isLoading
    : activeSection === "knowledge"
      ? knowledge.isLoading
      : activeSection === "test"
        ? (loadChannels && botChannels.isLoading) || knowledge.isLoading
        : false;
  const mutationError = createBot.error || saveConfiguration.error || addChannel.error || toggleChannel.error || toggleBotStatus.error;

  const closeNavigationGuard = () => {
    if (navigationBlocker.state === "blocked") navigationBlocker.reset();
  };

  const discardAndContinue = () => {
    if (navigationBlocker.state !== "blocked") return;
    resetEditorDrafts();
    navigationBlocker.proceed();
  };

  const saveAndContinue = async () => {
    if (navigationBlocker.state !== "blocked") return;
    if (await saveEditorDrafts()) navigationBlocker.proceed();
  };

  return (
    <>
      {navigation}
      <AIAgentsWorkspace
        activeSection={activeSection}
        addChannel={addChannel}
        botChannels={botChannels.data || []}
        botDraft={botDraft}
        businessId={business.id}
        canManage={canManage}
        deleteControl={selectedBot && canDelete ? <AgentDeleteControl key={selectedBot.id} bot={selectedBot}
          onPendingChange={setIsDeleting}
          disabled={isSavingEditor || saveConfiguration.isPending || toggleBotStatus.isPending}
          onDeleted={() => {
            discardDeletedAgent();
            queryClient.setQueryData<BotType[]>(["bots"], current => current?.filter(bot => bot.id !== selectedBot.id));
            navigate("/app/ai-agents", { replace: true });
            void Promise.all(["bots", "ai-agent-profiles", "bot-channels", "ai-runtime-agents"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
          }} /> : undefined}
        canManageChannels={canManageChannels}
        canSuggest={canSuggest}
        canViewChannels={canViewChannels}
        createAgentPending={createBot.isPending}
        createError={createBot.error}
        createOpen={createOpen}
        dirty={editorDirty}
        isSaving={isSavingEditor || saveConfiguration.isPending || toggleBotStatus.isPending || isDeleting}
        knowledgeItems={(knowledge.data || []).filter(item => item.business === business.id)}
        mutationError={mutationError}
        navigationBlocked={navigationBlocker.state === "blocked"}
        newAgentName={newAgentName}
        newAgentScenario={newAgentScenario}
        onSetNewAgentScenario={setNewAgentScenario}
        hasCRMAgent={botList.some(bot => bot.scenario === "crm")}
        onCloseCreate={() => setCreateOpen(false)}
        onCloseNavigationGuard={closeNavigationGuard}
        onCreateAgent={() => { if (newAgentScenario) createBot.mutate(); }}
        onDiscardAndContinue={discardAndContinue}
        onSaveAndContinue={() => {
          void saveAndContinue().catch(() => undefined);
        }}
        onNavigateSection={(section) => navigate(`/app/ai-agents/${selectedBot?.id}/${section}`)}
        onOpenMessages={() => navigate("/app/conversations")}
        onOpenCreate={() => setCreateOpen(true)}
        onReset={resetEditorDrafts}
        onRetry={() => void Promise.all([
          bots.refetch(),
          profiles.refetch(),
        ])}
        onRetrySection={() => void Promise.all([
          ...(loadChannels ? [botChannels.refetch()] : []),
          ...(["knowledge", "test"].includes(activeSection) ? [knowledge.refetch()] : []),
        ])}
        onSave={() => void saveEditorDrafts().catch(() => undefined)}
        onSetNewAgentName={setNewAgentName}
        onToggleStatus={(active) => toggleBotStatus.mutate(active)}
        pageError={pageError}
        profileForm={profileForm}
        saveState={saveState}
        sectionError={sectionError}
        sectionLoading={sectionLoading}
        selectedBot={selectedBot}
        selectedProfile={selectedProfile}
        setBotDraft={setBotDraft}
        setProfileForm={setProfileForm}
        toggleChannel={toggleChannel}
      />
    </>
  );
}
