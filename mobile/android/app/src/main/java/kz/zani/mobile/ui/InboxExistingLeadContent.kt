package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable private fun InboxExistingLeadSourceContent(source:InboxExistingLeadSource,copy:Map<String,String>) {
    fun text(k:String)=copy[k] ?: k
    Text(source.lead?.let {text("inboxExistingLeadOriginal")+": #$it"} ?: text("inboxExistingLeadAbsent"));Text(text("inboxExistingLeadConversationClient")+": "+(source.client?.let {"#$it"} ?: text("inboxExistingLeadNone")))
}
@Composable fun InboxExistingLeadContent(model:InboxExistingLeadModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val readScope=text("inboxExistingLeadTitle")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxExistingLeadTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxExistingLeadBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
        if(record!=null) {
            Text(text(when(record.phase){InboxExistingLeadPhase.PENDING->"inboxExistingLeadPending";InboxExistingLeadPhase.RESPONSE->"inboxExistingLeadResponse";InboxExistingLeadPhase.REJECTED->"inboxExistingLeadRejected";InboxExistingLeadPhase.UNKNOWN->"inboxExistingLeadUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            InboxExistingLeadSourceContent(record.attempt.review.source,copy);record.result?.let {Text(text("inboxExistingLeadResultID")+": #${it.id}");Text(text("inboxExistingLeadResultClient")+": #${it.client}");Text(it.message)}
            if(record.phase in listOf(InboxExistingLeadPhase.RESPONSE,InboxExistingLeadPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxExistingLeadTitle")+": "+text("inboxExistingLeadAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxExistingLeadAcknowledge"))}
        } else if(model.blocked)Text(text("inboxExistingLeadRetained"))
        else if(review!=null) {
            InboxExistingLeadSourceContent(review.source,copy);Text(text("inboxExistingLeadOmissions"));TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxExistingLeadSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {model.source?.let {InboxExistingLeadSourceContent(it,copy)};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxExistingLeadReview"))}}
        if(model.canLoad)TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("inboxExistingLeadLoad")},onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxExistingLeadLoad"))}
    }
}
