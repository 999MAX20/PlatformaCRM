package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.ReadProblem

@Composable fun InboxTaskSourceContent(model:InboxTaskSourceModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    fun id(value:Int?)=value?.let {"#$it"} ?: text("inboxTaskSourceNone")
    val s=model.state;val control=model.control;val scope=rememberCoroutineScope();val enabled=!model.controlsBlocked()
    val readScope=text("inboxTaskSourceTitle")
    if(!isCurrent() || !s.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxTaskSourceTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxTaskSourceBoundary"),style=MaterialTheme.typography.labelSmall)
        TextButton(enabled=enabled && model.canRead,onClick={scope.launch {if(isCurrent())model.read(control)}}) {Text(text("inboxTaskSourceRead"))}
        if(s.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading")}) else if(s.problem!=null)Text(text(when(s.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(s.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"});liveRegion=LiveRegionMode.Polite})
        else s.source?.let {Text(text("inboxTaskSourceClient")+": "+id(it.client));Text(text("inboxTaskSourceLead")+": "+id(it.lead));TextButton(enabled=enabled && model.canUse,onClick={if(isCurrent())model.use(control)}) {Text(text("inboxTaskSourceUse"))}}
        if(s.choice!=null){Text(text("inboxTaskSourceChosen"));TextButton(enabled=enabled,onClick={if(isCurrent())model.clearChoice(control)}) {Text(text("inboxTaskSourceClearChoice"))}}
    }
}
