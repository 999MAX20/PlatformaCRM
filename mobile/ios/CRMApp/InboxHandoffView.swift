import SwiftUI
import CRMCore

struct InboxHandoffRoute<Content:View>:View {
    @ObservedObject var model:InboxHandoffViewModel
    let isCurrent:@MainActor ()->Bool
    let content:Content
    init(model:InboxHandoffViewModel,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content:()->Content) {self.model=model;self.isCurrent=isCurrent;self.content=content()}
    var body:some View {
        let selection=model.session.selection,returned=model.returnControl
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && model.session.selection==selection},set:{if !$0 && isCurrent() {model.close(expected:returned)}})) {
            if let selection,isCurrent(),model.session.selection==selection {InboxHandoffView(model:model,selection:selection,isCurrent:isCurrent)}
        }
    }
}
struct InboxHandoffView:View {
    @ObservedObject var model:InboxHandoffViewModel
    let selection:ReplyDraftSelection
    let isCurrent:@MainActor ()->Bool
    @FocusState private var focused:Bool
    var body:some View {
        let control=model.control,input=model.inputControl,returned=model.returnControl,question=model.clearConfirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection==selection {
                    Section {Text(AppCopy.text("handoffLocalOnly"));Text(AppCopy.text("handoffNoReturnProof")).font(.caption)}
                    if model.blocked {
                        if let record=model.record {
                            Section(AppCopy.text("handoffTestResult")) {
                                Text(record.attempt.review.value.reason.isEmpty ? AppCopy.text("handoffBlankReason"):record.attempt.review.value.reason).textSelection(.enabled)
                                Text(AppCopy.text(phase(record.phase))).accessibilityAddTraits(.updatesFrequently)
                                if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("handoffTestAction")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")))}
                            }
                        } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                    } else if model.session.phase == .review,let review=model.session.review {
                        Section(AppCopy.text("clientDraftReview")) {Text(review.value.reason.isEmpty ? AppCopy.text("handoffBlankReason"):review.value.reason).textSelection(.enabled)}
                        if model.canSubmit {Button(AppCopy.text("handoffTestSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                    } else {
                        TextField(AppCopy.text("handoffReason"),text:Binding(get:{model.session.raw},set:{if isCurrent() {model.update($0,input:input)}}),axis:.vertical).lineLimit(3...12).focused($focused).accessibilityHint(model.session.inputError ? AppCopy.text("handoffReasonIssue") : "")
                        Text(AppCopy.text("handoffReasonOptional")).font(.caption)
                        if model.session.inputError {Text(AppCopy.text("handoffReasonIssue")).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
                        Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control);focused=model.session.inputError}}
                    }
                    if !model.blocked {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("handoffTestAction")+": "+AppCopy.text("clientDraftClear")))}
                }
            }.navigationTitle(AppCopy.text("handoffTestAction"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:returned)}}.accessibilityLabel(Text(AppCopy.text("handoffTestAction")+": "+AppCopy.text("back")))}}
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {VStack(spacing:20) {Text(AppCopy.text("clientDraftClearQuestion")).font(.headline);Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("handoffTestAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")));Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}.accessibilityLabel(Text(AppCopy.text("handoffTestAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftCancel")))}.padding()}
                }
        }
    }
    private func phase(_ p:HandoffPhase)->String {switch p {case .pending:"taskCommentFakePending";case .confirmed:"handoffTestConfirmed";case .rejected:"handoffTestRejected";case .unknown:"handoffTestUnknown"}}
}
