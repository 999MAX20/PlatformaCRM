package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskAppointmentEditContent(model:TaskAppointmentEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskAppointmentEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    fun original(value:TaskAppointmentOriginal)=when(value){TaskAppointmentOriginal.Unknown->text("taskAppointmentOriginalUnknown");TaskAppointmentOriginal.NotSet->text("taskScheduleNotSet");is TaskAppointmentOriginal.Appointment->"#${value.id}"}
    fun mode(value:TaskAppointmentEditMode?)=text(if(value==TaskAppointmentEditMode.SET)"taskAppointmentSet" else "taskAppointmentRemove")
    fun choice(value:TaskDraftAppointmentChoice?)=value?.let {(it.title?.takeIf {s->s.isNotEmpty()} ?: text("notAvailable"))+" · #${it.id}"} ?: text("taskDraftAppointmentOmit")
    val control=model.control;val question=model.clearConfirmation
    if(!isCurrent() || !model.canPresent || control==null)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("taskAppointmentAction"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
        Text(text("taskAppointmentOriginal")+": "+original(control.source.original))
        when {
            model.blocked->{val record=model.submission
                if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                    Text(mode(record.attempt.review.draft.mode));if(record.attempt.review.draft.mode==TaskAppointmentEditMode.SET){Text(choice(record.attempt.review.draft.choice));Text(record.attempt.review.draft.day)}
                    val key=when(record.phase){TaskAppointmentEditPhase.PENDING->"taskCommentFakePending";TaskAppointmentEditPhase.CONFIRMED->"taskAppointmentFakeConfirmed";TaskAppointmentEditPhase.REJECTED->"taskAppointmentFakeRejected";TaskAppointmentEditPhase.UNKNOWN->"taskAppointmentFakeUnknown"}
                    Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    record.result?.let {Text(text("taskAppointmentReturned")+": "+(it.value?.let {id->"#$id"} ?: text("taskScheduleNotSet")))}
                    if(record.phase==TaskAppointmentEditPhase.CONFIRMED || record.phase==TaskAppointmentEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                }
            }
            model.consumed->Text(text("taskAppointmentFakeConfirmed"))
            model.review!=null->{val draft=model.review!!.draft;Text(mode(draft.mode));if(draft.mode==TaskAppointmentEditMode.SET){Text(choice(draft.choice));Text(draft.day)};Text(text("taskAppointmentContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskAppointmentFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
            model.editing->{
                FilterChip(selected=model.draft.mode==TaskAppointmentEditMode.SET,onClick={if(isCurrent())model.choose(TaskAppointmentEditMode.SET,control)},label={Text(mode(TaskAppointmentEditMode.SET))})
                FilterChip(selected=model.draft.mode==TaskAppointmentEditMode.CLEAR,onClick={if(isCurrent())model.choose(TaskAppointmentEditMode.CLEAR,control)},label={Text(mode(TaskAppointmentEditMode.CLEAR))})
                if(model.draft.mode==TaskAppointmentEditMode.SET){Text(choice(model.draft.choice));TaskAppointmentEditPickerContent(model,copy,isCurrent)}
                if(model.showsIssue)Text(text("taskAppointmentInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
            }
            model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskAppointmentAction"))}
        }
    }
    if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskAppointmentAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
}
@Composable private fun TaskAppointmentEditPickerContent(model:TaskAppointmentEditModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    val read=model.picker;val state=read.state;val child=read.control;val parent=model.control;val input=model.inputControl
    fun text(key:String)=copy[key] ?: key
    fun label(title:String?,id:Int)=(title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #$id"
    val readScope=text("taskAppointmentAction")+(if(state.selectedID==null)"" else ": "+text("details"))
    if(!isCurrent() || !model.canPrepare || model.draft.mode!=TaskAppointmentEditMode.SET)return
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        if(state.selectedID!=null) {
            if(state.detailLoading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null){Text(text(TaskAppointmentReadFeedback.copyKey(state.problem)),modifier=Modifier.semantics {contentDescription=readScope+": "+text(TaskAppointmentReadFeedback.copyKey(state.problem));liveRegion=LiveRegionMode.Polite});TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())model.retryAppointment(parent,child)}) {Text(text("retry"))}}
            else read.choice(child)?.let {value->Text(label(value.title,value.id));Text(text("status")+": "+value.status);value.startAt?.let {Text(text("intervalStart")+": "+it)};value.endAt?.let {Text(text("intervalEnd")+": "+it)};Button(onClick={if(isCurrent())model.useAppointment(parent,child)}) {Text(text("taskDraftAppointmentUse"))}}
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.backAppointment(parent,child)}) {Text(text("back"))}
        } else {
            OutlinedTextField(value=model.draft.day,onValueChange={if(isCurrent())model.updateDay(it,input)},label={Text(text("taskDraftAppointmentDay"))},enabled=!state.loading,singleLine=true,isError=state.day.isNotEmpty() && !TaskAppointmentDay.valid(state.day),supportingText={if(state.day.isNotEmpty() && !TaskAppointmentDay.valid(state.day))Text(text("taskDraftAppointmentDayIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})},modifier=Modifier.fillMaxWidth())
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},onClick={if(isCurrent())model.readAppointments(parent,child)},enabled=read.canRead) {Text(text("searchSubmit"))}
            if(state.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null)Text(text(TaskAppointmentReadFeedback.copyKey(state.problem)),modifier=Modifier.semantics {contentDescription=readScope+": "+text(TaskAppointmentReadFeedback.copyKey(state.problem));liveRegion=LiveRegionMode.Polite})
            else if(state.loaded){Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()));if(state.partial)Text(text("partial"));if(state.items.isEmpty())Text(text("noResults"));state.items.forEach {row->TextButton(onClick={if(isCurrent())model.openAppointment(row.id,parent,child)}) {Text(label(row.title,row.id))}}}
        }
    }
}
