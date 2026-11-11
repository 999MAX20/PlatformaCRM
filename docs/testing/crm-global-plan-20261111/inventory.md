# Статическая карта реализации и существующих тестов

**Тесты не запускались.** Источники прочитаны как текст/AST без импорта Django.
Это каталог кандидатов для исполнения, а не подтверждение корректности и не список PASS.
[Машиночитаемый снимок](inventory.json) содержит все записи этой инвентаризации.
[Матрица](matrix.md) задаёт ожидаемые результаты; [браузерный план](browser.md) задаёт действия пользователя.

## Граница снимка

Начальный HEAD `ee4ff50fbcfe1c914fff6f49b31cb64830ceeb21`; HEAD инвентаризации `9d9b7a0dcc03b0411c4b25df9a77798d81fea24c` + рабочий diff. Source hashes и starting status
сохранены в `output/crm-global-test-plan-20261111`. Это локальная реализация, не доказательство
того, что те же файлы развёрнуты на стенде. Изменения другой задачи не присваиваются этому плану.

Найдено 216 записей API-каталога (88 router families и explicit routes),
98 route declarations и 11 sections Settings. Alias/redirect не новая функция.
Найдено 292 backend test-файлов, 115 browser spec-файлов,
59 файлов frontend Node checks и 8 Python script tests.
Число test-файлов/методов не равно числу реально исполняемых параметризованных тестов.
Router family включает generated list/detail URLs; это не полный runtime OpenAPI.
Custom actions и mixins проверяются по исходнику handler и существующим tests перед запуском.

## UI-маршруты

| URL pattern | Матрица | Исходник |
| --- | --- | --- |
| `/documents` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/documents/:documentId` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/pricing` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/bots` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/crm` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/contacts` | PUBLIC + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/login` | AUTH + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/signup` | ONBOARD + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/mfa` | AUTH + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/forgot-password` | AUTH + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/reset-password/:uid/:token` | AUTH + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/recover-account` | PLATFORM + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/invite/:token` | TEAM + UX/ACCESS | [publicRoutes.tsx](../../../frontend/src/app/publicRoutes.tsx) |
| `/app/voice/history` | VOICE + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/settings/voice` | VOICE + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/integrations/import` | IMPORT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/appointments` | RECORD + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/appointments/:id` | RECORD + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/support` | SUPPORT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/support/:id` | SUPPORT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/dashboard` | ANALYTICS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/account` | ACCOUNT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/leads` | LEGACY + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/leads/:id` | LEGACY + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/deals` | LEGACY + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/deals/:id` | LEGACY + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/clients` | CLIENT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/clients/:id` | CLIENT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/tasks` | TASK + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/tasks/:id` | TASK + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/calendar` | RECORD + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/calendar/:id` | RECORD + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/conversations` | INBOX + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/conversations/:id` | INBOX + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/timeline` | TIMELINE + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/bots` | BOT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/bots/:id` | BOT + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/integrations` | INTEGRATION + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/pricing` | PRICING + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/ai-assistant` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/ai` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/assistant` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/inbox` | INBOX + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/ai-agents` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/ai-agents/:id` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/ai-agents/:id/:section` | AI + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/automations` | AUTO + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/business` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/business/services` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/business/branches` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/business/resources` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/business/working-hours` | SCHEDULE + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/services` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/resources` | BUSINESS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/working-hours` | SCHEDULE + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/analytics` | ANALYTICS + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/settings` | UX + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/app/billing` | BILLING + UX/ACCESS | [merchantRoutes.tsx](../../../frontend/src/app/merchantRoutes.tsx) |
| `/platform` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/operations` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/merchants` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/merchants/:id` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/account` | ACCOUNT + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/support` | SUPPORT + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/support/:id` | SUPPORT + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/merchants/:id/incidents/:component/:episode` | SUPPORT + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/prospects` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/landings` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/billing` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/analytics` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/platform/settings` | PLATFORM + UX/ACCESS | [platformRoutes.tsx](../../../frontend/src/app/platformRoutes.tsx) |
| `/leads` | LEGACY + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/account` | ACCOUNT + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/deals` | LEGACY + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/clients` | CLIENT + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/tasks` | TASK + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/calendar` | RECORD + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/conversations` | INBOX + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/timeline` | TIMELINE + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/crm-bots` | BOT + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/integrations` | INTEGRATION + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/ai-assistant` | AI + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/ai` | AI + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/assistant` | AI + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/inbox` | INBOX + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/ai-agents` | AI + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/automations` | AUTO + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/services` | BUSINESS + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/resources` | BUSINESS + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/working-hours` | SCHEDULE + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/analytics` | ANALYTICS + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/settings` | UX + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/billing` | BILLING + UX/ACCESS | [legacyRoutes.tsx](../../../frontend/src/app/legacyRoutes.tsx) |
| `/app` | UX + UX/ACCESS | [router.tsx](../../../frontend/src/app/router.tsx) |
| `/app/notifications` | NOTIFY + UX/ACCESS | [router.tsx](../../../frontend/src/app/router.tsx) |
| `/dashboard/*` | LEGACY + UX/ACCESS | [router.tsx](../../../frontend/src/app/router.tsx) |
| `*` | PUBLIC + UX/ACCESS | [router.tsx](../../../frontend/src/app/router.tsx) |

## Settings: отдельная строка обхода на каждую секцию

| URL | Компонент |
| --- | --- |
| `/app/settings#integrations` | `IntegrationsSection` |
| `/app/settings#voice-input` | `VoiceInputSection` |
| `/app/settings#business-profile` | `BusinessProfileSection` |
| `/app/settings#team-access` | `TeamSection` |
| `/app/settings#roles` | `RolesSection` |
| `/app/settings#security-center` | `SecuritySection` |
| `/app/settings#appointment-messages` | `AppointmentMessagesSection` |
| `/app/settings#quick-replies` | `QuickRepliesSection` |
| `/app/settings#custom-fields` | `CustomFieldsSection` |
| `/app/settings#billing` | `BillingSection` |
| `/app/settings#usage` | `UsageSection` |

Account имеет отдельные компоненты MFA/devices/email/avatar/interface/notifications и ownership/recovery confirmations:
[frontend/src/features/account/AccountPage.tsx](../../../frontend/src/features/account/AccountPage.tsx). Все доступные разделы входят в B02/B03/B36/B41.
Agent detail/section параметры проходят все реально доступные tabs в B24–B27; platform detail panels в B35–B42.

## API: покрытие существующих входов

| Семейство / explicit path | Handler | Матрица |
| --- | --- | --- |
| `/api/branches/` | `BranchViewSet` | BUSINESS + ACCESS |
| `/api/businesses/` | `BusinessViewSet` | BUSINESS + ACCESS |
| `/api/business-members/` | `BusinessMemberViewSet` | TEAM + ACCESS |
| `/api/business-capabilities/` | `BusinessCapabilityViewSet` | ACCESS + ACCESS |
| `/api/routing-policies/` | `RoutingPolicyViewSet` | BUSINESS + ACCESS |
| `/api/team/members/` | `TeamMemberManagementViewSet` | TEAM + ACCESS |
| `/api/team/invitations/` | `BusinessInvitationViewSet` | TEAM + ACCESS |
| `/api/team/roles/` | `BusinessRoleViewSet` | TEAM + ACCESS |
| `/api/team/role-permissions/` | `RolePermissionViewSet` | TEAM + ACCESS |
| `/api/team/departments/` | `TeamViewSet` | TEAM + ACCESS |
| `/api/team/department-members/` | `TeamMembershipViewSet` | TEAM + ACCESS |
| `/api/clients/` | `ClientViewSet` | CLIENT + ACCESS |
| `/api/visit-plans/` | `VisitPlanViewSet` | PLAN + ACCESS |
| `/api/client-payments/` | `PaymentViewSet` | MONEY + ACCESS |
| `/api/pipelines/` | `PipelineViewSet` | LEGACY + ACCESS |
| `/api/pipeline-stages/` | `PipelineStageViewSet` | LEGACY + ACCESS |
| `/api/stage-transitions/` | `StageTransitionViewSet` | LEGACY + ACCESS |
| `/api/deals/` | `DealViewSet` | LEGACY + ACCESS |
| `/api/services/` | `ServiceViewSet` | BUSINESS + ACCESS |
| `/api/leads/` | `LeadViewSet` | LEGACY + ACCESS |
| `/api/lead-forms/` | `LeadFormViewSet` | PUBLIC + ACCESS |
| `/api/lead-form-fields/` | `LeadFormFieldViewSet` | PUBLIC + ACCESS |
| `/api/lead-form-submissions/` | `LeadFormSubmissionViewSet` | PUBLIC + ACCESS |
| `/api/lead-form-submission-errors/` | `LeadFormSubmissionErrorViewSet` | PUBLIC + ACCESS |
| `/api/resources/` | `ResourceViewSet` | SCHEDULE + ACCESS |
| `/api/working-hours/` | `WorkingHoursViewSet` | SCHEDULE + ACCESS |
| `/api/schedule-exceptions/` | `ScheduleExceptionViewSet` | SCHEDULE + ACCESS |
| `/api/appointments/` | `AppointmentViewSet` | RECORD + ACCESS |
| `/api/appointment-message-settings/` | `AppointmentMessageSettingViewSet` | NOTIFY + ACCESS |
| `/api/conversations/` | `ConversationViewSet` | INBOX + ACCESS |
| `/api/messages/` | `MessageViewSet` | INBOX + ACCESS |
| `/api/quick-replies/` | `QuickReplyTemplateViewSet` | INBOX + ACCESS |
| `/api/notifications/` | `NotificationViewSet` | NOTIFY + ACCESS |
| `/api/notification-preferences/` | `NotificationPreferenceViewSet` | NOTIFY + ACCESS |
| `/api/outreach/templates/` | `OutreachTemplateViewSet` | OUTREACH + ACCESS |
| `/api/outreach/campaigns/` | `OutreachCampaignViewSet` | OUTREACH + ACCESS |
| `/api/outreach/recipients/` | `OutreachRecipientViewSet` | OUTREACH + ACCESS |
| `/api/outreach/consents/` | `OutreachConsentViewSet` | OUTREACH + ACCESS |
| `/api/analytics-events/` | `AnalyticsEventViewSet` | ANALYTICS + ACCESS |
| `/api/report-widgets/` | `ReportWidgetViewSet` | ANALYTICS + ACCESS |
| `/api/scheduled-reports/` | `ScheduledReportViewSet` | ANALYTICS + ACCESS |
| `/api/activity-events/` | `ActivityEventViewSet` | TIMELINE + ACCESS |
| `/api/notes/` | `NoteViewSet` | CLIENT + ACCESS |
| `/api/tags/` | `TagViewSet` | FIELDS + ACCESS |
| `/api/tagged-objects/` | `TaggedObjectViewSet` | FIELDS + ACCESS |
| `/api/segments/` | `SegmentViewSet` | FIELDS + ACCESS |
| `/api/segment-filters/` | `SegmentFilterViewSet` | FIELDS + ACCESS |
| `/api/custom-fields/` | `CustomFieldDefinitionViewSet` | FIELDS + ACCESS |
| `/api/custom-field-values/` | `CustomFieldValueViewSet` | FIELDS + ACCESS |
| `/api/import-jobs/` | `ImportJobViewSet` | IMPORT + ACCESS |
| `/api/import-workspaces/` | `ImportWorkspaceViewSet` | IMPORT + ACCESS |
| `/api/export-jobs/` | `ExportJobViewSet` | EXPORT + ACCESS |
| `/api/file-attachments/` | `FileAttachmentViewSet` | FILE + ACCESS |
| `/api/security/support-grants/` | `SupportAccessGrantViewSet` | ACCESS + ACCESS |
| `/api/tasks/` | `TaskViewSet` | TASK + ACCESS |
| `/api/automation-rules/` | `AutomationRuleViewSet` | AUTO + ACCESS |
| `/api/automation-conditions/` | `AutomationConditionViewSet` | AUTO + ACCESS |
| `/api/automation-actions/` | `AutomationActionViewSet` | AUTO + ACCESS |
| `/api/automation-runs/` | `AutomationRunViewSet` | AUTO + ACCESS |
| `/api/billing/plans/` | `SubscriptionPlanViewSet` | BILLING + ACCESS |
| `/api/billing/current-subscription/` | `CurrentSubscriptionViewSet` | BILLING + ACCESS |
| `/api/billing/usage-summary/` | `UsageSummaryViewSet` | BILLING + ACCESS |
| `/api/billing/entitlements/` | `EntitlementSummaryViewSet` | BILLING + ACCESS |
| `/api/bots/` | `BotViewSet` | BOT + ACCESS |
| `/api/bot-channels/` | `BotChannelViewSet` | BOT + ACCESS |
| `/api/bot-conversations/` | `BotConversationViewSet` | BOT + ACCESS |
| `/api/bot-messages/` | `BotMessageViewSet` | BOT + ACCESS |
| `/api/inbox/conversations/` | `InboxConversationViewSet` | INBOX + ACCESS |
| `/api/ai/request-logs/` | `AIRequestLogViewSet` | AI + ACCESS |
| `/api/ai/jobs/` | `AIJobViewSet` | AI + ACCESS |
| `/api/ai/knowledge-items/` | `BusinessKnowledgeItemViewSet` | AI + ACCESS |
| `/api/ai/agent-profiles/` | `AgentProfileViewSet` | AI + ACCESS |
| `/api/ai/approval-requests/` | `ApprovalRequestViewSet` | AI + ACCESS |
| `/api/integration-event-logs/` | `IntegrationEventLogViewSet` | INTEGRATION + ACCESS |
| `/api/business-connectors/` | `BusinessConnectorViewSet` | INTEGRATION + ACCESS |
| `/api/connector-credentials/` | `ConnectorCredentialViewSet` | INTEGRATION + ACCESS |
| `/api/business-events/` | `BusinessEventViewSet` | INTEGRATION + ACCESS |
| `/api/connector-sync-runs/` | `ConnectorSyncRunViewSet` | INTEGRATION + ACCESS |
| `/api/api-tokens/` | `ApiTokenViewSet` | INTEGRATION + ACCESS |
| `/api/webhook-endpoints/` | `WebhookEndpointViewSet` | INTEGRATION + ACCESS |
| `/api/webhook-deliveries/` | `WebhookDeliveryLogViewSet` | INTEGRATION + ACCESS |
| `/api/pricing/kaspi/rules/` | `KaspiPricingRuleViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/catalog/` | `PricingCatalogItemViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/control/` | `KaspiPricingControlViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/alerts/` | `KaspiPricingAlertViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/competitor-offers/` | `KaspiCompetitorOfferViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/recommendations/` | `KaspiPricingRecommendationViewSet` | PRICING + ACCESS |
| `/api/pricing/kaspi/change-logs/` | `KaspiPriceChangeLogViewSet` | PRICING + ACCESS |
| `/api/billing/businesses/<int:business_id>/orders/` | `merchant_orders` | BILLING + ACCESS |
| `/api/billing/businesses/<int:business_id>/orders/<uuid:order_id>/<slug:action>/` | `merchant_card` | BILLING + ACCESS |
| `/api/billing/card-notifications/<slug:provider>/` | `card_notification` | BILLING + ACCESS |
| `/api/platform/merchants/<int:business_id>/billing-orders/` | `platform_orders` | BILLING + ACCESS |
| `/api/platform/merchants/<int:business_id>/billing-orders/<uuid:order_id>/<slug:action>/` | `platform_payment_action` | BILLING + ACCESS |
| `/health/` | `health` | OPS + ACCESS |
| `/api/service-status/` | `service_status` | OPS + ACCESS |
| `/health/db/` | `health_db` | OPS + ACCESS |
| `/ready/` | `readiness` | OPS + ACCESS |
| `/admin/` | `admin.site.urls` | AUTH + ACCESS |
| `/api/auth/csrf/` | `auth_csrf` | AUTH + ACCESS |
| `/api/auth/token/` | `ThrottledTokenObtainPairView.as_view()` | AUTH + ACCESS |
| `/api/auth/token/refresh/` | `ThrottledTokenRefreshView.as_view()` | AUTH + ACCESS |
| `/api/auth/logout/` | `LogoutView.as_view()` | AUTH + ACCESS |
| `/api/auth/social/` | `SocialAuthView.as_view()` | AUTH + ACCESS |
| `/api/auth/signup/owner/` | `OwnerSignupView.as_view()` | AUTH + ACCESS |
| `/api/auth/password-reset/request/` | `PasswordResetRequestView.as_view()` | AUTH + ACCESS |
| `/api/auth/account-recovery/` | `public_recovery` | PLATFORM + ACCESS |
| `/api/auth/recovery-confirmations/` | `recovery_confirmations` | PLATFORM + ACCESS |
| `/api/auth/recovery-confirmations/<uuid:recovery_id>/` | `recovery_decision` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/employee-access/` | `platform_employee_access` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/employee-access/<uuid:repair_id>/` | `platform_employee_access_action` | PLATFORM + ACCESS |
| `/api/auth/employee-access-confirmations/` | `employee_access_confirmations` | PLATFORM + ACCESS |
| `/api/auth/employee-access-confirmations/<uuid:repair_id>/` | `employee_access_decision` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/account-recovery/` | `platform_recovery` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/account-recovery/<uuid:recovery_id>/` | `platform_recovery_action` | PLATFORM + ACCESS |
| `/api/auth/password-reset/confirm/` | `PasswordResetConfirmView.as_view()` | AUTH + ACCESS |
| `/api/auth/me/avatar/` | `CurrentUserAvatarView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/me/` | `CurrentUserView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/ownership-transfers/` | `account_ownership_transfers` | PLATFORM + ACCESS |
| `/api/auth/ownership-transfers/<uuid:transfer_id>/decision/` | `account_ownership_decision` | PLATFORM + ACCESS |
| `/api/auth/change-password/` | `ChangePasswordView.as_view()` | AUTH + ACCESS |
| `/api/auth/sessions/` | `AccountSessionsView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/sessions/<uuid:session_id>/revoke/` | `RevokeAccountSessionView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/change-email/request/` | `EmailChangeRequestView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/change-email/confirm/` | `EmailChangeConfirmView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/login-history/` | `CurrentUserLoginHistoryView.as_view()` | ACCOUNT + ACCESS |
| `/api/auth/mfa/status/` | `MfaStatusView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/enrollment/start/` | `MfaEnrollmentStartView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/enrollment/confirm/` | `MfaEnrollmentConfirmView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/verify/` | `MfaVerifyView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/step-up/` | `MfaStepUpView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/recovery-codes/` | `MfaRecoveryCodesView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/disable/` | `MfaDisableView.as_view()` | AUTH + ACCESS |
| `/api/auth/mfa/sessions/revoke/` | `MfaRevokeSessionsView.as_view()` | AUTH + ACCESS |
| `/api/team/permissions/catalog/` | `team_permissions_catalog` | TEAM + ACCESS |
| `/api/team/performance/` | `team_performance` | TEAM + ACCESS |
| `/api/export/<str:entity_type>/` | `export_entity` | EXPORT + ACCESS |
| `/api/import-templates/<str:entity_type>/` | `import_template` | IMPORT + ACCESS |
| `/api/data/sales/` | `manual_sale` | IMPORT + ACCESS |
| `/api/data/catalog-items/` | `manual_catalog_item` | IMPORT + ACCESS |
| `/api/security/audit/` | `security_audit` | ACCESS + ACCESS |
| `/api/security/login-history/` | `security_login_history` | ACCESS + ACCESS |
| `/api/security/risk-summary/` | `security_risk_summary` | ACCESS + ACCESS |
| `/api/analytics/owner-dashboard/` | `owner_dashboard` | ANALYTICS + ACCESS |
| `/api/analytics/reports/summary/` | `report_summary` | ANALYTICS + ACCESS |
| `/api/analytics/reports/export/` | `report_export` | ANALYTICS + ACCESS |
| `/api/platform/ping/` | `platform_ping` | PLATFORM + ACCESS |
| `/api/work-queues/` | `work_queues` | ANALYTICS + ACCESS |
| `/api/platform/overview/` | `platform_overview` | PLATFORM + ACCESS |
| `/api/platform/operations-health/` | `platform_operations_health_view` | PLATFORM + ACCESS |
| `/api/platform/operations-worklist/` | `platform_worklist` | PLATFORM + ACCESS |
| `/api/platform/merchants/` | `platform_merchants` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/` | `platform_merchant_detail` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/crm/<str:kind>/` | `platform_clinic_records` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/crm/<str:kind>/<int:record_id>/` | `platform_clinic_record` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/crm/<str:kind>/<int:record_id>/<str:section>/` | `platform_clinic_record_section` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/crm-access-log/` | `platform_clinic_access_log` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/details/` | `platform_business_details` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/ownership/` | `platform_business_ownership` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/ownership/<uuid:transfer_id>/` | `platform_ownership_action` | PLATFORM + ACCESS |
| `/api/platform/merchants/<int:business_id>/support-actions/` | `platform_merchant_support_action` | PLATFORM + ACCESS |
| `/api/platform/activate-landing/` | `platform_activate_landing` | PLATFORM + ACCESS |
| `/api/pilot/readiness/` | `PilotReadinessView.as_view()` | OPS + ACCESS |
| `/api/onboarding/templates/` | `onboarding_templates` | ONBOARD + ACCESS |
| `/api/onboarding/status/` | `onboarding_status` | ONBOARD + ACCESS |
| `/api/onboarding/apply-template/` | `apply_onboarding_template` | ONBOARD + ACCESS |
| `/api/onboarding/demo-data/` | `onboarding_demo_data` | ONBOARD + ACCESS |
| `/api/onboarding/setup-channel/` | `onboarding_setup_channel` | ONBOARD + ACCESS |
| `/api/onboarding/first-message/` | `onboarding_first_message` | ONBOARD + ACCESS |
| `/api/files/private/<path:file_path>/` | `private_media_file` | FILE + ACCESS |
| `/api/public/website-chat/<uuid:public_token>/` | `PublicWebsiteChatChannelView.as_view()` | PUBLIC + ACCESS |
| `/api/public/forms/<uuid:public_id>/` | `PublicLeadFormView.as_view()` | PUBLIC + ACCESS |
| `/api/public/forms/<uuid:public_id>/submit/` | `PublicLeadFormSubmitView.as_view()` | PUBLIC + ACCESS |
| `/api/public/website-chat/<uuid:public_token>/conversations/` | `PublicWebsiteChatConversationCreateView.as_view()` | PUBLIC + ACCESS |
| `/api/public/website-chat/<uuid:public_token>/conversations/<uuid:conversation_id>/messages/` | `PublicWebsiteChatMessageCreateView.as_view()` | PUBLIC + ACCESS |
| `/api/integrations/telegram/webhook/` | `TelegramWebhookView.as_view()` | INTEGRATION + ACCESS |
| `/api/integrations/ycloud/channels/<int:pk>/` | `YCloudSetupView.as_view()` | INTEGRATION + ACCESS |
| `/api/integrations/ycloud/webhook/` | `YCloudWebhookView.as_view()` | INTEGRATION + ACCESS |
| `/api/integrations/whatsapp/webhook/` | `WhatsAppWebhookView.as_view()` | INTEGRATION + ACCESS |
| `/api/integrations/instagram/webhook/` | `InstagramWebhookView.as_view()` | INTEGRATION + ACCESS |
| `/api/public-api/clients/` | `PublicApiClientsView.as_view()` | INTEGRATION + ACCESS |
| `/api/ai/agents/` | `AIRuntimeAgentsView.as_view()` | AI + ACCESS |
| `/api/ai/speech/` | `SpeechView.as_view()` | VOICE + ACCESS |
| `/api/ai/conversations/` | `AgentConversationListView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/` | `AgentConversationDetailView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/turns/` | `AgentConversationTurnsView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/reset-memory/` | `AgentConversationResetView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/turns/<int:turn_id>/cancel/` | `AgentTurnCancelView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/turns/<int:turn_id>/retry/` | `AgentTurnRetryView.as_view()` | AI + ACCESS |
| `/api/ai/conversations/<uuid:conversation_id>/turns/<int:turn_id>/confirm/` | `AgentTurnConfirmView.as_view()` | AI + ACCESS |
| `/api/ai/assistant/status/` | `AIAssistantStatusView.as_view()` | AI + ACCESS |
| `/api/ai/assistant/chat/` | `AIAssistantChatView.as_view()` | AI + ACCESS |
| `/api/ai/analyst/brief/` | `AIAnalystBriefView.as_view()` | AI + ACCESS |
| `/api/ai/analyst/history/` | `AIHistoryView.as_view()` | AI + ACCESS |
| `/api/ai/crm/read/` | `CRMReadView.as_view()` | AI + ACCESS |
| `/api/ai/crm/plan/` | `CRMPlanView.as_view()` | AI + ACCESS |
| `/api/ai/owner-brief/daily/` | `AIOwnerDailyBriefView.as_view()` | AI + ACCESS |
| `/api/ai/tools/suggest/` | `AIToolSuggestView.as_view()` | AI + ACCESS |
| `/api/ai/tools/<int:log_id>/execute/` | `AIToolExecuteView.as_view()` | AI + ACCESS |
| `/api/platform/support-incidents/` | `views.SupportIncidentView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/incidents/` | `views.CaseIncidentsView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/staff/` | `views.SupportStaffView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/internal-notes/` | `views.CaseNotesView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/assign/` | `views.CaseAssignView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/transition/` | `views.CaseTransitionView.as_view()` | SUPPORT + ACCESS |
| `/api/platform/support-cases/` | `views.CaseListView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/` | `views.CaseListView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/` | `views.CaseDetailView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/<int:pk>/` | `views.CaseDetailView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/messages/` | `views.CaseMessagesView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/<int:pk>/messages/` | `views.CaseMessagesView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/events/` | `views.CaseEventsView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/<int:pk>/events/` | `views.CaseEventsView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/reopen/` | `views.CaseReopenView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/<int:pk>/reopen/` | `views.CaseReopenView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/platform/support-cases/<int:pk>/read/` | `views.CaseReadView.as_view(platform=platform)` | SUPPORT + ACCESS |
| `/api/support/cases/<int:pk>/read/` | `views.CaseReadView.as_view(platform=platform)` | SUPPORT + ACCESS |

## Основные источники и тестовые наборы по доменам

Каждый нижеуказанный test-файл существует. Это candidate reuse, не assertion-level coverage.
При запуске сохранять exact dotted label/test name, а не утверждать покрытие по имени файла.

### accounts

[apps/accounts](../../../apps/accounts); 12 test-файлов.

- [tests.py](../../../apps/accounts/tests.py) (`apps.accounts.tests`)
- [tests_admin_mfa.py](../../../apps/accounts/tests_admin_mfa.py) (`apps.accounts.tests_admin_mfa`)
- [tests_avatars.py](../../../apps/accounts/tests_avatars.py) (`apps.accounts.tests_avatars`)
- [tests_device_sessions.py](../../../apps/accounts/tests_device_sessions.py) (`apps.accounts.tests_device_sessions`)
- [tests_email_changes.py](../../../apps/accounts/tests_email_changes.py) (`apps.accounts.tests_email_changes`)
- [tests_legal_documents.py](../../../apps/accounts/tests_legal_documents.py) (`apps.accounts.tests_legal_documents`)
- [tests_login_csrf.py](../../../apps/accounts/tests_login_csrf.py) (`apps.accounts.tests_login_csrf`)
- [tests_mfa.py](../../../apps/accounts/tests_mfa.py) (`apps.accounts.tests_mfa`)
- [tests_password_throttle.py](../../../apps/accounts/tests_password_throttle.py) (`apps.accounts.tests_password_throttle`)
- [tests_recovery.py](../../../apps/accounts/tests_recovery.py) (`apps.accounts.tests_recovery`)
- [tests_session_policy.py](../../../apps/accounts/tests_session_policy.py) (`apps.accounts.tests_session_policy`)
- [tests_token_cleanup.py](../../../apps/accounts/tests_token_cleanup.py) (`apps.accounts.tests_token_cleanup`)

### activities

[apps/activities](../../../apps/activities); 5 test-файлов.

- [tests.py](../../../apps/activities/tests.py) (`apps.activities.tests`)
- [tests_note_read_scope.py](../../../apps/activities/tests_note_read_scope.py) (`apps.activities.tests_note_read_scope`)
- [tests_segments.py](../../../apps/activities/tests_segments.py) (`apps.activities.tests_segments`)
- [tests_timeline_workspace.py](../../../apps/activities/tests_timeline_workspace.py) (`apps.activities.tests_timeline_workspace`)
- [tests_write_boundaries.py](../../../apps/activities/tests_write_boundaries.py) (`apps.activities.tests_write_boundaries`)

### ai_core

[apps/ai_core](../../../apps/ai_core); 31 test-файлов.

- [tests.py](../../../apps/ai_core/tests.py) (`apps.ai_core.tests`)
- [tests_agent_runtime.py](../../../apps/ai_core/tests_agent_runtime.py) (`apps.ai_core.tests_agent_runtime`)
- [tests_approval_binding.py](../../../apps/ai_core/tests_approval_binding.py) (`apps.ai_core.tests_approval_binding`)
- [tests_conversation_api.py](../../../apps/ai_core/tests_conversation_api.py) (`apps.ai_core.tests_conversation_api`)
- [tests_conversation_execution.py](../../../apps/ai_core/tests_conversation_execution.py) (`apps.ai_core.tests_conversation_execution`)
- [tests_conversation_memory.py](../../../apps/ai_core/tests_conversation_memory.py) (`apps.ai_core.tests_conversation_memory`)
- [tests_conversation_state.py](../../../apps/ai_core/tests_conversation_state.py) (`apps.ai_core.tests_conversation_state`)
- [tests_crm_planner.py](../../../apps/ai_core/tests_crm_planner.py) (`apps.ai_core.tests_crm_planner`)
- [tests_crm_tools.py](../../../apps/ai_core/tests_crm_tools.py) (`apps.ai_core.tests_crm_tools`)
- [tests_history.py](../../../apps/ai_core/tests_history.py) (`apps.ai_core.tests_history`)
- [tests_history_answers.py](../../../apps/ai_core/tests_history_answers.py) (`apps.ai_core.tests_history_answers`)
- [tests_inbox_continuity.py](../../../apps/ai_core/tests_inbox_continuity.py) (`apps.ai_core.tests_inbox_continuity`)
- [tests_job_recovery.py](../../../apps/ai_core/tests_job_recovery.py) (`apps.ai_core.tests_job_recovery`)
- [tests_knowledge_isolation.py](../../../apps/ai_core/tests_knowledge_isolation.py) (`apps.ai_core.tests_knowledge_isolation`)
- [tests_prompt_preferences.py](../../../apps/ai_core/tests_prompt_preferences.py) (`apps.ai_core.tests_prompt_preferences`)
- [tests_quality.py](../../../apps/ai_core/tests_quality.py) (`apps.ai_core.tests_quality`)
- [tests_record_workflow.py](../../../apps/ai_core/tests_record_workflow.py) (`apps.ai_core.tests_record_workflow`)
- [tests_resource_booking.py](../../../apps/ai_core/tests_resource_booking.py) (`apps.ai_core.tests_resource_booking`)
- [tests_settings_certification.py](../../../apps/ai_core/tests_settings_certification.py) (`apps.ai_core.tests_settings_certification`)
- [tests_speech.py](../../../apps/ai_core/tests_speech.py) (`apps.ai_core.tests_speech`)
- [tests_speech_formatting.py](../../../apps/ai_core/tests_speech_formatting.py) (`apps.ai_core.tests_speech_formatting`)
- [tests_voice_booking_intent.py](../../../apps/ai_core/tests_voice_booking_intent.py) (`apps.ai_core.tests_voice_booking_intent`)
- [tests_voice_direct.py](../../../apps/ai_core/tests_voice_direct.py) (`apps.ai_core.tests_voice_direct`)
- [tests_voice_identity.py](../../../apps/ai_core/tests_voice_identity.py) (`apps.ai_core.tests_voice_identity`)
- [tests_voice_interface.py](../../../apps/ai_core/tests_voice_interface.py) (`apps.ai_core.tests_voice_interface`)
- [tests_voice_language.py](../../../apps/ai_core/tests_voice_language.py) (`apps.ai_core.tests_voice_language`)
- [tests_voice_locations.py](../../../apps/ai_core/tests_voice_locations.py) (`apps.ai_core.tests_voice_locations`)
- [tests_voice_policy.py](../../../apps/ai_core/tests_voice_policy.py) (`apps.ai_core.tests_voice_policy`)
- [tests_voice_schedule.py](../../../apps/ai_core/tests_voice_schedule.py) (`apps.ai_core.tests_voice_schedule`)
- [tests_voice_schedule_concurrency.py](../../../apps/ai_core/tests_voice_schedule_concurrency.py) (`apps.ai_core.tests_voice_schedule_concurrency`)
- [tests_workflows.py](../../../apps/ai_core/tests_workflows.py) (`apps.ai_core.tests_workflows`)

### analytics

[apps/analytics](../../../apps/analytics); 6 test-файлов.

- [tests.py](../../../apps/analytics/tests.py) (`apps.analytics.tests`)
- [tests_financial_sources.py](../../../apps/analytics/tests_financial_sources.py) (`apps.analytics.tests_financial_sources`)
- [tests_manual_finance.py](../../../apps/analytics/tests_manual_finance.py) (`apps.analytics.tests_manual_finance`)
- [tests_record_metrics.py](../../../apps/analytics/tests_record_metrics.py) (`apps.analytics.tests_record_metrics`)
- [tests_resource_visibility.py](../../../apps/analytics/tests_resource_visibility.py) (`apps.analytics.tests_resource_visibility`)
- [tests_workspace.py](../../../apps/analytics/tests_workspace.py) (`apps.analytics.tests_workspace`)

### automations

[apps/automations](../../../apps/automations); 12 test-файлов.

- [tests.py](../../../apps/automations/tests.py) (`apps.automations.tests`)
- [tests_action_validation.py](../../../apps/automations/tests_action_validation.py) (`apps.automations.tests_action_validation`)
- [tests_claim_ownership.py](../../../apps/automations/tests_claim_ownership.py) (`apps.automations.tests_claim_ownership`)
- [tests_configuration.py](../../../apps/automations/tests_configuration.py) (`apps.automations.tests_configuration`)
- [tests_configuration_authority.py](../../../apps/automations/tests_configuration_authority.py) (`apps.automations.tests_configuration_authority`)
- [tests_configuration_concurrency.py](../../../apps/automations/tests_configuration_concurrency.py) (`apps.automations.tests_configuration_concurrency`)
- [tests_dispatch_commit.py](../../../apps/automations/tests_dispatch_commit.py) (`apps.automations.tests_dispatch_commit`)
- [tests_follow_up_concurrency.py](../../../apps/automations/tests_follow_up_concurrency.py) (`apps.automations.tests_follow_up_concurrency`)
- [tests_follow_up_policy.py](../../../apps/automations/tests_follow_up_policy.py) (`apps.automations.tests_follow_up_policy`)
- [tests_history.py](../../../apps/automations/tests_history.py) (`apps.automations.tests_history`)
- [tests_queue_runtime.py](../../../apps/automations/tests_queue_runtime.py) (`apps.automations.tests_queue_runtime`)
- [tests_rule_editor.py](../../../apps/automations/tests_rule_editor.py) (`apps.automations.tests_rule_editor`)

### billing

[apps/billing](../../../apps/billing); 4 test-файлов.

- [tests.py](../../../apps/billing/tests.py) (`apps.billing.tests`)
- [tests_commerce.py](../../../apps/billing/tests_commerce.py) (`apps.billing.tests_commerce`)
- [tests_commerce_concurrency.py](../../../apps/billing/tests_commerce_concurrency.py) (`apps.billing.tests_commerce_concurrency`)
- [tests_settings_scope.py](../../../apps/billing/tests_settings_scope.py) (`apps.billing.tests_settings_scope`)

### bots

[apps/bots](../../../apps/bots); 23 test-файлов.

- [tests.py](../../../apps/bots/tests.py) (`apps.bots.tests`)
- [tests_automatic_booking.py](../../../apps/bots/tests_automatic_booking.py) (`apps.bots.tests_automatic_booking`)
- [tests_booking_creation.py](../../../apps/bots/tests_booking_creation.py) (`apps.bots.tests_booking_creation`)
- [tests_booking_creation_concurrency.py](../../../apps/bots/tests_booking_creation_concurrency.py) (`apps.bots.tests_booking_creation_concurrency`)
- [tests_booking_terms.py](../../../apps/bots/tests_booking_terms.py) (`apps.bots.tests_booking_terms`)
- [tests_booking_terms_concurrency.py](../../../apps/bots/tests_booking_terms_concurrency.py) (`apps.bots.tests_booking_terms_concurrency`)
- [tests_configuration.py](../../../apps/bots/tests_configuration.py) (`apps.bots.tests_configuration`)
- [tests_controlled_creation.py](../../../apps/bots/tests_controlled_creation.py) (`apps.bots.tests_controlled_creation`)
- [tests_customer_knowledge.py](../../../apps/bots/tests_customer_knowledge.py) (`apps.bots.tests_customer_knowledge`)
- [tests_customer_safety.py](../../../apps/bots/tests_customer_safety.py) (`apps.bots.tests_customer_safety`)
- [tests_deletion.py](../../../apps/bots/tests_deletion.py) (`apps.bots.tests_deletion`)
- [tests_handoff_notice.py](../../../apps/bots/tests_handoff_notice.py) (`apps.bots.tests_handoff_notice`)
- [tests_handoff_recovery.py](../../../apps/bots/tests_handoff_recovery.py) (`apps.bots.tests_handoff_recovery`)
- [tests_pause_inbound.py](../../../apps/bots/tests_pause_inbound.py) (`apps.bots.tests_pause_inbound`)
- [tests_preview.py](../../../apps/bots/tests_preview.py) (`apps.bots.tests_preview`)
- [tests_readiness.py](../../../apps/bots/tests_readiness.py) (`apps.bots.tests_readiness`)
- [tests_readiness_diagnostics.py](../../../apps/bots/tests_readiness_diagnostics.py) (`apps.bots.tests_readiness_diagnostics`)
- [tests_resource_booking.py](../../../apps/bots/tests_resource_booking.py) (`apps.bots.tests_resource_booking`)
- [tests_runtime_configuration.py](../../../apps/bots/tests_runtime_configuration.py) (`apps.bots.tests_runtime_configuration`)
- [tests_safety_migration.py](../../../apps/bots/tests_safety_migration.py) (`apps.bots.tests_safety_migration`)
- [tests_safety_recovery.py](../../../apps/bots/tests_safety_recovery.py) (`apps.bots.tests_safety_recovery`)
- [tests_safety_state.py](../../../apps/bots/tests_safety_state.py) (`apps.bots.tests_safety_state`)
- [tests_scenarios.py](../../../apps/bots/tests_scenarios.py) (`apps.bots.tests_scenarios`)

### branches

[apps/branches](../../../apps/branches); 10 test-файлов.

- [tests_access.py](../../../apps/branches/tests_access.py) (`apps.branches.tests_access`)
- [tests_bot.py](../../../apps/branches/tests_bot.py) (`apps.branches.tests_bot`)
- [tests_compatibility.py](../../../apps/branches/tests_compatibility.py) (`apps.branches.tests_compatibility`)
- [tests_concurrency.py](../../../apps/branches/tests_concurrency.py) (`apps.branches.tests_concurrency`)
- [tests_initial_location_migration.py](../../../apps/branches/tests_initial_location_migration.py) (`apps.branches.tests_initial_location_migration`)
- [tests_physical_resources.py](../../../apps/branches/tests_physical_resources.py) (`apps.branches.tests_physical_resources`)
- [tests_scheduling.py](../../../apps/branches/tests_scheduling.py) (`apps.branches.tests_scheduling`)
- [tests_single_location.py](../../../apps/branches/tests_single_location.py) (`apps.branches.tests_single_location`)
- [tests_single_location_concurrency.py](../../../apps/branches/tests_single_location_concurrency.py) (`apps.branches.tests_single_location_concurrency`)
- [tests_staff.py](../../../apps/branches/tests_staff.py) (`apps.branches.tests_staff`)

### businesses

[apps/businesses](../../../apps/businesses); 17 test-файлов.

- [tests_access.py](../../../apps/businesses/tests_access.py) (`apps.businesses.tests_access`)
- [tests_activation.py](../../../apps/businesses/tests_activation.py) (`apps.businesses.tests_activation`)
- [tests_booking_settings.py](../../../apps/businesses/tests_booking_settings.py) (`apps.businesses.tests_booking_settings`)
- [tests_booking_settings_migration.py](../../../apps/businesses/tests_booking_settings_migration.py) (`apps.businesses.tests_booking_settings_migration`)
- [tests_business_delete.py](../../../apps/businesses/tests_business_delete.py) (`apps.businesses.tests_business_delete`)
- [tests_demo_seed.py](../../../apps/businesses/tests_demo_seed.py) (`apps.businesses.tests_demo_seed`)
- [tests_employee_access.py](../../../apps/businesses/tests_employee_access.py) (`apps.businesses.tests_employee_access`)
- [tests_employee_access_concurrency.py](../../../apps/businesses/tests_employee_access_concurrency.py) (`apps.businesses.tests_employee_access_concurrency`)
- [tests_invitation_concurrency.py](../../../apps/businesses/tests_invitation_concurrency.py) (`apps.businesses.tests_invitation_concurrency`)
- [tests_invitation_token.py](../../../apps/businesses/tests_invitation_token.py) (`apps.businesses.tests_invitation_token`)
- [tests_member_deactivation.py](../../../apps/businesses/tests_member_deactivation.py) (`apps.businesses.tests_member_deactivation`)
- [tests_ownership.py](../../../apps/businesses/tests_ownership.py) (`apps.businesses.tests_ownership`)
- [tests_permission_reads.py](../../../apps/businesses/tests_permission_reads.py) (`apps.businesses.tests_permission_reads`)
- [tests_pilot_onboarding.py](../../../apps/businesses/tests_pilot_onboarding.py) (`apps.businesses.tests_pilot_onboarding`)
- [tests_role_visibility.py](../../../apps/businesses/tests_role_visibility.py) (`apps.businesses.tests_role_visibility`)
- [tests_settings_team.py](../../../apps/businesses/tests_settings_team.py) (`apps.businesses.tests_settings_team`)
- [tests_team_source_visibility.py](../../../apps/businesses/tests_team_source_visibility.py) (`apps.businesses.tests_team_source_visibility`)

### clients

[apps/clients](../../../apps/clients); 8 test-файлов.

- [tests.py](../../../apps/clients/tests.py) (`apps.clients.tests`)
- [tests_archive_dependencies.py](../../../apps/clients/tests_archive_dependencies.py) (`apps.clients.tests_archive_dependencies`)
- [tests_duplicate_visibility.py](../../../apps/clients/tests_duplicate_visibility.py) (`apps.clients.tests_duplicate_visibility`)
- [tests_merge_atomicity.py](../../../apps/clients/tests_merge_atomicity.py) (`apps.clients.tests_merge_atomicity`)
- [tests_query_cost.py](../../../apps/clients/tests_query_cost.py) (`apps.clients.tests_query_cost`)
- [tests_search_pagination.py](../../../apps/clients/tests_search_pagination.py) (`apps.clients.tests_search_pagination`)
- [tests_sensitive_notes.py](../../../apps/clients/tests_sensitive_notes.py) (`apps.clients.tests_sensitive_notes`)
- [tests_workspace_filters.py](../../../apps/clients/tests_workspace_filters.py) (`apps.clients.tests_workspace_filters`)

### conversations

[apps/conversations](../../../apps/conversations); 9 test-файлов.

- [tests_ai_behavior_boundaries.py](../../../apps/conversations/tests_ai_behavior_boundaries.py) (`apps.conversations.tests_ai_behavior_boundaries`)
- [tests_ai_confirmation.py](../../../apps/conversations/tests_ai_confirmation.py) (`apps.conversations.tests_ai_confirmation`)
- [tests_client_linking.py](../../../apps/conversations/tests_client_linking.py) (`apps.conversations.tests_client_linking`)
- [tests_create_read_visibility.py](../../../apps/conversations/tests_create_read_visibility.py) (`apps.conversations.tests_create_read_visibility`)
- [tests_inbox_context.py](../../../apps/conversations/tests_inbox_context.py) (`apps.conversations.tests_inbox_context`)
- [tests_inbox_tasks.py](../../../apps/conversations/tests_inbox_tasks.py) (`apps.conversations.tests_inbox_tasks`)
- [tests_message_history.py](../../../apps/conversations/tests_message_history.py) (`apps.conversations.tests_message_history`)
- [tests_message_history_concurrency.py](../../../apps/conversations/tests_message_history_concurrency.py) (`apps.conversations.tests_message_history_concurrency`)
- [tests_quick_replies.py](../../../apps/conversations/tests_quick_replies.py) (`apps.conversations.tests_quick_replies`)

### core

[apps/core](../../../apps/core); 72 test-файлов.

- [tests.py](../../../apps/core/tests.py) (`apps.core.tests`)
- [tests_api_contracts.py](../../../apps/core/tests_api_contracts.py) (`apps.core.tests_api_contracts`)
- [tests_api_exceptions.py](../../../apps/core/tests_api_exceptions.py) (`apps.core.tests_api_exceptions`)
- [tests_api_load_smoke.py](../../../apps/core/tests_api_load_smoke.py) (`apps.core.tests_api_load_smoke`)
- [tests_archive.py](../../../apps/core/tests_archive.py) (`apps.core.tests_archive`)
- [tests_b0_security.py](../../../apps/core/tests_b0_security.py) (`apps.core.tests_b0_security`)
- [tests_b101_capability_enforcement.py](../../../apps/core/tests_b101_capability_enforcement.py) (`apps.core.tests_b101_capability_enforcement`)
- [tests_b1_runtime.py](../../../apps/core/tests_b1_runtime.py) (`apps.core.tests_b1_runtime`)
- [tests_b2_roles_queues.py](../../../apps/core/tests_b2_roles_queues.py) (`apps.core.tests_b2_roles_queues`)
- [tests_b301_performance.py](../../../apps/core/tests_b301_performance.py) (`apps.core.tests_b301_performance`)
- [tests_b3_contracts.py](../../../apps/core/tests_b3_contracts.py) (`apps.core.tests_b3_contracts`)
- [tests_b4_capabilities.py](../../../apps/core/tests_b4_capabilities.py) (`apps.core.tests_b4_capabilities`)
- [tests_b5_performance.py](../../../apps/core/tests_b5_performance.py) (`apps.core.tests_b5_performance`)
- [tests_backup_readiness.py](../../../apps/core/tests_backup_readiness.py) (`apps.core.tests_backup_readiness`)
- [tests_business_flows_e2e.py](../../../apps/core/tests_business_flows_e2e.py) (`apps.core.tests_business_flows_e2e`)
- [tests_catalog_permissions.py](../../../apps/core/tests_catalog_permissions.py) (`apps.core.tests_catalog_permissions`)
- [tests_client_import_permissions.py](../../../apps/core/tests_client_import_permissions.py) (`apps.core.tests_client_import_permissions`)
- [tests_client_pii_projections.py](../../../apps/core/tests_client_pii_projections.py) (`apps.core.tests_client_pii_projections`)
- [tests_crm_cards.py](../../../apps/core/tests_crm_cards.py) (`apps.core.tests_crm_cards`)
- [tests_crm_projection_access.py](../../../apps/core/tests_crm_projection_access.py) (`apps.core.tests_crm_projection_access`)
- [tests_crm_server_concurrency.py](../../../apps/core/tests_crm_server_concurrency.py) (`apps.core.tests_crm_server_concurrency`)
- [tests_crm_server_scenarios.py](../../../apps/core/tests_crm_server_scenarios.py) (`apps.core.tests_crm_server_scenarios`)
- [tests_crm_workspace_filters.py](../../../apps/core/tests_crm_workspace_filters.py) (`apps.core.tests_crm_workspace_filters`)
- [tests_custom_fields.py](../../../apps/core/tests_custom_fields.py) (`apps.core.tests_custom_fields`)
- [tests_email_readiness.py](../../../apps/core/tests_email_readiness.py) (`apps.core.tests_email_readiness`)
- [tests_export_access.py](../../../apps/core/tests_export_access.py) (`apps.core.tests_export_access`)
- [tests_export_attempts.py](../../../apps/core/tests_export_attempts.py) (`apps.core.tests_export_attempts`)
- [tests_export_history.py](../../../apps/core/tests_export_history.py) (`apps.core.tests_export_history`)
- [tests_file_attachments.py](../../../apps/core/tests_file_attachments.py) (`apps.core.tests_file_attachments`)
- [tests_file_scanning.py](../../../apps/core/tests_file_scanning.py) (`apps.core.tests_file_scanning`)
- [tests_historical_resolution.py](../../../apps/core/tests_historical_resolution.py) (`apps.core.tests_historical_resolution`)
- [tests_idempotency_prune.py](../../../apps/core/tests_idempotency_prune.py) (`apps.core.tests_idempotency_prune`)
- [tests_import_custom_fields.py](../../../apps/core/tests_import_custom_fields.py) (`apps.core.tests_import_custom_fields`)
- [tests_import_export.py](../../../apps/core/tests_import_export.py) (`apps.core.tests_import_export`)
- [tests_import_history.py](../../../apps/core/tests_import_history.py) (`apps.core.tests_import_history`)
- [tests_import_job_boundaries.py](../../../apps/core/tests_import_job_boundaries.py) (`apps.core.tests_import_job_boundaries`)
- [tests_import_job_concurrency.py](../../../apps/core/tests_import_job_concurrency.py) (`apps.core.tests_import_job_concurrency`)
- [tests_import_lifecycle.py](../../../apps/core/tests_import_lifecycle.py) (`apps.core.tests_import_lifecycle`)
- [tests_import_mapping_ui.py](../../../apps/core/tests_import_mapping_ui.py) (`apps.core.tests_import_mapping_ui`)
- [tests_import_samples.py](../../../apps/core/tests_import_samples.py) (`apps.core.tests_import_samples`)
- [tests_import_workspace_activation.py](../../../apps/core/tests_import_workspace_activation.py) (`apps.core.tests_import_workspace_activation`)
- [tests_import_workspace_api.py](../../../apps/core/tests_import_workspace_api.py) (`apps.core.tests_import_workspace_api`)
- [tests_import_workspace_concurrency.py](../../../apps/core/tests_import_workspace_concurrency.py) (`apps.core.tests_import_workspace_concurrency`)
- [tests_import_workspace_drafts.py](../../../apps/core/tests_import_workspace_drafts.py) (`apps.core.tests_import_workspace_drafts`)
- [tests_import_workspace_engine.py](../../../apps/core/tests_import_workspace_engine.py) (`apps.core.tests_import_workspace_engine`)
- [tests_import_workspace_operations.py](../../../apps/core/tests_import_workspace_operations.py) (`apps.core.tests_import_workspace_operations`)
- [tests_import_workspace_sources.py](../../../apps/core/tests_import_workspace_sources.py) (`apps.core.tests_import_workspace_sources`)
- [tests_internal_notification_accounting.py](../../../apps/core/tests_internal_notification_accounting.py) (`apps.core.tests_internal_notification_accounting`)
- [tests_log_redaction.py](../../../apps/core/tests_log_redaction.py) (`apps.core.tests_log_redaction`)
- [tests_mixed_membership_scope.py](../../../apps/core/tests_mixed_membership_scope.py) (`apps.core.tests_mixed_membership_scope`)
- [tests_observability.py](../../../apps/core/tests_observability.py) (`apps.core.tests_observability`)
- [tests_observability_django.py](../../../apps/core/tests_observability_django.py) (`apps.core.tests_observability_django`)
- [tests_paid_beta_gate.py](../../../apps/core/tests_paid_beta_gate.py) (`apps.core.tests_paid_beta_gate`)
- [tests_platform_crm.py](../../../apps/core/tests_platform_crm.py) (`apps.core.tests_platform_crm`)
- [tests_platform_details.py](../../../apps/core/tests_platform_details.py) (`apps.core.tests_platform_details`)
- [tests_platform_operations.py](../../../apps/core/tests_platform_operations.py) (`apps.core.tests_platform_operations`)
- [tests_platform_overview.py](../../../apps/core/tests_platform_overview.py) (`apps.core.tests_platform_overview`)
- [tests_platform_rebuild.py](../../../apps/core/tests_platform_rebuild.py) (`apps.core.tests_platform_rebuild`)
- [tests_platform_s02.py](../../../apps/core/tests_platform_s02.py) (`apps.core.tests_platform_s02`)
- [tests_platform_worklists.py](../../../apps/core/tests_platform_worklists.py) (`apps.core.tests_platform_worklists`)
- [tests_production_audit.py](../../../apps/core/tests_production_audit.py) (`apps.core.tests_production_audit`)
- [tests_rate_limits.py](../../../apps/core/tests_rate_limits.py) (`apps.core.tests_rate_limits`)
- [tests_readiness_redaction.py](../../../apps/core/tests_readiness_redaction.py) (`apps.core.tests_readiness_redaction`)
- [tests_record_queues.py](../../../apps/core/tests_record_queues.py) (`apps.core.tests_record_queues`)
- [tests_security.py](../../../apps/core/tests_security.py) (`apps.core.tests_security`)
- [tests_service_status.py](../../../apps/core/tests_service_status.py) (`apps.core.tests_service_status`)
- [tests_storage_runtime.py](../../../apps/core/tests_storage_runtime.py) (`apps.core.tests_storage_runtime`)
- [tests_task_preview_context.py](../../../apps/core/tests_task_preview_context.py) (`apps.core.tests_task_preview_context`)
- [tests_tenant_isolation.py](../../../apps/core/tests_tenant_isolation.py) (`apps.core.tests_tenant_isolation`)
- [tests_work_queues.py](../../../apps/core/tests_work_queues.py) (`apps.core.tests_work_queues`)
- [tests_workspace_related_filters.py](../../../apps/core/tests_workspace_related_filters.py) (`apps.core.tests_workspace_related_filters`)
- [tests_xlsx_reader.py](../../../apps/core/tests_xlsx_reader.py) (`apps.core.tests_xlsx_reader`)

### crm

[apps/crm](../../../apps/crm); 5 test-файлов.

- [tests.py](../../../apps/crm/tests.py) (`apps.crm.tests`)
- [tests_amount_projections.py](../../../apps/crm/tests_amount_projections.py) (`apps.crm.tests_amount_projections`)
- [tests_creation.py](../../../apps/crm/tests_creation.py) (`apps.crm.tests_creation`)
- [tests_pipeline_boundaries.py](../../../apps/crm/tests_pipeline_boundaries.py) (`apps.crm.tests_pipeline_boundaries`)
- [tests_workspace_filters.py](../../../apps/crm/tests_workspace_filters.py) (`apps.crm.tests_workspace_filters`)

### integrations

[apps/integrations](../../../apps/integrations); 14 test-файлов.

- [tests.py](../../../apps/integrations/tests.py) (`apps.integrations.tests`)
- [tests_channel_ownership.py](../../../apps/integrations/tests_channel_ownership.py) (`apps.integrations.tests_channel_ownership`)
- [tests_channel_setup_consistency.py](../../../apps/integrations/tests_channel_setup_consistency.py) (`apps.integrations.tests_channel_setup_consistency`)
- [tests_connectors.py](../../../apps/integrations/tests_connectors.py) (`apps.integrations.tests_connectors`)
- [tests_credential_encryption.py](../../../apps/integrations/tests_credential_encryption.py) (`apps.integrations.tests_credential_encryption`)
- [tests_encrypted_config.py](../../../apps/integrations/tests_encrypted_config.py) (`apps.integrations.tests_encrypted_config`)
- [tests_provider_rollout.py](../../../apps/integrations/tests_provider_rollout.py) (`apps.integrations.tests_provider_rollout`)
- [tests_public_api.py](../../../apps/integrations/tests_public_api.py) (`apps.integrations.tests_public_api`)
- [tests_whatsapp_binding.py](../../../apps/integrations/tests_whatsapp_binding.py) (`apps.integrations.tests_whatsapp_binding`)
- [tests_ycloud.py](../../../apps/integrations/tests_ycloud.py) (`apps.integrations.tests_ycloud`)
- [tests_ycloud_coexistence.py](../../../apps/integrations/tests_ycloud_coexistence.py) (`apps.integrations.tests_ycloud_coexistence`)
- [tests_ycloud_coexistence_concurrency.py](../../../apps/integrations/tests_ycloud_coexistence_concurrency.py) (`apps.integrations.tests_ycloud_coexistence_concurrency`)
- [tests_ycloud_concurrency.py](../../../apps/integrations/tests_ycloud_concurrency.py) (`apps.integrations.tests_ycloud_concurrency`)
- [tests_ycloud_dispatch.py](../../../apps/integrations/tests_ycloud_dispatch.py) (`apps.integrations.tests_ycloud_dispatch`)

### leads

[apps/leads](../../../apps/leads); 11 test-файлов.

- [tests_assignment_patch.py](../../../apps/leads/tests_assignment_patch.py) (`apps.leads.tests_assignment_patch`)
- [tests_creation.py](../../../apps/leads/tests_creation.py) (`apps.leads.tests_creation`)
- [tests_crm_light.py](../../../apps/leads/tests_crm_light.py) (`apps.leads.tests_crm_light`)
- [tests_duplicate_visibility.py](../../../apps/leads/tests_duplicate_visibility.py) (`apps.leads.tests_duplicate_visibility`)
- [tests_form_field_access.py](../../../apps/leads/tests_form_field_access.py) (`apps.leads.tests_form_field_access`)
- [tests_form_write_boundaries.py](../../../apps/leads/tests_form_write_boundaries.py) (`apps.leads.tests_form_write_boundaries`)
- [tests_forms.py](../../../apps/leads/tests_forms.py) (`apps.leads.tests_forms`)
- [tests_offline_commands.py](../../../apps/leads/tests_offline_commands.py) (`apps.leads.tests_offline_commands`)
- [tests_public_intake_privacy.py](../../../apps/leads/tests_public_intake_privacy.py) (`apps.leads.tests_public_intake_privacy`)
- [tests_task_assignment.py](../../../apps/leads/tests_task_assignment.py) (`apps.leads.tests_task_assignment`)
- [tests_workspace_filters.py](../../../apps/leads/tests_workspace_filters.py) (`apps.leads.tests_workspace_filters`)

### notifications

[apps/notifications](../../../apps/notifications); 14 test-файлов.

- [tests.py](../../../apps/notifications/tests.py) (`apps.notifications.tests`)
- [tests_appointment_feed_links.py](../../../apps/notifications/tests_appointment_feed_links.py) (`apps.notifications.tests_appointment_feed_links`)
- [tests_bell.py](../../../apps/notifications/tests_bell.py) (`apps.notifications.tests_bell`)
- [tests_email.py](../../../apps/notifications/tests_email.py) (`apps.notifications.tests_email`)
- [tests_event_stream.py](../../../apps/notifications/tests_event_stream.py) (`apps.notifications.tests_event_stream`)
- [tests_mark_all_access.py](../../../apps/notifications/tests_mark_all_access.py) (`apps.notifications.tests_mark_all_access`)
- [tests_personal_api.py](../../../apps/notifications/tests_personal_api.py) (`apps.notifications.tests_personal_api`)
- [tests_personal_concurrency.py](../../../apps/notifications/tests_personal_concurrency.py) (`apps.notifications.tests_personal_concurrency`)
- [tests_personal_migration.py](../../../apps/notifications/tests_personal_migration.py) (`apps.notifications.tests_personal_migration`)
- [tests_personal_recipients.py](../../../apps/notifications/tests_personal_recipients.py) (`apps.notifications.tests_personal_recipients`)
- [tests_personal_services.py](../../../apps/notifications/tests_personal_services.py) (`apps.notifications.tests_personal_services`)
- [tests_realtime.py](../../../apps/notifications/tests_realtime.py) (`apps.notifications.tests_realtime`)
- [tests_service_messages.py](../../../apps/notifications/tests_service_messages.py) (`apps.notifications.tests_service_messages`)
- [tests_settings_preferences.py](../../../apps/notifications/tests_settings_preferences.py) (`apps.notifications.tests_settings_preferences`)

### onboarding

[apps/onboarding](../../../apps/onboarding); 2 test-файлов.

- [tests.py](../../../apps/onboarding/tests.py) (`apps.onboarding.tests`)
- [tests_preset_preservation.py](../../../apps/onboarding/tests_preset_preservation.py) (`apps.onboarding.tests_preset_preservation`)

### outreach

[apps/outreach](../../../apps/outreach); 6 test-файлов.

- [tests.py](../../../apps/outreach/tests.py) (`apps.outreach.tests`)
- [tests_automation_status_access.py](../../../apps/outreach/tests_automation_status_access.py) (`apps.outreach.tests_automation_status_access`)
- [tests_consent_xlsx_limits.py](../../../apps/outreach/tests_consent_xlsx_limits.py) (`apps.outreach.tests_consent_xlsx_limits`)
- [tests_mutation_permissions.py](../../../apps/outreach/tests_mutation_permissions.py) (`apps.outreach.tests_mutation_permissions`)
- [tests_public_intake_optout.py](../../../apps/outreach/tests_public_intake_optout.py) (`apps.outreach.tests_public_intake_optout`)
- [tests_template_safety.py](../../../apps/outreach/tests_template_safety.py) (`apps.outreach.tests_template_safety`)

### payments

[apps/payments](../../../apps/payments); 1 test-файлов.

- [tests.py](../../../apps/payments/tests.py) (`apps.payments.tests`)

### pricing

[apps/pricing](../../../apps/pricing); 2 test-файлов.

- [tests.py](../../../apps/pricing/tests.py) (`apps.pricing.tests`)
- [tests_business_validation.py](../../../apps/pricing/tests_business_validation.py) (`apps.pricing.tests_business_validation`)

### scheduling

[apps/scheduling](../../../apps/scheduling); 17 test-файлов.

- [tests.py](../../../apps/scheduling/tests.py) (`apps.scheduling.tests`)
- [tests_calendar_summary.py](../../../apps/scheduling/tests_calendar_summary.py) (`apps.scheduling.tests_calendar_summary`)
- [tests_import_commands.py](../../../apps/scheduling/tests_import_commands.py) (`apps.scheduling.tests_import_commands`)
- [tests_plan_concurrency.py](../../../apps/scheduling/tests_plan_concurrency.py) (`apps.scheduling.tests_plan_concurrency`)
- [tests_record_commands.py](../../../apps/scheduling/tests_record_commands.py) (`apps.scheduling.tests_record_commands`)
- [tests_record_completion.py](../../../apps/scheduling/tests_record_completion.py) (`apps.scheduling.tests_record_completion`)
- [tests_record_concurrency.py](../../../apps/scheduling/tests_record_concurrency.py) (`apps.scheduling.tests_record_concurrency`)
- [tests_record_migration.py](../../../apps/scheduling/tests_record_migration.py) (`apps.scheduling.tests_record_migration`)
- [tests_record_workspace.py](../../../apps/scheduling/tests_record_workspace.py) (`apps.scheduling.tests_record_workspace`)
- [tests_resource_booking.py](../../../apps/scheduling/tests_resource_booking.py) (`apps.scheduling.tests_resource_booking`)
- [tests_resource_booking_concurrency.py](../../../apps/scheduling/tests_resource_booking_concurrency.py) (`apps.scheduling.tests_resource_booking_concurrency`)
- [tests_resource_booking_migration.py](../../../apps/scheduling/tests_resource_booking_migration.py) (`apps.scheduling.tests_resource_booking_migration`)
- [tests_settings_delivery.py](../../../apps/scheduling/tests_settings_delivery.py) (`apps.scheduling.tests_settings_delivery`)
- [tests_specialist_schedule.py](../../../apps/scheduling/tests_specialist_schedule.py) (`apps.scheduling.tests_specialist_schedule`)
- [tests_visit_plans.py](../../../apps/scheduling/tests_visit_plans.py) (`apps.scheduling.tests_visit_plans`)
- [tests_working_hours_concurrency.py](../../../apps/scheduling/tests_working_hours_concurrency.py) (`apps.scheduling.tests_working_hours_concurrency`)
- [tests_working_hours_integrity.py](../../../apps/scheduling/tests_working_hours_integrity.py) (`apps.scheduling.tests_working_hours_integrity`)

### services

[apps/services](../../../apps/services); 2 test-файлов.

- [tests.py](../../../apps/services/tests.py) (`apps.services.tests`)
- [tests_metrics.py](../../../apps/services/tests_metrics.py) (`apps.services.tests_metrics`)

### support

[apps/support](../../../apps/support); 4 test-файлов.

- [tests_api.py](../../../apps/support/tests_api.py) (`apps.support.tests_api`)
- [tests_concurrency.py](../../../apps/support/tests_concurrency.py) (`apps.support.tests_concurrency`)
- [tests_domain.py](../../../apps/support/tests_domain.py) (`apps.support.tests_domain`)
- [tests_incidents.py](../../../apps/support/tests_incidents.py) (`apps.support.tests_incidents`)

### tasks

[apps/tasks](../../../apps/tasks); 5 test-файлов.

- [tests.py](../../../apps/tasks/tests.py) (`apps.tasks.tests`)
- [tests_concurrency.py](../../../apps/tasks/tests_concurrency.py) (`apps.tasks.tests_concurrency`)
- [tests_migrations.py](../../../apps/tasks/tests_migrations.py) (`apps.tasks.tests_migrations`)
- [tests_reminders.py](../../../apps/tasks/tests_reminders.py) (`apps.tasks.tests_reminders`)
- [tests_workspace.py](../../../apps/tasks/tests_workspace.py) (`apps.tasks.tests_workspace`)

## PostgreSQL concurrency candidates

Кроме этих имён включить PG-only guards/constraint tests из остальных модулей.
Не выдавать SQLite skips за PG PASS.

- [apps/ai_core/tests_voice_schedule_concurrency.py](../../../apps/ai_core/tests_voice_schedule_concurrency.py)
- [apps/automations/tests_configuration_concurrency.py](../../../apps/automations/tests_configuration_concurrency.py)
- [apps/automations/tests_follow_up_concurrency.py](../../../apps/automations/tests_follow_up_concurrency.py)
- [apps/billing/tests_commerce_concurrency.py](../../../apps/billing/tests_commerce_concurrency.py)
- [apps/bots/tests_booking_creation_concurrency.py](../../../apps/bots/tests_booking_creation_concurrency.py)
- [apps/bots/tests_booking_terms_concurrency.py](../../../apps/bots/tests_booking_terms_concurrency.py)
- [apps/branches/tests_concurrency.py](../../../apps/branches/tests_concurrency.py)
- [apps/branches/tests_single_location_concurrency.py](../../../apps/branches/tests_single_location_concurrency.py)
- [apps/businesses/tests_employee_access_concurrency.py](../../../apps/businesses/tests_employee_access_concurrency.py)
- [apps/businesses/tests_invitation_concurrency.py](../../../apps/businesses/tests_invitation_concurrency.py)
- [apps/conversations/tests_message_history_concurrency.py](../../../apps/conversations/tests_message_history_concurrency.py)
- [apps/core/tests_crm_server_concurrency.py](../../../apps/core/tests_crm_server_concurrency.py)
- [apps/core/tests_import_job_concurrency.py](../../../apps/core/tests_import_job_concurrency.py)
- [apps/core/tests_import_workspace_concurrency.py](../../../apps/core/tests_import_workspace_concurrency.py)
- [apps/integrations/tests_ycloud_coexistence_concurrency.py](../../../apps/integrations/tests_ycloud_coexistence_concurrency.py)
- [apps/integrations/tests_ycloud_concurrency.py](../../../apps/integrations/tests_ycloud_concurrency.py)
- [apps/notifications/tests_personal_concurrency.py](../../../apps/notifications/tests_personal_concurrency.py)
- [apps/scheduling/tests_plan_concurrency.py](../../../apps/scheduling/tests_plan_concurrency.py)
- [apps/scheduling/tests_record_concurrency.py](../../../apps/scheduling/tests_record_concurrency.py)
- [apps/scheduling/tests_resource_booking_concurrency.py](../../../apps/scheduling/tests_resource_booking_concurrency.py)
- [apps/scheduling/tests_working_hours_concurrency.py](../../../apps/scheduling/tests_working_hours_concurrency.py)
- [apps/support/tests_concurrency.py](../../../apps/support/tests_concurrency.py)
- [apps/tasks/tests_concurrency.py](../../../apps/tasks/tests_concurrency.py)

## Существующие браузерные specs

Это отдельный автоматизированный слой. Он не заменяет выполнение B01–B48 через «Компьютер».
Config/fixtures конкретного spec проверяются перед исполнением; default config может reuse localhost.

- [accessibility-responsive.spec.ts](../../../frontend/e2e/accessibility-responsive.spec.ts)
- [account-avatar.spec.ts](../../../frontend/e2e/account-avatar.spec.ts)
- [account-interface.spec.ts](../../../frontend/e2e/account-interface.spec.ts)
- [account-mfa-qr-recovery.spec.ts](../../../frontend/e2e/account-mfa-qr-recovery.spec.ts)
- [account-mfa-qr.spec.ts](../../../frontend/e2e/account-mfa-qr.spec.ts)
- [account-section-nav.spec.ts](../../../frontend/e2e/account-section-nav.spec.ts)
- [account-session-continuations.spec.ts](../../../frontend/e2e/account-session-continuations.spec.ts)
- [account-sessions.spec.ts](../../../frontend/e2e/account-sessions.spec.ts)
- [account-user-settings.spec.ts](../../../frontend/e2e/account-user-settings.spec.ts)
- [action-color-roles.spec.ts](../../../frontend/e2e/action-color-roles.spec.ts)
- [action-feedback.spec.ts](../../../frontend/e2e/action-feedback.spec.ts)
- [agent-header-picker.spec.ts](../../../frontend/e2e/agent-header-picker.spec.ts)
- [agent-reference-layout.spec.ts](../../../frontend/e2e/agent-reference-layout.spec.ts)
- [agent-setup.spec.ts](../../../frontend/e2e/agent-setup.spec.ts)
- [ai-agent-analytics-certification.spec.ts](../../../frontend/e2e/ai-agent-analytics-certification.spec.ts)
- [ai-agent-continuity.spec.ts](../../../frontend/e2e/ai-agent-continuity.spec.ts)
- [ai-agent-followup.spec.ts](../../../frontend/e2e/ai-agent-followup.spec.ts)
- [ai-agent-isolation.spec.ts](../../../frontend/e2e/ai-agent-isolation.spec.ts)
- [ai-agent-readiness.spec.ts](../../../frontend/e2e/ai-agent-readiness.spec.ts)
- [ai-agent-scenarios.spec.ts](../../../frontend/e2e/ai-agent-scenarios.spec.ts)
- [ai-agent-settings-certification.spec.ts](../../../frontend/e2e/ai-agent-settings-certification.spec.ts)
- [ai-agents-ux.spec.ts](../../../frontend/e2e/ai-agents-ux.spec.ts)
- [ai-crm-history.spec.ts](../../../frontend/e2e/ai-crm-history.spec.ts)
- [ai-functional-settings.spec.ts](../../../frontend/e2e/ai-functional-settings.spec.ts)
- [ai-inbox-memory.spec.ts](../../../frontend/e2e/ai-inbox-memory.spec.ts)
- [ai-job-recovery.spec.ts](../../../frontend/e2e/ai-job-recovery.spec.ts)
- [alert-application.spec.ts](../../../frontend/e2e/alert-application.spec.ts)
- [alert-components.spec.ts](../../../frontend/e2e/alert-components.spec.ts)
- [alert-remediation.spec.ts](../../../frontend/e2e/alert-remediation.spec.ts)
- [billing-commerce.spec.ts](../../../frontend/e2e/billing-commerce.spec.ts)
- [booking-responsible-settings.spec.ts](../../../frontend/e2e/booking-responsible-settings.spec.ts)
- [calendar-consumers.spec.ts](../../../frontend/e2e/calendar-consumers.spec.ts)
- [calendar-controls.spec.ts](../../../frontend/e2e/calendar-controls.spec.ts)
- [calendar-workspace.spec.ts](../../../frontend/e2e/calendar-workspace.spec.ts)
- [color-system-audit.spec.ts](../../../frontend/e2e/color-system-audit.spec.ts)
- [color-system-details.spec.ts](../../../frontend/e2e/color-system-details.spec.ts)
- [connection-probe.spec.ts](../../../frontend/e2e/connection-probe.spec.ts)
- [connection-recovery.spec.ts](../../../frontend/e2e/connection-recovery.spec.ts)
- [crm-toolbar-refinement.spec.ts](../../../frontend/e2e/crm-toolbar-refinement.spec.ts)
- [crm-unified-filters.spec.ts](../../../frontend/e2e/crm-unified-filters.spec.ts)
- [crm-workspace-overlay.spec.ts](../../../frontend/e2e/crm-workspace-overlay.spec.ts)
- [crm-workspaces-data.spec.ts](../../../frontend/e2e/crm-workspaces-data.spec.ts)
- [crm-workspaces-deals.spec.ts](../../../frontend/e2e/crm-workspaces-deals.spec.ts)
- [crm-workspaces-reference.spec.ts](../../../frontend/e2e/crm-workspaces-reference.spec.ts)
- [daily-workspaces.spec.ts](../../../frontend/e2e/daily-workspaces.spec.ts)
- [dashboard-data-loading.spec.ts](../../../frontend/e2e/dashboard-data-loading.spec.ts)
- [deals-empty-workspace.spec.ts](../../../frontend/e2e/deals-empty-workspace.spec.ts)
- [deals-kanban-density.spec.ts](../../../frontend/e2e/deals-kanban-density.spec.ts)
- [deals-workspace-density.spec.ts](../../../frontend/e2e/deals-workspace-density.spec.ts)
- [emerald-palette.spec.ts](../../../frontend/e2e/emerald-palette.spec.ts)
- [entity-workspaces.spec.ts](../../../frontend/e2e/entity-workspaces.spec.ts)
- [failure-certification.spec.ts](../../../frontend/e2e/failure-certification.spec.ts)
- [focus-modality.spec.ts](../../../frontend/e2e/focus-modality.spec.ts)
- [functional-certification.spec.ts](../../../frontend/e2e/functional-certification.spec.ts)
- [handoff-recovery.spec.ts](../../../frontend/e2e/handoff-recovery.spec.ts)
- [header-search-width.spec.ts](../../../frontend/e2e/header-search-width.spec.ts)
- [import-file-picker.spec.cjs](../../../frontend/e2e/import-file-picker.spec.cjs)
- [import-workspace.spec.cjs](../../../frontend/e2e/import-workspace.spec.cjs)
- [inbox-agent-safety.spec.ts](../../../frontend/e2e/inbox-agent-safety.spec.ts)
- [inbox-client-relink.spec.ts](../../../frontend/e2e/inbox-client-relink.spec.ts)
- [inbox-compact.spec.ts](../../../frontend/e2e/inbox-compact.spec.ts)
- [inbox-draft-provenance.spec.ts](../../../frontend/e2e/inbox-draft-provenance.spec.ts)
- [inbox-inspector.spec.ts](../../../frontend/e2e/inbox-inspector.spec.ts)
- [inbox-local-pilot.spec.ts](../../../frontend/e2e/inbox-local-pilot.spec.ts)
- [inspector-interaction.spec.ts](../../../frontend/e2e/inspector-interaction.spec.ts)
- [kazakh-typography.spec.ts](../../../frontend/e2e/kazakh-typography.spec.ts)
- [leads-offline-isolation.spec.ts](../../../frontend/e2e/leads-offline-isolation.spec.ts)
- [legal-documents.spec.ts](../../../frontend/e2e/legal-documents.spec.ts)
- [logout-callers.spec.ts](../../../frontend/e2e/logout-callers.spec.ts)
- [logout-cross-tab.spec.ts](../../../frontend/e2e/logout-cross-tab.spec.ts)
- [logout-recovery.spec.ts](../../../frontend/e2e/logout-recovery.spec.ts)
- [merchant-journeys-certification.spec.ts](../../../frontend/e2e/merchant-journeys-certification.spec.ts)
- [mfa-login.spec.ts](../../../frontend/e2e/mfa-login.spec.ts)
- [multibranch.spec.ts](../../../frontend/e2e/multibranch.spec.ts)
- [neutral-terminology.spec.ts](../../../frontend/e2e/neutral-terminology.spec.ts)
- [notification-refactor.spec.ts](../../../frontend/e2e/notification-refactor.spec.ts)
- [pilot-actions.spec.ts](../../../frontend/e2e/pilot-actions.spec.ts)
- [pilot-auth-security.spec.ts](../../../frontend/e2e/pilot-auth-security.spec.ts)
- [pilot-auth.spec.ts](../../../frontend/e2e/pilot-auth.spec.ts)
- [pilot-invitations.spec.ts](../../../frontend/e2e/pilot-invitations.spec.ts)
- [pilot-password-reset.spec.ts](../../../frontend/e2e/pilot-password-reset.spec.ts)
- [pilot-record-content.spec.ts](../../../frontend/e2e/pilot-record-content.spec.ts)
- [pilot-staff-sales-cycle.spec.ts](../../../frontend/e2e/pilot-staff-sales-cycle.spec.ts)
- [platform-clinic-crm.spec.ts](../../../frontend/e2e/platform-clinic-crm.spec.ts)
- [platform-details.spec.ts](../../../frontend/e2e/platform-details.spec.ts)
- [platform-employee-access.spec.ts](../../../frontend/e2e/platform-employee-access.spec.ts)
- [platform-operations.spec.ts](../../../frontend/e2e/platform-operations.spec.ts)
- [platform-overview.spec.ts](../../../frontend/e2e/platform-overview.spec.ts)
- [platform-ownership.spec.ts](../../../frontend/e2e/platform-ownership.spec.ts)
- [platform-recovery.spec.ts](../../../frontend/e2e/platform-recovery.spec.ts)
- [platform-s02.spec.ts](../../../frontend/e2e/platform-s02.spec.ts)
- [platform-shell.spec.ts](../../../frontend/e2e/platform-shell.spec.ts)
- [platform-support-incidents.spec.ts](../../../frontend/e2e/platform-support-incidents.spec.ts)
- [platform-support.spec.ts](../../../frontend/e2e/platform-support.spec.ts)
- [pricing-refactor.spec.ts](../../../frontend/e2e/pricing-refactor.spec.ts)
- [r01-daily-cycle.spec.ts](../../../frontend/e2e/r01-daily-cycle.spec.ts)
- [r01-inbox-task.spec.ts](../../../frontend/e2e/r01-inbox-task.spec.ts)
- [records-bell-recovery.spec.ts](../../../frontend/e2e/records-bell-recovery.spec.ts)
- [records-toolbar.spec.ts](../../../frontend/e2e/records-toolbar.spec.ts)
- [runtime-maintainability.spec.ts](../../../frontend/e2e/runtime-maintainability.spec.ts)
- [service-error-feedback.spec.ts](../../../frontend/e2e/service-error-feedback.spec.ts)
- [service-s03.spec.ts](../../../frontend/e2e/service-s03.spec.ts)
- [services-lifecycle.spec.ts](../../../frontend/e2e/services-lifecycle.spec.ts)
- [session-cache-isolation.spec.ts](../../../frontend/e2e/session-cache-isolation.spec.ts)
- [session-notices.spec.ts](../../../frontend/e2e/session-notices.spec.ts)
- [session-persistence.spec.ts](../../../frontend/e2e/session-persistence.spec.ts)
- [settings-assignment.spec.ts](../../../frontend/e2e/settings-assignment.spec.ts)
- [settings-functional.spec.ts](../../../frontend/e2e/settings-functional.spec.ts)
- [settings-redesign.spec.ts](../../../frontend/e2e/settings-redesign.spec.ts)
- [settings-workflow.spec.ts](../../../frontend/e2e/settings-workflow.spec.ts)
- [smoke.spec.ts](../../../frontend/e2e/smoke.spec.ts)
- [state-behavior.spec.ts](../../../frontend/e2e/state-behavior.spec.ts)
- [tasks-redesign.spec.ts](../../../frontend/e2e/tasks-redesign.spec.ts)
- [ui-operations.spec.ts](../../../frontend/e2e/ui-operations.spec.ts)
- [widget-colors.spec.ts](../../../frontend/e2e/widget-colors.spec.ts)

## Node и script checks

- [action-color-policy.test.mjs](../../../frontend/scripts/tests/action-color-policy.test.mjs)
- [action-feedback-policy.test.mjs](../../../frontend/scripts/tests/action-feedback-policy.test.mjs)
- [announcement-events.test.mjs](../../../frontend/scripts/tests/announcement-events.test.mjs)
- [app-error-normalization.test.mjs](../../../frontend/scripts/tests/app-error-normalization.test.mjs)
- [appointment-cache.test.mjs](../../../frontend/scripts/tests/appointment-cache.test.mjs)
- [audit-runtime.test.mjs](../../../frontend/scripts/tests/audit-runtime.test.mjs)
- [auth-request.test.mjs](../../../frontend/scripts/tests/auth-request.test.mjs)
- [auth-return-path.test.mjs](../../../frontend/scripts/tests/auth-return-path.test.mjs)
- [automation-editor.test.mjs](../../../frontend/scripts/tests/automation-editor.test.mjs)
- [automation-history.test.mjs](../../../frontend/scripts/tests/automation-history.test.mjs)
- [automation-models.test.mjs](../../../frontend/scripts/tests/automation-models.test.mjs)
- [bundle-budget.test.mjs](../../../frontend/scripts/tests/bundle-budget.test.mjs)
- [calendar-period.test.mjs](../../../frontend/scripts/tests/calendar-period.test.mjs)
- [calendar-years.test.mjs](../../../frontend/scripts/tests/calendar-years.test.mjs)
- [capture-field-options.test.mjs](../../../frontend/scripts/tests/capture-field-options.test.mjs)
- [chromatic-runtime.test.mjs](../../../frontend/scripts/tests/chromatic-runtime.test.mjs)
- [client-search.test.mjs](../../../frontend/scripts/tests/client-search.test.mjs)
- [clients-toolbar.test.mjs](../../../frontend/scripts/tests/clients-toolbar.test.mjs)
- [custom-field-filter.test.mjs](../../../frontend/scripts/tests/custom-field-filter.test.mjs)
- [daily-workspaces-policy.test.mjs](../../../frontend/scripts/tests/daily-workspaces-policy.test.mjs)
- [dashboard-appointment-dedupe.test.mjs](../../../frontend/scripts/tests/dashboard-appointment-dedupe.test.mjs)
- [error-boundary-policy.test.mjs](../../../frontend/scripts/tests/error-boundary-policy.test.mjs)
- [export-history.test.mjs](../../../frontend/scripts/tests/export-history.test.mjs)
- [failure-certification-registry.test.mjs](../../../frontend/scripts/tests/failure-certification-registry.test.mjs)
- [fallback-inventory.test.mjs](../../../frontend/scripts/tests/fallback-inventory.test.mjs)
- [fallback-surface-policy.test.mjs](../../../frontend/scripts/tests/fallback-surface-policy.test.mjs)
- [form-resolver-compatibility.test.mjs](../../../frontend/scripts/tests/form-resolver-compatibility.test.mjs)
- [functional-certification-registry.test.mjs](../../../frontend/scripts/tests/functional-certification-registry.test.mjs)
- [gate-environment-policy.test.mjs](../../../frontend/scripts/tests/gate-environment-policy.test.mjs)
- [i18n-dictionary-source.test.mjs](../../../frontend/scripts/tests/i18n-dictionary-source.test.mjs)
- [import-history.test.mjs](../../../frontend/scripts/tests/import-history.test.mjs)
- [import-review.test.mjs](../../../frontend/scripts/tests/import-review.test.mjs)
- [import-workspace-errors.test.mjs](../../../frontend/scripts/tests/import-workspace-errors.test.mjs)
- [inbox-delivery-policy.test.mjs](../../../frontend/scripts/tests/inbox-delivery-policy.test.mjs)
- [inbox-draft.test.mjs](../../../frontend/scripts/tests/inbox-draft.test.mjs)
- [inbox-sending-model.test.mjs](../../../frontend/scripts/tests/inbox-sending-model.test.mjs)
- [industry-terms.test.mjs](../../../frontend/scripts/tests/industry-terms.test.mjs)
- [landing-routes.test.mjs](../../../frontend/scripts/tests/landing-routes.test.mjs)
- [lead-csv-safety.test.mjs](../../../frontend/scripts/tests/lead-csv-safety.test.mjs)
- [lead-offline-commands.test.mjs](../../../frontend/scripts/tests/lead-offline-commands.test.mjs)
- [lead-offline-storage.test.mjs](../../../frontend/scripts/tests/lead-offline-storage.test.mjs)
- [login-page-policy.test.mjs](../../../frontend/scripts/tests/login-page-policy.test.mjs)
- [merchant-journey-certification.test.mjs](../../../frontend/scripts/tests/merchant-journey-certification.test.mjs)
- [notification-cache.test.mjs](../../../frontend/scripts/tests/notification-cache.test.mjs)
- [notification-dedupe.test.mjs](../../../frontend/scripts/tests/notification-dedupe.test.mjs)
- [notification-header-model.test.mjs](../../../frontend/scripts/tests/notification-header-model.test.mjs)
- [record-filters.test.mjs](../../../frontend/scripts/tests/record-filters.test.mjs)
- [record-legacy-export.test.mjs](../../../frontend/scripts/tests/record-legacy-export.test.mjs)
- [route-prefetch.test.mjs](../../../frontend/scripts/tests/route-prefetch.test.mjs)
- [settings-section-models.test.mjs](../../../frontend/scripts/tests/settings-section-models.test.mjs)
- [sidebar-navigation-policy.test.mjs](../../../frontend/scripts/tests/sidebar-navigation-policy.test.mjs)
- [task-workspace.test.mjs](../../../frontend/scripts/tests/task-workspace.test.mjs)
- [telemetry-privacy.test.mjs](../../../frontend/scripts/tests/telemetry-privacy.test.mjs)
- [telemetry-sdk-browser.test.mjs](../../../frontend/scripts/tests/telemetry-sdk-browser.test.mjs)
- [timeline-presentation.test.mjs](../../../frontend/scripts/tests/timeline-presentation.test.mjs)
- [token-csrf.test.mjs](../../../frontend/scripts/tests/token-csrf.test.mjs)
- [ui-toolkit-policy.test.mjs](../../../frontend/scripts/tests/ui-toolkit-policy.test.mjs)
- [vite-cache-isolation.test.mjs](../../../frontend/scripts/tests/vite-cache-isolation.test.mjs)
- [voice-audio.test.mjs](../../../frontend/scripts/tests/voice-audio.test.mjs)
- [test_api_load_smoke.py](../../../scripts/tests/test_api_load_smoke.py)
- [test_auth_cache.py](../../../scripts/tests/test_auth_cache.py)
- [test_browser_test_runtime.py](../../../scripts/tests/test_browser_test_runtime.py)
- [test_clean_archive.py](../../../scripts/tests/test_clean_archive.py)
- [test_codex_verify.py](../../../scripts/tests/test_codex_verify.py)
- [test_dev_local.py](../../../scripts/tests/test_dev_local.py)
- [test_local_postgres.py](../../../scripts/tests/test_local_postgres.py)
- [test_recovery_faults.py](../../../scripts/tests/test_recovery_faults.py)

## Открытые границы, найденные статически

- `OutreachPage` существует как компонент, но отсутствует в текущих route declarations: OUTREACH/B44 API-only до доказательства достижимости.
- `DevelopersSection` с API tokens/webhooks найден только как определение, без импорта в действующий Settings/router; INTEGRATION-05/06 остаются API-проверками, B44 фиксирует отсутствие пути.
- `/app/leads` и `/app/deals` используют LegacyRecordsPage, а `/leads` и `/deals` ссылаются на старые страницы: B43 проверяет контрактную совместимость и видимость.
- Plan API имеет create/history/schedule/revise/archive/restore/responsible; наличие plan не доказывает пакетную денежную логику.
- Payment API имеет list/retrieve/create/link-options, без generic update/delete. Refund создаётся ledger service, не редактированием receipt.
- SaaS commerce/external finance/provider capabilities/реальная AI-модель зависят от конфигурации; никакая конфигурация target сейчас не проверялась.
- Страницы public form/widget требуют реального embed/preview entry либо отдельного test harness, которого этот документ не создаёт.
- Текущий `codex_verify full` содержит только mobile owner/manager browser smoke; полная UX-матрица требует отдельных сценариев.
- Новые fixes timeline/task/lead могут появляться во время подготовки; перед тестированием нужно повторно сверить именно затронутый delta.

Ни одна из этих границ не является разрешением на реализацию отсутствующей функции.
