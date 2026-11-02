package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskDraftAppointmentPickerContent(model:TaskDraftModel,read:TaskAppointmentPickerModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    val owner=model.appointmentPickerOwner;val control=read.control;val input=read.inputControl;val state=read.state
    fun text(key:String)=copy[key] ?: key
    fun label(title:String?,id:Int)=(title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #$id"
    val pickerScope=text("taskDraftTitle")+": "+text("taskDraftAppointment")
    val readScope=pickerScope+(if(state.selectedID==null)"" else ": "+text("details"))
    if(!isCurrent() || !model.matchesAppointmentPicker(owner))return
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("taskDraftAppointment"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        if(state.selectedID!=null) {
            if(state.detailLoading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null) {Text(text(TaskAppointmentReadFeedback.copyKey(state.problem)),modifier=Modifier.semantics {contentDescription=readScope+": "+text(TaskAppointmentReadFeedback.copyKey(state.problem));liveRegion=LiveRegionMode.Polite});TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent() && model.matchesAppointmentPicker(owner))read.retryDetail(control)}) {Text(text("retry"))}}
            else read.choice(control)?.let {choice->
                Text(label(choice.title,choice.id));Text(text("status")+": "+choice.status)
                choice.startAt?.let {Text(text("intervalStart")+": "+it)};choice.endAt?.let {Text(text("intervalEnd")+": "+it)}
                Button(onClick={if(isCurrent())model.confirmAppointment(owner,control)}) {Text(text("taskDraftAppointmentUse"))}
            }
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent() && model.matchesAppointmentPicker(owner))read.backDetail(control)}) {Text(text("back"))}
        } else {
            OutlinedTextField(value=state.day,onValueChange={if(isCurrent() && model.matchesAppointmentPicker(owner))read.updateDay(it,input=input)},label={Text(text("taskDraftAppointmentDay"))},enabled=!state.loading,singleLine=true,isError=state.day.isNotEmpty() && !TaskAppointmentDay.valid(state.day),supportingText={if(state.day.isNotEmpty() && !TaskAppointmentDay.valid(state.day))Text(text("taskDraftAppointmentDayIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})},modifier=Modifier.fillMaxWidth())
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},onClick={if(isCurrent() && model.matchesAppointmentPicker(owner))read.read(control)},enabled=read.canRead) {Text(text("searchSubmit"))}
            if(state.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null)Text(text(TaskAppointmentReadFeedback.copyKey(state.problem)),modifier=Modifier.semantics {contentDescription=readScope+": "+text(TaskAppointmentReadFeedback.copyKey(state.problem));liveRegion=LiveRegionMode.Polite})
            else if(state.loaded) {
                Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()))
                if(state.partial)Text(text("partial"));if(state.items.isEmpty())Text(text("noResults"))
                state.items.forEach {row->TextButton(onClick={if(isCurrent() && model.matchesAppointmentPicker(owner))read.open(row.id,control)}) {Text(label(row.title,row.id))}}
            }
        }
        TextButton(modifier=Modifier.semantics {contentDescription=pickerScope+": "+text("clientDraftCancel")},onClick={if(isCurrent())model.closeAppointmentPicker(owner)}) {Text(text("clientDraftCancel"))}
    }
}
