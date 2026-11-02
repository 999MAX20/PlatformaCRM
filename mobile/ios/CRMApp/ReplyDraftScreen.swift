import SwiftUI
import CRMCore

struct ReplyDraftRoute<Content: View>: View {
    @ObservedObject var model: ReplyDraftViewModel
    let context: ReplyDraftContext?
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: ReplyDraftViewModel,context: ReplyDraftContext?,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) { self.model=model;self.context=context;self.isCurrent=isCurrent;self.content=content() }
    var body: some View {
        let selection=model.session.selection,returnControl=model.returnControl
        content.sheet(isPresented:Binding(get:{ isCurrent() && selection != nil && selection?.context == context && model.session.selection == selection },set:{ if !$0 && isCurrent() { model.close(expected:returnControl) } })) {
            if let selection,selection.context == context,model.session.selection == selection,isCurrent() { ReplyDraftScreen(model:model,selection:selection,isCurrent:isCurrent) }
        }
    }
}
struct ReplyDraftButton: View {
    @ObservedObject var model: ReplyDraftViewModel
    let open: (ReplyDraftContext) -> Void
    var body: some View {
        let entry=model.entryControl
        if let entry {
            Button(AppCopy.text("replyDraftTitle")) { if model.entryControl==entry {open(entry.context)} }
        }
    }
}
struct ReplyDraftScreen: View {
    @ObservedObject var model: ReplyDraftViewModel
    let selection: ReplyDraftSelection
    @FocusState private var focused: Bool
    let isCurrent:@MainActor ()->Bool
    var body: some View {
        let control=model.control
        NavigationStack {
            if let quick=model.quickReplies {
                QuickReplyRoute(model:quick,parent:selection,insert:{choice,picker in if isCurrent() && model.insert(choice,expected:control,picker:picker) {focused=true}},isCurrent:{isCurrent() && model.control==control && !model.submissionBlocked && model.session.available && model.session.phase == .editing}) {draftForm}
            } else {draftForm}
        }
    }
    private var draftForm: some View {
        let control=model.control,input=model.inputControl,returnControl=model.returnControl,question=model.clearConfirmation,entry=model.quickReplies?.entryControl
        return Form {
                if isCurrent(),model.session.selection == selection {
                    Section { Text(AppCopy.text("clientDraftOnly"));Text(AppCopy.text("fixtureMode")).font(.caption) }
                    if model.submissionBlocked {InboxReplyReceiptView(model:model,isCurrent:isCurrent)}
                    else if model.session.phase == .review,let review=model.session.review,review.selection == selection {
                        Section(AppCopy.text("clientDraftReview")) { Text(review.text).textSelection(.enabled) }
                        if model.canSubmit {Button(AppCopy.text("inboxReplyFakeSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                        else if model.hasTestPort {Text(AppCopy.text("inboxReplyTestUnavailable"))}
                    } else {
                        Section {
                            TextField(AppCopy.text("replyDraftText"),text:Binding(get:{model.session.text},set:{if isCurrent() {model.update($0,input:input)}}),axis:.vertical).lineLimit(5...16).focused($focused).accessibilityHint(model.session.emptyError ? AppCopy.text("replyDraftRequired") : "")
                            if model.session.emptyError { Text(AppCopy.text("replyDraftRequired")).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true) }
                        }
                        if entry != nil {Button(AppCopy.text("quickReplyTitle")) {Task {if isCurrent() {await model.openQuickReplies(expected:control,entry:entry)}}}}
                        Button(AppCopy.text("clientDraftReview")) { if isCurrent() {model.prepare(expected:control);focused=model.session.emptyError} }
                    }
                    if !model.submissionBlocked {Button(AppCopy.text("clientDraftClear"),role:.destructive) { if isCurrent() {model.askClear(expected:control)} }.accessibilityLabel(Text(AppCopy.text("replyDraftTitle")+": "+AppCopy.text("clientDraftClear")))}
                }
            }.navigationTitle(AppCopy.text("replyDraftTitle"))
                .toolbar { ToolbarItem(placement:.cancellationAction) { Button(AppCopy.text("back")) { if isCurrent() {model.back(expected:returnControl)} }.accessibilityLabel(Text(AppCopy.text("replyDraftTitle")+": "+AppCopy.text("back"))) } }
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {ReplyDraftClearContent(model:model,question:question,isCurrent:isCurrent)}
                }
    }
}

private struct ReplyDraftClearContent:View {
    @ObservedObject var model:ReplyDraftViewModel
    let question:ReplyDraftClearConfirmation
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientDraftClearQuestion")).font(.headline)
            Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("replyDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}.accessibilityLabel(Text(AppCopy.text("replyDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftCancel")))
        }.padding()
    }
}
