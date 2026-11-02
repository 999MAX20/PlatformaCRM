package kz.zani.mobile.ui
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun InboxTargetAssignmentContent(model:InboxTargetAssignmentModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val readScope=text("inboxTargetTitle")
    fun id(value:Int?)=value?.let {"#$it"} ?: text("inboxTargetNone")
    val control=model.control;val record=model.record;val review=model.review;val scope=rememberCoroutineScope()
    if(!isCurrent() || !model.presented)return
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxTargetTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()});Text(text("inboxTargetBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading")})
        model.failure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
        if(record!=null) {
            Text(text(when(record.phase){InboxTargetAssignmentPhase.PENDING->"inboxTargetPending";InboxTargetAssignmentPhase.RESPONSE->"inboxTargetResponse";InboxTargetAssignmentPhase.REJECTED->"inboxTargetRejected";InboxTargetAssignmentPhase.UNKNOWN->"inboxTargetUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text(text("inboxTargetOriginal")+": "+id(record.attempt.review.source.assignedTo));Text(record.attempt.review.candidate.reference.source.user.displayName ?: text("notAvailable"));Text(record.attempt.review.candidate.reference.source.user.email);Text(text("inboxTargetUser")+": "+id(record.attempt.review.candidate.reference.source.user.id));Text(text("inboxTargetMembership")+": "+id(record.attempt.review.candidate.reference.source.id));Text(record.attempt.review.candidate.reference.rawInput)
            if(record.phase in listOf(InboxTargetAssignmentPhase.RESPONSE,InboxTargetAssignmentPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxTargetTitle")+": "+text("inboxTargetAcknowledge")},onClick={if(isCurrent())model.acknowledge(record,control)}) {Text(text("inboxTargetAcknowledge"))}
        } else if(model.blocked)Text(text("inboxTargetRetained"))
        else if(review!=null) {
            Text(text("inboxTargetOriginal")+": "+id(review.source.assignedTo));Text(review.candidate.reference.source.user.displayName ?: text("notAvailable"));Text(review.candidate.reference.source.user.email);Text(text("inboxTargetUser")+": "+id(review.candidate.reference.source.user.id));Text(text("inboxTargetMembership")+": "+id(review.candidate.reference.source.id));Text(review.candidate.reference.rawInput)
            TextButton(enabled=model.canSubmit,onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("inboxTargetSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            model.source?.let {Text(text("inboxTargetOriginal")+": "+id(it.assignedTo))};TextButton(enabled=model.canPrepare,onClick={if(isCurrent())model.prepare(control)}) {Text(text("inboxTargetReview"))}
        }
        if(model.canLoad)TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("inboxTargetLoad")},onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text("inboxTargetLoad"))}
    }
}
