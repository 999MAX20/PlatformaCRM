package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskListScreen(agenda: AgendaViewModel, model: TaskListViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun status(raw: String?) = when (raw) { null -> text("all"); "open" -> text("taskOpen"); "in_progress" -> text("taskInProgress"); "done" -> text("taskDone"); "cancelled" -> text("taskCancelled"); else -> value(raw) }
    fun priority(raw: String?) = when (raw) { "low" -> text("priorityLow"); "normal" -> text("priorityNormal"); "high" -> text("priorityHigh"); "urgent" -> text("priorityUrgent"); else -> value(raw) }
    fun error(problem: ReadProblem) = text(when (problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })
    val scope = agenda.state.selection
    val business = scope?.business?.id
    val state = model.state
    val current = state.business == business && state.scopeEpoch == agenda.state.businessEpoch
    val control=if(current)model.control else null
    fun ownsControl()=control!=null && model.matches(control) && agenda.state.selection?.business?.id==control.business && agenda.state.businessEpoch==control.epoch
    val filterSelection=if(current)model.querySelection else null
    val detailSelection=model.detailSelection
    val draftContext=if(current && business!=null && state.scopeEpoch!=null)TaskDraftContext(business,state.scopeEpoch) else null
    fun ownsDraft()=ownsControl() && model.state.selectedID==null && model.comment?.control==null && model.cancelReason?.control==null
    val draftSelection=model.draft.state.selection?.takeIf {it.context==draftContext}
    val comment=model.comment
    val commentContext=if(current && business!=null && state.selectedID!=null && state.scopeEpoch!=null)TaskCommentContext(business,state.selectedID,state.scopeEpoch) else null
    val commentSelection=comment?.takeIf {it.state.available}?.state?.selection?.takeIf {it.read.context==commentContext}
    val reason=model.cancelReason
    // Read both controls during composition so peer ledger/preview changes refresh visibility.
    val completionControl=model.completion?.control
    val assignmentControl=model.selfAssignment?.control
    val undoCancelControl=model.undoCancelAction?.control
    val watcherControl=model.watcherAction?.control
    val reopenControl=model.reopenAction?.control
    val startControl=model.startAction?.control
    val childReturn=model.detailReturnControl
    fun ownsComment()=ownsControl() && model.detailSelection==detailSelection && model.state.detail!=null && !model.state.detailLoading && model.state.detailProblem==null && reason?.state?.selection==null
    fun ownsReason()=ownsControl() && model.detailSelection==detailSelection && model.state.detail!=null && !model.state.detailLoading && model.state.detailProblem==null && comment?.control==null
    val reasonSelection=reason?.takeIf {it.state.available}?.state?.selection?.takeIf {it.read.context==commentContext}
    var businessMenu by remember { mutableStateOf(false) }
    var statusMenu by remember { mutableStateOf(false) }
    var dueMenu by remember {mutableStateOf(false)}
    val readScope=text("tasks");val bootstrapScope=readScope+": "+text("business");val detailScope=readScope+": "+text("details")
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    val loading = Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val detailProgress = Modifier.semantics { contentDescription = detailScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    fun date(raw: String?) = raw?.let { formatAppointmentDate(it, scope?.business?.timezone, language) } ?: text("notAvailable")
    LaunchedEffect(business, agenda.state.businessEpoch) { if (!current || (!state.loaded && !state.loading && state.problem == null)) model.load(business, agenda.state.businessEpoch) }
    fun schedule(value: TaskScheduleValue)=when(value) {
        TaskScheduleValue.NotSet->text("taskScheduleNotSet")
        TaskScheduleValue.Unknown->text("notAvailable")
        is TaskScheduleValue.At->date(value.raw)
    }
    fun person(value: MobileUserRead,notSetKey: String)=when(value) {
        MobileUserRead.NotSet->text(notSetKey)
        MobileUserRead.Unknown->text("notAvailable")
        is MobileUserRead.Person->value.user.displayName ?: text("notAvailable")
    }
    fun back() {if(ownsControl() && model.backChildren(childReturn)==TaskChildBack.NO_CHILD)model.back(detailSelection)}
    BackHandler(enabled = current && state.selectedID != null, onBack = ::back)
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
        Text(text("tasks"), style = MaterialTheme.typography.titleLarge)
        if (scope != null) Box {
            OutlinedButton(onClick = { businessMenu = true }) { Text(scope.business.name) }
            DropdownMenu(expanded = businessMenu, onDismissRequest = { businessMenu = false }) {
                agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==scope.business.id},text = { Text(member.name) }, onClick = { businessMenu = false; agenda.load(member.id, scope.day) }) }
            }
        }
        when {
            business == null && agenda.state.problem != null -> {
                Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)})
                Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) }
            }
            business == null || !current || state.loading -> CircularProgressIndicator(loading)
            draftSelection != null -> TaskDraftContent(model.draft,draftSelection,copy,Modifier.weight(1f),isCurrent={ownsDraft()})
            reason!=null && reasonSelection!=null -> TaskCancelReasonContent(reason,reasonSelection,state.detail?.task?.title,copy,Modifier.weight(1f),isCurrent={ownsReason()})
            comment!=null && commentSelection!=null -> TaskCommentContent(comment,commentSelection,copy,Modifier.weight(1f),isCurrent={ownsComment()})
            state.selectedID != null -> {
                TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick = ::back) { Text(text("back")) }
                when {
                    state.detailLoading -> CircularProgressIndicator(detailProgress)
                    state.detailProblem != null -> {
                        Text(error(state.detailProblem), modifier = announcement.semantics {contentDescription=detailScope+": "+error(state.detailProblem)})
                        Button(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("retry")},onClick = {if(ownsControl())model.retryDetail(detailSelection)}) { Text(text("retry")) }
                    }
                    state.detail != null -> {
                        val detail = state.detail
                        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            item {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    if(comment!=null && commentContext!=null)TaskCommentEntry(comment,commentContext,copy,isCurrent={ownsComment()},onOpen={read->if(ownsControl())model.openComment(read)})
                                    if(ownsControl() && model.hasHiddenRetainedAction)Text(text("taskActionRetained"),modifier=announcement)
                                    model.fileMetadata?.let {files->TaskFileMetadataContent(files,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection})}
                                    model.undoCancelAction?.let {undo->TaskUndoCancelContent(undo,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && undo.control==undoCancelControl && model.undoCancelCurrent(control)},prepare={model.prepareUndoCancel(it,control)})}
                                    model.watcherAction?.let {watch->TaskWatcherContent(watch,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && watch.control==watcherControl && model.watcherCurrent(control)},prepare={model.prepareWatcher(it,control)})}
                                    model.reopenAction?.let {reopen->TaskReopenContent(reopen,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && reopen.control==reopenControl && model.reopenCurrent(control)},prepare={model.prepareReopen(it,control)})}
                                    model.dateEdit?.let {dates->TaskDateEditContent(dates,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.dateEditCurrent(control)},open={model.openDateEdit(it,control)})}
                                    model.clientEdit?.let {dates->TaskClientEditContent(dates,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.clientEditCurrent(control)},open={model.openClientEdit(it,control)})}
                                    model.appointmentEdit?.let {dates->TaskAppointmentEditContent(dates,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.appointmentEditCurrent(control)},open={model.openAppointmentEdit(it,control)})}
                                    model.priorityEdit?.let {priorities->TaskPriorityEditContent(priorities,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.priorityEditCurrent(control)},open={model.openPriorityEdit(it,control)})}
                                    model.titleEdit?.let {titles->TaskTitleEditContent(titles,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.titleEditCurrent(control)},open={model.openTitleEdit(it,control)})}
                                    model.descriptionEdit?.let {descriptions->TaskDescriptionEditContent(descriptions,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.descriptionEditCurrent(control)},open={model.openDescriptionEdit(it,control)})}
                                    model.targetAssignment?.let {assign->TaskAssignContent(assign,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.targetAssignCurrent(control)},open={model.openTargetAssign(it,control)})}
                                    model.snoozeAction?.let {snooze->TaskSnoozeContent(snooze,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && model.snoozeCurrent(control)},open={model.openSnooze(it,control)})}
                                    model.startAction?.let {start->TaskStartContent(start,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && start.control==startControl && model.startCurrent(control)},prepare={model.prepareStart(it,control)})}
                                    model.completion?.let {complete->TaskCompletionContent(complete,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && complete.control==completionControl && model.completionCurrent(control)},prepare={model.prepareCompletion(it,control)})}
                                    model.selfAssignment?.let {assignment->TaskSelfAssignmentContent(assignment,copy,isCurrent={ownsControl() && model.detailSelection==detailSelection && assignment.control==assignmentControl && model.selfAssignmentCurrent(control)},prepare={model.prepareSelfAssignment(it,control)})}
                                    if(reason!=null && commentContext!=null)TaskCancelReasonEntry(reason,commentContext,copy,isCurrent={!model.taskActionOccupied && ownsReason()},onOpen={read->if(ownsControl())model.openCancelReason(read)})
                                    Text(value(detail.task.title), style = MaterialTheme.typography.titleMedium)
                                    Text("${text("status")}: ${status(detail.task.status)}")
                                    Text("${text("taskPriority")}: ${priority(detail.task.priority)}")
                                    Text("${text("taskAssignee")}: ${person(detail.assignee,"taskNoAssignee")}")
                                    Text("${text("taskCreatedBy")}: ${person(detail.createdBy,"notAvailable")}")
                                    Text("${text("taskDue")}: ${date(detail.task.dueAt)}")
                                    Text("${text("taskReminderAt")}: ${schedule(detail.reminderAt)}")
                                    Text("${text("taskSnoozedUntil")}: ${schedule(detail.snoozedUntil)}")
                                    Text("${text("taskDescription")}: ${value(detail.description)}")
                                    Text(text("taskComments"), style = MaterialTheme.typography.titleMedium)
                                    if (detail.commentsCapped) Text(text("partial"), modifier = announcement)
                                    if (detail.comments.isEmpty()) Text(text("taskNoComments"))
                                }
                            }
                            items(detail.comments, key = { it.id }) { comment ->
                                Column { Text(value(comment.text)); Text("${text("taskCommentAuthor")}: ${person(comment.authorRead,"notAvailable")}"); Text(date(comment.createdAt), style = MaterialTheme.typography.labelSmall) }
                            }
                        }
                    }
                }
            }
            else -> {
                if(draftContext!=null)TaskDraftEntry(model.draft,draftContext,copy,isCurrent={ownsDraft() && !model.state.loading},onOpen={entry->model.openDraft(entry,control)})
                OutlinedTextField(value = state.query, onValueChange = {if(ownsControl())model.search(it,control)}, label = { Text(text("inboxSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Box {
                    OutlinedButton(onClick = { statusMenu = true }) { Text("${text("status")}: ${status(if(state.sourceFiltering)state.appliedFilter.status else state.status)}") }
                    DropdownMenu(expanded = statusMenu, onDismissRequest = { statusMenu = false }) {
                        (listOf<String?>(null) + state.statuses).forEach { option -> DropdownMenuItem(modifier=Modifier.semantics {selected=option==(if(state.sourceFiltering)state.appliedFilter.status else state.status)},text = { Text(status(option)) }, onClick = { statusMenu = false;if(ownsControl()){if(state.sourceFiltering)model.applyFilter(state.appliedFilter.copy(status=option),filterSelection) else model.filterStatus(option,state.status,control)} }) }
                    }
                }
                if(state.sourceFiltering) {
                    fun dueLabel(due: TaskDueFilter)=text(when(due){TaskDueFilter.ALL->"taskQueryAllDue";TaskDueFilter.TODAY->"today";TaskDueFilter.OVERDUE->"taskQueryOverdue"})
                    Box {
                        OutlinedButton(onClick={dueMenu=true}) {Text("${text("taskDue")}: ${dueLabel(state.appliedFilter.due)}")}
                        DropdownMenu(expanded=dueMenu,onDismissRequest={dueMenu=false}) {TaskDueFilter.entries.forEach {due->DropdownMenuItem(modifier=Modifier.semantics {selected=state.appliedFilter.due==due},text={Text(dueLabel(due))},onClick={dueMenu=false;if(ownsControl())model.applyFilter(state.appliedFilter.copy(due=due),filterSelection)})}}
                    }
                    if(state.appliedFilter!=TaskQueryFilter())TextButton(onClick={if(ownsControl())model.applyFilter(TaskQueryFilter(),filterSelection)}) {Text(text("taskQueryClear"))}
                    TextButton(onClick={if(ownsControl())model.refreshFilter(filterSelection)}) {Text(text("taskQueryRefresh"))}
                }
                if (state.problem != null) {
                    Text(error(state.problem), modifier = announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
                    Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {if(ownsControl())model.retryList(control)}) { Text(text("retry")) }
                } else {
                    if (state.partial) Text(text("partial"), modifier = announcement)
                    if (state.showsEmpty) Text(text(if (state.query.isBlank() && state.status == null) "tasksEmpty" else "noResults"), modifier = announcement)
                    if (state.visible.isEmpty()) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {if(ownsControl())model.retryList(control)}) { Text(text("retry")) }
                    LazyColumn(Modifier.weight(1f)) {
                        items(state.visible, key = { it.id }) { task ->
                            ListItem(headlineContent = { Text(value(task.title)) }, supportingContent = {
                                Column { Text(status(task.status)); Text("${text("taskPriority")}: ${priority(task.priority)}"); Text("${text("taskDue")}: ${date(task.dueAt)}") }
                            }, modifier = Modifier.clickable(role = Role.Button) {if(ownsControl())model.open(task.id,control)})
                        }
                    }
                }
            }
        }
    }
}
