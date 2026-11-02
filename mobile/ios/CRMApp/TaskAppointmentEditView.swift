import SwiftUI
import CRMCore

struct TaskAppointmentEditView:View {
    @ObservedObject var model:TaskAppointmentEditViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskAppointmentEditControl)->Void
    private func original(_ value:TaskAppointmentOriginal)->String {switch value {case .unknown:AppCopy.text("taskAppointmentOriginalUnknown");case .notSet:AppCopy.text("taskScheduleNotSet");case .appointment(let id):"#\(id)"}}
    private func mode(_ value:TaskAppointmentEditMode?)->String {AppCopy.text(value == .set ? "taskAppointmentSet":"taskAppointmentRemove")}
    private func choice(_ value:TaskDraftAppointmentChoice?)->String {value.map {($0.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\($0.id)"} ?? AppCopy.text("taskDraftAppointmentOmit")}
    private func status(_ phase:TaskAppointmentEditPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskAppointmentFakeConfirmed";case .rejected:"taskAppointmentFakeRejected";case .unknown:"taskAppointmentFakeUnknown"}}
    var body:some View {
        let question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskAppointmentAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                LabeledContent(AppCopy.text("taskAppointmentOriginal"),value:original(control.source.original))
                if model.blocked {
                    if let record=model.submission {
                        Text(mode(record.attempt.review.draft.mode))
                        if record.attempt.review.draft.mode == .set {Text(choice(record.attempt.review.draft.choice));Text(record.attempt.review.draft.day)}
                        Text(AppCopy.text(status(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskAppointmentReturned"),value:result.value.map {"#\($0)"} ?? AppCopy.text("taskScheduleNotSet"))}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskAppointmentFakeConfirmed"))}
                else if let review=model.review {
                    Text(mode(review.draft.mode));if review.draft.mode == .set {Text(choice(review.draft.choice));Text(review.draft.day)}
                    Text(AppCopy.text("taskAppointmentContract"))
                    Button(AppCopy.text("taskAppointmentFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    Button(mode(.set)) {if isCurrent() {model.choose(.set,expected:control)}}.accessibilityAddTraits(model.draft.mode == .set ? .isSelected:[])
                    Button(mode(.clear)) {if isCurrent() {model.choose(.clear,expected:control)}}.accessibilityAddTraits(model.draft.mode == .clear ? .isSelected:[])
                    if let selected=model.draft.mode {Text(mode(selected))}
                    if model.draft.mode == .set {
                        Text(choice(model.draft.choice))
                        TaskAppointmentEditPickerContent(model:model,read:model.picker,isCurrent:isCurrent)
                    }
                    if model.showsIssue {Text(AppCopy.text("taskAppointmentInputIssue")).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskAppointmentAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")));Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskAppointmentAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))}
            }
        }
    }
}
private struct TaskAppointmentEditPickerContent:View {
    @ObservedObject var model:TaskAppointmentEditViewModel
    @ObservedObject var read:TaskAppointmentPickerViewModel
    let isCurrent:@MainActor ()->Bool
    private func label(_ title:String?,id:Int)->String {(title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(id)"}
    var body:some View {
        let parent=model.control,input=model.inputControl,child=read.control
        let readScope=AppCopy.text("taskAppointmentAction")+(read.selectedID == nil ? "" : ": "+AppCopy.text("details"))
        VStack(alignment:.leading,spacing:12) {
            if isCurrent(),model.canPrepare,model.draft.mode == .set {
                if read.selectedID != nil {
                    if read.detailLoading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {
                        Text(AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure))).accessibilityLabel(Text(readScope+": "+AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure)))).accessibilityAddTraits(.updatesFrequently)
                        Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.retryAppointment(expected:parent,child:child)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else if let value=read.choice(expected:child) {
                        Text(label(value.title,id:value.id));Text(AppCopy.text("status")+": "+value.status)
                        if let start=value.startAt {Text(AppCopy.text("intervalStart")+": "+start)}
                        if let end=value.endAt {Text(AppCopy.text("intervalEnd")+": "+end)}
                        Button(AppCopy.text("taskDraftAppointmentUse")) {if isCurrent() {model.useAppointment(expected:parent,child:child)}}
                    }
                    Button(AppCopy.text("back")) {if isCurrent() {model.backAppointment(expected:parent,child:child)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    TextField(AppCopy.text("taskDraftAppointmentDay"),text:Binding(get:{model.draft.day},set:{if isCurrent() {model.updateDay($0,input:input)}})).disabled(read.loading).accessibilityHint(AppCopy.text("taskDraftAppointmentDayIssue"))
                    if !read.day.isEmpty,!TaskAppointmentDay.valid(read.day) {Text(AppCopy.text("taskDraftAppointmentDayIssue")).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("searchSubmit")) {Task {if isCurrent() {await model.readAppointments(expected:parent,child:child)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(!read.canRead)
                    if read.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {Text(AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure))).accessibilityLabel(Text(readScope+": "+AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure)))).accessibilityAddTraits(.updatesFrequently)}
                    else if read.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(read.items.count)).replacingOccurrences(of:"{total}",with:String(read.total))).font(.caption)
                        if read.partial {Text(AppCopy.text("partial"))};if read.items.isEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(read.items) {row in Button(label(row.title,id:row.id)) {Task {if isCurrent() {await model.openAppointment(row.id,expected:parent,child:child)}}}}
                    }
                }
            }
        }
    }
}
