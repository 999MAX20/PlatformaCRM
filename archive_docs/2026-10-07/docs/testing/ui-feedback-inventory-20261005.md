# Реестр UI-состояний — 05.10.2026

Снимок UI-FEEDBACK-20261005. AST-инвентаризация исходников, не количество
уникальных событий и не доказательство воспроизведения каждой ветки.
Политики API, фоновых задач и маршрутов — в [общем реестре](../../actual_docs/UNIFIED_FALLBACK_INVENTORY.generated.md).
Результаты и сценарии — в [отчёте](ui-feedback-20261005.md).

- 313 мест использования 19 выбранных семейств в 107 файлах.
- 117 явных вызовов уведомлений; динамические вызовы через неизвестные алиасы не подсчитывались.
- 18 JSX-элементов с явным role=alert; возможны пересечения с семействами выше.
- 100 строк потребляют semantic warning/danger soft/bold в 50 файлах.

## Семейства

| Семейство | Использований в production source |
| --- | --- |
| StatusNotice | 52 |
| ErrorState | 142 |
| ForbiddenState | 4 |
| EmptyState | 25 |
| LoadingState | 58 |
| PageSkeleton | 3 |
| InlineFallback | 0 |
| PageFallback | 1 |
| PermissionFallback | 1 |
| ConnectivityBanner | 1 |
| FieldErrorSummary | 0 |
| RecoveryDetails | 3 |
| ActionFeedbackToast | 1 |
| ToastSurface | 1 |
| RouteErrorView | 1 |
| AppErrorBoundary | 1 |
| RouteErrorBoundary | 16 |
| UnreadMessagesNotice | 1 |
| AiInsightCard | 2 |

Ноль означает наличие компонента без прямого JSX-вызова в production source;
тестовые каталоги исключены. Ссылки на номера строк относятся к этому снимку.

## Все найденные места

| Компонент / вызов | Источник | Условие / обработчик в коде | Ключи текста |
| --- | --- | --- | --- |
| ConnectivityBanner | [frontend/src/app/providers.tsx:58](../../frontend/src/app/providers.tsx#L58) | ConnectivityStatus | — |
| LoadingState | [frontend/src/app/router.tsx:222](../../frontend/src/app/router.tsx#L222) | isLoading | common.loadingAccess |
| LoadingState | [frontend/src/app/router.tsx:233](../../frontend/src/app/router.tsx#L233) | isLoading | common.loadingAccess |
| LoadingState | [frontend/src/app/router.tsx:248](../../frontend/src/app/router.tsx#L248) | isLoading | common.loadingAccess |
| LoadingState | [frontend/src/app/router.tsx:267](../../frontend/src/app/router.tsx#L267) | PageLoader | common.loadingWorkspace |
| LoadingState | [frontend/src/app/router.tsx:286](../../frontend/src/app/router.tsx#L286) | isLoading | common.checkingAccess |
| ForbiddenState | [frontend/src/app/router.tsx:289](../../frontend/src/app/router.tsx#L289) | !user \|\| !business?.id | — |
| LoadingState | [frontend/src/app/router.tsx:304](../../frontend/src/app/router.tsx#L304) | isLoading | common.loadingWorkspace |
| RouteErrorBoundary | [frontend/src/app/router.tsx:832](../../frontend/src/app/router.tsx#L832) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:842](../../frontend/src/app/router.tsx#L842) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:847](../../frontend/src/app/router.tsx#L847) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:852](../../frontend/src/app/router.tsx#L852) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:857](../../frontend/src/app/router.tsx#L857) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:861](../../frontend/src/app/router.tsx#L861) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:870](../../frontend/src/app/router.tsx#L870) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:881](../../frontend/src/app/router.tsx#L881) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:892](../../frontend/src/app/router.tsx#L892) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:903](../../frontend/src/app/router.tsx#L903) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:914](../../frontend/src/app/router.tsx#L914) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:923](../../frontend/src/app/router.tsx#L923) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:988](../../frontend/src/app/router.tsx#L988) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:1009](../../frontend/src/app/router.tsx#L1009) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:1014](../../frontend/src/app/router.tsx#L1014) | errorElement | — |
| RouteErrorBoundary | [frontend/src/app/router.tsx:1041](../../frontend/src/app/router.tsx#L1041) | errorElement | — |
| ToastSurface | [frontend/src/components/actions/UndoToastProvider.tsx:45](../../frontend/src/components/actions/UndoToastProvider.tsx#L45) | item | — |
| AiInsightCard | [frontend/src/components/ai/PageAiHints.tsx:42](../../frontend/src/components/ai/PageAiHints.tsx#L42) | PageAiHints | — |
| ForbiddenState | [frontend/src/components/auth/PermissionGate.tsx:32](../../frontend/src/components/auth/PermissionGate.tsx#L32) | mode === "forbidden" | — |
| LoadingState | [frontend/src/components/crm/CrmEntityDrawer.tsx:105](../../frontend/src/components/crm/CrmEntityDrawer.tsx#L105) | query.isLoading | — |
| ErrorState | [frontend/src/components/crm/CrmEntityDrawer.tsx:106](../../frontend/src/components/crm/CrmEntityDrawer.tsx#L106) | query.error | crmCard.loadError |
| ErrorState | [frontend/src/components/crm/drawers/appointment.tsx:144](../../frontend/src/components/crm/drawers/appointment.tsx#L144) | notesMutation.error \|\| lifecycleMutation.error | crmCard.saveError |
| ErrorState | [frontend/src/components/crm/drawers/deal.tsx:75](../../frontend/src/components/crm/drawers/deal.tsx#L75) | mutation.error | crmCard.saveError |
| ErrorState | [frontend/src/components/crm/drawers/fallback.tsx:203](../../frontend/src/components/crm/drawers/fallback.tsx#L203) | mutation.error \|\| lifecycleMutation.error | crmCard.saveError |
| ErrorState | [frontend/src/components/crm/drawers/lead.tsx:95](../../frontend/src/components/crm/drawers/lead.tsx#L95) | lifecycleMutation.error | crmCard.saveError |
| ErrorState | [frontend/src/components/crm/drawers/panels.tsx:246](../../frontend/src/components/crm/drawers/panels.tsx#L246) | uploadMutation.error \|\| attachmentActionError | — |
| ErrorState | [frontend/src/components/crm/drawers/panels.tsx:410](../../frontend/src/components/crm/drawers/panels.tsx#L410) | renameMutation.error | — |
| ErrorState | [frontend/src/components/crm/drawers/panels.tsx:495](../../frontend/src/components/crm/drawers/panels.tsx#L495) | mutation.error | crmCard.taskError |
| ErrorState | [frontend/src/components/crm/drawers/panels.tsx:602](../../frontend/src/components/crm/drawers/panels.tsx#L602) | mutation.error | crmCard.commentError |
| LoadingState | [frontend/src/components/crm/EntityWorkspace.tsx:192](../../frontend/src/components/crm/EntityWorkspace.tsx#L192) | EntityWorkspaceLoadingState | — |
| ErrorState | [frontend/src/components/crm/EntityWorkspace.tsx:200](../../frontend/src/components/crm/EntityWorkspace.tsx#L200) | EntityWorkspaceErrorState | — |
| EmptyState | [frontend/src/components/crm/EntityWorkspace.tsx:214](../../frontend/src/components/crm/EntityWorkspace.tsx#L214) | EntityWorkspaceEmptyState | — |
| StatusNotice | [frontend/src/components/forms/AppointmentForm.tsx:48](../../frontend/src/components/forms/AppointmentForm.tsx#L48) | SetupNotice | — |
| ErrorState | [frontend/src/components/forms/AppointmentForm.tsx:294](../../frontend/src/components/forms/AppointmentForm.tsx#L294) | slots.error | — |
| StatusNotice | [frontend/src/components/forms/AppointmentForm.tsx:297](../../frontend/src/components/forms/AppointmentForm.tsx#L297) | noSlots | appointment.noSlotsForDate, appointment.workingWindow, appointment.applyQuickHours, appointment.openHours |
| ErrorState | [frontend/src/components/forms/AppointmentForm.tsx:321](../../frontend/src/components/forms/AppointmentForm.tsx#L321) | submitError | — |
| LoadingState | [frontend/src/components/forms/AppointmentRescheduleForm.tsx:111](../../frontend/src/components/forms/AppointmentRescheduleForm.tsx#L111) | slots.isLoading | — |
| ErrorState | [frontend/src/components/forms/AppointmentRescheduleForm.tsx:123](../../frontend/src/components/forms/AppointmentRescheduleForm.tsx#L123) | submitError \|\| slots.error | — |
| StatusNotice | [frontend/src/components/forms/ClientForm.tsx:100](../../frontend/src/components/forms/ClientForm.tsx#L100) | duplicates.length | clients.duplicateTitle, clients.duplicateText, clients.noContact, clients.openExisting, clients.mergeCurrent |
| ErrorState | [frontend/src/components/forms/ClientForm.tsx:123](../../frontend/src/components/forms/ClientForm.tsx#L123) | duplicateError | — |
| StatusNotice | [frontend/src/components/forms/LeadForm.tsx:96](../../frontend/src/components/forms/LeadForm.tsx#L96) | !hasClients | leadForm.needClientTitle, leadForm.needClientText, clients.create |
| StatusNotice | [frontend/src/components/forms/LeadForm.tsx:106](../../frontend/src/components/forms/LeadForm.tsx#L106) | !hasServices | leadForm.serviceLaterTitle, leadForm.serviceLaterText, services.title |
| StatusNotice | [frontend/src/components/forms/LeadForm.tsx:123](../../frontend/src/components/forms/LeadForm.tsx#L123) | duplicates.length \|\| relatedLeadsCount | leadForm.relatedTitle, leadForm.relatedCount, leadForm.relatedText, clients.openExisting, clients.openExisting |
| ErrorState | [frontend/src/components/forms/WorkingHoursForm.tsx:250](../../frontend/src/components/forms/WorkingHoursForm.tsx#L250) | error | — |
| UnreadMessagesNotice | [frontend/src/components/layout/Header.tsx:429](../../frontend/src/components/layout/Header.tsx#L429) | chatToastOpen | — |
| StatusNotice | [frontend/src/components/notifications/NotificationProvider.tsx:41](../../frontend/src/components/notifications/NotificationProvider.tsx#L41) | ActionFeedbackToast | common.close |
| ActionFeedbackToast | [frontend/src/components/notifications/NotificationProvider.tsx:122](../../frontend/src/components/notifications/NotificationProvider.tsx#L122) | NotificationProvider | — |
| StatusNotice | [frontend/src/components/notifications/UnreadMessagesNotice.tsx:13](../../frontend/src/components/notifications/UnreadMessagesNotice.tsx#L13) | UnreadMessagesNotice | header.chatToastTitle, header.chatToastText, common.close, header.openMessages |
| EmptyState | [frontend/src/components/tables/DataTable.tsx:91](../../frontend/src/components/tables/DataTable.tsx#L91) | !rows.length | — |
| StatusNotice | [frontend/src/components/ui/ConnectivityBanner.tsx:20](../../frontend/src/components/ui/ConnectivityBanner.tsx#L20) | ConnectivityBanner | common.retry |
| StatusNotice | [frontend/src/components/ui/FallbackSurfaces.tsx:52](../../frontend/src/components/ui/FallbackSurfaces.tsx#L52) | InlineFallback | fallback.inline.title |
| RecoveryDetails | [frontend/src/components/ui/FallbackSurfaces.tsx:58](../../frontend/src/components/ui/FallbackSurfaces.tsx#L58) | InlineFallback | — |
| RecoveryDetails | [frontend/src/components/ui/FallbackSurfaces.tsx:118](../../frontend/src/components/ui/FallbackSurfaces.tsx#L118) | PageFallback | — |
| StatusNotice | [frontend/src/components/ui/FallbackSurfaces.tsx:126](../../frontend/src/components/ui/FallbackSurfaces.tsx#L126) | PermissionFallback | fallback.permission.title, fallback.permission.guidance |
| RecoveryDetails | [frontend/src/components/ui/FallbackSurfaces.tsx:137](../../frontend/src/components/ui/FallbackSurfaces.tsx#L137) | PermissionFallback | — |
| StatusNotice | [frontend/src/components/ui/FieldErrorSummary.tsx:26](../../frontend/src/components/ui/FieldErrorSummary.tsx#L26) | FieldErrorSummary | fallback.fields.title, fallback.fields.description |
| PageFallback | [frontend/src/components/ui/RouteErrorBoundary.tsx:56](../../frontend/src/components/ui/RouteErrorBoundary.tsx#L56) | RouteErrorView | routeError.title, routeError.back, routeError.home |
| RouteErrorView | [frontend/src/components/ui/RouteErrorBoundary.tsx:83](../../frontend/src/components/ui/RouteErrorBoundary.tsx#L83) | RouteErrorBoundary | — |
| StatusNotice | [frontend/src/components/ui/StateViews.tsx:36](../../frontend/src/components/ui/StateViews.tsx#L36) | ErrorState | fallback.inline.title |
| PermissionFallback | [frontend/src/components/ui/StateViews.tsx:55](../../frontend/src/components/ui/StateViews.tsx#L55) | error | — |
| StatusNotice | [frontend/src/components/ui/StateViews.tsx:58](../../frontend/src/components/ui/StateViews.tsx#L58) | ForbiddenState | permissions.hiddenTitle, actions.errorForbidden, permissions.hiddenText |
| ErrorState | [frontend/src/features/account/AccountPage.tsx:138](../../frontend/src/features/account/AccountPage.tsx#L138) | profileMutation.error | — |
| ErrorState | [frontend/src/features/account/AccountPage.tsx:169](../../frontend/src/features/account/AccountPage.tsx#L169) | loginHistory.error | common.retry |
| ErrorState | [frontend/src/features/account/AccountPage.tsx:181](../../frontend/src/features/account/AccountPage.tsx#L181) | notificationPreferenceMutation.error | — |
| ErrorState | [frontend/src/features/account/AccountPage.tsx:182](../../frontend/src/features/account/AccountPage.tsx#L182) | notificationPreferences.error | common.retry |
| ErrorState | [frontend/src/features/account/AccountPage.tsx:215](../../frontend/src/features/account/AccountPage.tsx#L215) | passwordMutation.error | — |
| ErrorState | [frontend/src/features/account/ActiveSessions.tsx:45](../../frontend/src/features/account/ActiveSessions.tsx#L45) | sessions.error | common.retry |
| ErrorState | [frontend/src/features/account/ActiveSessions.tsx:62](../../frontend/src/features/account/ActiveSessions.tsx#L62) | mfa.error | common.retry |
| ErrorState | [frontend/src/features/account/ActiveSessions.tsx:63](../../frontend/src/features/account/ActiveSessions.tsx#L63) | mutation.error | — |
| ErrorState | [frontend/src/features/account/InterfaceSettingsCard.tsx:52](../../frontend/src/features/account/InterfaceSettingsCard.tsx#L52) | mutation.error | — |
| ErrorState | [frontend/src/features/account/MfaSecurityCard.tsx:102](../../frontend/src/features/account/MfaSecurityCard.tsx#L102) | statusQuery.error \|\| startMutation.error | — |
| StatusNotice | [frontend/src/features/account/MfaSecurityCard.tsx:116](../../frontend/src/features/account/MfaSecurityCard.tsx#L116) | recoveryCodes.length | mfa.recoveryWarning |
| ErrorState | [frontend/src/features/account/MfaSecurityCard.tsx:123](../../frontend/src/features/account/MfaSecurityCard.tsx#L123) | actionMutation.error | — |
| ErrorState | [frontend/src/features/account/NotificationSoundControl.tsx:43](../../frontend/src/features/account/NotificationSoundControl.tsx#L43) | error | account.soundUnavailable |
| ErrorState | [frontend/src/features/analytics/AnalyticsPage.tsx:103](../../frontend/src/features/analytics/AnalyticsPage.tsx#L103) | !business | analytics.noBusiness |
| LoadingState | [frontend/src/features/analytics/AnalyticsPage.tsx:104](../../frontend/src/features/analytics/AnalyticsPage.tsx#L104) | appointments.isLoading \|\| services.isLoading \|\| metrics.isLoading | — |
| ErrorState | [frontend/src/features/analytics/AnalyticsPage.tsx:105](../../frontend/src/features/analytics/AnalyticsPage.tsx#L105) | metrics.error | analytics.loadError |
| LoadingState | [frontend/src/features/analytics/AnalyticsPage.tsx:272](../../frontend/src/features/analytics/AnalyticsPage.tsx#L272) | reportSummary.isLoading | analytics.loadingReports |
| ErrorState | [frontend/src/features/analytics/AnalyticsPage.tsx:273](../../frontend/src/features/analytics/AnalyticsPage.tsx#L273) | reportSummary.error | — |
| LoadingState | [frontend/src/features/analytics/AnalyticsPage.tsx:415](../../frontend/src/features/analytics/AnalyticsPage.tsx#L415) | teamPerformance.isLoading | analytics.loadingTeam |
| LoadingState | [frontend/src/features/assistant/AIAgentsPage.tsx:183](../../frontend/src/features/assistant/AIAgentsPage.tsx#L183) | isPageLoading | aiAgents.loading |
| ErrorState | [frontend/src/features/assistant/AIAgentsPage.tsx:186](../../frontend/src/features/assistant/AIAgentsPage.tsx#L186) | !business | aiAgents.noBusiness |
| LoadingState | [frontend/src/features/assistant/AIAgentsPage.tsx:189](../../frontend/src/features/assistant/AIAgentsPage.tsx#L189) | canonicalRoute | aiAgents.loading |
| LoadingState | [frontend/src/features/assistant/AIAssistantPage.tsx:428](../../frontend/src/features/assistant/AIAssistantPage.tsx#L428) | isLoading | — |
| ErrorState | [frontend/src/features/assistant/AIAssistantPage.tsx:429](../../frontend/src/features/assistant/AIAssistantPage.tsx#L429) | !business | aiAssistant.noBusiness |
| ErrorState | [frontend/src/features/assistant/AIAssistantPage.tsx:462](../../frontend/src/features/assistant/AIAssistantPage.tsx#L462) | briefMutation.error \|\| memoryMutation.error \|\| analystBrief.error \|\| suggestActionsMutation.error \|\| runSuggestedActionMutation.error | — |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:468](../../frontend/src/features/assistant/AIAssistantPage.tsx#L468) | aiStatus.data && !aiStatus.data.ready | aiAssistant.providerUnavailableTitle, aiAssistant.providerUnavailableText |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:591](../../frontend/src/features/assistant/AIAssistantPage.tsx#L591) | canSuggestActions | fallback.permission.title, permissions.forbidden, permissions.resource.ai_pipeline |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:603](../../frontend/src/features/assistant/AIAssistantPage.tsx#L603) | analystBrief.data && ["unavailable", "invalid_response"].includes(analystBrief.data.provider_state) | aiQuality.unavailable |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:605](../../frontend/src/features/assistant/AIAssistantPage.tsx#L605) | analystBrief.data?.provider_state === "mock" | aiQuality.mock |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:708](../../frontend/src/features/assistant/AIAssistantPage.tsx#L708) | !canViewAnalyst | fallback.permission.title, permissions.forbidden, permissions.resource.ai_analyst |
| StatusNotice | [frontend/src/features/assistant/AIAssistantPage.tsx:717](../../frontend/src/features/assistant/AIAssistantPage.tsx#L717) | !analystBrief.isLoading && analystHasNoSourceData | aiNavigator.noSourceDataState |
| AiInsightCard | [frontend/src/features/assistant/AIAssistantPage.tsx:781](../../frontend/src/features/assistant/AIAssistantPage.tsx#L781) | AIAssistantPage | — |
| LoadingState | [frontend/src/features/assistant/components/AgentNavigation.tsx:135](../../frontend/src/features/assistant/components/AgentNavigation.tsx#L135) | isLoading | aiAgents.loading |
| ErrorState | [frontend/src/features/assistant/components/AgentNavigation.tsx:136](../../frontend/src/features/assistant/components/AgentNavigation.tsx#L136) | error | common.retry |
| ErrorState | [frontend/src/features/assistant/components/AIAgentKnowledgeSection.tsx:120](../../frontend/src/features/assistant/components/AIAgentKnowledgeSection.tsx#L120) | saveKnowledge.error | — |
| ErrorState | [frontend/src/features/assistant/components/AIAgentModals.tsx:48](../../frontend/src/features/assistant/components/AIAgentModals.tsx#L48) | error | — |
| ErrorState | [frontend/src/features/assistant/components/AIAgentPreview.tsx:27](../../frontend/src/features/assistant/components/AIAgentPreview.tsx#L27) | !canTest | aiSetup.previewForbidden |
| StatusNotice | [frontend/src/features/assistant/components/AIAgentPreview.tsx:28](../../frontend/src/features/assistant/components/AIAgentPreview.tsx#L28) | blocked | aiSetup.saveBeforeTest |
| StatusNotice | [frontend/src/features/assistant/components/AIAgentPreview.tsx:46](../../frontend/src/features/assistant/components/AIAgentPreview.tsx#L46) | preview.data | — |
| ErrorState | [frontend/src/features/assistant/components/AIAgentPreview.tsx:54](../../frontend/src/features/assistant/components/AIAgentPreview.tsx#L54) | preview.error | — |
| ErrorState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:123](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L123) | pageError | common.retry |
| ErrorState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:178](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L178) | mutationError | — |
| ErrorState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:180](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L180) | activeSection === "channels" && !canViewChannels | aiAgents.channelsPermissionDenied |
| LoadingState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:182](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L182) | sectionLoading | aiAgents.sectionLoading |
| ErrorState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:184](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L184) | sectionError | common.retry |
| ErrorState | [frontend/src/features/assistant/components/AIAgentsWorkspace.tsx:228](../../frontend/src/features/assistant/components/AIAgentsWorkspace.tsx#L228) | mutationError | — |
| ErrorState | [frontend/src/features/auth/AuthProvider.tsx:232](../../frontend/src/features/auth/AuthProvider.tsx#L232) | recoveryError && !isAuthenticated | — |
| StatusNotice | [frontend/src/features/auth/AuthProvider.tsx:234](../../frontend/src/features/auth/AuthProvider.tsx#L234) | recoveryError && isAuthenticated | — |
| ErrorState | [frontend/src/features/auth/ForgotPasswordPage.tsx:54](../../frontend/src/features/auth/ForgotPasswordPage.tsx#L54) | error | — |
| StatusNotice | [frontend/src/features/auth/ForgotPasswordPage.tsx:55](../../frontend/src/features/auth/ForgotPasswordPage.tsx#L55) | requestMessage | — |
| LoadingState | [frontend/src/features/auth/InviteAcceptPage.tsx:72](../../frontend/src/features/auth/InviteAcceptPage.tsx#L72) | preview.isLoading \|\| isAuthLoading | invite.checking |
| ErrorState | [frontend/src/features/auth/InviteAcceptPage.tsx:88](../../frontend/src/features/auth/InviteAcceptPage.tsx#L88) | preview.error | — |
| StatusNotice | [frontend/src/features/auth/InviteAcceptPage.tsx:90](../../frontend/src/features/auth/InviteAcceptPage.tsx#L90) | preview.data?.status && preview.data.status !== "pending" | invite.inactive |
| ErrorState | [frontend/src/features/auth/InviteAcceptPage.tsx:104](../../frontend/src/features/auth/InviteAcceptPage.tsx#L104) | acceptMutation.error | — |
| ErrorState | [frontend/src/features/auth/InviteAcceptPage.tsx:123](../../frontend/src/features/auth/InviteAcceptPage.tsx#L123) | !isInvitedAccount | invite.wrongAccount |
| StatusNotice | [frontend/src/features/auth/LoginPage.tsx:231](../../frontend/src/features/auth/LoginPage.tsx#L231) | sessionExpiredNotice && !error | fallback.session.title, actions.errorUnauthenticated |
| StatusNotice | [frontend/src/features/auth/LoginPage.tsx:244](../../frontend/src/features/auth/LoginPage.tsx#L244) | error | fallback.inline.title |
| ErrorState | [frontend/src/features/auth/MfaPage.tsx:132](../../frontend/src/features/auth/MfaPage.tsx#L132) | error | — |
| StatusNotice | [frontend/src/features/auth/MfaPage.tsx:136](../../frontend/src/features/auth/MfaPage.tsx#L136) | recoveryCodes.length | mfa.recoveryWarning |
| ErrorState | [frontend/src/features/auth/ResetPasswordPage.tsx:63](../../frontend/src/features/auth/ResetPasswordPage.tsx#L63) | error | — |
| ErrorState | [frontend/src/features/automations/AutomationsPage.tsx:218](../../frontend/src/features/automations/AutomationsPage.tsx#L218) | !business | automations.noBusiness |
| LoadingState | [frontend/src/features/automations/AutomationsPage.tsx:219](../../frontend/src/features/automations/AutomationsPage.tsx#L219) | automationRules.isLoading \|\| templates.isLoading \|\| runs.isLoading | — |
| ErrorState | [frontend/src/features/automations/AutomationsPage.tsx:236](../../frontend/src/features/automations/AutomationsPage.tsx#L236) | applyTemplateMutation.error \|\| toggleMutation.error \|\| mutation.error \|\| createManualMutation.error | automations.saveError |
| EmptyState | [frontend/src/features/automations/AutomationsPage.tsx:337](../../frontend/src/features/automations/AutomationsPage.tsx#L337) | !ruleList.length | automations.emptyTitle, automations.emptyDescription, automations.createRule |
| ErrorState | [frontend/src/features/automations/AutomationsPage.tsx:432](../../frontend/src/features/automations/AutomationsPage.tsx#L432) | selectedRun.error | automations.runFailureDetails |
| ErrorState | [frontend/src/features/automations/AutomationsPage.tsx:490](../../frontend/src/features/automations/AutomationsPage.tsx#L490) | advancedError | — |
| LoadingState | [frontend/src/features/bots/BotDetailPage.tsx:76](../../frontend/src/features/bots/BotDetailPage.tsx#L76) | bot.isLoading \|\| botChannels.isLoading \|\| botConversations.isLoading \|\| botMessages.isLoading | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:77](../../frontend/src/features/bots/BotDetailPage.tsx#L77) | bot.error | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:78](../../frontend/src/features/bots/BotDetailPage.tsx#L78) | !bot.data | botDetail.notFound |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:122](../../frontend/src/features/bots/BotDetailPage.tsx#L122) | addWebsiteChannel.error | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:123](../../frontend/src/features/bots/BotDetailPage.tsx#L123) | addWhatsAppChannel.error | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:124](../../frontend/src/features/bots/BotDetailPage.tsx#L124) | previewMutation.error | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:125](../../frontend/src/features/bots/BotDetailPage.tsx#L125) | followUpMutation.error | — |
| ErrorState | [frontend/src/features/bots/BotDetailPage.tsx:126](../../frontend/src/features/bots/BotDetailPage.tsx#L126) | suggestReplyMutation.error | — |
| ErrorState | [frontend/src/features/bots/BotsPage.tsx:52](../../frontend/src/features/bots/BotsPage.tsx#L52) | !business | bots.noBusiness |
| LoadingState | [frontend/src/features/bots/BotsPage.tsx:53](../../frontend/src/features/bots/BotsPage.tsx#L53) | bots.isLoading \|\| botChannels.isLoading \|\| botConversations.isLoading | — |
| EmptyState | [frontend/src/features/bots/BotsPage.tsx:66](../../frontend/src/features/bots/BotsPage.tsx#L66) | !botList.length | bots.emptyTitle, bots.emptyText, bots.create |
| ErrorState | [frontend/src/features/calendar/CalendarPage.tsx:404](../../frontend/src/features/calendar/CalendarPage.tsx#L404) | !business | calendar.noBusiness |
| ErrorState | [frontend/src/features/calendar/CalendarPage.tsx:405](../../frontend/src/features/calendar/CalendarPage.tsx#L405) | createContext.error | — |
| LoadingState | [frontend/src/features/calendar/CalendarPage.tsx:406](../../frontend/src/features/calendar/CalendarPage.tsx#L406) | createContext.isLoading | — |
| ErrorState | [frontend/src/features/calendar/CalendarPage.tsx:435](../../frontend/src/features/calendar/CalendarPage.tsx#L435) | calendarDataError | common.retry |
| LoadingState | [frontend/src/features/calendar/CalendarPage.tsx:743](../../frontend/src/features/calendar/CalendarPage.tsx#L743) | isCalendarDataLoading | calendar.loadingInline |
| EmptyState | [frontend/src/features/calendar/CalendarPage.tsx:843](../../frontend/src/features/calendar/CalendarPage.tsx#L843) | !isCalendarDataLoading &&             !dayAppointments.length &&             !dayTasks.length | calendar.emptyDayTitle, calendar.emptyDayText, calendar.newBooking, calendar.openTodayTasks |
| ErrorState | [frontend/src/features/clients/ClientsPage.tsx:288](../../frontend/src/features/clients/ClientsPage.tsx#L288) | !business | clients.noBusiness |
| LoadingState | [frontend/src/features/clients/ClientsPage.tsx:289](../../frontend/src/features/clients/ClientsPage.tsx#L289) | pageLoading | — |
| ErrorState | [frontend/src/features/clients/ClientsPage.tsx:309](../../frontend/src/features/clients/ClientsPage.tsx#L309) | pageError | common.retry |
| ErrorState | [frontend/src/features/clients/ClientWorkspacePage.tsx:379](../../frontend/src/features/clients/ClientWorkspacePage.tsx#L379) | actions.business?.id | account.businessRequired |
| EmptyState | [frontend/src/features/clients/components/ClientInspector.tsx:76](../../frontend/src/features/clients/components/ClientInspector.tsx#L76) | !row.deals.length | clients.noDeals |
| EmptyState | [frontend/src/features/clients/components/ClientInspector.tsx:96](../../frontend/src/features/clients/components/ClientInspector.tsx#L96) | !row.tasks.length | clients.noActiveTasks |
| EmptyState | [frontend/src/features/clients/components/ClientInspector.tsx:113](../../frontend/src/features/clients/components/ClientInspector.tsx#L113) | FilesTab | clients.noFiles |
| EmptyState | [frontend/src/features/clients/components/ClientInspector.tsx:375](../../frontend/src/features/clients/components/ClientInspector.tsx#L375) | !historyItems.length | clients.emptyHistory |
| StatusNotice | [frontend/src/features/clients/components/ClientsModals.tsx:106](../../frontend/src/features/clients/components/ClientsModals.tsx#L106) | mergePreview | clients.mergePreviewWarning, clients.mergePreviewPolicy |
| EmptyState | [frontend/src/features/clients/components/ClientWorkspaceSections.tsx:70](../../frontend/src/features/clients/components/ClientWorkspaceSections.tsx#L70) | EmptyRelated | — |
| StatusNotice | [frontend/src/features/conversations/components/ConversationComposer.tsx:35](../../frontend/src/features/conversations/components/ConversationComposer.tsx#L35) | selected.status === "closed" | conversations.closedReplyNotice |
| StatusNotice | [frontend/src/features/conversations/components/ConversationListPane.tsx:155](../../frontend/src/features/conversations/components/ConversationListPane.tsx#L155) | connectorReadinessError | conversations.channelStatusUnavailable, common.retry |
| StatusNotice | [frontend/src/features/conversations/components/ConversationListPane.tsx:177](../../frontend/src/features/conversations/components/ConversationListPane.tsx#L177) | unavailableChannelCount | conversations.channelsUnavailable, conversations.openIntegrations |
| LoadingState | [frontend/src/features/conversations/components/ConversationListPane.tsx:228](../../frontend/src/features/conversations/components/ConversationListPane.tsx#L228) | loading | conversations.loadingDialogs |
| EmptyState | [frontend/src/features/conversations/components/ConversationListPane.tsx:231](../../frontend/src/features/conversations/components/ConversationListPane.tsx#L231) | !loading && !items.length | conversations.emptyTitle, conversations.emptyText |
| LoadingState | [frontend/src/features/conversations/components/ConversationThreadPane.tsx:208](../../frontend/src/features/conversations/components/ConversationThreadPane.tsx#L208) | messagesLoading | conversations.loadingHistory |
| EmptyState | [frontend/src/features/conversations/components/ConversationThreadPane.tsx:222](../../frontend/src/features/conversations/components/ConversationThreadPane.tsx#L222) | !messagesLoading && !messageList.length | conversations.noMessagesTitle, conversations.noMessagesText |
| ErrorState | [frontend/src/features/conversations/components/PipelineConfirmationDialog.tsx:39](../../frontend/src/features/conversations/components/PipelineConfirmationDialog.tsx#L39) | error | — |
| ErrorState | [frontend/src/features/conversations/ConversationsPage.tsx:1305](../../frontend/src/features/conversations/ConversationsPage.tsx#L1305) | pageError | common.retry |
| LoadingState | [frontend/src/features/conversations/ConversationsPage.tsx:1917](../../frontend/src/features/conversations/ConversationsPage.tsx#L1917) | quickReplies.isLoading | common.loading |
| EmptyState | [frontend/src/features/conversations/ConversationsPage.tsx:1920](../../frontend/src/features/conversations/ConversationsPage.tsx#L1920) | !quickReplies.isLoading && !quickReplyTemplates.length | conversations.noTemplates, conversations.noQuickRepliesText |
| LoadingState | [frontend/src/features/conversations/ConversationsPage.tsx:1984](../../frontend/src/features/conversations/ConversationsPage.tsx#L1984) | clientLinkCandidates.isLoading | common.loading |
| EmptyState | [frontend/src/features/conversations/ConversationsPage.tsx:1988](../../frontend/src/features/conversations/ConversationsPage.tsx#L1988) | !clientLinkCandidates.isLoading &&               !clientLinkCandidates.data?.length | conversations.noLinkCandidates, conversations.noLinkCandidatesText |
| LoadingState | [frontend/src/features/conversations/ConversationsPage.tsx:2017](../../frontend/src/features/conversations/ConversationsPage.tsx#L2017) | leadLinkCandidates.isLoading | common.loading |
| EmptyState | [frontend/src/features/conversations/ConversationsPage.tsx:2021](../../frontend/src/features/conversations/ConversationsPage.tsx#L2021) | !leadLinkCandidates.isLoading &&               !leadLinkCandidates.data?.length | conversations.noLinkCandidates, conversations.noLinkCandidatesText |
| LoadingState | [frontend/src/features/conversations/ConversationsPage.tsx:2048](../../frontend/src/features/conversations/ConversationsPage.tsx#L2048) | dealLinkCandidates.isLoading | common.loading |
| EmptyState | [frontend/src/features/conversations/ConversationsPage.tsx:2052](../../frontend/src/features/conversations/ConversationsPage.tsx#L2052) | !dealLinkCandidates.isLoading &&               !dealLinkCandidates.data?.length | conversations.noLinkCandidates, conversations.noLinkCandidatesText |
| PageSkeleton | [frontend/src/features/dashboard/DashboardPage.tsx:82](../../frontend/src/features/dashboard/DashboardPage.tsx#L82) | businessLoading | — |
| ErrorState | [frontend/src/features/dashboard/DashboardPage.tsx:83](../../frontend/src/features/dashboard/DashboardPage.tsx#L83) | !business | dashboard.noBusiness |
| EmptyState | [frontend/src/features/dashboard/ManagerDashboard.tsx:93](../../frontend/src/features/dashboard/ManagerDashboard.tsx#L93) | children.length | — |
| LoadingState | [frontend/src/features/dashboard/ManagerDashboard.tsx:361](../../frontend/src/features/dashboard/ManagerDashboard.tsx#L361) | isWorkQueuesLoading | dashboard.loadingPriorities |
| ErrorState | [frontend/src/features/dashboard/ManagerDashboard.tsx:365](../../frontend/src/features/dashboard/ManagerDashboard.tsx#L365) | workQueuesError | dashboard.priorityQueueError, common.retry |
| LoadingState | [frontend/src/features/dashboard/OwnerDashboard.tsx:572](../../frontend/src/features/dashboard/OwnerDashboard.tsx#L572) | isWorkQueuesLoading | dashboard.loadingPriorities |
| ErrorState | [frontend/src/features/dashboard/OwnerDashboard.tsx:576](../../frontend/src/features/dashboard/OwnerDashboard.tsx#L576) | workQueuesError | dashboard.priorityQueueError, common.retry |
| StatusNotice | [frontend/src/features/deals/components/DealDetailPanel.tsx:138](../../frontend/src/features/deals/components/DealDetailPanel.tsx#L138) | deal.status === "open" && !deal.nextTask && !deal.next_action_at | deals.noMoveWithoutNext |
| StatusNotice | [frontend/src/features/deals/components/DealModals.tsx:54](../../frontend/src/features/deals/components/DealModals.tsx#L54) | !clients.length | deals.needClientFirst, clients.create |
| ErrorState | [frontend/src/features/deals/DealsPage.tsx:258](../../frontend/src/features/deals/DealsPage.tsx#L258) | !business | deals.noBusiness |
| ErrorState | [frontend/src/features/deals/DealsPage.tsx:259](../../frontend/src/features/deals/DealsPage.tsx#L259) | createContext.error | — |
| LoadingState | [frontend/src/features/deals/DealsPage.tsx:260](../../frontend/src/features/deals/DealsPage.tsx#L260) | createContext.isLoading | — |
| LoadingState | [frontend/src/features/deals/DealsPage.tsx:261](../../frontend/src/features/deals/DealsPage.tsx#L261) | isLoading | — |
| ErrorState | [frontend/src/features/deals/DealsPage.tsx:287](../../frontend/src/features/deals/DealsPage.tsx#L287) | dealWorkspaceError | common.retry |
| ErrorState | [frontend/src/features/deals/DealsPage.tsx:295](../../frontend/src/features/deals/DealsPage.tsx#L295) | !data.pipelines.length | deals.noPipeline |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:165](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L165) | connector?.last_error | — |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:208](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L208) | isRequestOnly | integrations.card.requestNotice |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:211](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L211) | isRoadmapOnly | integrations.card.roadmapNotice |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:217](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L217) | connector.status !== "connected" | integrations.card.pendingNotice |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:219](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L219) | connector.status !== "connected" | integrations.card.connectedNotice |
| ErrorState | [frontend/src/features/integrations/components/ConnectorCard.tsx:231](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L231) | error | — |
| StatusNotice | [frontend/src/features/integrations/components/ConnectorCard.tsx:234](../../frontend/src/features/integrations/components/ConnectorCard.tsx#L234) | canManage | integrations.card.readOnly |
| ErrorState | [frontend/src/features/integrations/components/ImportPanel.tsx:123](../../frontend/src/features/integrations/components/ImportPanel.tsx#L123) | importError | — |
| StatusNotice | [frontend/src/features/integrations/components/ImportPanel.tsx:191](../../frontend/src/features/integrations/components/ImportPanel.tsx#L191) | errors.length | integrations.import.fixFileShort, integrations.import.rowNeedsReview, integrations.import.columnsNeedReview |
| StatusNotice | [frontend/src/features/integrations/components/ImportPanel.tsx:210](../../frontend/src/features/integrations/components/ImportPanel.tsx#L210) | duplicates.length | integrations.import.duplicatesFound, integrations.import.duplicatesDescription |
| StatusNotice | [frontend/src/features/integrations/components/ProviderCard.tsx:259](../../frontend/src/features/integrations/components/ProviderCard.tsx#L259) | connector?.last_error | — |
| StatusNotice | [frontend/src/features/integrations/components/ProviderCard.tsx:294](../../frontend/src/features/integrations/components/ProviderCard.tsx#L294) | latestRun.error | — |
| ErrorState | [frontend/src/features/integrations/components/ProviderCard.tsx:309](../../frontend/src/features/integrations/components/ProviderCard.tsx#L309) | error | — |
| ErrorState | [frontend/src/features/integrations/components/setup/InstagramSetup.tsx:150](../../frontend/src/features/integrations/components/setup/InstagramSetup.tsx#L150) | !channel | aiAgents.channelSetupUnavailable |
| ErrorState | [frontend/src/features/integrations/components/setup/InstagramSetup.tsx:160](../../frontend/src/features/integrations/components/setup/InstagramSetup.tsx#L160) | error | — |
| ErrorState | [frontend/src/features/integrations/components/setup/KaspiPricingSetup.tsx:89](../../frontend/src/features/integrations/components/setup/KaspiPricingSetup.tsx#L89) | error | — |
| ErrorState | [frontend/src/features/integrations/components/setup/KaspiSetup.tsx:91](../../frontend/src/features/integrations/components/setup/KaspiSetup.tsx#L91) | error | — |
| StatusNotice | [frontend/src/features/integrations/components/setup/KaspiSetup.tsx:107](../../frontend/src/features/integrations/components/setup/KaspiSetup.tsx#L107) | runsInMockMode | integrations.mock.providerDisabledNotice |
| ErrorState | [frontend/src/features/integrations/components/setup/MoySkladSetup.tsx:90](../../frontend/src/features/integrations/components/setup/MoySkladSetup.tsx#L90) | error | — |
| StatusNotice | [frontend/src/features/integrations/components/setup/MoySkladSetup.tsx:106](../../frontend/src/features/integrations/components/setup/MoySkladSetup.tsx#L106) | runsInMockMode | integrations.mock.providerDisabledNotice |
| ErrorState | [frontend/src/features/integrations/components/setup/OzonSetup.tsx:95](../../frontend/src/features/integrations/components/setup/OzonSetup.tsx#L95) | error | — |
| StatusNotice | [frontend/src/features/integrations/components/setup/OzonSetup.tsx:111](../../frontend/src/features/integrations/components/setup/OzonSetup.tsx#L111) | runsInMockMode | integrations.mock.providerDisabledNotice |
| ErrorState | [frontend/src/features/integrations/components/setup/TelegramSetup.tsx:98](../../frontend/src/features/integrations/components/setup/TelegramSetup.tsx#L98) | !channel | aiAgents.channelSetupUnavailable |
| ErrorState | [frontend/src/features/integrations/components/setup/TelegramSetup.tsx:108](../../frontend/src/features/integrations/components/setup/TelegramSetup.tsx#L108) | error | — |
| ErrorState | [frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx:191](../../frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx#L191) | !channel | aiAgents.channelSetupUnavailable |
| ErrorState | [frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx:201](../../frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx#L201) | error | — |
| ErrorState | [frontend/src/features/integrations/components/setup/WildberriesSetup.tsx:90](../../frontend/src/features/integrations/components/setup/WildberriesSetup.tsx#L90) | error | — |
| StatusNotice | [frontend/src/features/integrations/components/setup/WildberriesSetup.tsx:106](../../frontend/src/features/integrations/components/setup/WildberriesSetup.tsx#L106) | runsInMockMode | integrations.mock.providerDisabledNotice |
| LoadingState | [frontend/src/features/integrations/IntegrationsPage.tsx:118](../../frontend/src/features/integrations/IntegrationsPage.tsx#L118) | isBusinessLoading \|\| capabilities.isLoading \|\| connectors.isLoading | integrations.page.loading |
| EmptyState | [frontend/src/features/integrations/IntegrationsPage.tsx:122](../../frontend/src/features/integrations/IntegrationsPage.tsx#L122) | !business | integrations.page.noBusinessTitle, integrations.page.noBusinessDescription |
| ErrorState | [frontend/src/features/integrations/IntegrationsPage.tsx:203](../../frontend/src/features/integrations/IntegrationsPage.tsx#L203) | pageError | — |
| EmptyState | [frontend/src/features/integrations/IntegrationsPage.tsx:237](../../frontend/src/features/integrations/IntegrationsPage.tsx#L237) | !visibleData.length | integrations.overview.emptyTitle, integrations.overview.emptyText |
| ErrorState | [frontend/src/features/leads/LeadsPage.tsx:232](../../frontend/src/features/leads/LeadsPage.tsx#L232) | !business | leads.noBusiness |
| ErrorState | [frontend/src/features/leads/LeadsPage.tsx:233](../../frontend/src/features/leads/LeadsPage.tsx#L233) | createContext.error | — |
| PageSkeleton | [frontend/src/features/leads/LeadsPage.tsx:234](../../frontend/src/features/leads/LeadsPage.tsx#L234) | createContext.isLoading | — |
| PageSkeleton | [frontend/src/features/leads/LeadsPage.tsx:235](../../frontend/src/features/leads/LeadsPage.tsx#L235) | isPageLoading | — |
| ErrorState | [frontend/src/features/leads/LeadsPage.tsx:236](../../frontend/src/features/leads/LeadsPage.tsx#L236) | pageError | common.retry |
| LoadingState | [frontend/src/features/outreach/OutreachPage.tsx:289](../../frontend/src/features/outreach/OutreachPage.tsx#L289) | businessLoading \|\| campaigns.isLoading | outreach.loading |
| ErrorState | [frontend/src/features/outreach/OutreachPage.tsx:290](../../frontend/src/features/outreach/OutreachPage.tsx#L290) | !business | outreach.noBusiness |
| ErrorState | [frontend/src/features/outreach/OutreachPage.tsx:326](../../frontend/src/features/outreach/OutreachPage.tsx#L326) | pageError | — |
| EmptyState | [frontend/src/features/outreach/OutreachPage.tsx:444](../../frontend/src/features/outreach/OutreachPage.tsx#L444) | !campaignList.length | outreach.emptyTitle, outreach.emptyDescription |
| EmptyState | [frontend/src/features/outreach/OutreachPage.tsx:601](../../frontend/src/features/outreach/OutreachPage.tsx#L601) | selectedCampaign | outreach.selectCampaign, outreach.selectCampaignDescription |
| LoadingState | [frontend/src/features/payments/PaymentEntityPicker.tsx:41](../../frontend/src/features/payments/PaymentEntityPicker.tsx#L41) | options.isLoading | — |
| ErrorState | [frontend/src/features/payments/PaymentEntityPicker.tsx:42](../../frontend/src/features/payments/PaymentEntityPicker.tsx#L42) | options.error | common.retry |
| ErrorState | [frontend/src/features/payments/PaymentForm.tsx:109](../../frontend/src/features/payments/PaymentForm.tsx#L109) | mutation.error | — |
| ForbiddenState | [frontend/src/features/payments/PaymentsJournal.tsx:50](../../frontend/src/features/payments/PaymentsJournal.tsx#L50) | !canView | — |
| LoadingState | [frontend/src/features/payments/PaymentsJournal.tsx:58](../../frontend/src/features/payments/PaymentsJournal.tsx#L58) | payments.isLoading | — |
| ErrorState | [frontend/src/features/payments/PaymentsJournal.tsx:59](../../frontend/src/features/payments/PaymentsJournal.tsx#L59) | payments.error | common.retry |
| EmptyState | [frontend/src/features/payments/PaymentsJournal.tsx:60](../../frontend/src/features/payments/PaymentsJournal.tsx#L60) | !payments.isFetching && !payments.error && payments.data?.count === 0 | payments.empty, payments.emptyText |
| LoadingState | [frontend/src/features/platform/PlatformMerchantDetailPage.tsx:59](../../frontend/src/features/platform/PlatformMerchantDetailPage.tsx#L59) | merchant.isLoading | platform.merchantDetail.loading |
| ErrorState | [frontend/src/features/platform/PlatformMerchantDetailPage.tsx:60](../../frontend/src/features/platform/PlatformMerchantDetailPage.tsx#L60) | merchant.isError \|\| !merchant.data | platform.merchantDetail.error |
| EmptyState | [frontend/src/features/platform/PlatformMerchantDetailPage.tsx:173](../../frontend/src/features/platform/PlatformMerchantDetailPage.tsx#L173) | !workflow?.next_steps?.length | platform.merchantDetail.noNextSteps, platform.merchantDetail.noNextStepsText |
| ErrorState | [frontend/src/features/platform/PlatformMerchantDetailPage.tsx:201](../../frontend/src/features/platform/PlatformMerchantDetailPage.tsx#L201) | supportMutation.isError | — |
| LoadingState | [frontend/src/features/platform/PlatformMerchantsPage.tsx:55](../../frontend/src/features/platform/PlatformMerchantsPage.tsx#L55) | merchants.isLoading | platform.merchants.loading |
| ErrorState | [frontend/src/features/platform/PlatformMerchantsPage.tsx:56](../../frontend/src/features/platform/PlatformMerchantsPage.tsx#L56) | merchants.isError | platform.merchants.error |
| EmptyState | [frontend/src/features/platform/PlatformMerchantsPage.tsx:82](../../frontend/src/features/platform/PlatformMerchantsPage.tsx#L82) | !filtered.length | platform.merchants.emptyTitle, platform.merchants.emptyText |
| LoadingState | [frontend/src/features/platform/PlatformOperationsPage.tsx:30](../../frontend/src/features/platform/PlatformOperationsPage.tsx#L30) | health.isLoading | platform.operations.loading |
| ErrorState | [frontend/src/features/platform/PlatformOperationsPage.tsx:31](../../frontend/src/features/platform/PlatformOperationsPage.tsx#L31) | health.isError \|\| !health.data | platform.operations.error |
| LoadingState | [frontend/src/features/platform/PlatformOverviewPage.tsx:29](../../frontend/src/features/platform/PlatformOverviewPage.tsx#L29) | overview.isLoading | platform.overview.loading |
| ErrorState | [frontend/src/features/platform/PlatformOverviewPage.tsx:30](../../frontend/src/features/platform/PlatformOverviewPage.tsx#L30) | overview.isError \|\| !overview.data | platform.overview.error |
| ErrorState | [frontend/src/features/pricing/PricingPage.tsx:317](../../frontend/src/features/pricing/PricingPage.tsx#L317) | error | — |
| LoadingState | [frontend/src/features/pricing/PricingPage.tsx:384](../../frontend/src/features/pricing/PricingPage.tsx#L384) | catalogQuery.isLoading | pricing.loadingCatalog |
| LoadingState | [frontend/src/features/pricing/PricingPage.tsx:505](../../frontend/src/features/pricing/PricingPage.tsx#L505) | rulesQuery.isLoading | pricing.loadingRules |
| LoadingState | [frontend/src/features/pricing/PricingPage.tsx:624](../../frontend/src/features/pricing/PricingPage.tsx#L624) | changeLogsQuery.isLoading | pricing.loadingHistory |
| ErrorState | [frontend/src/features/resources/components/ResourceEditModal.tsx:97](../../frontend/src/features/resources/components/ResourceEditModal.tsx#L97) | errorMessage | — |
| StatusNotice | [frontend/src/features/resources/components/ResourceEditModal.tsx:99](../../frontend/src/features/resources/components/ResourceEditModal.tsx#L99) | !canManage | resources.readOnlyTitle, resources.readOnlyText |
| ErrorState | [frontend/src/features/resources/components/ResourceEditModal.tsx:143](../../frontend/src/features/resources/components/ResourceEditModal.tsx#L143) | scheduleError | — |
| ErrorState | [frontend/src/features/resources/ResourcesPage.tsx:272](../../frontend/src/features/resources/ResourcesPage.tsx#L272) | !business | resources.noBusiness |
| LoadingState | [frontend/src/features/resources/ResourcesPage.tsx:273](../../frontend/src/features/resources/ResourcesPage.tsx#L273) | resourcesQuery.isLoading \|\| teamMembersQuery.isLoading | — |
| LoadingState | [frontend/src/features/resources/ResourcesPage.tsx:299](../../frontend/src/features/resources/ResourcesPage.tsx#L299) | selectedResourceQuery.isLoading | — |
| ErrorState | [frontend/src/features/resources/ResourcesPage.tsx:302](../../frontend/src/features/resources/ResourcesPage.tsx#L302) | pageError | common.retry |
| ErrorState | [frontend/src/features/resources/ResourcesPage.tsx:408](../../frontend/src/features/resources/ResourcesPage.tsx#L408) | businessHoursQuery.error | — |
| ErrorState | [frontend/src/features/services/components/ServiceEditModal.tsx:76](../../frontend/src/features/services/components/ServiceEditModal.tsx#L76) | errorMessage | — |
| StatusNotice | [frontend/src/features/services/components/ServiceEditModal.tsx:78](../../frontend/src/features/services/components/ServiceEditModal.tsx#L78) | !canEdit | — |
| ErrorState | [frontend/src/features/services/ServicesPage.tsx:296](../../frontend/src/features/services/ServicesPage.tsx#L296) | !business | services.noBusiness |
| LoadingState | [frontend/src/features/services/ServicesPage.tsx:297](../../frontend/src/features/services/ServicesPage.tsx#L297) | overviewQuery.isLoading \|\| appointmentsQuery.isLoading \|\| servicesQuery.isLoading | — |
| LoadingState | [frontend/src/features/services/ServicesPage.tsx:318](../../frontend/src/features/services/ServicesPage.tsx#L318) | selectedServiceQuery.isLoading | — |
| ErrorState | [frontend/src/features/services/ServicesPage.tsx:321](../../frontend/src/features/services/ServicesPage.tsx#L321) | pageError | common.retry |
| LoadingState | [frontend/src/features/settings/components/AbsenceAppointmentsModal.tsx:47](../../frontend/src/features/settings/components/AbsenceAppointmentsModal.tsx#L47) | loading \|\| resources.isLoading | — |
| ErrorState | [frontend/src/features/settings/components/AbsenceAppointmentsModal.tsx:48](../../frontend/src/features/settings/components/AbsenceAppointmentsModal.tsx#L48) | error \|\| mutation.error \|\| resources.error | — |
| LoadingState | [frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx:71](../../frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx#L71) | exceptions.isLoading | — |
| ErrorState | [frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx:72](../../frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx#L72) | error | — |
| LoadingState | [frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx:98](../../frontend/src/features/settings/components/ScheduleExceptionsPanel.tsx#L98) | appointments.isLoading | — |
| ErrorState | [frontend/src/features/settings/components/TeamAccessControl.tsx:40](../../frontend/src/features/settings/components/TeamAccessControl.tsx#L40) | mutation.error | — |
| ErrorState | [frontend/src/features/settings/components/WorkingHoursEditModal.tsx:80](../../frontend/src/features/settings/components/WorkingHoursEditModal.tsx#L80) | errorMessage | — |
| StatusNotice | [frontend/src/features/settings/components/WorkingHoursEditModal.tsx:82](../../frontend/src/features/settings/components/WorkingHoursEditModal.tsx#L82) | !canManage | workingHours.readOnlyTitle, workingHours.readOnlyText |
| ErrorState | [frontend/src/features/settings/DevelopersSection.tsx:174](../../frontend/src/features/settings/DevelopersSection.tsx#L174) | error | — |
| ErrorState | [frontend/src/features/settings/sections/BillingSection.tsx:141](../../frontend/src/features/settings/sections/BillingSection.tsx#L141) | error | — |
| LoadingState | [frontend/src/features/settings/SettingsPage.tsx:685](../../frontend/src/features/settings/SettingsPage.tsx#L685) | isLoading | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:852](../../frontend/src/features/settings/SettingsPage.tsx#L852) | mutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:900](../../frontend/src/features/settings/SettingsPage.tsx#L900) | appointmentMessageMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:1079](../../frontend/src/features/settings/SettingsPage.tsx#L1079) | updateMemberMutation.error \|\| departmentMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:1088](../../frontend/src/features/settings/SettingsPage.tsx#L1088) | inviteMutation.error \|\| revokeInvitationMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:1775](../../frontend/src/features/settings/SettingsPage.tsx#L1775) | notificationPreferenceMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:1852](../../frontend/src/features/settings/SettingsPage.tsx#L1852) | quickReplyMutation.error \|\|               updateQuickReplyMutation.error \|\|               removeQuickReplyMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:2138](../../frontend/src/features/settings/SettingsPage.tsx#L2138) | updatePermissionMutation.error | — |
| ErrorState | [frontend/src/features/settings/SettingsPage.tsx:2297](../../frontend/src/features/settings/SettingsPage.tsx#L2297) | customFieldMutation.error \|\|               updateCustomFieldMutation.error \|\|               removeCustomFieldMutation.error | — |
| ErrorState | [frontend/src/features/settings/WorkingHoursPage.tsx:267](../../frontend/src/features/settings/WorkingHoursPage.tsx#L267) | !business | workingHours.noBusiness |
| LoadingState | [frontend/src/features/settings/WorkingHoursPage.tsx:268](../../frontend/src/features/settings/WorkingHoursPage.tsx#L268) | workingHours.isLoading \|\| resources.isLoading | — |
| ErrorState | [frontend/src/features/settings/WorkingHoursPage.tsx:283](../../frontend/src/features/settings/WorkingHoursPage.tsx#L283) | pageError | common.retry |
| ErrorState | [frontend/src/features/tasks/components/TaskDrawer.tsx:324](../../frontend/src/features/tasks/components/TaskDrawer.tsx#L324) | detailsErrorMessage | — |
| ErrorState | [frontend/src/features/tasks/components/TaskFormModal.tsx:252](../../frontend/src/features/tasks/components/TaskFormModal.tsx#L252) | errorMessage | — |
| EmptyState | [frontend/src/features/tasks/components/TaskList.tsx:123](../../frontend/src/features/tasks/components/TaskList.tsx#L123) | !tasks.length | tasks.emptyTitle, tasks.emptyText, tasks.create |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:169](../../frontend/src/features/tasks/TasksPage.tsx#L169) | !business | tasks.noBusiness |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:170](../../frontend/src/features/tasks/TasksPage.tsx#L170) | createContext.error | — |
| LoadingState | [frontend/src/features/tasks/TasksPage.tsx:171](../../frontend/src/features/tasks/TasksPage.tsx#L171) | createContext.isLoading | — |
| LoadingState | [frontend/src/features/tasks/TasksPage.tsx:185](../../frontend/src/features/tasks/TasksPage.tsx#L185) | taskSummary.isLoading \|\|     (canViewTeam && taskWorkload.isLoading) \|\|     tasksQuery.isLoading \|\|     (canCreateTask && taskTemplates.isLoading) \|\|     clients.isLoading \|\|  | — |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:187](../../frontend/src/features/tasks/TasksPage.tsx#L187) | taskSummary.error | — |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:189](../../frontend/src/features/tasks/TasksPage.tsx#L189) | canViewTeam && taskWorkload.error | — |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:191](../../frontend/src/features/tasks/TasksPage.tsx#L191) | tasksQuery.error | — |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:193](../../frontend/src/features/tasks/TasksPage.tsx#L193) | canCreateTask && taskTemplates.error | — |
| ErrorState | [frontend/src/features/tasks/TasksPage.tsx:195](../../frontend/src/features/tasks/TasksPage.tsx#L195) | botConversations.error | — |
| ErrorState | [frontend/src/features/timeline/TimelineActorFilter.tsx:101](../../frontend/src/features/timeline/TimelineActorFilter.tsx#L101) | actors.isError | common.retry |
| LoadingState | [frontend/src/features/timeline/TimelineActorFilter.tsx:113](../../frontend/src/features/timeline/TimelineActorFilter.tsx#L113) | actors.isPending | — |
| ErrorState | [frontend/src/features/timeline/TimelinePage.tsx:115](../../frontend/src/features/timeline/TimelinePage.tsx#L115) | !business | timeline.noBusiness |
| ForbiddenState | [frontend/src/features/timeline/TimelinePage.tsx:120](../../frontend/src/features/timeline/TimelinePage.tsx#L120) | !canView \|\|     (query.isError && normalizeAppError(query.error).category === "permission") | — |
| ErrorState | [frontend/src/features/timeline/TimelinePage.tsx:150](../../frontend/src/features/timeline/TimelinePage.tsx#L150) | query.isError | common.retry, timeline.reset |
| AppErrorBoundary | [frontend/src/main.tsx:16](../../frontend/src/main.tsx#L16) | component / parent state | — |
| LoadingState | [frontend/src/ui-catalog/CrmDrawer.stories.tsx:31](../../frontend/src/ui-catalog/CrmDrawer.stories.tsx#L31) | loading | — |

## Вызовы уведомлений

| Компонент / вызов | Источник | Условие / обработчик в коде | Ключи текста |
| --- | --- | --- | --- |
| showNotification | [frontend/src/components/actions/useActionFeedback.ts:75](../../frontend/src/components/actions/useActionFeedback.ts#L75) | useActionFeedback | common.retry |
| showNotification | [frontend/src/components/actions/useActionFeedback.ts:89](../../frontend/src/components/actions/useActionFeedback.ts#L89) | useActionFeedback | — |
| showNotification | [frontend/src/components/crm/drawers/appointment.tsx:47](../../frontend/src/components/crm/drawers/appointment.tsx#L47) | onSuccess | common.saved |
| showNotification | [frontend/src/components/crm/drawers/appointment.tsx:71](../../frontend/src/components/crm/drawers/appointment.tsx#L71) | onSuccess | — |
| showNotification | [frontend/src/components/crm/drawers/deal.tsx:51](../../frontend/src/components/crm/drawers/deal.tsx#L51) | onSuccess | crmCard.won, deals.lost, deals.reopen |
| showNotification | [frontend/src/components/crm/drawers/lead.tsx:64](../../frontend/src/components/crm/drawers/lead.tsx#L64) | onSuccess | leads.actionDone |
| showNotification | [frontend/src/features/bots/BotsPage.tsx:43](../../frontend/src/features/bots/BotsPage.tsx#L43) | BotsPage | — |
| notifySuccess | [frontend/src/features/calendar/AppointmentWorkspacePage.tsx:124](../../frontend/src/features/calendar/AppointmentWorkspacePage.tsx#L124) | onSuccess | appointments.actionDone |
| notifyError | [frontend/src/features/calendar/AppointmentWorkspacePage.tsx:127](../../frontend/src/features/calendar/AppointmentWorkspacePage.tsx#L127) | onError | — |
| notifySuccess | [frontend/src/features/calendar/AppointmentWorkspacePage.tsx:141](../../frontend/src/features/calendar/AppointmentWorkspacePage.tsx#L141) | onSuccess | appointments.rescheduledNotice |
| notifyError | [frontend/src/features/calendar/AppointmentWorkspacePage.tsx:145](../../frontend/src/features/calendar/AppointmentWorkspacePage.tsx#L145) | onError | common.refresh |
| showNotification | [frontend/src/features/calendar/CalendarPage.tsx:285](../../frontend/src/features/calendar/CalendarPage.tsx#L285) | setNotice | — |
| notifyError | [frontend/src/features/calendar/CalendarPage.tsx:304](../../frontend/src/features/calendar/CalendarPage.tsx#L304) | onError | — |
| notifyError | [frontend/src/features/calendar/CalendarPage.tsx:331](../../frontend/src/features/calendar/CalendarPage.tsx#L331) | onError | — |
| notifyError | [frontend/src/features/calendar/CalendarPage.tsx:349](../../frontend/src/features/calendar/CalendarPage.tsx#L349) | onError | common.refresh |
| notifyError | [frontend/src/features/calendar/CalendarPage.tsx:365](../../frontend/src/features/calendar/CalendarPage.tsx#L365) | onError | — |
| notifyError | [frontend/src/features/calendar/CalendarPage.tsx:380](../../frontend/src/features/calendar/CalendarPage.tsx#L380) | onError | common.refresh |
| showUndoToast | [frontend/src/features/clients/ClientsPage.tsx:174](../../frontend/src/features/clients/ClientsPage.tsx#L174) | onSuccess | clients.noticeArchived |
| notifySuccess | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:46](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L46) | onSuccess | common.saved |
| notifyError | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:49](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L49) | onError | common.refresh |
| notifySuccess | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:85](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L85) | onSuccess | clients.addTag |
| notifyError | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:87](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L87) | onError | — |
| showUndoToast | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:95](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L95) | onSuccess | clients.noticeArchived |
| notifyError | [frontend/src/features/clients/hooks/useClientWorkspaceActions.ts:104](../../frontend/src/features/clients/hooks/useClientWorkspaceActions.ts#L104) | onError | — |
| showNotification | [frontend/src/features/conversations/ConversationsPage.tsx:213](../../frontend/src/features/conversations/ConversationsPage.tsx#L213) | setNotice | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:799](../../frontend/src/features/conversations/ConversationsPage.tsx#L799) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:812](../../frontend/src/features/conversations/ConversationsPage.tsx#L812) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:820](../../frontend/src/features/conversations/ConversationsPage.tsx#L820) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:829](../../frontend/src/features/conversations/ConversationsPage.tsx#L829) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:838](../../frontend/src/features/conversations/ConversationsPage.tsx#L838) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:853](../../frontend/src/features/conversations/ConversationsPage.tsx#L853) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:866](../../frontend/src/features/conversations/ConversationsPage.tsx#L866) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:879](../../frontend/src/features/conversations/ConversationsPage.tsx#L879) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:892](../../frontend/src/features/conversations/ConversationsPage.tsx#L892) | onError | conversations.aiReplyForbidden |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:913](../../frontend/src/features/conversations/ConversationsPage.tsx#L913) | onError | conversations.aiPipelinePreviewForbidden |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:931](../../frontend/src/features/conversations/ConversationsPage.tsx#L931) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:940](../../frontend/src/features/conversations/ConversationsPage.tsx#L940) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:966](../../frontend/src/features/conversations/ConversationsPage.tsx#L966) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:976](../../frontend/src/features/conversations/ConversationsPage.tsx#L976) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:988](../../frontend/src/features/conversations/ConversationsPage.tsx#L988) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:998](../../frontend/src/features/conversations/ConversationsPage.tsx#L998) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:1010](../../frontend/src/features/conversations/ConversationsPage.tsx#L1010) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:1020](../../frontend/src/features/conversations/ConversationsPage.tsx#L1020) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:1030](../../frontend/src/features/conversations/ConversationsPage.tsx#L1030) | onError | — |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:1068](../../frontend/src/features/conversations/ConversationsPage.tsx#L1068) | getApiFieldErrors(error).preview_id | conversations.aiPipelineRunForbidden |
| notifyError | [frontend/src/features/conversations/ConversationsPage.tsx:1120](../../frontend/src/features/conversations/ConversationsPage.tsx#L1120) | onError | — |
| showUndoToast | [frontend/src/features/deals/DealsPage.tsx:149](../../frontend/src/features/deals/DealsPage.tsx#L149) | onSuccess | deals.noticeArchived, deals.noticeRestored |
| showNotification | [frontend/src/features/deals/DealsPage.tsx:154](../../frontend/src/features/deals/DealsPage.tsx#L154) | onUndo | deals.noticeRestored |
| notifyError | [frontend/src/features/deals/DealsPage.tsx:162](../../frontend/src/features/deals/DealsPage.tsx#L162) | onError | common.refresh |
| showNotification | [frontend/src/features/deals/DealsPage.tsx:250](../../frontend/src/features/deals/DealsPage.tsx#L250) | DealsPage | — |
| showNotification | [frontend/src/features/deals/DealWorkspacePage.tsx:99](../../frontend/src/features/deals/DealWorkspacePage.tsx#L99) | onSuccess | deals.actionDone |
| notifySuccess | [frontend/src/features/deals/hooks/useDealActions.ts:46](../../frontend/src/features/deals/hooks/useDealActions.ts#L46) | onSuccess | deals.actionDone |
| notifyError | [frontend/src/features/deals/hooks/useDealActions.ts:48](../../frontend/src/features/deals/hooks/useDealActions.ts#L48) | onError | — |
| notifySuccess | [frontend/src/features/deals/hooks/useDealActions.ts:56](../../frontend/src/features/deals/hooks/useDealActions.ts#L56) | onSuccess | deals.actionDone |
| notifyError | [frontend/src/features/deals/hooks/useDealActions.ts:58](../../frontend/src/features/deals/hooks/useDealActions.ts#L58) | onError | — |
| notifySuccess | [frontend/src/features/deals/hooks/useDealActions.ts:73](../../frontend/src/features/deals/hooks/useDealActions.ts#L73) | onSuccess | deals.actionDone |
| notifyError | [frontend/src/features/deals/hooks/useDealActions.ts:75](../../frontend/src/features/deals/hooks/useDealActions.ts#L75) | onError | — |
| notifySuccess | [frontend/src/features/deals/hooks/useDealActions.ts:85](../../frontend/src/features/deals/hooks/useDealActions.ts#L85) | onSuccess | deals.actionDone |
| notifyError | [frontend/src/features/deals/hooks/useDealActions.ts:87](../../frontend/src/features/deals/hooks/useDealActions.ts#L87) | onError | — |
| notifySuccess | [frontend/src/features/deals/hooks/useDealActions.ts:95](../../frontend/src/features/deals/hooks/useDealActions.ts#L95) | onSuccess | common.saved |
| notifyError | [frontend/src/features/deals/hooks/useDealActions.ts:98](../../frontend/src/features/deals/hooks/useDealActions.ts#L98) | onError | common.refresh |
| showNotification | [frontend/src/features/integrations/components/ProviderCard.tsx:190](../../frontend/src/features/integrations/components/ProviderCard.tsx#L190) | onSuccess | integrations.card.connectionSaved |
| showNotification | [frontend/src/features/integrations/components/setup/InstagramSetup.tsx:42](../../frontend/src/features/integrations/components/setup/InstagramSetup.tsx#L42) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/KaspiPricingSetup.tsx:41](../../frontend/src/features/integrations/components/setup/KaspiPricingSetup.tsx#L41) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/KaspiSetup.tsx:39](../../frontend/src/features/integrations/components/setup/KaspiSetup.tsx#L39) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/MoySkladSetup.tsx:36](../../frontend/src/features/integrations/components/setup/MoySkladSetup.tsx#L36) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/OzonSetup.tsx:38](../../frontend/src/features/integrations/components/setup/OzonSetup.tsx#L38) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/TelegramSetup.tsx:30](../../frontend/src/features/integrations/components/setup/TelegramSetup.tsx#L30) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx:45](../../frontend/src/features/integrations/components/setup/WhatsAppSetup.tsx#L45) | setNotice | — |
| showNotification | [frontend/src/features/integrations/components/setup/WildberriesSetup.tsx:36](../../frontend/src/features/integrations/components/setup/WildberriesSetup.tsx#L36) | setNotice | — |
| showUndoToast | [frontend/src/features/leads/hooks/useLeadActionHistory.ts:21](../../frontend/src/features/leads/hooks/useLeadActionHistory.ts#L21) | useLeadActionHistory | leads.undo, leads.actionUndone |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:60](../../frontend/src/features/leads/hooks/useLeadActions.ts#L60) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:103](../../frontend/src/features/leads/hooks/useLeadActions.ts#L103) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:125](../../frontend/src/features/leads/hooks/useLeadActions.ts#L125) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:153](../../frontend/src/features/leads/hooks/useLeadActions.ts#L153) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:174](../../frontend/src/features/leads/hooks/useLeadActions.ts#L174) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:217](../../frontend/src/features/leads/hooks/useLeadActions.ts#L217) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:253](../../frontend/src/features/leads/hooks/useLeadActions.ts#L253) | onError | — |
| notifyError | [frontend/src/features/leads/hooks/useLeadActions.ts:272](../../frontend/src/features/leads/hooks/useLeadActions.ts#L272) | onError | — |
| showNotification | [frontend/src/features/leads/LeadsPage.tsx:77](../../frontend/src/features/leads/LeadsPage.tsx#L77) | LeadsPage | — |
| showNotification | [frontend/src/features/leads/LeadsPage.tsx:158](../../frontend/src/features/leads/LeadsPage.tsx#L158) | showWarning | — |
| showNotification | [frontend/src/features/leads/LeadWorkspacePage.tsx:132](../../frontend/src/features/leads/LeadWorkspacePage.tsx#L132) | onSuccess | leads.actionDone |
| showNotification | [frontend/src/features/resources/ResourcesPage.tsx:149](../../frontend/src/features/resources/ResourcesPage.tsx#L149) | variables.id | resources.noticeSaved |
| showNotification | [frontend/src/features/resources/ResourcesPage.tsx:153](../../frontend/src/features/resources/ResourcesPage.tsx#L153) | variables.id | resources.noticeCreated |
| showNotification | [frontend/src/features/resources/ResourcesPage.tsx:162](../../frontend/src/features/resources/ResourcesPage.tsx#L162) | onSuccess | — |
| showNotification | [frontend/src/features/resources/ResourcesPage.tsx:168](../../frontend/src/features/resources/ResourcesPage.tsx#L168) | onError | — |
| showNotification | [frontend/src/features/resources/ResourcesPage.tsx:175](../../frontend/src/features/resources/ResourcesPage.tsx#L175) | ResourcesPage | — |
| showNotification | [frontend/src/features/services/ServicesPage.tsx:118](../../frontend/src/features/services/ServicesPage.tsx#L118) | variables.id | services.noticeSaved |
| showNotification | [frontend/src/features/services/ServicesPage.tsx:121](../../frontend/src/features/services/ServicesPage.tsx#L121) | variables.id | services.noticeCreated |
| showNotification | [frontend/src/features/services/ServicesPage.tsx:158](../../frontend/src/features/services/ServicesPage.tsx#L158) | onSuccess | — |
| showNotification | [frontend/src/features/services/ServicesPage.tsx:161](../../frontend/src/features/services/ServicesPage.tsx#L161) | onError | — |
| showNotification | [frontend/src/features/services/ServicesPage.tsx:168](../../frontend/src/features/services/ServicesPage.tsx#L168) | ServicesPage | — |
| showNotification | [frontend/src/features/settings/WorkingHoursPage.tsx:166](../../frontend/src/features/settings/WorkingHoursPage.tsx#L166) | onSuccess | workingHours.savedNotice |
| showNotification | [frontend/src/features/settings/WorkingHoursPage.tsx:178](../../frontend/src/features/settings/WorkingHoursPage.tsx#L178) | onSuccess | workingHours.presetNotice |
| showNotification | [frontend/src/features/settings/WorkingHoursPage.tsx:180](../../frontend/src/features/settings/WorkingHoursPage.tsx#L180) | onError | — |
| notifySuccess | [frontend/src/features/tasks/hooks/useTaskActions.ts:56](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L56) | useTaskActions | tasks.savedNotice |
| notifySuccess | [frontend/src/features/tasks/hooks/useTaskActions.ts:68](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L68) | onSuccess | tasks.savedNotice |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:70](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L70) | onError | — |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:82](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L82) | onError | common.refresh |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:91](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L91) | onError | — |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:96](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L96) | onError | — |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:101](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L101) | onError | — |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:107](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L107) | onError | common.refresh |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:116](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L116) | onError | common.refresh |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:125](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L125) | onError | common.refresh |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:133](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L133) | onError | — |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:139](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L139) | onError | common.refresh |
| showUndoToast | [frontend/src/features/tasks/hooks/useTaskActions.ts:149](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L149) | onSuccess | tasks.cancelledNotice, tasks.savedNotice |
| notifySuccess | [frontend/src/features/tasks/hooks/useTaskActions.ts:154](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L154) | onUndo | tasks.savedNotice |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:158](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L158) | onError | — |
| notifySuccess | [frontend/src/features/tasks/hooks/useTaskActions.ts:170](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L170) | onSuccess | tasks.savedNotice |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:172](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L172) | onError | — |
| notifySuccess | [frontend/src/features/tasks/hooks/useTaskActions.ts:183](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L183) | onSuccess | tasks.savedNotice |
| notifyError | [frontend/src/features/tasks/hooks/useTaskActions.ts:186](../../frontend/src/features/tasks/hooks/useTaskActions.ts#L186) | onError | common.refresh |
| showNotification | [frontend/src/features/tasks/TaskWorkspacePage.tsx:123](../../frontend/src/features/tasks/TaskWorkspacePage.tsx#L123) | onSuccess | tasks.savedNotice |
| showNotification | [frontend/src/features/tasks/TaskWorkspacePage.tsx:151](../../frontend/src/features/tasks/TaskWorkspacePage.tsx#L151) | onSuccess | tasks.savedNotice |
| showNotification | [frontend/src/features/tasks/TaskWorkspacePage.tsx:162](../../frontend/src/features/tasks/TaskWorkspacePage.tsx#L162) | onSuccess | tasks.savedNotice |

## Дополнительные локальные alert-элементы

| Компонент / вызов | Источник | Условие / обработчик в коде | Ключи текста |
| --- | --- | --- | --- |
| p | [frontend/src/components/forms/BusinessSettingsForm.tsx:134](../../frontend/src/components/forms/BusinessSettingsForm.tsx#L134) | — | — |
| section | [frontend/src/components/ui/FallbackSurfaces.tsx:87](../../frontend/src/components/ui/FallbackSurfaces.tsx#L87) | — | — |
| span | [frontend/src/components/ui/Input.tsx:38](../../frontend/src/components/ui/Input.tsx#L38) | — | — |
| span | [frontend/src/components/ui/Select.tsx:217](../../frontend/src/components/ui/Select.tsx#L217) | — | — |
| span | [frontend/src/components/ui/Textarea.tsx:30](../../frontend/src/components/ui/Textarea.tsx#L30) | — | — |
| p | [frontend/src/features/account/AvatarEditor.tsx:60](../../frontend/src/features/account/AvatarEditor.tsx#L60) | — | — |
| p | [frontend/src/features/account/AvatarEditor.tsx:61](../../frontend/src/features/account/AvatarEditor.tsx#L61) | — | — |
| p | [frontend/src/features/account/EmailSecurityRow.tsx:42](../../frontend/src/features/account/EmailSecurityRow.tsx#L42) | — | — |
| div | [frontend/src/features/assistant/components/AIHistoryPanel.tsx:33](../../frontend/src/features/assistant/components/AIHistoryPanel.tsx#L33) | — | — |
| p | [frontend/src/features/assistant/components/AIHistoryPanel.tsx:55](../../frontend/src/features/assistant/components/AIHistoryPanel.tsx#L55) | — | — |
| div | [frontend/src/features/assistant/components/CRMCommandPanel.tsx:66](../../frontend/src/features/assistant/components/CRMCommandPanel.tsx#L66) | — | — |
| p | [frontend/src/features/assistant/components/CRMCommandPanel.tsx:79](../../frontend/src/features/assistant/components/CRMCommandPanel.tsx#L79) | — | — |
| p | [frontend/src/features/assistant/components/InternalAgentSettings.tsx:65](../../frontend/src/features/assistant/components/InternalAgentSettings.tsx#L65) | — | — |
| div | [frontend/src/features/auth/SignupPage.tsx:148](../../frontend/src/features/auth/SignupPage.tsx#L148) | — | — |
| p | [frontend/src/features/auth/SignupPage.tsx:202](../../frontend/src/features/auth/SignupPage.tsx#L202) | — | — |
| p | [frontend/src/features/payments/PaymentEntityPicker.tsx:37](../../frontend/src/features/payments/PaymentEntityPicker.tsx#L37) | — | — |
| p | [frontend/src/features/payments/PaymentForm.tsx:110](../../frontend/src/features/payments/PaymentForm.tsx#L110) | — | — |
| p | [frontend/src/features/payments/PaymentForm.tsx:111](../../frontend/src/features/payments/PaymentForm.tsx#L111) | — | — |
