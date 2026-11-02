package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun InboxLinkDealContent(model:InboxLinkDealModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    fun id(value:Int?)=value?.let {"#$it"} ?: text("inboxDealNone")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxDealTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxDealBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator()
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}))}
        if(record!=null) {
            Text(text(when(record.phase){InboxLinkDealPhase.PENDING->"inboxDealPending";InboxLinkDealPhase.RESPONSE->"inboxDealResponse";InboxLinkDealPhase.REJECTED->"inboxDealRejected";InboxLinkDealPhase.UNKNOWN->"inboxDealUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text(text("inboxDealOriginal")+": "+id(record.attempt.review.source.deal));Text(text("inboxDealOriginalLead")+": "+id(record.attempt.review.source.lead));Text(text("inboxDealOriginalClient")+": "+id(record.attempt.review.source.client));Text(record.attempt.review.candidate.reference.source.title+" · #${record.attempt.review.candidate.reference.source.id}");Text(record.attempt.review.candidate.reference.rawInput);Text(text("inboxDealExpectedClient")+": "+id(record.attempt.review.source.client ?: record.attempt.review.candidate.reference.source.client));Text(text("inboxDealExpectedLead")+": "+id(record.attempt.review.source.lead ?: record.attempt.review.candidate.reference.source.lead))
            if(record.phase in listOf(InboxLinkDealPhase.RESPONSE,InboxLinkDealPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxDealTitle")+": "+text("inboxDealAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxDealAcknowledge"))}
        } else if(model.blocked)Text(text("inboxDealRetained"))
        else if(review!=null) {
            Text(text("inboxDealOriginal")+": "+id(review.source.deal));Text(text("inboxDealOriginalLead")+": "+id(review.source.lead));Text(text("inboxDealOriginalClient")+": "+id(review.source.client));Text(review.candidate.reference.source.title+" · #${review.candidate.reference.source.id}");Text(review.candidate.reference.rawInput);Text(text("inboxDealExpectedClient")+": "+id(review.source.client ?: review.candidate.reference.source.client));Text(text("inboxDealExpectedLead")+": "+id(review.source.lead ?: review.candidate.reference.source.lead))
            TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxDealSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("inboxDealTitle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            model.source?.let {Text(text("inboxDealOriginal")+": "+id(it.deal));Text(text("inboxDealOriginalLead")+": "+id(it.lead));Text(text("inboxDealOriginalClient")+": "+id(it.client))};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxDealReview"))}
        }
        if(model.canLoad)TextButton(onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxDealLoad"))}
    }
}
