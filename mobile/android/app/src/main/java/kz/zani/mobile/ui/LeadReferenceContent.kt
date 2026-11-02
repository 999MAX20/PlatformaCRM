package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable fun LeadReferenceContent(model:LeadReferenceModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val s=model.state;val control=model.control;val input=model.input;val scope=rememberCoroutineScope()
    val readScope=s.selectedID?.let {text("leadReferenceTitle")+" #$it"} ?: text("leadReferenceSearch")
    if(!isCurrent() || !s.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("leadReferenceTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("leadReferenceReadOnly"),style=MaterialTheme.typography.labelSmall)
        s.choice?.let {Text(text("leadReferenceChosen")+": "+it.detail.lead.title+" · #${it.detail.lead.id}");TextButton(enabled=!model.controlsBlocked(),onClick={if(isCurrent())model.clearChoice(control)}) {Text(text("leadReferenceClearChoice"))}}
        if(s.selectedID!=null) {
            val detail=s.detail
            if(s.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading")}) else if(s.problem!=null) {Text(text(when(s.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(s.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notFound";else->"unavailable"});liveRegion=LiveRegionMode.Polite});TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},enabled=!model.controlsBlocked(),onClick={scope.launch {if(isCurrent())model.open(s.selectedID,control)}}) {Text(text("retry"))}}
            else if(detail!=null) {Text(detail.lead.title+" · #${detail.lead.id}");Text(text("leadReferenceClient")+": "+detail.lead.client.name+" · #${detail.lead.client_id}");Text(detail.lead.status);Text(detail.lead.source);Text(detail.message);TextButton(enabled=!model.controlsBlocked() && s.canUse,onClick={if(isCurrent())model.use(control)}) {Text(text("leadReferenceUse"))}}
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},enabled=!model.controlsBlocked(),onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            OutlinedTextField(value=s.query,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("leadReferenceSearch"))},singleLine=true,enabled=!model.controlsBlocked() && !s.loading,modifier=Modifier.fillMaxWidth())
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchSubmit")},enabled=!model.controlsBlocked() && !s.loading,onClick={scope.launch {if(isCurrent())model.search(control)}}) {Text(text("searchSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchClear")},enabled=!model.controlsBlocked() && !s.loading,onClick={if(isCurrent())model.clear(control)}) {Text(text("searchClear"))}
            if(s.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading")}) else if(s.problem!=null)Text(text(when(s.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(s.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notFound";else->"unavailable"});liveRegion=LiveRegionMode.Polite})
            else if(s.loaded){Text(text("clientSearchCount").replace("{loaded}",s.items.size.toString()).replace("{total}",s.total.toString()));if(s.partial)Text(text("partial"));if(s.showsEmpty)Text(text("noResults"));s.items.forEach {row->TextButton(enabled=!model.controlsBlocked(),onClick={scope.launch {if(isCurrent())model.open(row.id,control)}}) {Text(row.title+" · #${row.id}")}}}
        }
    }
}
