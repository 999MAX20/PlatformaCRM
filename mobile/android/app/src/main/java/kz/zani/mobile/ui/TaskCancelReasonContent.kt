package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.*
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskCancelReasonEntry(model:TaskCancelReasonModel,context:TaskCommentContext,copy:Map<String,String>,isCurrent:()->Boolean,onOpen:(TaskCommentRead)->Unit) {
    val entry=model.entryControl
    if(isCurrent() && entry!=null && entry.read.context==context)TextButton(onClick={if(isCurrent() && model.entryControl==entry)onOpen(entry.read)}) {Text(copy["taskCancelReasonDraftTitle"] ?: "taskCancelReasonDraftTitle")}
}
@Composable fun TaskCancelReasonContent(model: TaskCancelReasonModel,selection: TaskCancelReasonSelection,title: String?,copy: Map<String,String>,modifier: Modifier,isCurrent:()->Boolean) {
    fun text(key: String)=copy[key] ?: key
    val state=model.state;val control=model.control;val input=model.inputControl;val returnControl=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection || !state.available)return
    val error=when(state.problem){TaskCancelReasonProblem.MINIMUM->text("taskCancelReasonRequired").replace("{count}","3");TaskCancelReasonProblem.MAXIMUM->text("clientDraftMaxLength").replace("{limit}","2000");TaskCancelReasonProblem.CHARACTERS->text("taskCancelReasonCharacters");null->null}
    val focus=remember(selection) {FocusRequester()}
    BackHandler {if(isCurrent())model.back(expected=returnControl)}
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("taskCancelReasonDraftTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("clientDraftOnly"));Text("${text("taskTitle")}: ${title?.takeIf {it.isNotEmpty()} ?: text("notAvailable")}")
        TextButton(modifier=Modifier.semantics {contentDescription=text("taskCancelReasonDraftTitle")+": "+text("back")},onClick={if(isCurrent())model.back(expected=returnControl)}) {Text(text("back"))}
        val review=state.review
        val submission=model.submission
        if(model.submissionBlocked) {
            if(submission!=null) {
                Text(submission.attempt.review.text)
                val key=when(submission.phase) {TaskCancelAttemptPhase.PENDING->"taskCommentFakePending";TaskCancelAttemptPhase.CONFIRMED->"taskCancelFakeConfirmed";TaskCancelAttemptPhase.REJECTED->"taskCommentFakeRejected";TaskCancelAttemptPhase.UNKNOWN->"taskCommentFakeUnknown"}
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(submission.phase==TaskCancelAttemptPhase.CONFIRMED || submission.phase==TaskCancelAttemptPhase.REJECTED)Button(modifier=Modifier.semantics {contentDescription=text("taskCancelReasonDraftTitle")+": "+text(if(submission.phase==TaskCancelAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,submission)}) {Text(text(if(submission.phase==TaskCancelAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if(state.phase==TaskCommentPhase.REVIEW && review!=null && review.selection==selection) {
            Text(review.text)
            if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(review,control)}) {Text(text("taskCancelFakeSubmit"))}
        } else {
            OutlinedTextField(value=state.text,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskCancelReasonLabel"))},isError=error!=null,minLines=4,modifier=Modifier.fillMaxWidth().focusRequester(focus),supportingText={error?.let {Text(it,modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}})
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);if(model.state.problem!=null)focus.requestFocus()}}) {Text(text("clientDraftReview"))}
        }
        if(!model.submissionBlocked)TextButton(modifier=Modifier.semantics {contentDescription=text("taskCancelReasonDraftTitle")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
    }
    if(question!=null)AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskCancelReasonDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}){Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskCancelReasonDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftCancel")},onClick={model.dismissClear(question)}){Text(text("clientDraftCancel"))}})
}
