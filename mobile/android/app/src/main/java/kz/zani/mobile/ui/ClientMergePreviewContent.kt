package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun ClientMergePreviewContent(owner:ClientProfileViewModel,model:ClientMergePreviewModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val readScope=text("clientMergePreviewTitle")
    fun error(problem:ReadProblem)=text(when(problem) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"})
    val keys=mapOf(
        "leads" to "clientMergeCountLeads",
        "appointments" to "clientMergeCountAppointments",
        "conversations" to "clientMergeCountConversations",
        "bot_conversations" to "clientMergeCountBotConversations",
        "tasks" to "clientMergeCountTasks",
        "deals" to "clientMergeCountDeals",
        "notes" to "clientMergeCountNotes",
        "activity_events" to "clientMergeCountActivityEvents",
        "analytics_events" to "clientMergeCountAnalyticsEvents",
        "notifications" to "clientMergeCountNotifications",
        "tags" to "clientMergeCountTags",
        "attachments" to "clientMergeCountAttachments",
        "custom_field_values" to "clientMergeCountCustomFieldValues"
    )
    val control=model.control;val entry=owner.mergeEntry
    BackHandler(enabled=control!=null && isCurrent(),onBack={if(isCurrent())owner.closeMerge(control)})
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("clientMergePreviewTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("clientMergeFixtureOnly"))
        if(control!=null && owner.ownsMerge(control)) {
            TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())owner.closeMerge(control)}) {Text(text("back"))}
            if(!model.catalogReady) {
                if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
                else model.problem?.let {Text(error(it),modifier=Modifier.semantics {contentDescription=readScope+": "+error(it)});Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())owner.launchRetryMerge(control)}) {Text(text("retry"))}}
            } else {
                Text(text("clientMergeChoose"))
                if(model.candidates.isEmpty())Text(text("clientMergeEmpty"),modifier=Modifier.semantics {contentDescription=readScope+": "+text("clientMergeEmpty")})
                model.candidates.forEach {row->TextButton(onClick={if(isCurrent())owner.chooseMerge(row.id,control)},modifier=Modifier.semantics {selected=model.selected==row.id}) {Column {Text(row.fullName);Text(row.phone);Text(row.email)}}}
                if(model.loading)CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
                else {
                    model.problem?.let {Text(error(it),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite;contentDescription=readScope+": "+error(it)})}
                    if(model.selected!=null)Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text(if(model.problem==null)"clientDraftReview" else "retry")},onClick={if(isCurrent())owner.launchPreviewMerge(control)}) {Text(text(if(model.problem==null)"clientDraftReview" else "retry"))}
                    model.result?.let {preview->
                        Text(preview.duplicate.fullName,style=MaterialTheme.typography.titleMedium)
                        Text(text("clientMergeArchivePolicy"))
                        ClientMergeTransferCounts.fields.forEach {field->val key=keys[field];val value=preview.transferred.provided[field];if(key!=null && value!=null)Text("${text(key)}: $value")}
                    }
                }
            }
        } else if(entry!=null)Button(onClick={if(isCurrent())owner.launchOpenMerge(entry)}) {Text(text("clientMergePreviewTitle"))}
    }
}
