import SwiftUI
import CRMCore

struct TaskClientEditView:View {
    @ObservedObject var model:TaskClientEditViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskClientEditControl)->Void
    private func original(_ value:TaskClientOriginal)->String {switch value {case .unknown:AppCopy.text("taskClientOriginalUnknown");case .notSet:AppCopy.text("taskScheduleNotSet");case .client(let id):"#\(id)"}}
    private func mode(_ value:TaskClientEditMode?)->String {AppCopy.text(value == .set ? "taskClientSet":"taskClientRemove")}
    private func choice(_ value:TaskDraftClientChoice?)->String {value.map {($0.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\($0.id)"} ?? AppCopy.text("taskDraftClientOmit")}
    private func status(_ phase:TaskClientEditPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskClientFakeConfirmed";case .rejected:"taskClientFakeRejected";case .unknown:"taskClientFakeUnknown"}}
    var body:some View {
        let question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskClientAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                LabeledContent(AppCopy.text("taskClientOriginal"),value:original(control.source.original))
                if model.blocked {
                    if let record=model.submission {
                        Text(mode(record.attempt.review.draft.mode))
                        if record.attempt.review.draft.mode == .set {Text(choice(record.attempt.review.draft.choice));Text(record.attempt.review.draft.query)}
                        Text(AppCopy.text(status(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskClientReturned"),value:result.value.map {"#\($0)"} ?? AppCopy.text("taskScheduleNotSet"))}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskClientFakeConfirmed"))}
                else if let review=model.review {
                    Text(mode(review.draft.mode));if review.draft.mode == .set {Text(choice(review.draft.choice));Text(review.draft.query)}
                    Text(AppCopy.text("taskClientContract"))
                    Button(AppCopy.text("taskClientFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    Button(mode(.set)) {if isCurrent() {model.choose(.set,expected:control)}}.accessibilityAddTraits(model.draft.mode == .set ? .isSelected:[])
                    Button(mode(.clear)) {if isCurrent() {model.choose(.clear,expected:control)}}.accessibilityAddTraits(model.draft.mode == .clear ? .isSelected:[])
                    if let selected=model.draft.mode {Text(mode(selected))}
                    if model.draft.mode == .set {
                        Text(choice(model.draft.choice))
                        TaskClientEditPickerContent(model:model,read:model.picker,isCurrent:isCurrent)
                    }
                    if model.showsIssue {Text(AppCopy.text("taskClientInputIssue")).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskClientAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")));Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskClientAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))}
            }
        }
    }
}
private struct TaskClientEditPickerContent:View {
    @ObservedObject var model:TaskClientEditViewModel
    @ObservedObject var read:ClientSearchViewModel
    @ObservedObject var profile:ClientProfileViewModel
    let isCurrent:@MainActor ()->Bool
    init(model:TaskClientEditViewModel,read:ClientSearchViewModel,isCurrent:@escaping @MainActor ()->Bool) {self.model=model;self.read=read;self.profile=read.profile;self.isCurrent=isCurrent}
    private func label(_ title:String?,id:Int)->String {(title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(id)"}
    var body:some View {
        let parent=model.control,input=model.inputControl,child=read.control
        let readScope=AppCopy.text("taskClientAction")+": "+AppCopy.text(read.session.profileSelection == nil ? "clientServerSearch" : "details")
        VStack(alignment:.leading,spacing:12) {
            if isCurrent(),model.canPrepare,model.draft.mode == .set {
                if let selected=read.session.profileSelection {
                    if profile.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=profile.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently);Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.retryClient(expected:parent,child:child)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))}
                    else if let detail=profile.detail,detail.valid(for:selected.selection.context.business,id:selected.id) {
                        Text(label(detail.client.title,id:detail.client.id))
                        Button(AppCopy.text("taskDraftClientUse")) {if isCurrent() {model.useClient(expected:parent,child:child)}}
                    }
                    Button(AppCopy.text("back")) {if isCurrent() {model.backClient(expected:parent,child:child)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    TextField(AppCopy.text("clientSearch"),text:Binding(get:{model.draft.query},set:{if isCurrent() {model.updateQuery($0,input:input)}})).disabled(read.session.loading)
                    Button(AppCopy.text("searchSubmit")) {Task {if isCurrent() {await model.readClients(expected:parent,child:child)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(read.session.loading)
                    if read.session.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.session.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)}
                    else if read.session.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(read.session.items.count)).replacingOccurrences(of:"{total}",with:String(read.session.total))).font(.caption)
                        if read.session.partial {Text(AppCopy.text("partial"))};if read.session.showsEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(read.session.items) {row in Button(label(row.title,id:row.id)) {Task {if isCurrent() {await model.openClient(row.id,expected:parent,child:child)}}}}
                    }
                }
            }
        }
    }
}
