package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.ReadProblem

@Composable fun MemberReferenceContent(model:MemberReferenceModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val s=model.state;val control=model.control;val input=model.input;val scope=rememberCoroutineScope();val enabled=!model.controlsBlocked()
    val readScope=text("memberReferenceTitle")
    if(!isCurrent() || !s.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("memberReferenceTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("memberReferenceReadOnly"),style=MaterialTheme.typography.labelSmall)
        OutlinedTextField(value=s.rawInput,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("memberReferenceIdentifier"))},enabled=enabled,singleLine=true,isError=s.invalidIdentifier,supportingText={if(s.invalidIdentifier)Text(text("memberReferenceInvalid"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})},modifier=Modifier.fillMaxWidth())
        TextButton(enabled=enabled && s.canRead,onClick={scope.launch {if(isCurrent())model.read(control)}}) {Text(text("memberReferenceRead"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("searchClear")},enabled=enabled,onClick={if(isCurrent())model.clear(control)}) {Text(text("searchClear"))}
        if(s.loading)CircularProgressIndicator(modifier=Modifier.semantics {contentDescription=readScope+": "+text("loading")}) else if(s.problem!=null)Text(text(when(s.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(s.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"});liveRegion=LiveRegionMode.Polite})
        else s.source?.let {source->Text((source.user.displayName ?: text("notAvailable"))+" · #${source.id}");Text(source.user.email);Text(text(if(source.isActive)"memberReferenceActive" else "memberReferenceInactive"));TextButton(enabled=enabled && model.canUse,onClick={if(isCurrent())model.use(control)}) {Text(text("memberReferenceUse"))}}
        s.choice?.let {Text(text("memberReferenceChosen")+": "+(it.source.user.displayName ?: text("notAvailable")));TextButton(enabled=enabled,onClick={if(isCurrent())model.clearChoice(control)}) {Text(text("memberReferenceClearChoice"))}}
    }
}
