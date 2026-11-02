package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskPriorityEditContent(model:TaskPriorityEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskPriorityEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    fun priority(raw:String)=text(when(raw){"low"->"priorityLow";"normal"->"priorityNormal";"high"->"priorityHigh";"urgent"->"priorityUrgent";else->"notAvailable"})
    val control=model.control;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskPriorityEditAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(priority(record.attempt.review.value.raw))
                        val key=when(record.phase) {TaskPriorityEditPhase.PENDING->"taskCommentFakePending";TaskPriorityEditPhase.CONFIRMED->"taskPriorityEditFakeConfirmed";TaskPriorityEditPhase.REJECTED->"taskPriorityEditFakeRejected";TaskPriorityEditPhase.UNKNOWN->"taskPriorityEditFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskPriorityEditReturned")+": "+priority(it.priority))}
                        if(record.phase==TaskPriorityEditPhase.CONFIRMED || record.phase==TaskPriorityEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskPriorityEditFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(priority(review.value.raw));Text(text("taskPriorityEditContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskPriorityEditFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{TaskDraftValues.priorities.forEach {value->FilterChip(selected=model.raw==value,onClick={if(isCurrent())model.choose(value,control)},label={Text(priority(value))})}
                    if(model.showsIssue)Text(text("taskPriorityEditInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskPriorityEditAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskPriorityEditAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
