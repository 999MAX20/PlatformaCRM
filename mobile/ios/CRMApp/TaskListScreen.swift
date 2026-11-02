import SwiftUI
import CRMCore

struct TaskListScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: TaskListViewModel
    var isActive = true
    private var business: Int? { agenda.session.selection?.business.id }
    private var current: Bool { model.business == business && model.scopeEpoch == agenda.businessEpoch }
    private func owns(_ control:TaskListControl?)->Bool {guard let control else {return false};return model.matches(control) && agenda.session.selection?.business.id==control.business && agenda.businessEpoch==control.epoch}
    private func value(_ raw: String?) -> String {
        guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw
    }
    private func status(_ raw: String?) -> String {
        switch raw { case nil: AppCopy.text("all"); case "open": AppCopy.text("taskOpen"); case "in_progress": AppCopy.text("taskInProgress"); case "done": AppCopy.text("taskDone"); case "cancelled": AppCopy.text("taskCancelled"); default: value(raw) }
    }
    private func priority(_ raw: String?) -> String {
        switch raw { case "low": AppCopy.text("priorityLow"); case "normal": AppCopy.text("priorityNormal"); case "high": AppCopy.text("priorityHigh"); case "urgent": AppCopy.text("priorityUrgent"); default: value(raw) }
    }
    private func date(_ raw: String?) -> String {
        raw.flatMap { AppointmentDate.format(startAt: $0, timezone: agenda.session.selection?.business.timezone, language: AppCopy.language) } ?? AppCopy.text("notAvailable")
    }
    private func schedule(_ value: TaskScheduleValue) -> String {
        switch value {case .notSet:AppCopy.text("taskScheduleNotSet");case .unknown:AppCopy.text("notAvailable");case .instant(let raw):date(raw)}
    }
    private func person(_ read: MobileUserRead,notSetKey: String) -> String {
        switch read {case .notSet:AppCopy.text(notSetKey);case .unknown:AppCopy.text("notAvailable");case .person(let user):user.displayName ?? AppCopy.text("notAvailable")}
    }
    private func error(_ failure: ReadFailure) -> String { failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure) }
    private var draftContext: TaskDraftContext? { guard current,let business,let epoch=model.scopeEpoch else {return nil};return TaskDraftContext(business:business,epoch:epoch) }
    var body: some View {
        let control=current ? model.control:nil
        let readScope=AppCopy.text("tasks"),bootstrapScope=AppCopy.text("tasks")+": "+AppCopy.text("business")
        let previousStatus=model.status
        let filterSelection=current ? model.querySelection:nil
        let detailSelection=model.detailSelection
        let commentReturn=model.comment?.returnControl,reasonReturn=model.cancelReason?.returnControl
        TaskDraftRoute(model:model.draft,context:draftContext,isCurrent:{owns(control) && model.selectedID==nil && model.comment?.control==nil && model.cancelReason?.control==nil}) {
        NavigationStack {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business }, set: { id in Task { await agenda.load(business: id) } })) {
                        ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                    }
                }
                if business == nil, let failure = agenda.failure {
                    Text(error(failure)).accessibilityLabel(Text(bootstrapScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else if business == nil || !current || model.loading {
                    ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))
                } else {
                    TextField(AppCopy.text("inboxSearch"), text:Binding(get:{model.query},set:{if owns(control) {model.search($0,expected:control)}})).textFieldStyle(.roundedBorder)
                    Picker(AppCopy.text("status"), selection: Binding(get:{model.sourceFiltering ? model.appliedFilter.status:model.status},set:{value in if model.sourceFiltering {let due=model.appliedFilter.due;Task {if owns(control) {await model.applyFilter(TaskQueryFilter(status:value,due:due),expected:filterSelection)}}} else if owns(control) {model.filterStatus(value,previous:previousStatus,expected:control)}})) {
                        Text(AppCopy.text("all")).tag(nil as String?)
                        ForEach(model.statuses, id: \.self) { option in Text(status(option)).tag(Optional(option)) }
                    }
                    if model.sourceFiltering {
                        Picker(AppCopy.text("taskDue"),selection:Binding(get:{model.appliedFilter.due},set:{due in let status=model.appliedFilter.status;Task {if owns(control) {await model.applyFilter(TaskQueryFilter(status:status,due:due),expected:filterSelection)}}})) {
                            Text(AppCopy.text("taskQueryAllDue")).tag(TaskDueFilter.all)
                            Text(AppCopy.text("today")).tag(TaskDueFilter.today)
                            Text(AppCopy.text("taskQueryOverdue")).tag(TaskDueFilter.overdue)
                        }
                        if model.appliedFilter != TaskQueryFilter() {Button(AppCopy.text("taskQueryClear")) {Task {if owns(control) {await model.applyFilter(TaskQueryFilter(),expected:filterSelection)}}}}
                        Button(AppCopy.text("taskQueryRefresh")) {Task {if owns(control) {await model.refreshFilter(expected:filterSelection)}}}
                    }
                    if let context=draftContext {TaskDraftEntry(model:model.draft,context:context,isCurrent:{owns(control) && model.selectedID==nil && !model.loading},onOpen:{entry in model.openDraft(expected:entry,parent:control)})}
                    if let failure = model.failure {
                        Text(error(failure)).accessibilityLabel(Text(readScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retryList(expected:control)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else {
                        if model.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if model.showsEmpty { Text(AppCopy.text(model.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && model.status == nil ? "tasksEmpty" : "noResults")) }
                        if model.visible.isEmpty { Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retryList(expected:control)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
                        List(model.visible) { item in
                            Button { Task {if owns(control) {await model.open(id:item.id,expected:control)}} } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(value(item.title))
                                    Text(status(item.status)).font(.caption)
                                    Text("\(AppCopy.text("taskPriority")): \(priority(item.priority))").font(.caption)
                                    Text("\(AppCopy.text("taskDue")): \(date(item.due_at))").font(.caption)
                                }.foregroundStyle(.primary)
                            }
                        }.listStyle(.plain)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal).navigationTitle(AppCopy.text("tasks"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selectedID != nil }, set: { if !$0,owns(control) { model.back(expected:detailSelection,comment:commentReturn,reason:reasonReturn) } })) { if current { detailContent } }
            .task(id: "\(business ?? 0):\(agenda.businessEpoch):\(isActive)") {
                guard isActive else { return }
                if !current || (!model.loaded && !model.loading && model.failure == nil) { await model.load(business: business, epoch: agenda.businessEpoch) } }
        }
    }
    }
    @ViewBuilder private var detailContent: some View {
        let parent=model.control,target=model.detailSelection
        if let reason=model.cancelReason {
            TaskCancelReasonRoute(model:reason,context:current ? model.selectedID.flatMap {id in model.scopeEpoch.map {TaskCommentContext(business:business ?? 0,task:id,epoch:$0)}} : nil,title:model.detail?.task.title,isCurrent:{owns(parent) && model.detailSelection==target && model.detail != nil && !model.detailLoading && model.detailFailure==nil && model.comment?.control==nil}) {commentDetailContent}
        } else {commentDetailContent}
    }
    @ViewBuilder private var commentDetailContent: some View {
        let parent=model.control,target=model.detailSelection
        if let comment=model.comment {
            TaskCommentRoute(model:comment,context:current ? model.selectedID.flatMap {id in model.scopeEpoch.map {TaskCommentContext(business:business ?? 0,task:id,epoch:$0)}} : nil,isCurrent:{owns(parent) && model.detailSelection==target && model.detail != nil && !model.detailLoading && model.detailFailure==nil && model.cancelReason?.session.selection==nil}) {taskDetailBody}
        } else {taskDetailBody}
    }
    @ViewBuilder private func taskActions(control:TaskListControl?,target:TaskDetailSelection?)->some View {
        if owns(control),model.detailSelection==target,model.hasHiddenRetainedAction {Text(AppCopy.text("taskActionRetained")).accessibilityAddTraits(.updatesFrequently)}
        if let files=model.fileMetadata {TaskFileMetadataView(model:files,isCurrent:{owns(control) && model.detailSelection==target})}
        if let dates=model.dateEdit {TaskDateEditView(model:dates,isCurrent:{owns(control) && model.detailSelection==target && model.dateEditCurrent(control)},open:{model.openDateEdit($0,parent:control)})}
        if let dates=model.clientEdit {TaskClientEditView(model:dates,isCurrent:{owns(control) && model.detailSelection==target && model.clientEditCurrent(control)},open:{model.openClientEdit($0,parent:control)})}
        if let dates=model.appointmentEdit {TaskAppointmentEditView(model:dates,isCurrent:{owns(control) && model.detailSelection==target && model.appointmentEditCurrent(control)},open:{model.openAppointmentEdit($0,parent:control)})}
        if let priorities=model.priorityEdit {TaskPriorityEditView(model:priorities,isCurrent:{owns(control) && model.detailSelection==target && model.priorityEditCurrent(control)},open:{model.openPriorityEdit($0,parent:control)})}
        if let titles=model.titleEdit {TaskTitleEditView(model:titles,isCurrent:{owns(control) && model.detailSelection==target && model.titleEditCurrent(control)},open:{model.openTitleEdit($0,parent:control)})}
        if let descriptions=model.descriptionEdit {TaskDescriptionEditView(model:descriptions,isCurrent:{owns(control) && model.detailSelection==target && model.descriptionEditCurrent(control)},open:{model.openDescriptionEdit($0,parent:control)})}
        if let assign=model.targetAssignment {TaskAssignView(model:assign,isCurrent:{owns(control) && model.detailSelection==target && model.targetAssignCurrent(control)},open:{model.openTargetAssign($0,parent:control)})}
        if let snooze=model.snoozeAction {TaskSnoozeView(model:snooze,isCurrent:{owns(control) && model.detailSelection==target && model.snoozeCurrent(control)},open:{model.openSnooze($0,parent:control)})}
        if let undo=model.undoCancelAction {TaskUndoCancelView(model:undo,isCurrent:{owns(control) && model.detailSelection==target && model.undoCancelCurrent(control)},prepare:{model.prepareUndoCancel($0,parent:control)})}
        if let watch=model.watcherAction {TaskWatcherView(model:watch,isCurrent:{owns(control) && model.detailSelection==target && model.watcherCurrent(control)},prepare:{model.prepareWatcher($0,parent:control)})}
        if let reopen=model.reopenAction {TaskReopenView(model:reopen,isCurrent:{owns(control) && model.detailSelection==target && model.reopenCurrent(control)},prepare:{model.prepareReopen($0,parent:control)})}
        if let start=model.startAction {TaskStartView(model:start,isCurrent:{owns(control) && model.detailSelection==target && model.startCurrent(control)},prepare:{model.prepareStart($0,parent:control)})}
        if let completion=model.completion {TaskCompletionView(model:completion,isCurrent:{owns(control) && model.detailSelection==target && model.completionCurrent(control)},prepare:{model.prepareCompletion($0,parent:control)})}
        if let assignment=model.selfAssignment {TaskSelfAssignmentView(model:assignment,isCurrent:{owns(control) && model.detailSelection==target && model.selfAssignmentCurrent(control)},prepare:{model.prepareSelfAssignment($0,parent:control)})}
    }
    private var taskDetailBody: some View {
        let control=current ? model.control:nil
        let target=model.detailSelection
        let detailScope=AppCopy.text("tasks")+": "+AppCopy.text("details")
        return Group {
            if model.detailLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(detailScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.detailFailure, let id = model.selectedID {
                VStack { Text(error(failure)).accessibilityLabel(Text(detailScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retryDetail(expected:target)}} }.accessibilityLabel(Text(detailScope+": "+AppCopy.text("retry"))) }
            } else if let detail = model.detail {
                Form {
                    Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                    if let comment=model.comment,let epoch=model.scopeEpoch {TaskCommentEntry(model:comment,context:TaskCommentContext(business:detail.business,task:detail.task.id,epoch:epoch),isCurrent:{owns(control) && model.detailSelection==target && model.detail != nil && !model.detailLoading && model.detailFailure==nil && model.cancelReason?.session.selection==nil},onOpen:{read in if owns(control) {model.openComment(read)}})}
                    if let reason=model.cancelReason,let epoch=model.scopeEpoch {TaskCancelReasonEntry(model:reason,context:TaskCommentContext(business:detail.business,task:detail.task.id,epoch:epoch),isCurrent:{!model.taskActionOccupied && owns(control) && model.detailSelection==target && model.detail != nil && !model.detailLoading && model.detailFailure==nil && model.comment?.control==nil},onOpen:{read in if owns(control) {model.openCancelReason(read)}})}
                    if let completion=model.completion,let assignment=model.selfAssignment {
                        TaskActionObservedContent(completion:completion,assignment:assignment) {taskActions(control:control,target:target)}
                    } else {taskActions(control:control,target:target)}
                    LabeledContent(AppCopy.text("taskTitle"), value: value(detail.task.title))
                    LabeledContent(AppCopy.text("status"), value: status(detail.task.status))
                    LabeledContent(AppCopy.text("taskPriority"), value: priority(detail.task.priority))
                    LabeledContent(AppCopy.text("taskAssignee"),value:person(detail.details.assignee,notSetKey:"taskNoAssignee"))
                    LabeledContent(AppCopy.text("taskCreatedBy"),value:person(detail.details.created_by,notSetKey:"notAvailable"))
                    LabeledContent(AppCopy.text("taskDue"), value: date(detail.task.due_at))
                    LabeledContent(AppCopy.text("taskReminderAt"),value:schedule(detail.details.reminder_at))
                    LabeledContent(AppCopy.text("taskSnoozedUntil"),value:schedule(detail.details.snoozed_until))
                    Section(AppCopy.text("taskDescription")) { Text(value(detail.details.description)) }
                    Section(AppCopy.text("taskComments")) {
                        if detail.commentsCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if detail.comments.isEmpty { Text(AppCopy.text("taskNoComments")) }
                        ForEach(detail.comments) { comment in VStack(alignment: .leading) { Text(value(comment.text)); LabeledContent(AppCopy.text("taskCommentAuthor"),value:person(comment.authorRead,notSetKey:"notAvailable")); Text(date(comment.created_at)).font(.caption) } }
                    }
                }
            }
        }.navigationTitle(AppCopy.text("tasks"))
    }
}
