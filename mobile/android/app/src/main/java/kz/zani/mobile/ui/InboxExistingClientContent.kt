package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable private fun InboxExistingClientSourceContent(source:InboxExistingClientSource,copy:Map<String,String>) {fun text(k:String)=copy[k] ?: k;Text(source.client?.let {text("inboxExistingOriginal")+": #$it"} ?: text("inboxExistingAbsent"))}
@Composable fun InboxExistingClientContent(model:InboxExistingClientModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val readScope=text("inboxExistingTitle")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxExistingTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxExistingBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
        if(record!=null) {
            Text(text(when(record.phase){InboxExistingClientPhase.PENDING->"inboxExistingPending";InboxExistingClientPhase.RESPONSE->"inboxExistingResponse";InboxExistingClientPhase.REJECTED->"inboxExistingRejected";InboxExistingClientPhase.UNKNOWN->"inboxExistingUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            InboxExistingClientSourceContent(record.attempt.review.source,copy);record.result?.let {Text(text("inboxExistingResultID")+": #${it.id}");Text(it.fullName);Text(it.phone);Text(it.email)}
            if(record.phase in listOf(InboxExistingClientPhase.RESPONSE,InboxExistingClientPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxExistingTitle")+": "+text("inboxExistingAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxExistingAcknowledge"))}
        } else if(model.blocked)Text(text("inboxExistingRetained"))
        else if(review!=null) {
            InboxExistingClientSourceContent(review.source,copy);Text(text("inboxExistingOmissions"));TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxExistingSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {model.source?.let {InboxExistingClientSourceContent(it,copy)};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxExistingReview"))}}
        if(model.canLoad)TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("inboxExistingLoad")},onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxExistingLoad"))}
    }
}
