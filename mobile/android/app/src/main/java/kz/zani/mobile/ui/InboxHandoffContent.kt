package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun InboxHandoffContent(model:InboxHandoffModel,selection:ReplyDraftSelection,copy:Map<String,String>,modifier:Modifier=Modifier,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val state=model.state;val control=model.control;val input=model.inputControl;val returned=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection)return
    val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    BackHandler {if(isCurrent())model.back(returned)}
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("handoffTestAction"),style=MaterialTheme.typography.titleMedium)
        TextButton(modifier=Modifier.semantics {contentDescription=text("handoffTestAction")+": "+text("back")},onClick={if(isCurrent())model.back(returned)}) {Text(text("back"))}
        Text(text("handoffLocalOnly"));Text(text("handoffNoReturnProof"),style=MaterialTheme.typography.bodySmall)
        if(model.blocked) {
            val record=model.record
            if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                Text(text("handoffTestResult"),style=MaterialTheme.typography.titleSmall);Text(record.attempt.review.value.reason.ifEmpty {text("handoffBlankReason")})
                Text(text(when(record.phase){HandoffPhase.PENDING->"taskCommentFakePending";HandoffPhase.CONFIRMED->"handoffTestConfirmed";HandoffPhase.REJECTED->"handoffTestRejected";HandoffPhase.UNKNOWN->"handoffTestUnknown"}),modifier=announcement)
                if(record.phase==HandoffPhase.CONFIRMED || record.phase==HandoffPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("handoffTestAction")+": "+text(if(record.phase==HandoffPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text(if(record.phase==HandoffPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
            }
        } else if(state.phase==ReplyDraftPhase.REVIEW && state.review!=null) {
            val review=state.review;Text(text("clientDraftReview"),style=MaterialTheme.typography.titleSmall);Text(review.value.reason.ifEmpty {text("handoffBlankReason")})
            if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(review,control)}) {Text(text("handoffTestSubmit"))}
        } else {
            OutlinedTextField(value=state.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("handoffReason"))},isError=state.inputError,minLines=3,modifier=Modifier.fillMaxWidth(),supportingText={Text(text(if(state.inputError)"handoffReasonIssue" else "handoffReasonOptional"),modifier=announcement)})
            Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
        }
        if(!model.blocked)TextButton(modifier=Modifier.semantics {contentDescription=text("handoffTestAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
    }
    if(question!=null)AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("handoffTestAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("handoffTestAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftCancel")},onClick={model.dismissClear(question)}) {Text(text("clientDraftCancel"))}})
}
