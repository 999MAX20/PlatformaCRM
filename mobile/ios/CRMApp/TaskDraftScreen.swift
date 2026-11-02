import SwiftUI
import CRMCore

struct TaskDraftRoute<Content: View>: View {
    @ObservedObject var model: TaskDraftViewModel
    let context: TaskDraftContext?
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: TaskDraftViewModel,context: TaskDraftContext?,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) { self.model=model;self.context=context;self.isCurrent=isCurrent;self.content=content() }
    var body: some View {
        let selection=model.session.selection,returnControl=model.returnControl
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.context == context && model.session.selection == selection},set:{if !$0 && isCurrent() {model.close(expected:returnControl)}})) {
            if let selection,selection.context == context,model.session.selection == selection,isCurrent() { TaskDraftScreen(model:model,selection:selection,isCurrent:isCurrent) }
        }
    }
}
struct TaskDraftEntry:View {
    @ObservedObject var model:TaskDraftViewModel
    let context:TaskDraftContext
    let isCurrent:@MainActor ()->Bool
    let onOpen:@MainActor (TaskDraftEntryControl)->Void
    var body:some View {
        let entry=model.entryControl
        if isCurrent(),let entry,entry.context==context {Button(AppCopy.text("taskDraftTitle")) {if isCurrent() && model.entryControl==entry {onOpen(entry)}}}
    }
}
struct TaskDraftScreen: View {
    @ObservedObject var model: TaskDraftViewModel
    let selection: TaskDraftSelection
    @FocusState private var focus: TaskDraftField?
    let isCurrent:@MainActor ()->Bool
    private func submissionKey(_ phase: TaskCreateAttemptPhase) -> String {
        switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskCreateFakeConfirmed";case .rejected:"taskCommentFakeRejected";case .unknown:"taskCommentFakeUnknown"}
    }
    private func binding(_ field: TaskDraftField,_ input:TaskDraftInputControl?) -> Binding<String> {
        Binding(get:{guard isCurrent(),model.inputControl==input,input != nil else {return ""};return switch field {case .title:model.session.values.title;case .description:model.session.values.description;case .priority:model.session.values.priority;case .dueAt:model.session.values.dueDate.raw;case .reminderAt:model.session.values.reminderDate.raw}},set:{if isCurrent() {model.update(field,$0,input:input)}})
    }
    private func clientLabel(_ choice:TaskDraftClientChoice?)->String {choice.map {($0.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\($0.id)"} ?? AppCopy.text("taskDraftClientOmit")}
    private func appointmentLabel(_ choice:TaskDraftAppointmentChoice?)->String {choice.map {($0.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\($0.id)"} ?? AppCopy.text("taskDraftAppointmentOmit")}
    private func parentLabel(_ choice:TaskDraftParentChoice?)->String {choice.map {($0.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\($0.id)"} ?? AppCopy.text("taskDraftParentOmit")}
    private func priority(_ raw: String) -> String {
        switch raw {case "low":AppCopy.text("priorityLow");case "normal":AppCopy.text("priorityNormal");case "high":AppCopy.text("priorityHigh");case "urgent":AppCopy.text("priorityUrgent");default:AppCopy.text("notAvailable")}
    }
    private func issue(_ field: TaskDraftField) -> String? {
        guard let problem=model.session.issues.first(where:{$0.field == field})?.problem else {return nil}
        switch problem {case .required:return AppCopy.text("taskDraftRequired");case .titleLength:return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"255");case .priority:return AppCopy.text("notAvailable");case .characters:return AppCopy.text("taskCancelReasonCharacters");case .date:return AppCopy.text("taskSnoozeInputIssue")}
    }
    var body: some View {
        let control=model.control,input=model.inputControl,returnControl=model.returnControl,question=model.clearConfirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection == selection {
                    Section {Text(AppCopy.text("clientDraftOnly"));Text(AppCopy.text("fixtureMode")).font(.caption)}
                    if model.submissionBlocked {
                        Section {
                            if let record=model.submission {
                                Text(record.attempt.review.preview.title)
                                LabeledContent(AppCopy.text("taskDraftClient"),value:clientLabel(record.attempt.review.values.client))
                            LabeledContent(AppCopy.text("taskDraftAppointment"),value:appointmentLabel(record.attempt.review.values.appointment))
                            LabeledContent(AppCopy.text("taskDraftParent"),value:parentLabel(record.attempt.review.values.parentTask))
                                if let client=record.clientID {LabeledContent(AppCopy.text("taskCreateClientReturned"),value:"#\(client)")}
                            if let id=record.appointmentID {LabeledContent(AppCopy.text("taskCreateAppointmentReturned"),value:"#\(id)")}
                            if let id=record.parentTaskID {LabeledContent(AppCopy.text("taskCreateParentReturned"),value:"#\(id)")}
                                if let due=record.attempt.review.preview.dueAt {LabeledContent(AppCopy.text("taskDue"),value:due)}
                                if let reminder=record.attempt.review.preview.reminderAt {LabeledContent(AppCopy.text("taskReminderAt"),value:reminder)}
                                if let returned=record.reminderAt {LabeledContent(AppCopy.text("taskCreateReminderReturned"),value:returned)}
                                Text(AppCopy.text(submissionKey(record.phase))).accessibilityAddTraits(.updatesFrequently)
                                if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskDraftTitle")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")))}
                            } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                        }
                    } else if let owner=model.parentPickerOwner,let read=model.parents {
                        Section {TaskDraftParentPickerContent(model:model,read:read,isCurrent:{isCurrent() && model.matchesParentPicker(owner)})}
                    } else if let owner=model.appointmentPickerOwner,let read=model.appointments {
                        Section {TaskDraftAppointmentPickerContent(model:model,read:read,isCurrent:{isCurrent() && model.matchesAppointmentPicker(owner)})}
                    } else if let owner=model.clientPickerOwner,let search=model.clients {
                        Section {TaskDraftClientPickerContent(model:model,search:search,isCurrent:{isCurrent() && model.matchesClientPicker(owner)})}
                    } else if model.session.phase == .review,let review=model.session.review,review.selection == selection {
                        Section(AppCopy.text("clientDraftReview")) {
                            LabeledContent(AppCopy.text("taskTitle"),value:review.preview.title)
                            LabeledContent(AppCopy.text("taskDraftClient"),value:clientLabel(review.values.client))
                            LabeledContent(AppCopy.text("taskDraftAppointment"),value:appointmentLabel(review.values.appointment))
                            LabeledContent(AppCopy.text("taskDraftParent"),value:parentLabel(review.values.parentTask))
                            LabeledContent(AppCopy.text("taskPriority"),value:priority(review.preview.priority))
                            Text(review.preview.description).textSelection(.enabled)
                            if let due=review.preview.dueAt {LabeledContent(AppCopy.text("taskDue"),value:due)}
                            if let reminder=review.preview.reminderAt {LabeledContent(AppCopy.text("taskReminderAt"),value:reminder)}
                        }
                        if model.canSubmit {Button(AppCopy.text("taskCreateFakeSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                    } else {
                        Section {
                            Text(parentLabel(model.session.values.parentTask))
                            if model.parentPickerAvailable {Button(AppCopy.text("taskDraftParentChoose")) {if isCurrent() {model.openParentPicker(input:input)}}}
                            if model.session.values.parentTask != nil {Button(AppCopy.text("taskDraftParentRemove")) {if isCurrent() {model.clearParent(input:input)}}}
                            Text(appointmentLabel(model.session.values.appointment))
                            if model.appointmentPickerAvailable {Button(AppCopy.text("taskDraftAppointmentChoose")) {if isCurrent() {model.openAppointmentPicker(input:input)}}}
                            if model.session.values.appointment != nil {Button(AppCopy.text("taskDraftAppointmentRemove")) {if isCurrent() {model.clearAppointment(input:input)}}}
                            Text(clientLabel(model.session.values.client))
                            if model.clientPickerAvailable {Button(AppCopy.text("taskDraftClientChoose")) {if isCurrent() {model.openClientPicker(input:input)}}}
                            if model.session.values.client != nil {Button(AppCopy.text("taskDraftClientRemove")) {if isCurrent() {model.clearClient(input:input)}}}
                            TextField(AppCopy.text("taskTitle"),text:binding(.title,input)).focused($focus,equals:.title).accessibilityHint(issue(.title) ?? "")
                            if let error=issue(.title) { Text(error).foregroundStyle(.red).accessibilityHidden(true) }
                            TextField(AppCopy.text("taskDescription"),text:binding(.description,input),axis:.vertical).lineLimit(4...12).focused($focus,equals:.description).accessibilityHint(issue(.description) ?? "")
                            if let error=issue(.description) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            Picker(AppCopy.text("taskPriority"),selection:binding(.priority,input)) {ForEach(TaskDraftValues.priorities,id:\.self) {Text(priority($0)).tag($0)}}.accessibilityHint(issue(.priority) ?? "")
                            if let error=issue(.priority) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            ForEach(TaskDraftDueMode.allCases,id:\.self) {mode in
                                Button(AppCopy.text(mode == .omit ? "taskCreateDueOmit":"taskCreateDueSet")) {if isCurrent() {model.chooseDue(mode,input:input)}}
                                    .accessibilityAddTraits(model.session.values.dueDate.mode==mode ? .isSelected:[])
                            }
                            if model.session.values.dueDate.mode == .setDate {
                                TextField(AppCopy.text("taskSnoozeInput"),text:binding(.dueAt,input)).focused($focus,equals:.dueAt).accessibilityHint(issue(.dueAt) ?? "")
                                if let error=issue(.dueAt) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            }
                            ForEach(TaskDraftDueMode.allCases,id:\.self) {mode in
                                Button(AppCopy.text(mode == .omit ? "taskCreateReminderOmit":"taskCreateReminderSet")) {if isCurrent() {model.chooseReminder(mode,input:input)}}
                                    .accessibilityAddTraits(model.session.values.reminderDate.mode==mode ? .isSelected:[])
                            }
                            if model.session.values.reminderDate.mode == .setDate {
                                TextField(AppCopy.text("taskReminderAt"),text:binding(.reminderAt,input)).focused($focus,equals:.reminderAt).accessibilityHint(issue(.reminderAt) ?? "")
                                if let error=issue(.reminderAt) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            }
                        }
                        Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control);focus=model.session.issues.first?.field}}
                    }
                    if !model.submissionBlocked,model.clientPickerOwner==nil,model.appointmentPickerOwner==nil,model.parentPickerOwner==nil {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.askClear(expected:control)}}}
                }
            }.navigationTitle(AppCopy.text("taskDraftTitle"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:returnControl)}}.accessibilityLabel(Text(AppCopy.text("taskDraftTitle")+": "+AppCopy.text("back")))}}
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {TaskDraftClearContent(model:model,question:question,isCurrent:isCurrent)}
                }
        }
    }
}

private struct TaskDraftClearContent:View {
    @ObservedObject var model:TaskDraftViewModel
    let question:TaskDraftClearConfirmation
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientDraftClearQuestion")).font(.headline)
            Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}
        }.padding()
    }
}
