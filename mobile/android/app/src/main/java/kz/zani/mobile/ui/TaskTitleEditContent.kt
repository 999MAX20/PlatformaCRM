package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskTitleEditContent(model:TaskTitleEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskTitleEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val input=model.inputControl;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskTitleEditAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(text("taskTitleEditRaw")+": "+record.attempt.review.value.raw);Text(text("taskTitleEditProposed")+": "+record.attempt.review.value.title)
                        val key=when(record.phase) {TaskTitleEditPhase.PENDING->"taskCommentFakePending";TaskTitleEditPhase.CONFIRMED->"taskTitleEditFakeConfirmed";TaskTitleEditPhase.REJECTED->"taskTitleEditFakeRejected";TaskTitleEditPhase.UNKNOWN->"taskTitleEditFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskTitleEditReturned")+": "+it.title)}
                        if(record.phase==TaskTitleEditPhase.CONFIRMED || record.phase==TaskTitleEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskTitleEditFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("taskTitleEditRaw")+": "+review.value.raw);Text(text("taskTitleEditProposed")+": "+review.value.title);Text(text("taskTitleEditContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskTitleEditFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{OutlinedTextField(value=model.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskTitle"))},singleLine=true,modifier=Modifier.fillMaxWidth(),isError=model.showsIssue,supportingText={if(model.showsIssue)Text(text("taskTitleEditInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskTitleEditAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskTitleEditAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
