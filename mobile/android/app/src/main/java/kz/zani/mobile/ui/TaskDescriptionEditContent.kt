package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskDescriptionEditContent(model:TaskDescriptionEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskDescriptionEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val input=model.inputControl;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskDescriptionEditAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            model.mode?.let {Text(text(if(it==TaskDescriptionMode.REPLACE)"taskDescriptionEditReplace" else "taskDescriptionEditRemove"))}
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(text("taskDescriptionEditRaw")+": "+record.attempt.review.value.raw);Text(text("taskDescriptionEditProposed")+": "+record.attempt.review.value.description)
                        val key=when(record.phase) {TaskDescriptionEditPhase.PENDING->"taskCommentFakePending";TaskDescriptionEditPhase.CONFIRMED->"taskDescriptionEditFakeConfirmed";TaskDescriptionEditPhase.REJECTED->"taskDescriptionEditFakeRejected";TaskDescriptionEditPhase.UNKNOWN->"taskDescriptionEditFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskDescriptionEditReturned")+": "+it.description)}
                        if(record.phase==TaskDescriptionEditPhase.CONFIRMED || record.phase==TaskDescriptionEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskDescriptionEditFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("taskDescriptionEditRaw")+": "+review.value.raw);Text(text("taskDescriptionEditProposed")+": "+review.value.description);Text(text("taskDescriptionEditContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskDescriptionEditFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{TaskDescriptionMode.entries.forEach {value->FilterChip(selected=model.mode==value,onClick={if(isCurrent())model.choose(value,control)},label={Text(text(if(value==TaskDescriptionMode.REPLACE)"taskDescriptionEditReplace" else "taskDescriptionEditRemove"))})}
                    if(model.mode==TaskDescriptionMode.REPLACE)OutlinedTextField(value=model.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskDescriptionEditRaw"))},minLines=3,modifier=Modifier.fillMaxWidth(),isError=model.showsIssue,supportingText={if(model.showsIssue)Text(text("taskDescriptionEditInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
                    if(model.showsIssue && model.mode!=TaskDescriptionMode.REPLACE)Text(text("taskDescriptionEditInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskDescriptionEditAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskDescriptionEditAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
