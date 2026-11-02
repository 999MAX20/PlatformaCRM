package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskDraftEntry(model:TaskDraftModel,context:TaskDraftContext,copy:Map<String,String>,isCurrent:()->Boolean,onOpen:(TaskDraftEntryControl)->Unit) {
    val entry=model.entryControl
    if(isCurrent() && entry!=null && entry.context==context)TextButton(onClick={if(isCurrent() && model.entryControl==entry)onOpen(entry)}) {Text(copy["taskDraftTitle"] ?: "taskDraftTitle")}
}
@Composable fun TaskDraftContent(model: TaskDraftModel,selection: TaskDraftSelection,copy: Map<String,String>,modifier: Modifier,isCurrent:()->Boolean) {
    val state=model.state
    val control=model.control;val input=model.inputControl;val returnControl=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection)return
    fun text(key: String)=copy[key] ?: key
    fun clientLabel(choice:TaskDraftClientChoice?)=choice?.let {(it.title?.takeIf {s->s.isNotEmpty()} ?: text("notAvailable"))+" · #${it.id}"} ?: text("taskDraftClientOmit")
    fun appointmentLabel(choice:TaskDraftAppointmentChoice?)=choice?.let {(it.title?.takeIf {s->s.isNotEmpty()} ?: text("notAvailable"))+" · #${it.id}"} ?: text("taskDraftAppointmentOmit")
    fun parentLabel(choice:TaskDraftParentChoice?)=choice?.let {(it.title?.takeIf {s->s.isNotEmpty()} ?: text("notAvailable"))+" · #${it.id}"} ?: text("taskDraftParentOmit")
    fun priority(raw: String)=text(when(raw){"low"->"priorityLow";"normal"->"priorityNormal";"high"->"priorityHigh";"urgent"->"priorityUrgent";else->"notAvailable"})
    fun issue(field: TaskDraftField)=state.issues.firstOrNull {it.field==field}?.let {when(it.problem){TaskDraftProblem.REQUIRED->text("taskDraftRequired");TaskDraftProblem.TITLE_LENGTH->text("clientDraftMaxLength").replace("{limit}","255");TaskDraftProblem.PRIORITY->text("notAvailable");TaskDraftProblem.CHARACTERS->text("taskCancelReasonCharacters");TaskDraftProblem.DATE->text("taskSnoozeInputIssue")}}
    val focus=remember(selection) {FocusRequester()}
    val descriptionFocus=remember(selection) {FocusRequester()}
    val dueFocus=remember(selection) {FocusRequester()}
    val reminderFocus=remember(selection) {FocusRequester()}
    var menu by remember(input) {mutableStateOf(false)}
    BackHandler {if(isCurrent())model.back(expected=returnControl)}
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("taskDraftTitle"),style=MaterialTheme.typography.titleLarge,modifier=Modifier.semantics {heading()})
        Text(text("clientDraftOnly"))
        TextButton(modifier=Modifier.semantics {contentDescription=text("taskDraftTitle")+": "+text("back")},onClick={if(isCurrent())model.back(expected=returnControl)}) {Text(text("back"))}
        val submission=model.submission
        if(model.submissionBlocked) {
            if(submission!=null) {
                Text(submission.attempt.review.preview.title)
                Text(text("taskDraftClient")+": "+clientLabel(submission.attempt.review.values.client))
            Text(text("taskDraftAppointment")+": "+appointmentLabel(submission.attempt.review.values.appointment))
            Text(text("taskDraftParent")+": "+parentLabel(submission.attempt.review.values.parentTask))
                submission.clientID?.let {Text(text("taskCreateClientReturned")+": #$it")}
                submission.appointmentID?.let {Text(text("taskCreateAppointmentReturned")+": #$it")}
                submission.parentTaskID?.let {Text(text("taskCreateParentReturned")+": #$it")}
                submission.attempt.review.preview.dueAt?.let {Text(text("taskDue")+": "+it)}
                submission.attempt.review.preview.reminderAt?.let {Text(text("taskReminderAt")+": "+it)}
                submission.reminderAt?.let {Text(text("taskCreateReminderReturned")+": "+it)}
                val key=when(submission.phase) {TaskCreateAttemptPhase.PENDING->"taskCommentFakePending";TaskCreateAttemptPhase.CONFIRMED->"taskCreateFakeConfirmed";TaskCreateAttemptPhase.REJECTED->"taskCommentFakeRejected";TaskCreateAttemptPhase.UNKNOWN->"taskCommentFakeUnknown"}
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(submission.phase==TaskCreateAttemptPhase.CONFIRMED || submission.phase==TaskCreateAttemptPhase.REJECTED)Button(modifier=Modifier.semantics {contentDescription=text("taskDraftTitle")+": "+text(if(submission.phase==TaskCreateAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,submission)}) {Text(text(if(submission.phase==TaskCreateAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if(model.parentPickerOwner!=null && model.parents!=null) {
            val owner=model.parentPickerOwner;TaskDraftParentPickerContent(model,model.parents,copy,isCurrent={isCurrent() && model.matchesParentPicker(owner)})
        } else if(model.appointmentPickerOwner!=null && model.appointments!=null) {
            val owner=model.appointmentPickerOwner;TaskDraftAppointmentPickerContent(model,model.appointments,copy,isCurrent={isCurrent() && model.matchesAppointmentPicker(owner)})
        } else if(model.clientPickerOwner!=null && model.clients!=null) {
            val owner=model.clientPickerOwner;TaskDraftClientPickerContent(model,model.clients,copy,isCurrent={isCurrent() && model.matchesClientPicker(owner)})
        } else if(state.phase==TaskDraftPhase.REVIEW && state.review?.selection==selection) {
            val v=state.review!!.preview
            Text(text("taskDraftClient")+": "+clientLabel(state.review!!.values.client))
            Text(text("taskDraftAppointment")+": "+appointmentLabel(state.review!!.values.appointment))
            Text(text("taskDraftParent")+": "+parentLabel(state.review!!.values.parentTask))
            Text("${text("taskTitle")}: ${v.title}");Text("${text("taskPriority")}: ${priority(v.priority)}");Text("${text("taskDescription")}: ${v.description}")
            v.dueAt?.let {Text(text("taskDue")+": "+it)}
            v.reminderAt?.let {Text(text("taskReminderAt")+": "+it)}
            val review=state.review!!;if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(review,control)}) {Text(text("taskCreateFakeSubmit"))}
        } else {
            Text(text("taskDraftClient")+": "+clientLabel(state.values.client))
            Text(text("taskDraftAppointment")+": "+appointmentLabel(state.values.appointment))
            Text(text("taskDraftParent")+": "+parentLabel(state.values.parentTask))
            if(model.parentPickerAvailable)Button(onClick={if(isCurrent())model.openParentPicker(input)}) {Text(text("taskDraftParentChoose"))}
            if(state.values.parentTask!=null)TextButton(onClick={if(isCurrent())model.clearParent(input)}) {Text(text("taskDraftParentRemove"))}
            if(model.appointmentPickerAvailable)Button(onClick={if(isCurrent())model.openAppointmentPicker(input)}) {Text(text("taskDraftAppointmentChoose"))}
            if(state.values.appointment!=null)TextButton(onClick={if(isCurrent())model.clearAppointment(input)}) {Text(text("taskDraftAppointmentRemove"))}
            if(model.clientPickerAvailable)Button(onClick={if(isCurrent())model.openClientPicker(input)}) {Text(text("taskDraftClientChoose"))}
            if(state.values.client!=null)TextButton(onClick={if(isCurrent())model.clearClient(input)}) {Text(text("taskDraftClientRemove"))}
            OutlinedTextField(value=state.values.title,onValueChange={if(isCurrent())model.update(TaskDraftField.TITLE,it,input)},label={Text(text("taskTitle"))},singleLine=true,isError=issue(TaskDraftField.TITLE)!=null,supportingText={issue(TaskDraftField.TITLE)?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}},modifier=Modifier.fillMaxWidth().focusRequester(focus))
            OutlinedTextField(value=state.values.description,onValueChange={if(isCurrent())model.update(TaskDraftField.DESCRIPTION,it,input)},label={Text(text("taskDescription"))},minLines=4,isError=issue(TaskDraftField.DESCRIPTION)!=null,supportingText={issue(TaskDraftField.DESCRIPTION)?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}},modifier=Modifier.fillMaxWidth().focusRequester(descriptionFocus))
            Box {
                OutlinedButton(onClick={if(isCurrent() && model.inputControl==input)menu=true}) {Text("${text("taskPriority")}: ${priority(state.values.priority)}")}
                DropdownMenu(expanded=menu,onDismissRequest={menu=false}) {TaskDraftValues.priorities.forEach {raw->DropdownMenuItem(modifier=Modifier.semantics {selected=raw==state.values.priority},text={Text(priority(raw))},onClick={if(isCurrent() && model.inputControl==input) {menu=false;model.update(TaskDraftField.PRIORITY,raw,input)}})}}
            }
            issue(TaskDraftField.PRIORITY)?.let {Text(text("taskPriority")+": "+it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
            TaskDraftDueMode.entries.forEach {mode->FilterChip(selected=state.values.dueDate.mode==mode,onClick={if(isCurrent())model.chooseDue(mode,input)},label={Text(text(if(mode==TaskDraftDueMode.OMIT)"taskCreateDueOmit" else "taskCreateDueSet"))})}
            if(state.values.dueDate.mode==TaskDraftDueMode.SET)OutlinedTextField(value=state.values.dueDate.raw,onValueChange={if(isCurrent())model.update(TaskDraftField.DUE_AT,it,input)},label={Text(text("taskSnoozeInput"))},singleLine=true,isError=issue(TaskDraftField.DUE_AT)!=null,supportingText={issue(TaskDraftField.DUE_AT)?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}},modifier=Modifier.fillMaxWidth().focusRequester(dueFocus))
            TaskDraftDueMode.entries.forEach {mode->FilterChip(selected=state.values.reminderDate.mode==mode,onClick={if(isCurrent())model.chooseReminder(mode,input)},label={Text(text(if(mode==TaskDraftDueMode.OMIT)"taskCreateReminderOmit" else "taskCreateReminderSet"))})}
            if(state.values.reminderDate.mode==TaskDraftDueMode.SET)OutlinedTextField(value=state.values.reminderDate.raw,onValueChange={if(isCurrent())model.update(TaskDraftField.REMINDER_AT,it,input)},label={Text(text("taskReminderAt"))},singleLine=true,isError=issue(TaskDraftField.REMINDER_AT)!=null,supportingText={issue(TaskDraftField.REMINDER_AT)?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}},modifier=Modifier.fillMaxWidth().focusRequester(reminderFocus))
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);when(model.state.issues.firstOrNull()?.field) {TaskDraftField.TITLE->focus.requestFocus();TaskDraftField.DESCRIPTION->descriptionFocus.requestFocus();TaskDraftField.DUE_AT->dueFocus.requestFocus();TaskDraftField.REMINDER_AT->reminderFocus.requestFocus();else->Unit}}}) {Text(text("clientDraftReview"))}
        }
        if(!model.submissionBlocked && model.clientPickerOwner==null && model.appointmentPickerOwner==null && model.parentPickerOwner==null)TextButton(onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
    }
    if(question!=null)AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(onClick={if(isCurrent())model.confirmClear(question)}){Text(text("clientDraftClear"))}},dismissButton={TextButton(onClick={model.dismissClear(question)}){Text(text("clientDraftCancel"))}})
}
