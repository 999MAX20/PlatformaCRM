package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable private fun InboxExistingDealSourceContent(source:InboxExistingDealSource,copy:Map<String,String>) {
    fun text(k:String)=copy[k] ?: k
    Text(source.deal?.let {text("inboxExistingDealOriginal")+": #$it"} ?: text("inboxExistingDealAbsent"));Text(text("inboxExistingDealConversationClient")+": "+(source.client?.let {"#$it"} ?: text("inboxExistingDealNone")));Text(text("inboxExistingDealConversationLead")+": "+(source.lead?.let {"#$it"} ?: text("inboxExistingDealNone")))
}
@Composable fun InboxExistingDealContent(model:InboxExistingDealModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val readScope=text("inboxExistingDealTitle")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxExistingDealTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxExistingDealBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
        if(record!=null) {
            Text(text(when(record.phase){InboxExistingDealPhase.PENDING->"inboxExistingDealPending";InboxExistingDealPhase.RESPONSE->"inboxExistingDealResponse";InboxExistingDealPhase.REJECTED->"inboxExistingDealRejected";InboxExistingDealPhase.UNKNOWN->"inboxExistingDealUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            InboxExistingDealSourceContent(record.attempt.review.source,copy);record.result?.let {Text(text("inboxExistingDealResultID")+": #${it.id}");Text(text("inboxExistingDealResultClient")+": #${it.client}");Text(text("inboxExistingDealResultLead")+": "+(it.lead?.let {id->"#$id"} ?: text("inboxExistingDealNone")));Text(it.title)}
            if(record.phase in listOf(InboxExistingDealPhase.RESPONSE,InboxExistingDealPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxExistingDealTitle")+": "+text("inboxExistingDealAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxExistingDealAcknowledge"))}
        } else if(model.blocked)Text(text("inboxExistingDealRetained"))
        else if(review!=null) {
            InboxExistingDealSourceContent(review.source,copy);Text(text("inboxExistingDealOmissions"));TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxExistingDealSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {model.source?.let {InboxExistingDealSourceContent(it,copy)};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxExistingDealReview"))}}
        if(model.canLoad)TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("inboxExistingDealLoad")},onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxExistingDealLoad"))}
    }
}
