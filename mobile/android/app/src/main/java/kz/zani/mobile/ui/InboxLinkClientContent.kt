package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun InboxLinkClientContent(model:InboxLinkClientModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    fun label(c:TaskDraftClientChoice)=(c.title?.takeIf {it.isNotEmpty()} ?: text("notAvailable"))+" · #${c.id}"
    val control=model.control;val scope=rememberCoroutineScope();val record=model.record;val review=model.review
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxLinkTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxLinkBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=text("loading")})
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"}))}
        if(record!=null) {
            Text(text(when(record.phase){InboxLinkClientPhase.PENDING->"inboxLinkPending";InboxLinkClientPhase.RESPONSE->"inboxLinkResponse";InboxLinkClientPhase.REJECTED->"inboxLinkRejected";InboxLinkClientPhase.UNKNOWN->"inboxLinkUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text(text("inboxLinkOriginal")+": "+(record.attempt.review.source.client?.let {"#$it"} ?: text("inboxLinkNotLinked")));Text(text("inboxLinkCandidate")+": "+label(record.attempt.review.candidate.choice));Text(record.attempt.review.candidate.rawQuery)
            if(record.phase in listOf(InboxLinkClientPhase.RESPONSE,InboxLinkClientPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLinkTitle")+": "+text("inboxLinkAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxLinkAcknowledge"))}
        } else if(model.blocked)Text(text("inboxLinkRetained"))
        else if(review!=null) {
            Text(text("inboxLinkOriginal")+": "+(review.source.client?.let {"#$it"} ?: text("inboxLinkNotLinked")));Text(label(review.candidate.choice));Text(review.candidate.rawQuery)
            TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxLinkSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLinkTitle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else if(model.editing) {
            val picker=model.picker
            if(picker!=null) {
                val state=picker.state;val profile=picker.profile.state;val child=picker.control;val input=model.input;val selected=state.profileSelection
                if(model.canEdit) {
                    if(selected!=null) {
                        if(profile.loading)CircularProgressIndicator() else if(profile.problem!=null){Text(text("unavailable"));TextButton(onClick={if(isCurrent())model.retryClient(control,child)}) {Text(text("retry"))}}
                        else if(profile.detail!=null && profile.detail.validFor(selected.selection.context.business,selected.id)){Text((profile.detail.client.title ?: text("notAvailable"))+" · #${profile.detail.client.id}");TextButton(onClick={if(isCurrent())model.useClient(control,child)}) {Text(text("inboxLinkUse"))}}
                        TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLinkTitle")+": "+text("details")+": "+text("back")},onClick={if(isCurrent())model.backClient(control,child)}) {Text(text("back"))}
                    } else {
                        OutlinedTextField(value=state.query,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("clientSearch"))},enabled=!state.loading,singleLine=true,modifier=Modifier.fillMaxWidth())
                        TextButton(enabled=!state.loading,onClick={if(isCurrent())model.search(control,child)}) {Text(text("searchSubmit"))}
                        if(state.loading)CircularProgressIndicator() else if(state.problem!=null)Text(text("unavailable")) else if(state.loaded){Text(text("clientSearchCount").replace("{loaded}",state.items.size.toString()).replace("{total}",state.total.toString()));if(state.partial)Text(text("partial"));if(state.showsEmpty)Text(text("noResults"));state.items.forEach {row->TextButton(onClick={if(isCurrent())model.openClient(row.id,control,child)}) {Text((row.title ?: text("notAvailable"))+" · #${row.id}")}}}
                    }
                }
            }
            model.candidate?.let {Text(label(it.choice));TextButton(onClick={if(isCurrent())model.clearChoice(control)}) {Text(text("inboxLinkClear"))}}
            TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxLinkReview"))};TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLinkTitle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            model.source?.let {Text(text("inboxLinkOriginal")+": "+(it.client?.let {id->"#$id"} ?: text("inboxLinkNotLinked")))}
            if(model.canOpen)TextButton(onClick={if(isCurrent())model.open(control)}) {Text(text("inboxLinkChoose"))}
        }
        if(model.canLoad)TextButton(onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxLinkLoad"))}
    }
}
