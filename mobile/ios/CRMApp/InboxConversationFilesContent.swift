import SwiftUI
import CRMCore

struct InboxConversationFilesObservedContent<Content:View>:View {
    @ObservedObject var files:InboxConversationFilesViewModel
    let content:()->Content
    init(files:InboxConversationFilesViewModel,@ViewBuilder content:@escaping ()->Content) {self.files=files;self.content=content}
    var body:some View {let _=files.control;return content()}
}
struct InboxConversationFilesRoute<Content:View>:View {
    @ObservedObject var parent:InboxViewModel
    let isCurrent:@MainActor ()->Bool
    let content:Content
    init(parent:InboxViewModel,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content:()->Content) {self.parent=parent;self.isCurrent=isCurrent;self.content=content()}
    var body:some View {
        let presentation=parent.filesPresentationControl
        content.navigationDestination(isPresented:Binding(get:{isCurrent() && parent.matchesFiles(presentation)},set:{if !$0,isCurrent() {parent.closeFiles(expected:presentation)}})) {
            if let files=parent.fileMetadata {InboxConversationFilesContent(model:files,isCurrent:{isCurrent() && parent.matchesFiles(presentation)},close:{if isCurrent() {parent.closeFiles(expected:presentation)}})}
        }
    }
}
struct InboxConversationFilesContent:View {
    @ObservedObject var model:InboxConversationFilesViewModel
    let isCurrent:@MainActor ()->Bool
    let close:@MainActor ()->Void
    private func name(_ row:InboxConversationFileMetadata)->String {(row.originalName.isEmpty ? AppCopy.text("notAvailable"):row.originalName)+" · #\(row.id)"}
    @ViewBuilder private func assignmentSection(_ control:InboxConversationFilesControl?)->some View {
        Section(AppCopy.text("inboxSelfTitle")) {
            Text(AppCopy.text("inboxSelfBoundary")).font(.caption)
            if model.assignmentLoading {ProgressView(AppCopy.text("loading"))}
            if let error=model.assignmentFailure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
            if let record=model.assignmentRecord {
                Text(AppCopy.text(record.phase == .pending ? "inboxSelfPending":record.phase == .response ? "inboxSelfResponse":record.phase == .rejected ? "inboxSelfRejected":"inboxSelfUnknown")).accessibilityAddTraits(.updatesFrequently)
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(record.attempt.review.authorization.actor))
                LabeledContent(AppCopy.text("inboxSelfPrevious"),value:record.attempt.review.source.assignedTo.map(String.init) ?? AppCopy.text("notAvailable"))
                if let result=record.result {LabeledContent(AppCopy.text("inboxSelfObservedAt"),value:result.source.updatedAt)}
                if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxSelfAcknowledge")) {if isCurrent() {model.acknowledgeAssignment(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxSelfTitle")+": "+AppCopy.text("inboxSelfAcknowledge")))}
            } else if model.assignmentBlocked {Text(AppCopy.text("inboxSelfRetained"))}
            else if let review=model.assignmentReview {
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(review.authorization.actor))
                LabeledContent(AppCopy.text("inboxSelfPrevious"),value:review.source.assignedTo.map(String.init) ?? AppCopy.text("notAvailable"))
                Button(AppCopy.text("inboxSelfSubmit")) {Task {if isCurrent() {await model.submitAssignment(review,expected:control)}}}.disabled(!model.canSubmitAssignment)
                Button(AppCopy.text("back")) {if isCurrent() {model.backAssignment(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxSelfTitle")+": "+AppCopy.text("back")))
            } else if model.canPrepareAssignment {Button(AppCopy.text("inboxSelfReview")) {if isCurrent() {model.prepareAssignment(expected:control)}}}
            if model.canLoadAssignment {Button(AppCopy.text("inboxSelfLoad")) {Task {if isCurrent() {await model.loadAssignment(expected:control)}}}}
        }
    }
    @ViewBuilder private func markerSection(_ control:InboxConversationFilesControl?)->some View {
        Section(AppCopy.text("inboxMarkerTitle")) {
            Text(AppCopy.text("inboxMarkerBoundary")).font(.caption)
            if model.markerLoading {ProgressView(AppCopy.text("loading"))}
            if let error=model.markerFailure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
            if let record=model.markerRecord {
                Text(AppCopy.text(record.attempt.review.action == .read ? "inboxMarkerActionRead":"inboxMarkerActionUnread"))
                Text(AppCopy.text(record.phase == .pending ? "inboxMarkerPending":record.phase == .response ? "inboxMarkerResponse":record.phase == .rejected ? "inboxMarkerRejected":"inboxMarkerUnknown")).accessibilityAddTraits(.updatesFrequently)
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(record.attempt.review.authorization.actor))
                LabeledContent(AppCopy.text("inboxMarkerOriginalCount"),value:String(record.attempt.review.source.unreadCount))
                if let result=record.result {LabeledContent(AppCopy.text("inboxMarkerResponseCount"),value:String(result.source.unreadCount));LabeledContent(AppCopy.text("inboxSelfObservedAt"),value:result.source.updatedAt)}
                if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxMarkerAcknowledge")) {if isCurrent() {model.acknowledgeMarker(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxMarkerTitle")+": "+AppCopy.text("inboxMarkerAcknowledge")))}
            } else if model.markerBlocked {Text(AppCopy.text("inboxMarkerRetained"))}
            else if let review=model.markerReview {
                Text(AppCopy.text(review.action == .read ? "inboxMarkerActionRead":"inboxMarkerActionUnread"))
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(review.authorization.actor))
                LabeledContent(AppCopy.text("inboxMarkerOriginalCount"),value:String(review.source.unreadCount))
                Button(AppCopy.text("inboxMarkerSubmit")) {Task {if isCurrent() {await model.submitMarker(review,expected:control)}}}.disabled(!model.canSubmitMarker)
                Button(AppCopy.text("back")) {if isCurrent() {model.backMarker(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxMarkerTitle")+": "+AppCopy.text("back")))
            } else if model.canPrepareMarker {
                Button(AppCopy.text("inboxMarkerReviewRead")) {if isCurrent() {model.prepareMarker(action:.read,expected:control)}}
                Button(AppCopy.text("inboxMarkerReviewUnread")) {if isCurrent() {model.prepareMarker(action:.unread,expected:control)}}
            }
            if model.canLoadMarker {Button(AppCopy.text("inboxMarkerLoad")) {Task {if isCurrent() {await model.loadMarker(expected:control)}}}}
        }
    }
    @ViewBuilder private func prioritySection(_ control:InboxConversationFilesControl?)->some View {
        Section(AppCopy.text("inboxPriorityTitle")) {
            Text(AppCopy.text("inboxPriorityBoundary")).font(.caption)
            if model.priorityLoading {ProgressView(AppCopy.text("loading"))}
            if let error=model.priorityFailure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
            if let record=model.priorityRecord {
                Text(AppCopy.text(record.phase == .pending ? "inboxPriorityPending":record.phase == .response ? "inboxPriorityResponse":record.phase == .rejected ? "inboxPriorityRejected":"inboxPriorityUnknown")).accessibilityAddTraits(.updatesFrequently)
                LabeledContent(AppCopy.text("inboxPriorityOriginal"),value:record.attempt.review.source.priority)
                LabeledContent(AppCopy.text("inboxPriorityChosen"),value:AppCopy.text("inboxPriorityValue_"+record.attempt.review.value.rawValue))
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(record.attempt.review.authorization.actor))
                if let result=record.result {LabeledContent(AppCopy.text("inboxSelfObservedAt"),value:result.source.updatedAt)}
                if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxPriorityAcknowledge")) {if isCurrent() {model.acknowledgePriority(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxPriorityTitle")+": "+AppCopy.text("inboxPriorityAcknowledge")))}
            } else if model.priorityBlocked {Text(AppCopy.text("inboxPriorityRetained"))}
            else if let review=model.priorityReview {
                LabeledContent(AppCopy.text("inboxPriorityOriginal"),value:review.source.priority)
                LabeledContent(AppCopy.text("inboxPriorityChosen"),value:AppCopy.text("inboxPriorityValue_"+review.value.rawValue))
                Button(AppCopy.text("inboxPrioritySubmit")) {Task {if isCurrent() {await model.submitPriority(review,expected:control)}}}.disabled(!model.canSubmitPriority)
                Button(AppCopy.text("back")) {if isCurrent() {model.backPriority(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxPriorityTitle")+": "+AppCopy.text("back")))
            } else {
                if let source=model.prioritySource {LabeledContent(AppCopy.text("inboxPriorityOriginal"),value:source.priority)}
                if let choice=model.selectedPriorityValue {LabeledContent(AppCopy.text("inboxPriorityChosen"),value:AppCopy.text("inboxPriorityValue_"+choice.rawValue))}
                if model.canChoosePriority {
                    ForEach(InboxPriorityValue.allCases,id:\.rawValue) {value in Button(AppCopy.text("inboxPriorityValue_"+value.rawValue)) {if isCurrent() {model.choosePriority(value,expected:control)}}}
                    if model.selectedPriorityValue != nil {Button(AppCopy.text("inboxPriorityClear")) {if isCurrent() {model.clearPriorityChoice(expected:control)}}}
                }
                if model.canPreparePriority {Button(AppCopy.text("inboxPriorityReview")) {if isCurrent() {model.preparePriority(expected:control)}}}
            }
            if model.canLoadPriority {Button(AppCopy.text("inboxPriorityLoad")) {Task {if isCurrent() {await model.loadPriority(expected:control)}}}}
        }
    }
    @ViewBuilder private func lifecycleSection(_ control:InboxConversationFilesControl?)->some View {
        Section(AppCopy.text("inboxLifecycleTitle")) {
            Text(AppCopy.text("inboxLifecycleBoundary")).font(.caption)
            if model.lifecycleLoading {ProgressView(AppCopy.text("loading"))}
            if let error=model.lifecycleFailure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
            if let record=model.lifecycleRecord {
                Text(AppCopy.text(record.attempt.review.action == .close ? "inboxLifecycleActionClose":"inboxLifecycleActionReopen"))
                Text(AppCopy.text(record.phase == .pending ? "inboxLifecyclePending":record.phase == .response ? "inboxLifecycleResponse":record.phase == .rejected ? "inboxLifecycleRejected":"inboxLifecycleUnknown")).accessibilityAddTraits(.updatesFrequently)
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(record.attempt.review.authorization.actor))
                LabeledContent(AppCopy.text("inboxLifecycleOriginalStatus"),value:String(record.attempt.review.source.status))
                if let result=record.result {Text(AppCopy.text("inboxLifecycleFlags")+" · "+AppCopy.text(result.source.botEnabled ? "inboxLifecycleYes":"inboxLifecycleNo")+" / "+AppCopy.text(result.source.handoffRequired ? "inboxLifecycleYes":"inboxLifecycleNo"));LabeledContent(AppCopy.text("inboxLifecycleResponseStatus"),value:String(result.source.status));LabeledContent(AppCopy.text("inboxSelfObservedAt"),value:result.source.updatedAt)}
                if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxLifecycleAcknowledge")) {if isCurrent() {model.acknowledgeLifecycle(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLifecycleTitle")+": "+AppCopy.text("inboxLifecycleAcknowledge")))}
            } else if model.lifecycleBlocked {Text(AppCopy.text("inboxLifecycleRetained"))}
            else if let review=model.lifecycleReview {
                Text(AppCopy.text(review.action == .close ? "inboxLifecycleActionClose":"inboxLifecycleActionReopen"))
                LabeledContent(AppCopy.text("inboxSelfActor"),value:String(review.authorization.actor))
                Text(AppCopy.text("inboxLifecycleFlags")+" · "+AppCopy.text(review.source.botEnabled ? "inboxLifecycleYes":"inboxLifecycleNo")+" / "+AppCopy.text(review.source.handoffRequired ? "inboxLifecycleYes":"inboxLifecycleNo"))
                LabeledContent(AppCopy.text("inboxLifecycleOriginalStatus"),value:String(review.source.status))
                Button(AppCopy.text("inboxLifecycleSubmit")) {Task {if isCurrent() {await model.submitLifecycle(review,expected:control)}}}.disabled(!model.canSubmitLifecycle)
                Button(AppCopy.text("back")) {if isCurrent() {model.backLifecycle(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLifecycleTitle")+": "+AppCopy.text("back")))
            } else if model.canPrepareLifecycle {
                Button(AppCopy.text("inboxLifecycleReviewClose")) {if isCurrent() {model.prepareLifecycle(action:.close,expected:control)}}
                Button(AppCopy.text("inboxLifecycleReviewReopen")) {if isCurrent() {model.prepareLifecycle(action:.reopen,expected:control)}}
            }
            if model.canLoadLifecycle {Button(AppCopy.text("inboxLifecycleLoad")) {Task {if isCurrent() {await model.loadLifecycle(expected:control)}}}}
        }
    }
    var body:some View {
        let control=model.control
        let fileScope=AppCopy.text("inboxFilesTitle"),detailScope=AppCopy.text("inboxFilesTitle")+": "+AppCopy.text("details")
        List {
            if isCurrent(),model.presented {
                Section {
                    Text(AppCopy.text("fixtureMode")).font(.caption)
                    Text(AppCopy.text("fileMetadataWindow")).font(.caption)
                    Text(AppCopy.text("fileVerificationUnknown"))
                }
                if model.selected==nil {assignmentSection(control);markerSection(control);prioritySection(control);lifecycleSection(control);if let link=model.linkClient {InboxLinkClientContent(model:link,isCurrent:isCurrent)};if let leads=model.leadReference {LeadReferenceContent(model:leads,isCurrent:isCurrent)};if let link=model.linkLead {InboxLinkLeadContent(model:link,isCurrent:isCurrent)};if let deal=model.dealReference {DealReferenceContent(model:deal,isCurrent:isCurrent)};if let link=model.linkDeal {InboxLinkDealContent(model:link,isCurrent:isCurrent)};if let member=model.memberReference {MemberReferenceContent(model:member,isCurrent:isCurrent)};if let target=model.targetAssignment {InboxTargetAssignmentContent(model:target,isCurrent:isCurrent)};if let source=model.taskSource {InboxTaskSourceContent(model:source,isCurrent:isCurrent)};if let create=model.createTask {InboxCreateTaskContent(model:create,isCurrent:isCurrent)};if let existing=model.existingClient {InboxExistingClientContent(model:existing,isCurrent:isCurrent)};if let lead=model.existingLead {InboxExistingLeadContent(model:lead,isCurrent:isCurrent)};if let deal=model.existingDeal {InboxExistingDealContent(model:deal,isCurrent:isCurrent)}}
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("loading"))).accessibilityAddTraits(.updatesFrequently)}
                else if let row=model.selected {
                    Section {
                        LabeledContent(AppCopy.text("fileOriginalName"),value:row.originalName)
                        LabeledContent(AppCopy.text("fileContentType"),value:row.contentType.isEmpty ? AppCopy.text("notAvailable"):row.contentType)
                        LabeledContent(AppCopy.text("fileSizeBytes"),value:String(row.size))
                        LabeledContent(AppCopy.text("fileCreatedAt"),value:row.createdAt)
                        Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(detailScope+": "+AppCopy.text("back")))
                    }
                } else {
                    Section {
                        if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(fileScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)}
                        if model.loaded && model.items.isEmpty {Text(AppCopy.text("fileMetadataEmpty")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("fileMetadataEmpty")))}
                        ForEach(model.items) {row in Button(name(row)) {if isCurrent() {model.select(row,expected:control)}}}
                        Button(AppCopy.text(model.failure==nil ? "fileMetadataLoad":"retry")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(fileScope+": "+AppCopy.text(model.failure==nil ? "fileMetadataLoad":"retry")))
                    }
                }
            }
        }.navigationTitle(AppCopy.text("inboxFilesTitle")).toolbar {Button(AppCopy.text("back")) {if isCurrent() {close()}}.accessibilityLabel(Text(fileScope+": "+AppCopy.text("back")))}
    }
}
