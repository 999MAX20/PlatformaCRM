import { CRMAgentRuntime } from "./CRMAgentRuntime";
import { CRMAgentSettings } from "./CRMAgentSettings";
import { useEffect, useState, type ComponentProps, type Dispatch, type ReactNode, type SetStateAction } from "react";

import { getApiErrorMessage } from "../../../api/client";
import { CrmWorkspacePage } from "../../../components/crm";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type {
  AgentProfile,
  Bot,
  BotChannel,
  BusinessKnowledgeItem,
  Id,
} from "../../../types";
import type { AgentFormState, AgentSection, BotDraftState } from "../aiAgentsTypes";
import { getOnboardingSteps } from "../aiAgentsUtils";
import { AIAgentEditorShell } from "./AIAgentEditorShell";
import { AgentPreviewPanel } from "./AgentPreviewPanel";
import { InstructionsSection, ModelsSection } from "./AIAgentConfigSection";
import { CustomerAgentOverview } from "./AIAgentRuntimeSection";
import { CreateAgentModal, UnsavedAgentChangesModal } from "./AIAgentModals";
import {
  AgentActionsSection,
  ChannelManagerSection,
  EmptyAgentsState,
  KnowledgeSection,
  ProfileManagerSection,
  TestAndLaunchSection,
} from "./AIAgentsSections";

type AddChannelMutation = ComponentProps<typeof ChannelManagerSection>["addChannel"];
type ToggleChannelMutation = ComponentProps<typeof ChannelManagerSection>["toggleChannel"];

export function AIAgentsWorkspace({
  activeSection,
  addChannel,
  botChannels,
  botDraft,
  businessId,
  canManage,
  canManageChannels,
  canSuggest,
  canViewChannels,
  createAgentPending,
  createError,
  createOpen,
  dirty,
  hasUserEdits,
  navigation,
  isSaving,
  knowledgeItems,
  mutationError,
  navigationBlocked,
  newAgentName,
  newAgentScenario,
  onSetNewAgentScenario,
  hasCRMAgent,
  onCloseCreate,
  onCloseNavigationGuard,
  onCreateAgent,
  onDiscardAndContinue,
  onSaveAndContinue,
  onNavigateSection,
  onOpenMessages,
  onOpenCreate,
  onReset,
  onRetry,
  onRetrySection,
  onSave,
  onSetNewAgentName,
  pageError,
  profileForm,
  saveState,
  sectionError,
  sectionLoading,
  selectedBot,
  selectedProfile,
  setBotDraft,
  setProfileForm,
  toggleChannel,
  deleteControl,
}: {
  activeSection: AgentSection;
  addChannel: AddChannelMutation;
  botChannels: BotChannel[];
  botDraft: BotDraftState;
  businessId: Id;
  canManage: boolean;
  canManageChannels: boolean;
  canSuggest: boolean;
  canViewChannels: boolean;
  createAgentPending: boolean;
  createError: unknown;
  createOpen: boolean;
  dirty: boolean;
  hasUserEdits: boolean;
  navigation: ReactNode;
  isSaving: boolean;
  knowledgeItems: BusinessKnowledgeItem[];
  mutationError: unknown;
  navigationBlocked: boolean;
  newAgentName: string;
  newAgentScenario: "inbox" | "crm" | null;
  onSetNewAgentScenario: (value: "inbox" | "crm") => void;
  hasCRMAgent: boolean;
  onCloseCreate: () => void;
  onCloseNavigationGuard: () => void;
  onCreateAgent: () => void;
  onDiscardAndContinue: () => void;
  onSaveAndContinue: () => void;
  onNavigateSection: (section: AgentSection) => void;
  onOpenMessages: () => void;
  onOpenCreate: () => void;
  onReset: () => void;
  onRetry: () => void;
  onRetrySection: () => void;
  onSave: () => void;
  onSetNewAgentName: Dispatch<SetStateAction<string>>;
  pageError: unknown;
  profileForm: AgentFormState;
  saveState: ComponentProps<typeof AIAgentEditorShell>["saveState"];
  sectionError: unknown;
  sectionLoading: boolean;
  selectedBot: Bot | null;
  selectedProfile: AgentProfile | null;
  setBotDraft: Dispatch<SetStateAction<BotDraftState>>;
  setProfileForm: Dispatch<SetStateAction<AgentFormState>>;
  toggleChannel: ToggleChannelMutation;
  deleteControl?: ReactNode;
}) {
  const { t } = useI18n();
  const [previewOpen, setPreviewOpen] = useState(false);
  useEffect(() => setPreviewOpen(false), [selectedBot?.id]);
  const showPreview = previewOpen && selectedBot?.scenario !== "crm" && activeSection !== "test";

  if (pageError) {
    return (
      <CrmWorkspacePage maxWidthClassName="max-w-[1520px]">
        <ErrorState
          error={pageError} message={getApiErrorMessage(pageError)}
          action={(
            <Button type="button" variant="secondary" onClick={onRetry}>
              {t("common.retry")}
            </Button>
          )}
        />
      </CrmWorkspacePage>
    );
  }

  const channels = botChannels.filter((channel) => channel.bot === selectedBot?.id);
  const activeChannelsCount = channels.filter((channel) => channel.status === "active").length;
  const activeKnowledgeCount = knowledgeItems.filter((item) => item.is_active).length;
  const onboardingSteps = selectedBot
    ? getOnboardingSteps({
        botId: selectedBot.id,
        profileReady: selectedBot.readiness?.profile_ready ?? Boolean(selectedProfile?.is_active),
        hasActiveChannel: selectedBot.readiness?.channel_ready ?? activeChannelsCount > 0,
        hasKnowledge: selectedBot.readiness?.knowledge_ready ?? activeKnowledgeCount > 0,
        t,
      })
    : [];
  const channelByName = (name: BotChannel["channel"]) => channels.find((channel) => channel.channel === name);

  return (
    <CrmWorkspacePage
      edgeToEdge
      className="px-4 pt-5 pb-24 sm:px-6 sm:pt-6 lg:pb-6"
      heightClassName="h-auto min-h-0"
      maxWidthClassName="max-w-[1520px]"
      testId="ai-agents-workspace-ready"
    >
      <div className="min-w-0">

        {selectedBot ? (
          <AIAgentEditorShell
            bot={selectedBot}
            activeSection={activeSection}
            canManage={canManage}
            dirty={dirty}
            hasUserEdits={hasUserEdits}
            profileExists={Boolean(selectedProfile)}
            navigation={navigation}
            previewOpen={showPreview}
            onOpenPreview={() => setPreviewOpen(!previewOpen)}
            preview={selectedBot.scenario !== "crm" && activeSection !== "test" ? <AgentPreviewPanel key={selectedBot.id} open={showPreview} onClose={() => setPreviewOpen(false)}>
              <TestAndLaunchSection bot={selectedBot} dirty={dirty || isSaving} canTest={canManage && canSuggest} />
            </AgentPreviewPanel> : undefined}
            saveDisabled={!botDraft.name.trim()}
            isSaving={isSaving}
            saveState={saveState}
            onSectionChange={onNavigateSection}
            onOpenMessages={onOpenMessages}
            onReset={onReset}
            onSave={onSave}
            showFooter={hasUserEdits || ["profile", "instructions", "advanced", "actions"].includes(activeSection) || (selectedBot.scenario === "crm" && activeSection === "knowledge")}
            afterFooter={activeSection === "advanced" ? deleteControl : undefined}
          >
            {mutationError ? <ErrorState error={mutationError} message={getApiErrorMessage(mutationError)} /> : null}
            {activeSection === "channels" && !canViewChannels ? (
              <ErrorState message={t("aiAgents.channelsPermissionDenied")} />
            ) : sectionLoading ? (
              <LoadingState initial />
            ) : sectionError ? (
              <ErrorState
                error={sectionError} message={getApiErrorMessage(sectionError)}
                action={<Button type="button" variant="secondary" onClick={onRetrySection}>{t("common.retry")}</Button>}
              />
            ) : activeSection === "overview" ? (
              <CustomerAgentOverview bot={selectedBot} onboardingSteps={onboardingSteps} channels={channels} canViewChannels={canViewChannels} />
            ) : activeSection === "instructions" ? (
              <InstructionsSection scenario={selectedBot.scenario} botDraft={botDraft} setBotDraft={setBotDraft} form={profileForm} setForm={setProfileForm} canManage={canManage} />
            ) : activeSection === "advanced" ? (
              <ModelsSection draft={botDraft} setDraft={setBotDraft} canManage={canManage} readiness={selectedBot.readiness} />
            ) : activeSection === "profile" ? (
              <ProfileManagerSection
                scenario={selectedBot.scenario}
                botDraft={botDraft}
                setBotDraft={setBotDraft}
                form={profileForm}
                setForm={setProfileForm}
                canManage={canManage}
                readiness={selectedBot.readiness}
              />
            ) : activeSection === "channels" ? (
              <ChannelManagerSection
                key={selectedBot.id}
                businessId={businessId}
                bot={selectedBot}
                canManage={canManageChannels}
                channelByName={channelByName}
                addChannel={addChannel}
                toggleChannel={toggleChannel}
              />
            ) : activeSection === "knowledge" ? (
              <>{selectedBot.scenario === "crm" && <CRMAgentSettings section="sources" form={profileForm} setForm={setProfileForm} canManage={canManage} />}<KnowledgeSection key={selectedBot.id} agentId={selectedBot.id} businessId={businessId} items={knowledgeItems} canManage={canManage} customerAgent={selectedBot.scenario === "inbox"} /></>
            ) : activeSection === "work" || activeSection === "analytics" ? (
              <CRMAgentRuntime key={`${selectedBot.id}-${activeSection}`} bot={selectedBot} section={activeSection} dirty={dirty} />
            ) : activeSection === "actions" && selectedBot.scenario === "crm" ? (
              <CRMAgentSettings section="actions" form={profileForm} setForm={setProfileForm} canManage={canManage} />
            ) : activeSection === "actions" ? (
              <AgentActionsSection
                botDraft={botDraft}
                setBotDraft={setBotDraft}
                form={profileForm}
                setForm={setProfileForm}
                canManage={canManage}
              />
            ) : (
              <TestAndLaunchSection
                bot={selectedBot}
                dirty={dirty}
                canTest={canManage && canSuggest}
              />
            )}
          </AIAgentEditorShell>
        ) : (
          <div className="space-y-3">
            {navigation}
            {mutationError ? <ErrorState error={mutationError} message={getApiErrorMessage(mutationError)} /> : null}
            <EmptyAgentsState canManage={canManage} onCreate={onOpenCreate} />
          </div>
        )}
      </div>

      <CreateAgentModal
        open={createOpen}
        canManage={canManage}
        error={createError}
        name={newAgentName}
        scenario={newAgentScenario}
        onScenarioChange={onSetNewAgentScenario}
        hasCRMAgent={hasCRMAgent}
        onNameChange={onSetNewAgentName}
        onClose={onCloseCreate}
        onSubmit={onCreateAgent}
        isCreating={createAgentPending}
      />
      <UnsavedAgentChangesModal
        open={navigationBlocked}
        isSaving={isSaving}
        onClose={onCloseNavigationGuard}
        onDiscard={onDiscardAndContinue}
        onSave={onSaveAndContinue}
      />
    </CrmWorkspacePage>
  );
}
