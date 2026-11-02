package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskClientEditContent(model:TaskClientEditModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(TaskClientEditControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    fun original(value:TaskClientOriginal)=when(value){TaskClientOriginal.Unknown->text("taskClientOriginalUnknown");TaskClientOriginal.NotSet->text("taskScheduleNotSet");is TaskClientOriginal.Client->"#${value.id}"}
    fun mode(value:TaskClientEditMode?)=text(if(value==TaskClientEditMode.SET)"taskClientSet" else "taskClientRemove")
    fun choice(value:TaskDraftClientChoice?)=value?.let {(it.title?.takeIf {s->s.isNotEmpty()} ?: text("notAvailable"))+" · #${it.id}"} ?: text("taskDraftClientOmit")
    val control=model.control;val question=model.clearConfirmation
    if(!isCurrent() || !model.canPresent || control==null)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("taskClientAction"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
        Text(text("taskClientOriginal")+": "+original(control.source.original))
        when {
            model.blocked->{val record=model.submission
                if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                    Text(mode(record.attempt.review.draft.mode));if(record.attempt.review.draft.mode==TaskClientEditMode.SET){Text(choice(record.attempt.review.draft.choice));Text(record.attempt.review.draft.query)}
                    val key=when(record.phase){TaskClientEditPhase.PENDING->"taskCommentFakePending";TaskClientEditPhase.CONFIRMED->"taskClientFakeConfirmed";TaskClientEditPhase.REJECTED->"taskClientFakeRejected";TaskClientEditPhase.UNKNOWN->"taskClientFakeUnknown"}
                    Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                    record.result?.let {Text(text("taskClientReturned")+": "+(it.value?.let {id->"#$id"} ?: text("taskScheduleNotSet")))}
                    if(record.phase==TaskClientEditPhase.CONFIRMED || record.phase==TaskClientEditPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                }
            }
            model.consumed->Text(text("taskClientFakeConfirmed"))
            model.review!=null->{val draft=model.review!!.draft;Text(mode(draft.mode));if(draft.mode==TaskClientEditMode.SET){Text(choice(draft.choice));Text(draft.query)};Text(text("taskClientContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskClientFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
            model.editing->{
                FilterChip(selected=model.draft.mode==TaskClientEditMode.SET,onClick={if(isCurrent())model.choose(TaskClientEditMode.SET,control)},label={Text(mode(TaskClientEditMode.SET))})
                FilterChip(selected=model.draft.mode==TaskClientEditMode.CLEAR,onClick={if(isCurrent())model.choose(TaskClientEditMode.CLEAR,control)},label={Text(mode(TaskClientEditMode.CLEAR))})
                if(model.draft.mode==TaskClientEditMode.SET){Text(choice(model.draft.choice));TaskClientEditPickerContent(model,copy,isCurrent)}
                if(model.showsIssue)Text(text("taskClientInputIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                Button(onClick={if(isCurrent())model.prepare(control)}) {Text(text("clientDraftReview"))}
                TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) {Text(text("clientDraftClear"))}
                TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
            }
            model.canOpen->TextButton(onClick={if(isCurrent())open(control)}) {Text(text("taskClientAction"))}
        }
    }
    if(question!=null)AlertDialog(onDismissRequest={if(isCurrent())model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}) {Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("taskClientAction")+": "+text("clientDraftClearQuestion")+": "+text("back")},onClick={if(isCurrent())model.dismissClear(question)}) {Text(text("back"))}})
}
@Composable private fun TaskClientEditPickerContent(model:TaskClientEditModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    val read=model.picker;val state=read.state;val profile=read.profile.state;val child=read.control;val parent=model.control;val input=model.inputControl
    fun text(key:String)=copy[key] ?: key
    fun label(title:String?,id:Int)=(title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #$id"
    fun error(problem:ReadProblem)=text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})
    val readScope=text("taskClientAction")+": "+text(if(state.profileSelection==null)"clientServerSearch" else "details")
    if(!isCurrent() || !model.canPrepare || model.draft.mode!=TaskClientEditMode.SET)return
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        val selected=state.profileSelection
        if(selected!=null) {
            if(profile.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(profile.problem!=null){Text(error(profile.problem),modifier=Modifier.semantics {contentDescription=readScope+": "+error(profile.problem);liveRegion=LiveRegionMode.Polite});TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())model.retryClient(parent,child)}) {Text(text("retry"))}}
            else if(profile.detail!=null && profile.detail.validFor(selected.selection.context.business,selected.id)) {Text(label(profile.detail.client.title,profile.detail.client.id));Button(onClick={if(isCurrent())model.useClient(parent,child)}) {Text(text("taskDraftClientUse"))}}
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.backClient(parent,child)}) {Text(text("back"))}
        } else {
            OutlinedTextField(value=model.draft.query,onValueChange={if(isCurrent())model.updateQuery(it,input)},label={Text(text("clientSearch"))},enabled=!state.loading,singleLine=true,modifier=Modifier.fillMaxWidth())
            Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},onClick={if(isCurrent())model.readClients(parent,child)},enabled=!state.loading) {Text(text("searchSubmit"))}
            if(state.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null)Text(error(state.problem),modifier=Modifier.semantics {contentDescription=readScope+": "+error(state.problem);liveRegion=LiveRegionMode.Polite})
            else if(state.loaded){Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()));if(state.partial)Text(text("partial"));if(state.showsEmpty)Text(text("noResults"));state.items.forEach {row->TextButton(onClick={if(isCurrent())model.openClient(row.id,parent,child)}) {Text(label(row.title,row.id))}}}
        }
    }
}
