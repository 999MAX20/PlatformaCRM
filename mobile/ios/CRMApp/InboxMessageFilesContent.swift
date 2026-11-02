import SwiftUI
import CRMCore

struct InboxMessageFilesObservedContent<Content:View>:View {
    @ObservedObject var files:InboxMessageFilesViewModel
    let content:()->Content
    init(files:InboxMessageFilesViewModel,@ViewBuilder content:@escaping ()->Content) {self.files=files;self.content=content}
    var body:some View {let _=files.control;return content()}
}
struct InboxMessageFilesRoute<Content:View>:View {
    @ObservedObject var parent:InboxViewModel
    let isCurrent:@MainActor ()->Bool
    let content:Content
    init(parent:InboxViewModel,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content:()->Content) {self.parent=parent;self.isCurrent=isCurrent;self.content=content()}
    var body:some View {
        let presentation=parent.messageFilesPresentationControl
        content.navigationDestination(isPresented:Binding(get:{isCurrent() && parent.matchesMessageFiles(presentation)},set:{if !$0,isCurrent() {parent.closeMessageFiles(expected:presentation)}})) {
            if let files=parent.messageMetadata {InboxMessageFilesContent(model:files,isCurrent:{isCurrent() && parent.matchesMessageFiles(presentation)},close:{if isCurrent() {parent.closeMessageFiles(expected:presentation)}})}
        }
    }
}
struct InboxMessageFilesContent:View {
    @ObservedObject var model:InboxMessageFilesViewModel
    let isCurrent:@MainActor ()->Bool
    let close:@MainActor ()->Void
    private func name(_ row:InboxMessageFileMetadata)->String {(row.originalName.isEmpty ? AppCopy.text("notAvailable"):row.originalName)+" · #\(row.id)"}
    private func retryKey(_ phase:InboxRetryPhase)->String {switch phase {case .pending:"inboxRetryPending";case .response:"inboxRetryResponse";case .rejected:"inboxRetryRejected";case .unknown:"inboxRetryUnknown"}}
    private func observed(_ value:InboxObservedText)->String {
        switch value {case .missing:return AppCopy.text("messageObservationMissing");case .null:return AppCopy.text("messageObservationNull");case .value(let raw):return raw.isEmpty ? AppCopy.text("messageObservationEmpty"):raw}
    }
    var body:some View {
        let control=model.control
        let fileScope=AppCopy.text("inboxMessageFilesTitle"),detailScope=AppCopy.text("inboxMessageFilesTitle")+": "+AppCopy.text("details")
        let windowScope=AppCopy.text("inboxMessageReadTitle")
        List {
            if isCurrent(),model.presented {
                Section {
                    Text(AppCopy.text("fixtureMode")).font(.caption)
                    Text(AppCopy.text("fileMetadataWindow")).font(.caption)
                    Text(AppCopy.text("fileVerificationUnknown"))
                    if let context=model.context {Text("#\(context.message)").font(.caption)}
                    if let window=model.window {
                        Text(AppCopy.text("inboxMessageFilesWindow").replacingOccurrences(of:"{loaded}",with:String(window.providedMessages)).replacingOccurrences(of:"{total}",with:String(window.count))).font(.caption)
                        if window.limited {Text(AppCopy.text("partial"))}
                    }
                }
                if let observation=model.window?.observation {
                    Section {
                        LabeledContent(AppCopy.text("messageObservedStatus"),value:AppCopy.text(observation.state.copyKey))
                        LabeledContent(AppCopy.text("messageObservedStatusRaw"),value:observed(observation.status))
                        LabeledContent(AppCopy.text("messageObservedSentAt"),value:observed(observation.sentAt))
                        LabeledContent(AppCopy.text("messageObservedDeliveredAt"),value:observed(observation.deliveredAt))
                        LabeledContent(AppCopy.text("messageObservedReadAt"),value:observed(observation.readAt))
                        Text(AppCopy.text("messageObservationLimits")).font(.caption)
                    }
                }
                if model.retryRecord != nil || model.retryReview != nil || model.retryBlocked || model.canPrepareRetry {Section(AppCopy.text("inboxRetryTitle")) {
                    if let record=model.retryRecord {
                        Text(AppCopy.text("inboxRetryOriginal")+" #\(record.attempt.review.source.context.message)")
                        Text(record.attempt.review.source.text)
                        Text(AppCopy.text(retryKey(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {Text(AppCopy.text("inboxRetryResultMessage")+" #\(result.id)");Text(AppCopy.text("messageStateTitle")+": "+AppCopy.text(InboxMessageState(result.status).copyKey))}
                        if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxRetryAcknowledge")) {if isCurrent() {model.acknowledgeRetry(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxRetryTitle")+": "+AppCopy.text("inboxRetryAcknowledge")))}
                    } else if let review=model.retryReview {
                        Text(AppCopy.text("inboxRetryReview"))
                        Text(AppCopy.text("inboxRetryOriginal")+" #\(review.source.context.message)")
                        Text(review.source.text)
                        Text(AppCopy.text("inboxRetryLimits")).font(.caption)
                        Button(AppCopy.text("inboxRetrySubmit")) {Task {if isCurrent() {await model.submitRetry(review,expected:control)}}}.disabled(!model.canSubmitRetry)
                        Button(AppCopy.text("back")) {if isCurrent() {model.backRetry(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxRetryTitle")+": "+AppCopy.text("back")))
                    } else if model.retryBlocked {Text(AppCopy.text("inboxRetryBlocked"))}
                    else if model.canPrepareRetry {Button(AppCopy.text("inboxRetryPrepare")) {if isCurrent() {model.prepareRetry(expected:control)}}}
                }}
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(windowScope+": "+AppCopy.text("loading"))).accessibilityAddTraits(.updatesFrequently)}
                else if let row=model.selected {
                    Section {
                        LabeledContent(AppCopy.text("fileOriginalName"),value:row.originalName)
                        LabeledContent(AppCopy.text("fileContentType"),value:row.contentType.isEmpty ? AppCopy.text("notAvailable"):row.contentType)
                        LabeledContent(AppCopy.text("fileSizeBytes"),value:String(row.size))
                        LabeledContent(AppCopy.text("fileCreatedAt"),value:row.createdAt)
                        Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(detailScope+": "+AppCopy.text("back")))
                    }
                } else {
                    Section(AppCopy.text("inboxMessageFilesTitle")) {
                        if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(fileScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)}
                        if (model.window != nil) && (model.window?.items ?? []).isEmpty {Text(AppCopy.text("fileMetadataEmpty")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("fileMetadataEmpty")))}
                        ForEach((model.window?.items ?? [])) {row in Button(name(row)) {if isCurrent() {model.select(row,expected:control)}}.disabled(model.retryReview != nil)}
                        Button(AppCopy.text(model.failure==nil ? "fileMetadataLoad":"retry")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(fileScope+": "+AppCopy.text(model.failure==nil ? "fileMetadataLoad":"retry"))).disabled(model.retryReview != nil || model.retryRecord?.phase == .pending)
                    }
                }
            }
        }.navigationTitle(AppCopy.text("inboxMessageReadTitle")).toolbar {Button(AppCopy.text("back")) {if isCurrent() {close()}}.accessibilityLabel(Text(windowScope+": "+AppCopy.text("back")))}
    }
}
