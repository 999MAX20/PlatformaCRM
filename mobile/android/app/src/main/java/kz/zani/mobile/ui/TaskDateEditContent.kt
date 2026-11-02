package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskDateEditContent(model:TaskDateEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskDateEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    fun field(value:TaskDateField)=text(if(value==TaskDateField.DUE)"taskDue" else "taskReminderAt")
    fun mode(value:TaskDateMode)=text(if(value==TaskDateMode.SET)"taskDateSet" else "taskDateRemove")
    val control=model.control;val input=model.inputControl;val question=model.clearConfirmation
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskDateAction"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(field(record.attempt.review.change.field)+" · "+mode(record.attempt.review.change.mode))
                        if(record.attempt.review.change.mode==TaskDateMode.SET)Text(record.attempt.review.change.raw)
                        val key=when(record.phase){TaskDateEditPhase.PENDING->"taskCommentFakePending";TaskDateEditPhase.CONFIRMED->"taskDateFakeConfirmed";TaskDateEditPhase.REJECTED->"taskDateFakeRejected";TaskDateEditPhase.UNKNOWN->"taskDateFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        record.result?.let {Text(text("taskDateReturned")+": "+(it.value ?: text("taskScheduleNotSet")))}
                        if(record.phase==TaskDateEditPhase.CONFIRMED || record.phase==TaskDateEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskDateFakeConfirmed"))
                model.review!=null->{val change=model.review!!.change;Text(field(change.field)+" · "+mode(change.mode));if(change.mode==TaskDateMode.SET)Text(change.raw);Text(text("taskDateContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskDateFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.editing->{Text(text("taskDateChooseField"));TaskDateField.entries.forEach {option->FilterChip(selected=model.draft.field==option,onClick={if(isCurrent())model.select(option,control)},label={Text(field(option))})}
                    if(model.draft.field!=null) {
                        FilterChip(selected=model.draft.mode==TaskDateMode.SET,onClick={if(isCurrent())model.choose(TaskDateMode.SET,control)},label={Text(mode(TaskDateMode.SET))})
                        FilterChip(selected=model.draft.mode==TaskDateMode.CLEAR,onClick={if(isCurrent())model.choose(TaskDateMode.CLEAR,control)},label={Text(mode(TaskDateMode.CLEAR))})
                        if(model.draft.mode==TaskDateMode.SET)OutlinedTextField(value=model.draft.raw,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("taskSnoozeInput"))},singleLine=true,modifier=Modifier.fillMaxWidth(),isError=model.showsIssue,supportingText={if(model.showsIssue)Text(text("taskDateInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
                    }
                    if(model.showsIssue && (model.draft.field==null || model.draft.mode!=TaskDateMode.SET))Text(text("taskDateInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
                model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskDateAction"))}
            }
        }
        if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskDateAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
    }
}
