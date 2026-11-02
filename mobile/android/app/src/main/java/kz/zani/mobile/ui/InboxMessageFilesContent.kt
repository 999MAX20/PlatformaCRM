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

@Composable fun InboxMessageFilesContent(model:InboxMessageFilesModel,copy:Map<String,String>,isCurrent:()->Boolean,modifier:Modifier=Modifier) {
    fun text(key:String)=copy[key] ?: key
    fun observed(value:InboxObservedText)=when(value) {InboxObservedText.Missing->text("messageObservationMissing");InboxObservedText.Null->text("messageObservationNull");is InboxObservedText.Value->value.raw.ifEmpty {text("messageObservationEmpty")}}
    val control=model.control;val scope=rememberCoroutineScope();val announcement=Modifier.semantics {liveRegion=LiveRegionMode.Polite}
    val fileScope=text("inboxMessageFilesTitle");val detailScope=fileScope+": "+text("details")
    val windowScope=text("inboxMessageReadTitle")
    if(!isCurrent() || !model.presented)return
    Column(modifier,verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("inboxMessageReadTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=windowScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
        LazyColumn(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            item {
                Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall);Text(text("fileMetadataWindow"),style=MaterialTheme.typography.labelSmall);Text(text("fileVerificationUnknown"))
                model.context?.let {Text("#${it.message}",style=MaterialTheme.typography.labelSmall)}
                model.window?.let {w->Text(text("inboxMessageFilesWindow").replace("{loaded}",w.providedMessages.toString()).replace("{total}",w.count.toString()),style=MaterialTheme.typography.labelSmall);if(w.limited)Text(text("partial"),modifier=announcement)}
            }
            model.window?.observation?.let {o->item {
                Text("${text("messageObservedStatus")}: ${text(o.state.copyKey)}")
                Text("${text("messageObservedStatusRaw")}: ${observed(o.status)}")
                Text("${text("messageObservedSentAt")}: ${observed(o.sentAt)}")
                Text("${text("messageObservedDeliveredAt")}: ${observed(o.deliveredAt)}")
                Text("${text("messageObservedReadAt")}: ${observed(o.readAt)}")
                Text(text("messageObservationLimits"),style=MaterialTheme.typography.labelSmall)
            }}
            item {
                val record=model.retryRecord;val review=model.retryReview
                if(record!=null || review!=null || model.retryBlocked || model.canPrepareRetry)Text(text("inboxRetryTitle"),style=MaterialTheme.typography.titleSmall)
                if(record!=null) {
                    Text(text("inboxRetryOriginal")+" #${record.attempt.review.source.context.message}");Text(record.attempt.review.source.text)
                    Text(text(when(record.phase){InboxRetryPhase.PENDING->"inboxRetryPending";InboxRetryPhase.RESPONSE->"inboxRetryResponse";InboxRetryPhase.REJECTED->"inboxRetryRejected";InboxRetryPhase.UNKNOWN->"inboxRetryUnknown"}),modifier=announcement)
                    record.result?.let {Text(text("inboxRetryResultMessage")+" #${it.id}");Text(text("messageStateTitle")+": "+text(InboxMessageState.from(it.status).copyKey))}
                    if(record.phase in listOf(InboxRetryPhase.RESPONSE,InboxRetryPhase.REJECTED))TextButton(modifier=Modifier.semantics {contentDescription=text("inboxRetryTitle")+": "+text("inboxRetryAcknowledge")},onClick={if(isCurrent())model.acknowledgeRetry(record,control)}) {Text(text("inboxRetryAcknowledge"))}
                } else if(review!=null) {
                    Text(text("inboxRetryReview"));Text(text("inboxRetryOriginal")+" #${review.source.context.message}");Text(review.source.text);Text(text("inboxRetryLimits"),style=MaterialTheme.typography.labelSmall)
                    TextButton(onClick={scope.launch {if(isCurrent())model.submitRetry(review,control)}},enabled=model.canSubmitRetry) {Text(text("inboxRetrySubmit"))}
                    TextButton(modifier=Modifier.semantics {contentDescription=text("inboxRetryTitle")+": "+text("back")},onClick={if(isCurrent())model.backRetry(control)}) {Text(text("back"))}
                } else if(model.retryBlocked)Text(text("inboxRetryBlocked"),modifier=announcement)
                else if(model.canPrepareRetry)TextButton(onClick={if(isCurrent())model.prepareRetry(control)}) {Text(text("inboxRetryPrepare"))}
            }
            val row=model.selected
            if(!model.loading && row!=null) {
                item {
                    Text("${text("fileOriginalName")}: ${row.originalName}");Text("${text("fileContentType")}: ${row.contentType.ifEmpty {text("notAvailable")}}")
                    Text("${text("fileSizeBytes")}: ${row.size}");Text("${text("fileCreatedAt")}: ${row.createdAt}")
                    TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
                }
            } else if(!model.loading) {
                item {
                    Text(text("inboxMessageFilesTitle"),style=MaterialTheme.typography.titleSmall)
                    model.failure?.let {Text(text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=announcement.semantics {contentDescription=fileScope+": "+text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"})})}
                    if(model.window?.items?.isEmpty()==true)Text(text("fileMetadataEmpty"),modifier=announcement.semantics {contentDescription=fileScope+": "+text("fileMetadataEmpty")})
                    TextButton(modifier=Modifier.semantics {contentDescription=fileScope+": "+text(if(model.failure==null)"fileMetadataLoad" else "retry")},onClick={scope.launch {if(isCurrent())model.load(control)}},enabled=model.retryReview==null && model.retryRecord?.phase!=InboxRetryPhase.PENDING) {Text(text(if(model.failure==null)"fileMetadataLoad" else "retry"))}
                }
                items(model.window?.items ?: emptyList(),key={it.id}) {file->TextButton(onClick={if(isCurrent())model.select(file,control)},enabled=model.retryReview==null) {Text((file.originalName.ifEmpty {text("notAvailable")})+" · #${file.id}")}}
            }
        }
    }
}
