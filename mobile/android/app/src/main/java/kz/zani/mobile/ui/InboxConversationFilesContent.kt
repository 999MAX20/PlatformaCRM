package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun InboxConversationFilesContent(model:InboxConversationFilesModel,copy:Map<String,String>,isCurrent:()->Boolean,modifier:Modifier=Modifier) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val scope=rememberCoroutineScope();val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    val fileScope=text("inboxFilesTitle");val detailScope=fileScope+": "+text("details")
    if(!isCurrent() || !model.presented)return
    Column(modifier,verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("inboxFilesTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall);Text(text("fileMetadataWindow"),style=MaterialTheme.typography.labelSmall);Text(text("fileVerificationUnknown"))
        val row=model.selected
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=fileScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
        else if(row!=null) {
            Text("${text("fileOriginalName")}: ${row.originalName}");Text("${text("fileContentType")}: ${row.contentType.ifEmpty {text("notAvailable")}}")
            Text("${text("fileSizeBytes")}: ${row.size}");Text("${text("fileCreatedAt")}: ${row.createdAt}")
            TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else {
            model.failure?.let {Text(text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=announcement.semantics {contentDescription=fileScope+": "+text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
            if(model.loaded && model.items.isEmpty())Text(text("fileMetadataEmpty"),modifier=announcement.semantics {contentDescription=fileScope+": "+text("fileMetadataEmpty")})
            TextButton(modifier=Modifier.semantics {contentDescription=fileScope+": "+text(if(model.failure==null)"fileMetadataLoad" else "retry")},onClick={scope.launch {if(isCurrent())model.load(control)}}) {Text(text(if(model.failure==null)"fileMetadataLoad" else "retry"))}
            LazyColumn(Modifier.weight(1f)) {item {InboxSelfAssignmentContent(model,copy,isCurrent)};item {InboxReadMarkerContent(model,copy,isCurrent)};item {InboxPriorityContent(model,copy,isCurrent)};item {InboxLifecycleContent(model,copy,isCurrent)};item {model.linkClient?.let {InboxLinkClientContent(it,copy,isCurrent)}};item {model.leadReference?.let {LeadReferenceContent(it,copy,isCurrent)}};item {model.linkLead?.let {InboxLinkLeadContent(it,copy,isCurrent)}};item {model.dealReference?.let {DealReferenceContent(it,copy,isCurrent)}};item {model.linkDeal?.let {InboxLinkDealContent(it,copy,isCurrent)}};item {model.memberReference?.let {MemberReferenceContent(it,copy,isCurrent)}};item {model.targetAssignment?.let {InboxTargetAssignmentContent(it,copy,isCurrent)}};item {model.taskSource?.let {InboxTaskSourceContent(it,copy,isCurrent)}};item {model.createTask?.let {InboxCreateTaskContent(it,copy,isCurrent)}};item {model.existingClient?.let {InboxExistingClientContent(it,copy,isCurrent)}};item {model.existingLead?.let {InboxExistingLeadContent(it,copy,isCurrent)}};item {model.existingDeal?.let {InboxExistingDealContent(it,copy,isCurrent)}};items(model.items,key={it.id}) {file->TextButton(onClick={if(isCurrent())model.select(file,control)}) {Text((file.originalName.ifEmpty {text("notAvailable")})+" · #${file.id}")}}}
        }
    }
}

@Composable private fun InboxSelfAssignmentContent(model:InboxConversationFilesModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val scope=rememberCoroutineScope();val record=model.assignmentRecord;val review=model.assignmentReview
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxSelfTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()})
        Text(text("inboxSelfBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.assignmentLoading)CircularProgressIndicator(Modifier.semantics {contentDescription=text("loading")})
        model.assignmentFailure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
        if(record!=null) {
            Text(text(when(record.phase){InboxSelfAssignmentPhase.PENDING->"inboxSelfPending";InboxSelfAssignmentPhase.RESPONSE->"inboxSelfResponse";InboxSelfAssignmentPhase.REJECTED->"inboxSelfRejected";InboxSelfAssignmentPhase.UNKNOWN->"inboxSelfUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text("${text("inboxSelfActor")}: ${record.attempt.review.authorization.actor}")
            Text("${text("inboxSelfPrevious")}: ${record.attempt.review.source.assignedTo?.toString() ?: text("notAvailable")}")
            record.result?.let {Text("${text("inboxSelfObservedAt")}: ${it.source.updatedAt}")}
            if(record.phase in listOf(InboxSelfAssignmentPhase.RESPONSE,InboxSelfAssignmentPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxSelfTitle")+": "+text("inboxSelfAcknowledge")},onClick={if(isCurrent())model.acknowledgeAssignment(record,control)}) {Text(text("inboxSelfAcknowledge"))}
        } else if(model.assignmentBlocked)Text(text("inboxSelfRetained"))
        else if(review!=null) {
            Text("${text("inboxSelfActor")}: ${review.authorization.actor}");Text("${text("inboxSelfPrevious")}: ${review.source.assignedTo?.toString() ?: text("notAvailable")}")
            TextButton(enabled=model.canSubmitAssignment,onClick={scope.launch {if(isCurrent())model.submitAssignment(review,control)}}) {Text(text("inboxSelfSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("inboxSelfTitle")+": "+text("back")},onClick={if(isCurrent())model.backAssignment(control)}) {Text(text("back"))}
        } else if(model.canPrepareAssignment)TextButton(onClick={if(isCurrent())model.prepareAssignment(control)}) {Text(text("inboxSelfReview"))}
        if(model.canLoadAssignment)TextButton(onClick={scope.launch {if(isCurrent())model.loadAssignment(control)}}) {Text(text("inboxSelfLoad"))}
    }
}

@Composable private fun InboxReadMarkerContent(model:InboxConversationFilesModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val scope=rememberCoroutineScope();val record=model.markerRecord;val review=model.markerReview
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxMarkerTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()})
        Text(text("inboxMarkerBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.markerLoading)CircularProgressIndicator(Modifier.semantics {contentDescription=text("loading")})
        model.markerFailure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
        if(record!=null) {
            Text(text(if(record.attempt.review.action==InboxReadMarkerAction.READ)"inboxMarkerActionRead" else "inboxMarkerActionUnread"))
            Text(text(when(record.phase){InboxReadMarkerPhase.PENDING->"inboxMarkerPending";InboxReadMarkerPhase.RESPONSE->"inboxMarkerResponse";InboxReadMarkerPhase.REJECTED->"inboxMarkerRejected";InboxReadMarkerPhase.UNKNOWN->"inboxMarkerUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text("${text("inboxSelfActor")}: ${record.attempt.review.authorization.actor}")
            Text("${text("inboxMarkerOriginalCount")}: ${record.attempt.review.source.unreadCount.toString()}")
            record.result?.let {Text("${text("inboxMarkerResponseCount")}: ${it.source.unreadCount}");Text("${text("inboxSelfObservedAt")}: ${it.source.updatedAt}")}
            if(record.phase in listOf(InboxReadMarkerPhase.RESPONSE,InboxReadMarkerPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxMarkerTitle")+": "+text("inboxMarkerAcknowledge")},onClick={if(isCurrent())model.acknowledgeMarker(record,control)}) {Text(text("inboxMarkerAcknowledge"))}
        } else if(model.markerBlocked)Text(text("inboxMarkerRetained"))
        else if(review!=null) {
            Text(text(if(review.action==InboxReadMarkerAction.READ)"inboxMarkerActionRead" else "inboxMarkerActionUnread"))
            Text("${text("inboxSelfActor")}: ${review.authorization.actor}");Text("${text("inboxMarkerOriginalCount")}: ${review.source.unreadCount.toString()}")
            TextButton(enabled=model.canSubmitMarker,onClick={scope.launch {if(isCurrent())model.submitMarker(review,control)}}) {Text(text("inboxMarkerSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("inboxMarkerTitle")+": "+text("back")},onClick={if(isCurrent())model.backMarker(control)}) {Text(text("back"))}
        } else if(model.canPrepareMarker) {
            TextButton(onClick={if(isCurrent())model.prepareMarker(InboxReadMarkerAction.READ,control)}) {Text(text("inboxMarkerReviewRead"))}
            TextButton(onClick={if(isCurrent())model.prepareMarker(InboxReadMarkerAction.UNREAD,control)}) {Text(text("inboxMarkerReviewUnread"))}
        }
        if(model.canLoadMarker)TextButton(onClick={scope.launch {if(isCurrent())model.loadMarker(control)}}) {Text(text("inboxMarkerLoad"))}
    }
}

@Composable private fun InboxPriorityContent(model:InboxConversationFilesModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val scope=rememberCoroutineScope();val record=model.priorityRecord;val review=model.priorityReview
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxPriorityTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()})
        Text(text("inboxPriorityBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.priorityLoading)CircularProgressIndicator(Modifier.semantics {contentDescription=text("loading")})
        model.priorityFailure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}))}
        if(record!=null) {
            Text(text(when(record.phase){InboxPriorityPhase.PENDING->"inboxPriorityPending";InboxPriorityPhase.RESPONSE->"inboxPriorityResponse";InboxPriorityPhase.REJECTED->"inboxPriorityRejected";InboxPriorityPhase.UNKNOWN->"inboxPriorityUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text("${text("inboxPriorityOriginal")}: ${record.attempt.review.source.priority}");Text("${text("inboxPriorityChosen")}: ${text("inboxPriorityValue_"+record.attempt.review.value.wire)}");Text("${text("inboxSelfActor")}: ${record.attempt.review.authorization.actor}")
            record.result?.let {Text("${text("inboxSelfObservedAt")}: ${it.source.updatedAt}")}
            if(record.phase in listOf(InboxPriorityPhase.RESPONSE,InboxPriorityPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxPriorityTitle")+": "+text("inboxPriorityAcknowledge")},onClick={if(isCurrent())model.acknowledgePriority(record,control)}) {Text(text("inboxPriorityAcknowledge"))}
        } else if(model.priorityBlocked)Text(text("inboxPriorityRetained"))
        else if(review!=null) {
            Text("${text("inboxPriorityOriginal")}: ${review.source.priority}");Text("${text("inboxPriorityChosen")}: ${text("inboxPriorityValue_"+review.value.wire)}")
            TextButton(enabled=model.canSubmitPriority,onClick={scope.launch {if(isCurrent())model.submitPriority(review,control)}}) {Text(text("inboxPrioritySubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("inboxPriorityTitle")+": "+text("back")},onClick={if(isCurrent())model.backPriority(control)}) {Text(text("back"))}
        } else {
            model.prioritySource?.let {Text("${text("inboxPriorityOriginal")}: ${it.priority}")};model.selectedPriorityValue?.let {Text("${text("inboxPriorityChosen")}: ${text("inboxPriorityValue_"+it.wire)}")}
            if(model.canChoosePriority) {
                InboxPriorityValue.entries.forEach {value->TextButton(onClick={if(isCurrent())model.choosePriority(value,control)}) {Text(text("inboxPriorityValue_"+value.wire))}}
                if(model.selectedPriorityValue!=null)TextButton(onClick={if(isCurrent())model.clearPriorityChoice(control)}) {Text(text("inboxPriorityClear"))}
            }
            if(model.canPreparePriority)TextButton(onClick={if(isCurrent())model.preparePriority(control)}) {Text(text("inboxPriorityReview"))}
        }
        if(model.canLoadPriority)TextButton(onClick={scope.launch {if(isCurrent())model.loadPriority(control)}}) {Text(text("inboxPriorityLoad"))}
    }
}

@Composable private fun InboxLifecycleContent(model:InboxConversationFilesModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val scope=rememberCoroutineScope();val record=model.lifecycleRecord;val review=model.lifecycleReview
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxLifecycleTitle"),style=MaterialTheme.typography.titleSmall,modifier=Modifier.semantics {heading()})
        Text(text("inboxLifecycleBoundary"),style=MaterialTheme.typography.labelSmall)
        if(model.lifecycleLoading)CircularProgressIndicator(Modifier.semantics {contentDescription=text("loading")})
        model.lifecycleFailure?.let {Text(text(when(it){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
        if(record!=null) {
            Text(text(if(record.attempt.review.action==InboxLifecycleAction.CLOSE)"inboxLifecycleActionClose" else "inboxLifecycleActionReopen"))
            Text(text(when(record.phase){InboxLifecyclePhase.PENDING->"inboxLifecyclePending";InboxLifecyclePhase.RESPONSE->"inboxLifecycleResponse";InboxLifecyclePhase.REJECTED->"inboxLifecycleRejected";InboxLifecyclePhase.UNKNOWN->"inboxLifecycleUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            Text("${text("inboxSelfActor")}: ${record.attempt.review.authorization.actor}")
            Text("${text("inboxLifecycleOriginalStatus")}: ${record.attempt.review.source.status.toString()}")
            record.result?.let {Text("${text("inboxLifecycleFlags")}: ${text(if(it.source.botEnabled)"inboxLifecycleYes" else "inboxLifecycleNo")} / ${text(if(it.source.handoffRequired)"inboxLifecycleYes" else "inboxLifecycleNo")}");Text("${text("inboxLifecycleResponseStatus")}: ${it.source.status}");Text("${text("inboxSelfObservedAt")}: ${it.source.updatedAt}")}
            if(record.phase in listOf(InboxLifecyclePhase.RESPONSE,InboxLifecyclePhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLifecycleTitle")+": "+text("inboxLifecycleAcknowledge")},onClick={if(isCurrent())model.acknowledgeLifecycle(record,control)}) {Text(text("inboxLifecycleAcknowledge"))}
        } else if(model.lifecycleBlocked)Text(text("inboxLifecycleRetained"))
        else if(review!=null) {
            Text("${text("inboxLifecycleFlags")}: ${text(if(review.source.botEnabled)"inboxLifecycleYes" else "inboxLifecycleNo")} / ${text(if(review.source.handoffRequired)"inboxLifecycleYes" else "inboxLifecycleNo")}")
            Text(text(if(review.action==InboxLifecycleAction.CLOSE)"inboxLifecycleActionClose" else "inboxLifecycleActionReopen"))
            Text("${text("inboxSelfActor")}: ${review.authorization.actor}");Text("${text("inboxLifecycleOriginalStatus")}: ${review.source.status.toString()}")
            TextButton(enabled=model.canSubmitLifecycle,onClick={scope.launch {if(isCurrent())model.submitLifecycle(review,control)}}) {Text(text("inboxLifecycleSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("inboxLifecycleTitle")+": "+text("back")},onClick={if(isCurrent())model.backLifecycle(control)}) {Text(text("back"))}
        } else if(model.canPrepareLifecycle) {
            TextButton(onClick={if(isCurrent())model.prepareLifecycle(InboxLifecycleAction.CLOSE,control)}) {Text(text("inboxLifecycleReviewClose"))}
            TextButton(onClick={if(isCurrent())model.prepareLifecycle(InboxLifecycleAction.REOPEN,control)}) {Text(text("inboxLifecycleReviewReopen"))}
        }
        if(model.canLoadLifecycle)TextButton(onClick={scope.launch {if(isCurrent())model.loadLifecycle(control)}}) {Text(text("inboxLifecycleLoad"))}
    }
}
