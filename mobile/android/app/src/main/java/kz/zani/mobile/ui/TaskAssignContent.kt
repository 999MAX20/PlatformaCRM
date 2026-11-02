package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskAssignContent(model:TaskAssignModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskAssignControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val input=model.inputControl;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskAssignAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.value.raw)
                        val key=when(record.phase) {TaskAssignPhase.PENDING->"taskCommentFakePending";TaskAssignPhase.CONFIRMED->"taskAssignFakeConfirmed";TaskAssignPhase.REJECTED->"taskAssignFakeRejected";TaskAssignPhase.UNKNOWN->"taskAssignFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskAssignReturned")+": "+it.assignee);Text(text("status")+": "+text(if(it.status=="open")"taskOpen" else "taskInProgress"))}
                        if(record.phase==TaskAssignPhase.CONFIRMED || record.phase==TaskAssignPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskAssignFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(review.value.raw);Text(text("taskAssignContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskAssignFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{Text(text("taskAssignSyntheticMembers"),style=MaterialTheme.typography.labelSmall);model.eligibleMembers.forEach {id->TextButton(onClick={if(isCurrent())model.select(id,input)}) {Text(id.toString())}};OutlinedTextField(value=model.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskAssignInput"))},singleLine=true,modifier=Modifier.fillMaxWidth())
                    if(model.showsIssue)Text(text("taskAssignInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskAssignAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskAssignAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
