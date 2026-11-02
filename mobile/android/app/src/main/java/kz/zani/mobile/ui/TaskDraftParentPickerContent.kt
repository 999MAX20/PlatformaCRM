package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskDraftParentPickerContent(model:TaskDraftModel,read:TaskParentPickerModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    val owner=model.parentPickerOwner;val control=read.control;val state=read.state
    fun text(key:String)=copy[key] ?: key
    fun error(problem:ReadProblem)=text(when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})
    fun label(title:String?,id:Int)=(title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #$id"
    val pickerScope=text("taskDraftTitle")+": "+text("taskDraftParent")
    val readScope=pickerScope+(if(state.selectedID==null)"" else ": "+text("details"))
    if(!isCurrent() || !model.matchesParentPicker(owner))return
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("taskDraftParent"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        if(state.selectedID!=null) {
            if(state.detailLoading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null) {Text(error(state.problem),modifier=Modifier.semantics {contentDescription=readScope+": "+error(state.problem);liveRegion=LiveRegionMode.Polite});TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent() && model.matchesParentPicker(owner))read.retryDetail(control)}) {Text(text("retry"))}}
            else read.choice(control)?.let {choice->
                Text(label(choice.title,choice.id));Text(text("status")+": "+choice.status)
                Button(onClick={if(isCurrent())model.confirmParent(owner,control)}) {Text(text("taskDraftParentUse"))}
            }
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent() && model.matchesParentPicker(owner))read.backDetail(control)}) {Text(text("back"))}
        } else {
            Button(onClick={if(isCurrent() && model.matchesParentPicker(owner))read.read(control)},enabled=read.canRead) {Text(text("taskDraftParentLoad"))}
            if(state.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            else if(state.problem!=null)Text(error(state.problem),modifier=Modifier.semantics {contentDescription=readScope+": "+error(state.problem);liveRegion=LiveRegionMode.Polite})
            else if(state.loaded) {
                Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()))
                if(state.partial)Text(text("partial"));if(state.items.isEmpty())Text(text("noResults"))
                state.items.forEach {row->TextButton(onClick={if(isCurrent() && model.matchesParentPicker(owner))read.open(row.id,control)}) {Text(label(row.title,row.id))}}
            }
        }
        TextButton(modifier=Modifier.semantics {contentDescription=pickerScope+": "+text("clientDraftCancel")},onClick={if(isCurrent())model.closeParentPicker(owner)}) {Text(text("clientDraftCancel"))}
    }
}
