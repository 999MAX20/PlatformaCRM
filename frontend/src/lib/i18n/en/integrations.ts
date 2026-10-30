export const integrations: Record<string, string> = {
  "telegramSetup.tokenSaved": "Key saved. Now check the connection.",
  "telegramSetup.tokenCleared": "Key cleared.",
  "telegramSetup.connectionChecked": "Telegram connection checked.",
  "telegramSetup.connectionFailed": "Could not check Telegram connection.",
  "telegramSetup.inboxConnected":
    "Incoming messages are connected. Message the bot as a client and check the conversation.",
  "telegramSetup.inboxFailed": "Could not connect incoming messages.",
  "telegramSetup.description":
    "Connect Telegram to messages and automatic replies.",
  "telegramSetup.key": "Key",
  "telegramSetup.saved": "Saved",
  "telegramSetup.needed": "Needed",
  "telegramSetup.protection": "Protection",
  "telegramSetup.ready": "Ready",
  "telegramSetup.willConfigure": "Will configure",
  "telegramSetup.inbox": "Incoming",
  "telegramSetup.connected": "Connected",
  "telegramSetup.notConnected": "Not connected",
  "telegramSetup.botKey": "Bot key",
  "telegramSetup.botKeyText":
    "Create a bot in @BotFather, paste the key here and run a check. The key will not be shown again.",
  "telegramSetup.botKeyPlaceholder": "Paste bot key",
  "telegramSetup.checkKey": "Check key",
  "telegramSetup.connectInbox": "Connect incoming",
  "telegramSetup.readyNotice":
    "Telegram is ready. Send a message to the bot as a client and check the incoming conversation.",
  "telegramSetup.latestEvents": "Latest events",
  "telegramSetup.noEvents": "No events yet.",
  "telegramSetup.addChannelFirst": "Add a Telegram channel for this bot first.",
  "developers.advanced": "Advanced",
  "developers.title": "Integration keys and events",
  "developers.description":
    "Advanced layer for technical connections. Use it only together with a developer or PlatformaCRM support.",
  "developers.summary": "{tokens} keys · {webhooks} events",
  "developers.defaultTokenName": "CRM integration key",
  "developers.defaultWebhookName": "Production webhook",
  "developers.copyNow": "Copy the key now",
  "developers.copyNowText":
    "The full key is shown only once. After closing, only the short prefix will remain visible.",
  "developers.copied": "Copied",
  "developers.tokensTitle": "Integration keys",
  "developers.tokensText": "Minimum: read-only access to clients.",
  "developers.name": "Name",
  "developers.scopes": "Access scopes",
  "developers.createToken": "Create key",
  "developers.lastUsed": "Last used:",
  "developers.active": "Active",
  "developers.revoked": "Revoked",
  "developers.rotate": "Rotate",
  "developers.revoke": "Revoke",
  "developers.noTokens": "No keys yet.",
  "developers.webhooksTitle": "External events",
  "developers.webhooksText": "Use the safe demo endpoint for testing.",
  "developers.signatureSecret": "Signature secret",
  "developers.events": "Events",
  "developers.addWebhook": "Add event",
  "developers.copySecret": "Copy secret",
  "developers.allEvents": "all events",
  "developers.check": "Check",
  "developers.noWebhooks": "No external events configured yet.",
  "developers.deliveryTitle": "Delivery logs",
  "developers.deliveryText":
    "Latest deliveries, provider responses and manual retry for failed events.",
  "developers.refresh": "Refresh",
  "developers.noDeliveries":
    "No deliveries yet. Click “Check” on an external event.",
  "developers.attempts": "attempts",
  "developers.showPayload": "Show technical event data",
  "whatsappSetup.savedNotice": "WhatsApp pilot prepared. Status: {status}.",
  "whatsappSetup.title": "WhatsApp connection",
  "whatsappSetup.description":
    "The PlatformaCRM support team prepares the connection. The owner sees only status and clear actions.",
  "whatsappSetup.supportTitle": "Safe support-assisted setup",
  "whatsappSetup.supportText":
    "We verify the number, message flow, and enable the channel without exposing technical keys in the workspace.",
  "whatsappSetup.preparePilot": "Prepare pilot",
  "whatsappSetup.modePilot": "Pilot mode",
  "whatsappSetup.modeDisabled": "Disabled",
  "whatsappSetup.saveConnection": "Save connection",
  "whatsappSetup.checkStatus": "Check status",
  "whatsappSetup.channelStatus": "Channel status",
  "whatsappSetup.protection": "Protection",
  "whatsappSetup.configured": "configured",
  "whatsappSetup.supportManaged": "managed by support",
  "whatsappSetup.lastEvent": "Last event",
  "whatsappSetup.none": "none",
  "whatsappSetup.testHistory": "Message history",
  "whatsappSetup.emptyHistory":
    "History is empty. First inbound and outbound messages will appear here.",
  "whatsappSetup.noChannel":
    "WhatsApp is not added yet. Request it in Integrations or contact PlatformaCRM support.",
  "integrations.guide.importTitle": "Import your base",
  "integrations.guide.importText":
    "Start with clients, leads, sales or catalog through Excel/CSV.",
  "integrations.guide.openImport": "Open import",
  "integrations.guide.startImport": "Start with import",
  "integrations.guide.channelsTitle": "Enable inbound channels",
  "integrations.guide.channelsText":
    "Website chat and Telegram send first requests straight to the inbox.",
  "integrations.guide.checkChannels": "Check channels",
  "integrations.guide.connectChannel": "Connect channel",
  "integrations.guide.whatsappTitle": "Request WhatsApp setup",
  "integrations.guide.whatsappText":
    "WhatsApp and Instagram are connected honestly: by request, without a fake auto-connect.",
  "integrations.guide.requestCreated": "Request created",
  "integrations.guide.fillRequest": "Fill request",
  "integrations.guide.demoSyncTitle": "Check demo sync",
  "integrations.guide.demoSyncText":
    "Kaspi, 1C, inventory and marketplaces are safely checked with demo events for now.",
  "integrations.guide.openDataConnectors": "Open data connectors",
  "integrations.guide.eyebrow": "Integration onboarding",
  "integrations.guide.title": "Connect capabilities in order",
  "integrations.guide.description":
    "The owner sees a clear route, not an API catalog: data first, then inbound channels, then requests for external services.",
  "integrations.guide.activeConnections": "Active connections",
  "integrations.group.messages": "Channels",
  "integrations.group.messagesText":
    "Connect the AI agent to the channels where customers write to your company.",
  "integrations.group.data": "Accounting and inventory",
  "integrations.group.dataText":
    "Fact sources for the AI analyst: sales, inventory, catalog and documents.",
  "integrations.group.marketplace": "Marketplaces",
  "integrations.group.marketplaceText":
    "Orders, payments, inventory and pricing risks across external platforms.",
  "integrations.group.system": "System sources",
  "integrations.group.systemText":
    "Additional data import methods and service channels.",
  "integrations.provider.website": "Website",
  "integrations.provider.websiteUse":
    "Website chat and forms go straight to messages and leads.",
  "integrations.provider.telegram": "Telegram",
  "integrations.provider.telegramUse":
    "Customer dialogs and fast manager replies.",
  "integrations.provider.whatsapp": "WhatsApp",
  "integrations.provider.whatsappUse":
    "WhatsApp Business messages in one work window.",
  "integrations.provider.instagram": "Instagram",
  "integrations.provider.instagramUse":
    "Direct requests are routed to managers.",
  "integrations.provider.excelCsv": "Excel / CSV",
  "integrations.provider.excelCsvUse":
    "Fast import of clients, sales and catalog data.",
  "integrations.provider.oneC": "1C",
  "integrations.provider.oneCUse":
    "Sales, invoices, inventory and directories.",
  "integrations.provider.moysklad": "MoySklad",
  "integrations.provider.moyskladUse":
    "Inventory, stock levels and product catalog.",
  "integrations.provider.kaspi": "Kaspi",
  "integrations.provider.kaspiUse": "Orders, payments and business data.",
  "integrations.provider.kaspiPricing": "Kaspi Pricing",
  "integrations.provider.kaspiPricingUse":
    "Pricing agent: competitor monitoring, thresholds and autopilot.",
  "integrations.provider.wildberries": "Wildberries",
  "integrations.provider.wildberriesUse": "Orders, SKU, inventory and returns.",
  "integrations.provider.ozon": "Ozon",
  "integrations.provider.ozonUse":
    "FBS/FBO shipments, inventory and cancellations.",
  "integrations.provider.googleSheets": "Google Sheets",
  "integrations.provider.googleSheetsUse":
    "Recurring spreadsheet import without development work.",
  "integrations.provider.email": "Email",
  "integrations.provider.emailUse":
    "Notifications, inbound email and fallback.",
  "integrations.status.active": "Active",
  "integrations.status.connected": "Connected",
  "integrations.status.draft": "Draft",
  "integrations.status.pendingRequest": "Requested",
  "integrations.status.providerConfiguring": "Configuring",
  "integrations.status.setupRequired": "Setup needed",
  "integrations.status.needsAttention": "Needs attention",
  "integrations.status.syncing": "Syncing",
  "integrations.status.disabled": "Disabled",
  "integrations.status.disconnected": "Disconnected",
  "integrations.status.error": "Error",
  "integrations.status.failed": "Error",
  "integrations.status.expiredCredentials": "Access expired",
  "integrations.status.roadmap": "Planned",
  "integrations.status.soon": "Soon",
  "integrations.status.request": "By request",
  "integrations.status.received": "Received",
  "integrations.status.processed": "Processed",
  "integrations.status.simulated": "Simulation",
  "integrations.status.applied": "Applied",
  "integrations.status.blocked": "Blocked",
  "integrations.status.ignored": "Skipped",
  "integrations.status.succeeded": "Succeeded",
  "integrations.status.running": "Running",
  "integrations.status.queued": "Queued",
  "integrations.status.paused": "Paused",
  "integrations.status.skipped": "Skipped",
  "integrations.status.pending": "Queued",
  "integrations.status.notConnected": "Not connected",
  "integrations.status.notConnectedShort": "Not connected",
  "integrations.import.clients": "Clients",
  "integrations.import.clientsHelp": "Creates real client cards.",
  "integrations.import.leads": "Leads",
  "integrations.import.leadsHelp": "Creates clients and leads.",
  "integrations.import.deals": "Deals",
  "integrations.import.sales": "Sales",
  "integrations.import.salesHelp": "Creates sales events for analytics.",
  "integrations.import.catalog": "Products, services and inventory",
  "integrations.import.catalogShort": "Catalog",
  "integrations.import.catalogHelp":
    "Creates services and catalog or inventory events.",
  "integrations.import.chooseFile": "Choose a CSV or XLSX file.",
  "integrations.import.panelDescription":
    "Upload a file with clients, leads, sales or catalog items. PlatformaCRM checks it first and shows a preview.",
  "integrations.import.eyebrow": "Excel / CSV connector",
  "integrations.import.title": "Import real data",
  "integrations.import.description":
    "Upload CSV/XLSX, check column mapping, preview and row errors, then confirm import. Data stays scoped to the current business.",
  "integrations.import.downloadTemplate": "Download template",
  "integrations.import.template": "Template",
  "integrations.import.checkFile": "Check file",
  "integrations.import.preview": "Preview",
  "integrations.import.noFile": "No file uploaded yet",
  "integrations.import.noFileSelected": "No file selected yet",
  "integrations.import.noFileSelectedText":
    "Upload a file to see the preview and errors.",
  "integrations.import.fileMeta": "{entity} · {rows} rows · {status}",
  "integrations.import.previewPlaceholder":
    "A preview of the first rows will appear here.",
  "integrations.import.confirm": "Confirm import",
  "integrations.import.import": "Import",
  "integrations.import.fixFile": "Fix the file before importing",
  "integrations.import.fixFileShort": "Fix the file",
  "integrations.import.rowError": "Row {row}, {field}: {message}",
  "integrations.import.rowNeedsReview": "Check the data in row {row}.",
  "integrations.import.columnsNeedReview": "Check the required columns in the file.",
  "integrations.import.entity": "Data type",
  "integrations.import.skipColumn": "Do not import",
  "integrations.import.recheckRequired": "Mapping changed. Preview again before importing.",
  "integrations.import.previewSample": "Preview: {shown} of {total} rows",
  "integrations.import.fields.full_name": "Client name",
  "integrations.import.fields.client_name": "Client name",
  "integrations.import.fields.phone": "Phone",
  "integrations.import.fields.email": "Email",
  "integrations.import.fields.service_name": "Service",
  "integrations.import.fields.source": "Source",
  "integrations.import.fields.notes": "Notes",
  "integrations.import.fields.message": "Message",
  "integrations.import.fields.status": "Status",
  "integrations.import.fields.lost_reason": "Loss reason",
  "integrations.import.fields.external_id": "External ID",
  "integrations.import.fields.occurred_at": "Date and time",
  "integrations.import.fields.item_name": "Product or service",
  "integrations.import.fields.quantity": "Quantity",
  "integrations.import.fields.amount": "Amount",
  "integrations.import.fields.title": "Title",
  "integrations.import.fields.currency": "Currency",
  "integrations.import.fields.stage": "Stage",
  "integrations.import.fields.item_type": "Item type",
  "integrations.import.fields.sku": "SKU",
  "integrations.import.fields.name": "Name",
  "integrations.import.fields.description": "Description",
  "integrations.import.fields.duration_minutes": "Duration in minutes",
  "integrations.import.fields.price_from": "Price from",
  "integrations.import.fields.stock_quantity": "Stock quantity",
  "integrations.import.fields.mapping": "Column mapping",
  "integrations.import.validation.amount": "Amount must be a number.",
  "integrations.import.validation.quantity": "Quantity must be a number.",
  "integrations.import.validation.price": "Price must be a number.",
  "integrations.import.validation.stock": "Stock quantity must be a number.",
  "integrations.import.validation.name": "Name is required.",
  "integrations.import.validation.duration": "Duration must be a positive integer.",
  "integrations.import.validation.datetime": "Use ISO datetime, for example 2026-05-22T10:00:00+05:00.",
  "integrations.import.validation.mapping": "Select at least one column mapping.",
  "integrations.import.validation.status": "Invalid lead status.",
  "integrations.import.validation.lostReason": "A lost lead requires a reason.",
  "integrations.import.validation.unexpectedReason": "Loss reason is only allowed for a lost lead.",
  "integrations.import.validation.requiredColumn": "Map the required column.",
  "integrations.import.columnMapping": "Column mapping",
  "integrations.import.noMapping": "No mapping found.",
  "integrations.import.duplicates": "Duplicates",
  "integrations.import.duplicatesFound": "Possible duplicates found",
  "integrations.import.duplicatesDescription":
    "PlatformaCRM will not create a second card when a client is already found by phone or email.",
  "integrations.import.duplicatesCount": "{count} possible duplicates",
  "integrations.import.summaryRows": "Rows",
  "integrations.import.summaryCreated": "Created",
  "integrations.import.summaryUpdated": "Updated",
  "integrations.import.summarySkipped": "Skipped",
  "integrations.import.summaryErrors": "Errors",
  "integrations.import.summaryDuplicates": "Duplicates",
  "integrations.import.summaryImported": "Imported",
  "integrations.import.previewEmpty":
    "Preview will appear after a file is uploaded.",
  "integrations.import.previewAfterCheck":
    "Preview will appear after the file is checked.",
  "integrations.import.history": "Import history",
  "integrations.import.noImports": "No imports yet.",
  "integrations.import.status.uploaded": "Uploaded",
  "integrations.import.status.previewed": "Checked",
  "integrations.import.status.imported": "Imported",
  "integrations.import.status.failed": "Error",
  "integrations.import.status.none": "No data",
  "integrations.website.previewName": "Test visitor",
  "integrations.website.previewMessage":
    "Hello, I want to check available time.",
  "integrations.website.followUpMessage":
    "Please tell me the nearest available slot.",
  "integrations.website.conversationCreated":
    "Test conversation created. Lead #{lead}, client #{client}.",
  "integrations.website.followUpAdded":
    "Follow-up message added to the same inbox conversation.",
  "integrations.website.snippetCopied": "Install code copied.",
  "integrations.website.title": "Website and landing chat",
  "integrations.website.eyebrow": "Website chat",
  "integrations.website.description":
    "The website widget receives a request and creates a client, lead and inbox conversation. Technical keys are hidden: the owner sees only clear setup and message testing.",
  "integrations.website.openInbox": "Open inbox",
  "integrations.website.loading": "Checking website channel...",
  "integrations.website.notConfiguredTitle":
    "Website channel is not created yet",
  "integrations.website.notConfiguredText":
    "Create a website channel in bot settings or through quick start. Then install code copy and test message sending will appear here.",
  "integrations.website.openBots": "Open bots",
  "integrations.website.checkReadiness": "Check readiness",
  "integrations.website.channelStatus": "Website channel: {status}",
  "integrations.website.readyText":
    "The widget is ready. Internal connection code is hidden so integrations do not become a technical panel.",
  "integrations.website.copySnippet": "Copy install code",
  "integrations.website.copyNotice":
    "Install code is copied to the clipboard and does not show the internal key on the CRM screen.",
  "integrations.website.testTitle": "Test website message",
  "integrations.website.testText":
    "Uses the public endpoint without authentication, like a real landing visitor.",
  "integrations.website.name": "Name",
  "integrations.website.phone": "Phone",
  "integrations.website.message": "Message",
  "integrations.website.createDialog": "Create test conversation",
  "integrations.website.followUpTitle": "Message to the same conversation",
  "integrations.website.addMessage": "Add message",
  "integrations.telegram.savedMock":
    "Settings saved. Check completed in safe demo mode: {reason}",
  "integrations.telegram.saved": "Telegram settings saved.",
  "integrations.telegram.testMock":
    "Connection code saved, check completed in safe demo mode.",
  "integrations.telegram.testOk": "Telegram connection checked successfully.",
  "integrations.telegram.testFailed": "Check failed: {reason}",
  "integrations.telegram.unknownError": "unknown error",
  "integrations.telegram.title": "Connect Telegram",
  "integrations.telegram.eyebrow": "Telegram beta connector",
  "integrations.telegram.openInbox": "Open Telegram inbox",
  "integrations.telegram.description":
    "The first external pilot channel: Telegram messages land in the inbox. Setup is handled safely with support, without exposing secret connection data in daily work.",
  "integrations.telegram.ownerGuide": "Owner-friendly setup",
  "integrations.telegram.step1":
    "1. Check the status and make sure the channel exists in PlatformaCRM.",
  "integrations.telegram.step2":
    "2. Hand setup to support if external Telegram is not connected yet.",
  "integrations.telegram.step3":
    "3. Support confirms channel readiness after setup.",
  "integrations.telegram.step4":
    "4. Check the channel and open incoming messages.",
  "integrations.telegram.token": "Connection data",
  "integrations.telegram.tokenSaved": "Shared with support",
  "integrations.telegram.tokenMissing": "Waiting for setup",
  "integrations.telegram.messageIntake": "Message intake",
  "integrations.telegram.intakeConfigured": "Configured inside PlatformaCRM",
  "integrations.telegram.intakePending": "Will be configured after saving",
  "integrations.telegram.webhook": "Channel preparation",
  "integrations.telegram.webhookConfigured": "Channel prepared",
  "integrations.telegram.webhookPending": "Will be prepared after check",
  "integrations.telegram.lastInbound": "Last inbound",
  "integrations.telegram.lastOutbound": "Last outbound",
  "integrations.telegram.noEvents": "No events yet",
  "integrations.telegram.betaNotice":
    "Real Telegram traffic is enabled only after support review, queues and monitoring are ready. For now this connection works safely as a beta foundation.",
  "integrations.telegram.supportSetupTitle": "Support-assisted connection",
  "integrations.telegram.supportSetupText":
    "The owner sees channel status and checks. Secret connection data is not shown after saving and is not needed for daily work.",
  "integrations.telegram.advancedSetup": "Advanced pilot setup",
  "integrations.telegram.advancedSetupHelp":
    "Use this only if support asks for the connection code. PlatformaCRM stores it safely and does not show it again in the interface.",
  "integrations.telegram.botFatherToken": "Telegram connection code",
  "integrations.telegram.tokenReplacePlaceholder":
    "Code is already saved. Enter a new one only to replace it.",
  "integrations.telegram.tokenPlaceholder": "Paste the BotFather code",
  "integrations.telegram.save": "Save",
  "integrations.telegram.testConnection": "Check connection",
  "integrations.telegram.readOnly":
    "Your role can view the status but cannot change the Telegram connection.",
  "integrations.telegram.channelCreated":
    "Channel created. Now paste the bot key.",
  "integrations.telegram.tokenSavedNotice":
    "Key saved. Check the connection and enable incoming messages.",
  "integrations.telegram.connectionChecked": "Connection checked.",
  "integrations.telegram.connectionCheckFailed":
    "Could not check the connection.",
  "integrations.telegram.inboundConnected": "Incoming messages connected.",
  "integrations.telegram.inboundConnectFailed":
    "Could not connect incoming messages.",
  "integrations.telegram.createChannel": "Create Telegram channel",
  "integrations.telegram.inlineDescription":
    "Connect the bot so PlatformaCRM can receive customer messages and send replies on behalf of your company.",
  "integrations.telegram.botKey": "Bot key",
  "integrations.telegram.tokenSavedPrivate":
    "Key is saved privately. Paste a new one only to replace it.",
  "integrations.telegram.tokenInstruction":
    "Paste the key issued by BotFather.",
  "integrations.telegram.tokenInputPlaceholder": "Paste the bot key",
  "integrations.telegram.saveKey": "Save key",
  "integrations.telegram.connectInbound": "Connect incoming",
  "integrations.request.title": "{provider}: connection request",
  "integrations.request.eyebrow": "{provider}: request-assisted setup",
  "integrations.request.whatsappText":
    "We collect data for manual channel review. The real external connection is not enabled automatically.",
  "integrations.request.instagramText":
    "We collect data for a future Meta-ready connection. Instagram password is not needed and is not requested.",
  "integrations.request.companyName": "Company name",
  "integrations.request.whatsappNumber": "WhatsApp number",
  "integrations.request.contactPerson": "Contact person",
  "integrations.request.officialProvider": "Official connection",
  "integrations.request.qrPilot": "QR pilot by support",
  "integrations.request.monthlyMessages": "Expected messages per month",
  "integrations.request.metaAssetsYes": "Meta Business / Facebook Page exists",
  "integrations.request.metaAssetsNo": "No Meta Business yet",
  "integrations.request.notSure": "Not sure yet",
  "integrations.request.facebookPage": "Facebook Page, if any",
  "integrations.request.comment": "Comment",
  "integrations.request.update": "Update request",
  "integrations.request.submit": "Submit request",
  "integrations.request.saved":
    "Request saved. Platform support will see it as a connector request.",
  "integrations.data.kaspiDescription":
    "Read-only visibility: orders, sales and future analytics. No repricing or write-back.",
  "integrations.data.oneCDescription":
    "In pilot, we work through files and the Excel/CSV pipeline. Full sync and accounting are not enabled.",
  "integrations.data.googleSheetsDescription":
    "Request table import for clients, leads and sales. No background sync in pilot.",
  "integrations.data.emailDescription":
    "Request email connection for leads and notifications. Transactional sending is connected separately.",
  "integrations.data.moyskladDescription":
    "Request-ready foundation for inventory and catalog after the pilot.",
  "integrations.data.wildberriesDescription":
    "Marketplace visibility roadmap: sales, SKUs, inventory and returns.",
  "integrations.data.ozonDescription":
    "Marketplace visibility roadmap without write-back or price management.",
  "integrations.data.yandexMarketDescription":
    "Future marketplace connector, currently only an interest request.",
  "integrations.data.requestSaved": "{name}: request saved.",
  "integrations.data.demoImported":
    "Demo import event recorded. This safely checks future sync without an external connection.",
  "integrations.data.title": "Kaspi / 1C / inventory / marketplaces",
  "integrations.data.eyebrow": "Data connectors foundation",
  "integrations.instagram.username": "Instagram username",
  "integrations.instagram.metaAccessReturned":
    "Meta returned Instagram access. Complete the connection.",
  "integrations.instagram.channelCreated":
    "Channel created. Now connect Instagram through Meta.",
  "integrations.instagram.accessSaved":
    "Instagram access saved privately. Now check the connection.",
  "integrations.instagram.metaOpenFailed":
    "Could not open Meta connection. Contact PlatformaCRM support.",
  "integrations.instagram.connectedNotice": "Instagram connected.",
  "integrations.instagram.connectionChecked": "Instagram connection checked.",
  "integrations.instagram.connectionCheckFailed":
    "Instagram access did not pass the check.",
  "integrations.instagram.finishConnection": "Complete connection",
  "integrations.instagram.createChannel": "Create Instagram channel",
  "integrations.instagram.inlineDescription":
    "Connect Instagram Direct through Meta so PlatformaCRM can receive messages and route dialogs to managers.",
  "integrations.instagram.accountId": "Instagram account ID",
  "integrations.instagram.idSaved": "ID already saved",
  "integrations.instagram.facebookPageId": "Facebook Page ID",
  "integrations.instagram.updateAccess": "Update access",
  "integrations.instagram.saveAccess": "Save access",
  "integrations.instagram.metaConnection": "Meta connection",
  "integrations.instagram.metaDescription":
    "Sign in to Meta and choose the page linked to Instagram Business.",
  "integrations.instagram.connectWithMeta": "Connect through Meta",
  "integrations.instagram.metaConfirmed":
    "Meta confirmed access. Complete the connection.",
  "integrations.instagram.completeConnection": "Complete connection",
  "integrations.whatsapp.metaDataReturned":
    "Meta returned connection data. Check the fields and complete the connection.",
  "integrations.whatsapp.channelCreated":
    "Channel created. Now connect WhatsApp through Meta.",
  "integrations.whatsapp.accessSaved":
    "WhatsApp access saved privately. Now check the connection.",
  "integrations.whatsapp.connectionChecked": "WhatsApp connection checked.",
  "integrations.whatsapp.connectionCheckFailed":
    "WhatsApp access did not pass the check.",
  "integrations.whatsapp.metaOpenFailed":
    "Could not open Meta connection. Contact PlatformaCRM support.",
  "integrations.whatsapp.metaAccessDenied":
    "Meta did not confirm access. Try connecting WhatsApp again.",
  "integrations.whatsapp.metaConfirmed":
    "Meta confirmed access. Complete the connection.",
  "integrations.whatsapp.metaFallbackOpened":
    "A fallback Meta connection window opened. Finish signing in and return to PlatformaCRM.",
  "integrations.whatsapp.connectedNotice": "WhatsApp connected.",
  "integrations.whatsapp.finishConnection": "Complete connection",
  "integrations.whatsapp.createChannel": "Create WhatsApp channel",
  "integrations.ycloud.connection": "Connection via YCloud",
  "integrations.ycloud.connect": "Connect via YCloud",
  "integrations.ycloud.setupRequired": "Platform setup is required",
  "integrations.ycloud.pending": "Waiting for connection confirmation",
  "integrations.ycloud.expired": "Connection link expired",
  "integrations.ycloud.requestFailed": "Could not complete the request. Check your access and try again.",
  "integrations.ycloud.needsAttention": "Connection needs attention. Retry processing or contact an administrator.",
  "integrations.ycloud.openSignup": "Continue connection",
  "integrations.ycloud.otherMethod": "Another connection method",
  "integrations.whatsapp.inlineDescription":
    "Confirm Meta access so PlatformaCRM can receive and send messages through WhatsApp Business.",
  "integrations.whatsapp.phoneNumberId": "WhatsApp phone number ID",
  "integrations.whatsapp.phoneNumberIdSaved": "Phone number ID already saved",
  "integrations.whatsapp.businessAccountId": "Business account ID",
  "integrations.whatsapp.customerPhoneNumber": "Customer-facing number",
  "integrations.whatsapp.updateAccess": "Update access",
  "integrations.whatsapp.saveAccess": "Save access",
  "integrations.whatsapp.metaConnection": "Meta connection",
  "integrations.whatsapp.metaDescription":
    "Sign in to Meta and choose your company WhatsApp Business account.",
  "integrations.whatsapp.connectWithMeta": "Connect through Meta",
  "integrations.whatsapp.completeConnection": "Complete connection",
  "integrations.setupMetric.access": "Access",
  "integrations.setupMetric.saved": "Saved",
  "integrations.setupMetric.required": "Required",
  "integrations.setupMetric.mode": "Mode",
  "integrations.setupMetric.readOnly": "Read only",
  "integrations.setupMetric.demoReadOnly": "Demo / read only",
  "integrations.mock.providerDisabledNotice":
    "Provider traffic is disabled here. Checks and imports use demo events only and do not prove a live integration is connected.",
  "integrations.mock.connectionChecked":
    "Checked in demo mode. No live provider request was sent.",
  "integrations.mock.syncLoaded":
    "Demo events loaded: {count}. This does not mean the live provider is connected.",
  "integrations.setupMetric.notYet": "Not yet",
  "integrations.setupAction.enterAccessKey": "Enter access key",
  "integrations.setupAction.accessKeyReplacePlaceholder":
    "Access is already saved. Paste a new key only to replace it.",
  "integrations.setupAction.hideAdvanced": "Hide advanced settings",
  "integrations.setupAction.showAdvanced": "Advanced settings",
  "integrations.setupAction.syncDays": "Load period, days",
  "integrations.setupAction.saveAccess": "Save access",
  "integrations.kaspi.accessSaved":
    "Kaspi connected. Access is saved privately, and orders can be loaded.",
  "integrations.kaspi.connectionChecked": "Kaspi connection checked.",
  "integrations.kaspi.connectionCheckFailed": "Could not check Kaspi access.",
  "integrations.kaspi.ordersLoaded": "Orders loaded: {count} events.",
  "integrations.kaspi.ordersLoadFailed": "Could not load orders.",
  "integrations.kaspi.orders": "Orders",
  "integrations.kaspi.ordersLoadedBefore": "Loaded before",
  "integrations.kaspi.connectionTitle": "Kaspi connection",
  "integrations.kaspi.connectionDescription":
    "Kaspi currently connects through a seller access key. This is a temporary self-service path until official partner authorization is available.",
  "integrations.kaspi.accessKey": "Kaspi access key",
  "integrations.kaspi.accessKeyPlaceholder":
    "Paste the key from the Kaspi seller dashboard",
  "integrations.kaspi.merchantId": "Store ID",
  "integrations.kaspi.orderState.archive": "Archive / completed",
  "integrations.kaspi.orderState.new": "New",
  "integrations.kaspi.orderState.pickup": "Pickup",
  "integrations.kaspi.orderState.signRequired": "Signature required",
  "integrations.kaspi.pageSize": "Order limit per load",
  "integrations.kaspi.connect": "Connect Kaspi",
  "integrations.kaspi.loadOrders": "Load orders",
  "integrations.kaspi.readOnlyNotice":
    "PlatformaCRM only reads orders for analytics. Price changes, order acceptance and cancellations in Kaspi are disabled here.",
  "integrations.moysklad.accessSaved":
    "MoySklad connected. Access is saved privately, and the connection can be checked.",
  "integrations.moysklad.connectionChecked": "MoySklad connection checked.",
  "integrations.moysklad.connectionCheckFailed":
    "Could not check MoySklad access.",
  "integrations.moysklad.dataLoaded": "Data loaded: {count} events.",
  "integrations.moysklad.dataLoadFailed": "Could not load MoySklad data.",
  "integrations.moysklad.inventory": "Inventory",
  "integrations.moysklad.loadedBefore": "Loaded before",
  "integrations.moysklad.connectionTitle": "MoySklad connection",
  "integrations.moysklad.connectionDescription":
    "Enter the MoySklad access key. PlatformaCRM stores it privately and uses it only to load data.",
  "integrations.moysklad.accessKey": "MoySklad access key",
  "integrations.moysklad.accessKeyPlaceholder": "Paste the MoySklad access key",
  "integrations.moysklad.entity.products": "Products",
  "integrations.moysklad.entity.stock": "Inventory",
  "integrations.moysklad.entity.sales": "Sales",
  "integrations.moysklad.entity.clients": "Counterparties",
  "integrations.moysklad.pageSize": "Row limit per load",
  "integrations.moysklad.connect": "Connect MoySklad",
  "integrations.moysklad.loadData": "Load data",
  "integrations.moysklad.readOnlyNotice":
    "PlatformaCRM only reads products, inventory, sales and counterparties. Document, price and inventory changes in MoySklad are disabled.",
  "integrations.ozon.accessSaved":
    "Ozon connected. Access is saved privately, and the connection can be checked.",
  "integrations.ozon.connectionChecked": "Ozon connection checked.",
  "integrations.ozon.connectionCheckFailed": "Could not check Ozon access.",
  "integrations.ozon.dataLoaded": "Ozon data loaded: {count} events.",
  "integrations.ozon.dataLoadFailed": "Could not load Ozon data.",
  "integrations.ozon.data": "Data",
  "integrations.ozon.connectionTitle": "Ozon connection",
  "integrations.ozon.connectionDescription":
    "Enter access details from the Ozon seller dashboard. PlatformaCRM uses them only to read shipments and inventory.",
  "integrations.ozon.enterAccess": "Enter access",
  "integrations.ozon.sellerId": "Ozon seller ID",
  "integrations.ozon.sellerIdReplacePlaceholder":
    "ID is already saved. Enter a new one only to replace it.",
  "integrations.ozon.sellerIdPlaceholder": "ID from the Ozon dashboard",
  "integrations.ozon.accessKey": "Ozon access key",
  "integrations.ozon.accessKeyPlaceholder": "Key from the Ozon dashboard",
  "integrations.ozon.entity.stocks": "Inventory",
  "integrations.ozon.limit": "Record limit per load",
  "integrations.ozon.connect": "Connect Ozon",
  "integrations.ozon.loadData": "Load data",
  "integrations.ozon.readOnlyNotice":
    "PlatformaCRM does not update Ozon prices, inventory, product cards, fulfillment or order cancellations. This connection only loads data for reports.",
  "integrations.wildberries.accessSaved":
    "Wildberries connected. Access is saved privately, and the connection can be checked.",
  "integrations.wildberries.connectionChecked":
    "Wildberries connection checked.",
  "integrations.wildberries.connectionCheckFailed":
    "Could not check Wildberries access.",
  "integrations.wildberries.dataLoaded":
    "Wildberries data loaded: {count} events.",
  "integrations.wildberries.dataLoadFailed": "Could not load Wildberries data.",
  "integrations.wildberries.updateWindow": "WB update",
  "integrations.wildberries.updateWindowValue": "~30 minutes",
  "integrations.wildberries.connectionTitle": "Wildberries connection",
  "integrations.wildberries.connectionDescription":
    "Enter the access key from the Wildberries seller dashboard. PlatformaCRM only reads orders and sales for analytics.",
  "integrations.wildberries.accessKey": "Wildberries access key",
  "integrations.wildberries.accessKeyPlaceholder":
    "Paste the Wildberries access key",
  "integrations.wildberries.entity.orders": "Orders",
  "integrations.wildberries.entity.sales": "Sales",
  "integrations.wildberries.entity.stocks": "Inventory",
  "integrations.wildberries.stocksOptional":
    "Wildberries inventory is optional: the main workflow is orders and sales.",
  "integrations.wildberries.connect": "Connect Wildberries",
  "integrations.wildberries.loadData": "Load data",
  "integrations.wildberries.readOnlyNotice":
    "PlatformaCRM does not change Wildberries prices, product cards, shipments or orders. This connection only loads data for reports.",
  "integrations.kaspiPricing.stoppedNotice":
    "Pricing agent stopped. Price application is blocked.",
  "integrations.kaspiPricing.resumedNotice": "Pricing agent is active again.",
  "integrations.kaspiPricing.productTitle": "Separate PlatformaCRM product for pricing",
  "integrations.kaspiPricing.productDescription":
    "The standard Kaspi connector only reads orders and business data. Kaspi Pricing manages price rules, thresholds, competitor monitoring and autopilot.",
  "integrations.kaspiPricing.openAgent": "Open agent",
  "integrations.kaspiPricing.rules": "Rules",
  "integrations.kaspiPricing.activeRules": "Active",
  "integrations.kaspiPricing.autopilot": "Autopilot",
  "integrations.kaspiPricing.signals": "Signals",
  "integrations.kaspiPricing.agentStopped": "Agent stopped",
  "integrations.kaspiPricing.agentReady": "Agent ready",
  "integrations.kaspiPricing.priceApplyBlocked":
    "Price application is blocked.",
  "integrations.kaspiPricing.emergencyStopDescription":
    "Emergency stop is available separately from the standard Kaspi integration.",
  "integrations.kaspiPricing.resume": "Resume",
  "integrations.kaspiPricing.stopAgent": "Stop agent",
  "integrations.kaspiPricing.latestChange": "Latest change",
  "integrations.kaspiPricing.history": "History",
  "integrations.kaspiPricing.noChanges":
    "No changes yet. Create a rule and calculate a recommendation.",
  "integrations.data.description":
    "A lightweight layer for future integrations: request, status and safe demo import check. No ERP, realtime full sync, write-back, repricing or accounting logic.",
  "integrations.data.commentPlaceholder": "Request comment",
  "integrations.data.status.request": "Available by request",
  "integrations.data.update": "Update",
  "integrations.data.request": "Request",
  "integrations.data.checkDemoImport": "Check demo import",
  "integrations.page.loading": "Loading integrations...",
  "integrations.page.noBusinessTitle": "No business selected",
  "integrations.page.noBusinessDescription":
    "Create a business to connect channels and external services.",
  "integrations.page.title": "Business connections",
  "integrations.page.description":
    "PlatformaCRM pilot connector map: self-service channels, request connections, plan upsell modules and roadmap without dead-end buttons.",
  "integrations.page.safeTokenNotice": "No technical tokens in CRM",
  "integrations.page.includedTitle": "Included",
  "integrations.page.includedText":
    "Can be enabled in pilot without an external provider.",
  "integrations.page.requestTitle": "By request",
  "integrations.page.requestText":
    "We create an interest card but do not promise auto-connect.",
  "integrations.page.roadmapTitle": "Soon / Roadmap",
  "integrations.page.roadmapText": "Shown as future value and upsell.",
  "integrations.page.connectedTitle": "Connected",
  "integrations.page.connectedText":
    "Active connectors for the current business.",
  "integrations.page.searchPlaceholder":
    "Find connector: WhatsApp, Excel, Kaspi...",
  "integrations.page.allStatuses": "All statuses",
  "integrations.page.selfServiceTitle": "Self-service",
  "integrations.page.upgradeTitle": "Higher plan",
  "integrations.page.allGroups": "All areas",
  "integrations.page.reset": "Reset",
  "integrations.page.resultsMeta":
    "Found: {found} of {total}. In pilot, the owner sees what can be connected now, what needs a request and what is a future module.",
  "integrations.page.noResultsTitle": "No connectors found",
  "integrations.page.noResultsDescription":
    "Reset filters or try another search query.",
  "integrations.overview.title": "Connections",
  "integrations.overview.description":
    "Connect external services for data, sales and operations. AI agent communication channels are configured inside the agent card.",
  "integrations.overview.openAnalysis": "Open analysis",
  "integrations.overview.agentChannelsTitle":
    "Communication channels moved to AI agents",
  "integrations.overview.agentChannelsText":
    "WhatsApp, Telegram, Instagram and website chat connect to a specific AI manager. This makes it clear where the agent replies and which channels are enabled.",
  "integrations.overview.openAgentChannels": "Open agent channels",
  "integrations.overview.recommendedTitle": "Recommended integration",
  "integrations.overview.recommendedText":
    "Start with {provider}: it gives PlatformaCRM more request context and reduces manual handling.",
  "integrations.overview.connectNow": "Show connection",
  "integrations.overview.searchPlaceholder":
    "Search: website, Telegram, Kaspi...",
  "integrations.overview.allGroups": "All areas",
  "integrations.overview.status.all": "All statuses",
  "integrations.overview.status.connected": "Connected",
  "integrations.overview.status.setup": "Setup needed",
  "integrations.overview.status.request": "By request",
  "integrations.overview.status.planned": "Planned",
  "integrations.overview.status.error": "Needs attention",
  "integrations.overview.emptyTitle": "Nothing found",
  "integrations.overview.emptyText": "Reset filters or try another query.",
  "integrations.overview.guideTitle": "Connection order",
  "integrations.overview.guideMeta":
    "{connected} connected · {setup} need setup",
  "integrations.overview.guideStep1":
    "1. Configure communication channels in AI agents, where it is clear which agent replies to customers.",
  "integrations.overview.guideStep2":
    "2. Add Excel/CSV, inventory or marketplaces so analytics can see sales and stock.",
  "integrations.overview.guideStep3":
    "3. Keep this page focused on services that provide business data or support operations.",
  "integrations.overview.simpleTitle": "No overload",
  "integrations.overview.simpleText":
    "Each card shows a clear status and one main action. Manual keys and extra fields open only inside the setup for that service.",
  "integrations.availability.included": "Included",
  "integrations.availability.upgrade": "Higher plan",
  "integrations.availability.request": "By request",
  "integrations.availability.soon": "Soon",
  "integrations.availability.roadmap": "Roadmap",
  "integrations.setupState.active": "Can be enabled now",
  "integrations.setupState.setup_required": "Setup required",
  "integrations.setupState.request_required": "Connected by request",
  "integrations.setupState.coming_soon": "Preparing",
  "integrations.setupState.roadmap": "On roadmap",
  "integrations.merchantStatus.available": "Ready to connect",
  "integrations.merchantStatus.connected": "Connected",
  "integrations.merchantStatus.setup_required": "Needs setup",
  "integrations.merchantStatus.pending_request": "Connecting by request",
  "integrations.merchantStatus.coming_soon": "Soon",
  "integrations.merchantStatus.unavailable_on_plan":
    "Unavailable on current plan",
  "integrations.merchantStatus.error": "Connection error",
  "integrations.merchantStatus.disconnected": "Disconnected",
  "integrations.connectorHint.selfService":
    "Can be enabled in pilot without an external provider. This is a safe self-service connector.",
  "integrations.connectorHint.request":
    "The button creates a connection request inside PlatformaCRM. The real connection is handled manually by the PlatformaCRM team.",
  "integrations.connectorHint.upgrade":
    "Available on {plan} plan or higher. We show an honest upsell without a broken button.",
  "integrations.connectorHint.roadmap":
    "Shown as a future capability without promising a production-ready connection.",
  "integrations.capability.communications": "Communications",
  "integrations.capability.sales": "Sales",
  "integrations.capability.calendar": "Calendar",
  "integrations.capability.finance": "Finance",
  "integrations.capability.inventory": "Inventory",
  "integrations.capability.marketing": "Marketing",
  "integrations.capability.custom": "Custom",
  "integrations.group.messaging.eyebrow": "Messages",
  "integrations.group.messaging.title": "Communication channels",
  "integrations.group.messaging.text":
    "WhatsApp, Telegram, Instagram and other inbound channels for leads and conversations.",
  "integrations.group.imports.eyebrow": "Import",
  "integrations.group.imports.title": "Files and tables",
  "integrations.group.imports.text":
    "Excel, CSV and spreadsheets for quickly moving clients, sales and catalog data.",
  "integrations.group.sales.eyebrow": "Sales",
  "integrations.group.sales.title": "Marketplaces and sales",
  "integrations.group.sales.text":
    "Read-only visibility for orders, sales and events without replacing external systems.",
  "integrations.group.website.eyebrow": "Website",
  "integrations.group.website.title": "Website and widgets",
  "integrations.group.website.text":
    "Widget, forms and website requests inside one PlatformaCRM cabinet.",
  "integrations.group.accounting.eyebrow": "Accounting",
  "integrations.group.accounting.title": "Finance, stock and accounting",
  "integrations.group.accounting.text":
    "Lightweight visibility from 1C, MoySklad and inventory sources.",
  "integrations.bots.eyebrow": "Reply automation",
  "integrations.bots.title": "PlatformaCRM chatbots",
  "integrations.bots.description":
    "Channels receive messages and leads. PlatformaCRM chatbots help answer frequent questions, collect requests and hand conversations to managers.",
  "integrations.bots.safeNotice":
    "No API keys, webhooks or technical settings for merchants",
  "integrations.bots.cardTitle": "PlatformaCRM {channel} bot",
  "integrations.bots.whatsappText":
    "Automatically replies to clients, accepts requests and hands WhatsApp conversations to managers.",
  "integrations.bots.telegramText":
    "Accepts Telegram requests, collects contact details and helps a manager join faster.",
  "integrations.bots.instagramText":
    "Prepares Instagram requests for processing: quick replies, lead capture and manager handoff.",
  "integrations.bots.state.needs_channel": "Connect the channel first",
  "integrations.bots.state.setup_required": "Setup required",
  "integrations.bots.state.active": "Bot active",
  "integrations.bots.state.needs_attention": "Action required",
  "integrations.bots.settingsTitle": "Simple settings",
  "integrations.bots.settings.greeting": "Greeting",
  "integrations.bots.settings.handoff": "Manager handoff",
  "integrations.bots.settings.workingHours": "Working hours",
  "integrations.bots.settings.faq": "Frequent questions",
  "integrations.bots.settings.knowledge": "Business knowledge base",
  "integrations.bots.connectChannel": "Connect channel",
  "integrations.bots.configure": "Configure bot",
  "integrations.bots.openScenarios": "Scenarios",
  "integrations.action.reconnect": "Enable again",
  "integrations.action.connected": "Connected",
  "integrations.action.requestSent": "Request sent",
  "integrations.action.continueSetup": "Continue setup",
  "integrations.action.create": "Create connection",
  "integrations.action.disconnect": "Disconnect",
  "integrations.setupMessage.connected":
    "The channel is active. New requests and events will go to Inbox, CRM, analytics and automations.",
  "integrations.setupMessage.needsAttention":
    "Connection was created and is waiting for setup or manual review by the PlatformaCRM team.",
  "integrations.setupMessage.disabled":
    "The channel is disabled. It can be restored after setup or support request.",
  "integrations.card.businessValue": "Business value",
  "integrations.card.plan": "Plan",
  "integrations.card.connection": "Connection",
  "integrations.card.ownerAction": "Owner next step",
  "integrations.card.requestNotice":
    "Clicking creates a connection request. It does not enable the external service automatically.",
  "integrations.card.roadmapNotice":
    "The button is intentionally disabled: this connector is shown as a future capability or plan upsell without a false ready-connection promise.",
  "integrations.card.pendingNotice":
    "Connection was created but still needs setup or review. For request connectors this is a normal pilot status.",
  "integrations.card.connectedNotice":
    "Connection is active. Data from this channel is used in CRM, Inbox, analytics and automations.",
  "integrations.card.readOnly":
    "Your role can view integrations but cannot manage connections.",
  "integrations.card.credentialsExpired":
    "Access is not connected or has expired.",
  "integrations.card.latestRun": "Latest sync",
  "integrations.card.noRuns": "No sync runs yet.",
  "integrations.card.retryRun": "Retry",
  "integrations.card.kaspiPricingSeparateSetup":
    "Kaspi Pricing opens in a separate setup window.",
  "integrations.card.kaspiPricingNoGenericConfig":
    "Kaspi Pricing does not use the generic connector setup.",
  "integrations.card.connectionSaved": "Connection details saved.",
  "integrations.card.configure": "Configure",
  "integrations.card.connect": "Connect",
  "integrations.card.disableChannel": "{title}: disable",
  "integrations.card.enableChannel": "{title}: enable",
  "integrations.card.websiteFlipTitle":
    "Do not lose website leads after the first click.",
  "integrations.card.websiteFlipText":
    "PlatformaCRM receives form requests and sends them straight to messages.",
  "integrations.card.websiteFlow": "Website → Messages → Leads",
  "integrations.card.connectionTitle": "Connection: {title}",
  "integrations.card.websiteNoExtraData":
    "Website chat connects through the channel key. No additional data is required.",
  "integrations.card.accountId": "Account ID",
  "integrations.card.accountIdPlaceholder": "Account, store or dashboard ID",
  "integrations.card.accessKey": "Access key",
  "integrations.card.accessKeyPlaceholder": "Paste the access key",
  "integrations.card.accessKeyReplacePlaceholder":
    "Key is already saved. Paste a new one only to replace it.",
  "integrations.card.webhookSecret": "Verification key",
  "integrations.card.simpleSetupTitle": "Simple setup path",
  "integrations.card.simpleSetupText":
    "Create a request or check the connection status here. Account IDs, keys and webhook values stay in the support/admin fallback.",
  "integrations.card.manualSupportSetup": "Manual support setup",
  "integrations.error.actionRequired":
    "Connection needs attention. Check the setup status or ask the business owner to reconnect it.",
  "integrations.error.webhookSetup":
    "Inbound messages are not ready yet. Ask the owner or PlatformaCRM support to finish the webhook/setup check.",
  "integrations.error.permission":
    "Your role can view this connection but cannot change its setup.",
  "integrations.error.rateLimit":
    "The provider is temporarily limiting requests. Try again later or ask support to review the connection.",
  "integrations.error.providerUnavailable":
    "The provider did not respond. Try the check again later; no CRM data was changed.",
  "integrations.error.supportReview":
    "This connection needs support review before it can be enabled for daily work.",
  "integrations.card.check": "Check",
  "integrations.card.requestConnection": "Request connection",
  "integrations.setup.needHelp": "Need help connecting?",
  "integrations.setup.hideManualSetup": "Hide manual setup",
  "integrations.setup.openMessages": "Open messages",
  "integrations.setup.channelEnabled": "Channel enabled",
  "integrations.setup.toggleChannel": "Enable or disable {title}",
  "integrations.page.merchantDescription": "Connect channels and external services, check their status and recover data exchange.",
  "integrations.page.merchantRequestText": "This connection requires a request and provider confirmation.",
  "integrations.page.merchantResultsMeta": "Found: {found} of {total}.",
  "integrations.page.attentionTitle": "Needs attention",
  "integrations.page.attentionText": "Connections with an error or incomplete setup.",
  "integrations.card.configureContext": "Configure {title}",
  "integrations.card.connectContext": "Connect {title}",
};
