package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskSnoozeContent(model:TaskSnoozeModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskSnoozeControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val input=model.inputControl;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskSnoozeAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.value.raw)
                        val key=when(record.phase) {TaskSnoozePhase.PENDING->"taskCommentFakePending";TaskSnoozePhase.CONFIRMED->"taskSnoozeFakeConfirmed";TaskSnoozePhase.REJECTED->"taskSnoozeFakeRejected";TaskSnoozePhase.UNKNOWN->"taskSnoozeFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskSnoozeReturned")+": "+it.snoozedUntil)}
                        if(record.phase==TaskSnoozePhase.CONFIRMED || record.phase==TaskSnoozePhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskSnoozeFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(review.value.raw);Text(text("taskSnoozeContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskSnoozeFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{OutlinedTextField(value=model.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskSnoozeInput"))},singleLine=true,modifier=Modifier.fillMaxWidth(),isError=model.showsIssue,supportingText={if(model.showsIssue)Text(text("taskSnoozeInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskSnoozeAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskSnoozeAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
