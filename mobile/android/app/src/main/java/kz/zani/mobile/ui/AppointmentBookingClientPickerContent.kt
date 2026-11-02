package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp

@Composable fun AppointmentBookingClientPickerContent(model:AppointmentBookingModel,search:ClientSearchModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    fun label(title:String?,id:Int)=(title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #$id"
    val owner=model.clientPickerOwner;val state=search.state;val control=search.control;val input=search.inputControl;val profile=search.profile.state
    val pickerScope=text("bookingTitle")+": "+text("clients")
    val readScope=pickerScope+": "+text(if(state.profileSelection==null)"clientServerSearch" else "details")
    if(!isCurrent() || !model.matchesClientPicker(owner))return
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("client"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        val selected=state.profileSelection
        if(selected!=null) {
            when {
                profile.loading->CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
                profile.problem!=null->{Text(text(if(profile.problem==kz.zani.mobile.core.ReadProblem.DENIED)"denied" else "unavailable"),modifier=Modifier.semantics {contentDescription=readScope+": "+text(if(profile.problem==kz.zani.mobile.core.ReadProblem.DENIED)"denied" else "unavailable")});Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent() && model.matchesClientPicker(owner))search.retryProfile(control)}) {Text(text("retry"))}}
                profile.detail!=null && profile.detail.validFor(selected.selection.context.business,selected.id)->{
                    Text(label(profile.detail.client.title,profile.detail.client.id))
                    Button(onClick={if(isCurrent())model.confirmClient(owner,control)}) {Text(text("bookingUseClient"))}
                }
            }
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent() && model.matchesClientPicker(owner))search.backProfile(control)}) {Text(text("back"))}
        } else {
            OutlinedTextField(value=state.query,onValueChange={if(isCurrent() && model.matchesClientPicker(owner))search.update(it,input)},label={Text(text("clientSearch"))},singleLine=true)
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},enabled=!state.loading,onClick={if(isCurrent() && model.matchesClientPicker(owner))search.submit(control)}) {Text(text("searchSubmit"))}
            when {
                state.loading->CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
                state.problem!=null->{Text(text(if(state.problem==kz.zani.mobile.core.ReadProblem.DENIED)"denied" else "unavailable"),modifier=Modifier.semantics {contentDescription=readScope+": "+text(if(state.problem==kz.zani.mobile.core.ReadProblem.DENIED)"denied" else "unavailable")});Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent() && model.matchesClientPicker(owner))search.submit(control)}) {Text(text("retry"))}}
                state.loaded->{
                    Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()),style=MaterialTheme.typography.labelSmall)
                    if(state.partial)Text(text("partial"))
                    if(state.showsEmpty)Text(text("noResults"))
                    state.items.forEach {client->TextButton(onClick={if(isCurrent() && model.matchesClientPicker(owner))search.openClient(client.id,control)}) {Text(label(client.title,client.id))}}
                }
            }
        }
        Button(modifier=Modifier.semantics {contentDescription=pickerScope+": "+text("clientDraftCancel")},onClick={if(isCurrent())model.closeClientPicker(owner)}) {Text(text("clientDraftCancel"))}
    }
}
