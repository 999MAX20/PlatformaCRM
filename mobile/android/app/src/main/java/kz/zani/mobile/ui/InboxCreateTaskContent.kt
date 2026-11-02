package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable private fun InboxCreateTaskDetails(review:InboxCreateTaskReview,copy:Map<String,String>) {
    fun text(k:String)=copy[k] ?: k
    fun id(value:Int?)=value?.let {"#$it"} ?: text("inboxTaskCreateNone")
    Text(text("inboxTaskCreateClient")+": "+id(review.source.client));Text(text("inboxTaskCreateLead")+": "+id(review.source.lead));Text(text("inboxTaskCreateActor")+": "+id(review.authorization.actor));Text(text("inboxTaskCreateOmissions"))
}
@Composable fun InboxCreateTaskContent(model:InboxCreateTaskModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxTaskCreateTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxTaskCreateBoundary"),style=MaterialTheme.typography.labelSmall)
        if(record!=null) {
            Text(text(when(record.phase){InboxCreateTaskPhase.PENDING->"inboxTaskCreatePending";InboxCreateTaskPhase.RESPONSE->"inboxTaskCreateResponse";InboxCreateTaskPhase.REJECTED->"inboxTaskCreateRejected";InboxCreateTaskPhase.UNKNOWN->"inboxTaskCreateUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            InboxCreateTaskDetails(record.attempt.review,copy);record.result?.let {Text(text("inboxTaskCreateResultID")+": #${it.id}");Text(it.title)}
            if(record.phase in listOf(InboxCreateTaskPhase.RESPONSE,InboxCreateTaskPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxTaskCreateTitle")+": "+text("inboxTaskCreateAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxTaskCreateAcknowledge"))}
        } else if(model.blocked)Text(text("inboxTaskCreateRetained"))
        else if(review!=null) {
            InboxCreateTaskDetails(review,copy);TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxTaskCreateSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("inboxTaskCreateTitle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {Text(text("inboxTaskCreateOmissions"));TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxTaskCreateReview"))}}
    }
}
