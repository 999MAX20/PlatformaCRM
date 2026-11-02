package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun ReplyDraftContent(model: ReplyDraftModel,selection: ReplyDraftSelection,copy: Map<String,String>,modifier: Modifier=Modifier,isCurrent:()->Boolean) {
    fun text(key: String)=copy[key] ?: key
    val state=model.state
    val control=model.control;val input=model.inputControl;val returnControl=model.returnControl;val question=model.clearConfirmation
    if(!isCurrent() || state.selection!=selection) return
    val quick=model.quickReplies
    val picker=quick?.state?.selection?.takeIf {it.context.draft==selection}
    if(!model.submissionBlocked && quick!=null && picker!=null) {QuickReplyContent(quick,picker,copy,{choice,window->if(isCurrent())model.insert(choice,control,window)},modifier,isCurrent={isCurrent() && model.control==control && model.state.available && model.state.phase==ReplyDraftPhase.EDITING});return}
    val entry=quick?.entryControl
    val focus=remember(selection) { FocusRequester() }
    BackHandler { if(isCurrent())model.back(expected=returnControl) }
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("replyDraftTitle"),style=MaterialTheme.typography.titleMedium)
        TextButton(modifier=Modifier.semantics {contentDescription=text("replyDraftTitle")+": "+text("back")},onClick={if(isCurrent())model.back(expected=returnControl)}) {Text(text("back"))}
        Text(text("clientDraftOnly"))
        if(model.submissionBlocked) {InboxReplyReceiptContent(model,copy,isCurrent)}
        else if(state.phase==ReplyDraftPhase.REVIEW && state.review?.selection==selection) {
            Text(text("clientDraftReview"),style=MaterialTheme.typography.titleSmall)
            Text(state.review!!.text)
            val review=state.review!!;if(model.canSubmit)Button(onClick={if(isCurrent())model.launchSubmit(review,control)}) {Text(text("inboxReplyFakeSubmit"))} else if(model.hasTestPort)Text(text("inboxReplyTestUnavailable"))
        } else {
            OutlinedTextField(value=state.text,onValueChange={if(isCurrent())model.update(it,input)},label={Text(text("replyDraftText"))},isError=state.emptyError,minLines=5,modifier=Modifier.fillMaxWidth().focusRequester(focus),supportingText={if(state.emptyError)Text(text("replyDraftRequired"),modifier=Modifier.semantics { liveRegion=LiveRegionMode.Polite })})
            LaunchedEffect(selection) {focus.requestFocus()}
            if(entry!=null)TextButton(onClick={if(isCurrent())model.openQuickReplies(control,entry)}) {Text(text("quickReplyTitle"))}
            Button(onClick={if(isCurrent() && model.control==control) {model.prepare(expected=control);if(model.state.emptyError)focus.requestFocus()}}) { Text(text("clientDraftReview")) }
        }
        if(!model.submissionBlocked)TextButton(modifier=Modifier.semantics {contentDescription=text("replyDraftTitle")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.askClear(control)}) { Text(text("clientDraftClear")) }
    }
    if(question!=null) AlertDialog(onDismissRequest={model.dismissClear(question)},title={Text(text("clientDraftClearQuestion"))},confirmButton={TextButton(modifier=Modifier.semantics {contentDescription=text("replyDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftClear")},onClick={if(isCurrent())model.confirmClear(question)}){Text(text("clientDraftClear"))}},dismissButton={TextButton(modifier=Modifier.semantics {contentDescription=text("replyDraftTitle")+": "+text("clientDraftClearQuestion")+": "+text("clientDraftCancel")},onClick={model.dismissClear(question)}){Text(text("clientDraftCancel"))}})
}
