import SwiftUI
import CRMCore

struct TaskCancelReasonRoute<Content: View>: View {
    @ObservedObject var model: TaskCancelReasonViewModel
    let context: TaskCommentContext?
    let title: String?
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: TaskCancelReasonViewModel,context: TaskCommentContext?,title: String?,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) {self.model=model;self.context=context;self.title=title;self.isCurrent=isCurrent;self.content=content()}
    var body: some View {
        let selection=model.session.selection,returnControl=model.returnControl
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.read.context==context && model.session.selection==selection && model.session.available},set:{if !$0 && isCurrent() {model.close(expected:returnControl)}})) {
            if let selection,selection.read.context==context,model.session.selection==selection,model.session.available,isCurrent() {TaskCancelReasonScreen(model:model,selection:selection,title:title,isCurrent:isCurrent)}
        }
    }
}
struct TaskCancelReasonEntry:View {
    @ObservedObject var model:TaskCancelReasonViewModel
    let context:TaskCommentContext
    let isCurrent:@MainActor ()->Bool
    let onOpen:@MainActor (TaskCommentRead)->Void
    var body:some View {
        let entry=model.entryControl
        if isCurrent(),let entry,entry.read.context==context {
            Button(AppCopy.text("taskCancelReasonDraftTitle")) {if isCurrent() && model.entryControl==entry {onOpen(entry.read)}}
        }
    }
}
struct TaskCancelReasonScreen: View {
    @ObservedObject var model: TaskCancelReasonViewModel
    let selection: TaskCancelReasonSelection
    let title: String?
    let isCurrent:@MainActor ()->Bool
    @FocusState private var focused: Bool
    private func submissionKey(_ phase: TaskCancelAttemptPhase) -> String {
        switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskCancelFakeConfirmed";case .rejected:"taskCommentFakeRejected";case .unknown:"taskCommentFakeUnknown"}
    }
    private var error: String? {
        switch model.session.problem {
        case .minimum:AppCopy.text("taskCancelReasonRequired").replacingOccurrences(of:"{count}",with:"3")
        case .maximum:AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"2000")
        case .characters:AppCopy.text("taskCancelReasonCharacters")
        case nil:nil
        }
    }
    var body: some View {
        let control=model.control,input=model.inputControl,returnControl=model.returnControl,question=model.clearConfirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection==selection,model.session.available {
                    Section {
                        Text(AppCopy.text("clientDraftOnly"));Text(AppCopy.text("fixtureMode")).font(.caption)
                        LabeledContent(AppCopy.text("taskTitle"),value:title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))
                    }
                    if model.submissionBlocked {
                        Section {
                            if let record=model.submission {
                                Text(record.attempt.review.text).textSelection(.enabled)
                                Text(AppCopy.text(submissionKey(record.phase))).accessibilityAddTraits(.updatesFrequently)
                                if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskCancelReasonDraftTitle")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")))}
                            } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                        }
                    } else if model.session.phase == .review,let review=model.session.review,review.selection==selection {
                        Section(AppCopy.text("clientDraftReview")) {Text(review.text).textSelection(.enabled)}
                        if model.canSubmit {Button(AppCopy.text("taskCancelFakeSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                    } else {
                        Section {
                            TextField(AppCopy.text("taskCancelReasonLabel"),text:Binding(get:{model.session.text},set:{if isCurrent() {model.update($0,input:input)}}),axis:.vertical).lineLimit(4...14).focused($focused).accessibilityHint(error ?? "")
                            if let error {Text(error).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
                        }
                        Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control);focused=model.session.problem != nil}}
                    }
                    if !model.submissionBlocked {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskCancelReasonDraftTitle")+": "+AppCopy.text("clientDraftClear")))}
                }
            }.navigationTitle(AppCopy.text("taskCancelReasonDraftTitle"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:returnControl)}}.accessibilityLabel(Text(AppCopy.text("taskCancelReasonDraftTitle")+": "+AppCopy.text("back")))}}
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {TaskCancelReasonClearContent(model:model,question:question,isCurrent:isCurrent)}
                }
        }
    }
}

private struct TaskCancelReasonClearContent:View {
    @ObservedObject var model:TaskCancelReasonViewModel
    let question:TaskCancelReasonClearConfirmation
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientDraftClearQuestion")).font(.headline)
            Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskCancelReasonDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}.accessibilityLabel(Text(AppCopy.text("taskCancelReasonDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftCancel")))
        }.padding()
    }
}
