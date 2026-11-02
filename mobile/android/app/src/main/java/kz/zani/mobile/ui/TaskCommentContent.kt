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

@Composable fun TaskCommentEntry(model: TaskCommentModel,context: TaskCommentContext,copy: Map<String,String>,isCurrent:()->Boolean,onOpen: (TaskCommentRead)->Unit=model::open) {
    val entry=model.entryControl
    if(isCurrent() && entry!=null && entry.read.context==context)TextButton(onClick={if(isCurrent() && model.entryControl==entry)onOpen(entry.read)}) {Text(copy["taskCommentDraftTitle"] ?: "taskCommentDraftTitle")}
}
@Composable fun TaskCommentContent(model: TaskCommentModel,selection: TaskCommentSelection,copy: Map<String,String>,modifier: Modifier,isCurrent:()->Boolean) {
    fun text(key: String)=copy[key] ?: key
    val state=model.state;val control=model.control;val input=model.inputControl;val returnControl=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection || !state.available)return
    val focus=remember(selection) {FocusRequester()}
    BackHandler {if(isCurrent())model.back(expected=returnControl)}
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("taskCommentDraftTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("clientDraftOnly"));TextButton(modifier=Modifier.semantics {contentDescription=text("taskCommentDraftTitle")+": "+text("back")},onClick={if(isCurrent())model.back(expected=returnControl)}) {Text(text("back"))}
        val review=state.review
        val submission=model.submission
        if(model.submissionBlocked) {
            if(submission!=null) {
                Text(submission.attempt.text)
                val key=when(submission.phase) {
                    TaskCommentAttemptPhase.PENDING->"taskCommentFakePending"
                    TaskCommentAttemptPhase.CONFIRMED->"taskCommentFakeConfirmed"
                    TaskCommentAttemptPhase.REJECTED->"taskCommentFakeRejected"
                    TaskCommentAttemptPhase.UNKNOWN->"taskCommentFakeUnknown"
                }
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(submission.phase==TaskCommentAttemptPhase.CONFIRMED || submission.phase==TaskCommentAttemptPhase.REJECTED)Button(modifier=Modifier.semantics {contentDescription=text("taskCommentDraftTitle")+": "+text(if(submission.phase==TaskCommentAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,submission)}) {Text(text(if(submission.phase==TaskCommentAttemptPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if(state.phase==TaskCommentPhase.REVIEW && review!=null && review.selection==selection) {
            Text(text("clientDraftReview"),style=MaterialTheme.typography.titleSmall);Text(review.text)
            if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(review,control)}) {Text(text("taskCommentFakeSubmit"))}
        } else {
            OutlinedTextField(value=state.text,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskCommentDraftText"))},minLines=5,isError=state.emptyError,modifier=Modifier.fillMaxWidth().focusRequester(focus),supportingText={if(state.emptyError)Text(text("replyDraftRequired"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);if(model.state.emptyError)focus.requestFocus()}}) {Text(text("clientDraftReview"))}
        }
        if(!model.submissionBlocked)TextButton(modifier=Modifier.semantics {contentDescription=text("taskCommentDraftTitle")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
    }
    if(question!=null)AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskCommentDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}){Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskCommentDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftCancel")},onClick={model.dismissClear(question)}){Text(text("clientDraftCancel"))}})
}
