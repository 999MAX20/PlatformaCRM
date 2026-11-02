import SwiftUI
import CRMCore

struct TaskCommentRoute<Content: View>: View {
    @ObservedObject var model: TaskCommentViewModel
    let context: TaskCommentContext?
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: TaskCommentViewModel,context: TaskCommentContext?,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) {self.model=model;self.context=context;self.isCurrent=isCurrent;self.content=content()}
    var body: some View {
        let selection=model.session.selection,returnControl=model.returnControl
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.read.context==context && model.session.selection==selection && model.session.available},set:{if !$0 && isCurrent() {model.close(expected:returnControl)}})) {
            if let selection,selection.read.context==context,model.session.selection==selection,model.session.available,isCurrent() {TaskCommentScreen(model:model,selection:selection,isCurrent:isCurrent)}
        }
    }
}
struct TaskCommentEntry: View {
    @ObservedObject var model: TaskCommentViewModel
    let context: TaskCommentContext
    let isCurrent:@MainActor ()->Bool
    let onOpen: @MainActor (TaskCommentRead) -> Void
    init(model: TaskCommentViewModel,context: TaskCommentContext,isCurrent:@escaping @MainActor ()->Bool,onOpen: (@MainActor (TaskCommentRead)->Void)?=nil) {self.model=model;self.context=context;self.isCurrent=isCurrent;self.onOpen=onOpen ?? model.open}
    var body: some View {
        let entry=model.entryControl
        if isCurrent(),let entry,entry.read.context==context {Button(AppCopy.text("taskCommentDraftTitle")) {if isCurrent() && model.entryControl==entry {onOpen(entry.read)}}}
    }
}
struct TaskCommentScreen: View {
    @ObservedObject var model: TaskCommentViewModel
    let selection: TaskCommentSelection
    @FocusState private var focused: Bool
    let isCurrent:@MainActor ()->Bool
    private func submissionKey(_ phase: TaskCommentAttemptPhase) -> String {
        switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskCommentFakeConfirmed";case .rejected:"taskCommentFakeRejected";case .unknown:"taskCommentFakeUnknown"}
    }
    var body: some View {
        let control=model.control,input=model.inputControl,returnControl=model.returnControl,question=model.clearConfirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection==selection,model.session.available {
                    Section {Text(AppCopy.text("clientDraftOnly"));Text(AppCopy.text("fixtureMode")).font(.caption)}
                    if model.submissionBlocked {
                        Section {
                            if let record=model.submission {
                                Text(record.attempt.text).textSelection(.enabled)
                                Text(AppCopy.text(submissionKey(record.phase))).accessibilityAddTraits(.updatesFrequently)
                                if record.phase == .confirmed || record.phase == .rejected {
                                    Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone" : "taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskCommentDraftTitle")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone" : "taskCommentFakeEdit")))
                                }
                            } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                        }
                    } else if model.session.phase == .review,let review=model.session.review,review.selection==selection {
                        Section(AppCopy.text("clientDraftReview")) {Text(review.text).textSelection(.enabled)}
                        if model.canSubmit {Button(AppCopy.text("taskCommentFakeSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                    } else {
                        Section {
                            TextField(AppCopy.text("taskCommentDraftText"),text:Binding(get:{model.session.text},set:{if isCurrent() {model.update($0,input:input)}}),axis:.vertical).lineLimit(5...16).focused($focused).accessibilityHint(model.session.emptyError ? AppCopy.text("replyDraftRequired") : "")
                            if model.session.emptyError {Text(AppCopy.text("replyDraftRequired")).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
                        }
                        Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control);focused=model.session.emptyError}}
                    }
                    if !model.submissionBlocked {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskCommentDraftTitle")+": "+AppCopy.text("clientDraftClear")))}
                }
            }.navigationTitle(AppCopy.text("taskCommentDraftTitle"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:returnControl)}}.accessibilityLabel(Text(AppCopy.text("taskCommentDraftTitle")+": "+AppCopy.text("back")))}}
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {TaskCommentClearContent(model:model,question:question,isCurrent:isCurrent)}
                }
        }
    }
}

private struct TaskCommentClearContent:View {
    @ObservedObject var model:TaskCommentViewModel
    let question:TaskCommentClearConfirmation
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientDraftClearQuestion")).font(.headline)
            Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskCommentDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}.accessibilityLabel(Text(AppCopy.text("taskCommentDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftCancel")))
        }.padding()
    }
}
