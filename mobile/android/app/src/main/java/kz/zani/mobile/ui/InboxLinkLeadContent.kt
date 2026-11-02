package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun InboxLinkLeadContent(model:InboxLinkLeadModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    fun id(value:Int?)=value?.let {"#$it"} ?: text("inboxLeadNone")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxLeadTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxLeadBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator()
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}))}
        if(record!=null) {
            Text(text(when(record.phase){InboxLinkLeadPhase.PENDING->"inboxLeadPending";InboxLinkLeadPhase.RESPONSE->"inboxLeadResponse";InboxLinkLeadPhase.REJECTED->"inboxLeadRejected";InboxLinkLeadPhase.UNKNOWN->"inboxLeadUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text(text("inboxLeadOriginal")+": "+id(record.attempt.review.source.lead));Text(text("inboxLeadOriginalClient")+": "+id(record.attempt.review.source.client));Text(record.attempt.review.candidate.reference.detail.lead.title+" · #${record.attempt.review.candidate.reference.detail.lead.id}");Text(record.attempt.review.candidate.reference.rawQuery);Text(text("inboxLeadExpectedClient")+": "+id(record.attempt.review.source.client ?: record.attempt.review.candidate.reference.detail.lead.client_id))
            if(record.phase in listOf(InboxLinkLeadPhase.RESPONSE,InboxLinkLeadPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLeadTitle")+": "+text("inboxLeadAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxLeadAcknowledge"))}
        } else if(model.blocked)Text(text("inboxLeadRetained"))
        else if(review!=null) {
            Text(text("inboxLeadOriginal")+": "+id(review.source.lead));Text(text("inboxLeadOriginalClient")+": "+id(review.source.client));Text(review.candidate.reference.detail.lead.title+" · #${review.candidate.reference.detail.lead.id}");Text(review.candidate.reference.rawQuery);Text(text("inboxLeadExpectedClient")+": "+id(review.source.client ?: review.candidate.reference.detail.lead.client_id))
            TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxLeadSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLeadTitle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            model.source?.let {Text(text("inboxLeadOriginal")+": "+id(it.lead));Text(text("inboxLeadOriginalClient")+": "+id(it.client))};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxLeadReview"))}
        }
        if(model.canLoad)TextButton(onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxLeadLoad"))}
    }
}
