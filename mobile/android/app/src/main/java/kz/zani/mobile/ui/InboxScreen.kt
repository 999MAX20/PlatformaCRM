package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun InboxScreen(agenda: AgendaViewModel, model: InboxViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun error(problem: ReadProblem) = text(when (problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })
    fun sender(raw: String?) = when (raw) { "client" -> text("senderClient"); "manager" -> text("senderManager"); "ai" -> text("senderAi"); else -> value(raw) }
    val scope = agenda.state.selection
    val business = scope?.business?.id
    val state = model.state
    val control=model.control
    val list=model.listControl
    val input=model.listInputControl
    val threadRetry=model.threadRetryControl
    val ownerEpoch=agenda.state.businessEpoch
    fun ownsControl()=control!=null && model.matches(control) && agenda.state.selection?.business?.id==control.business && agenda.state.businessEpoch==control.epoch
    val current = state.business == business && state.scopeEpoch == agenda.state.businessEpoch
    val threadSelection=model.threadSelection
    val links = model.clientLinks
    val clientState = links?.state
    val clientRequest = clientState?.request
    val presentation=links?.presentation
    val inspectorControl=links?.control
    val inspectorReturn=links?.returnControl
    val inspectorEntry=links?.entryControl
    val rootReturn=model.returnControl
    val messageFiles=model.messageMetadata;val messagePresentation=model.messageFilesPresentationControl;val messageControl=messageFiles?.control
    val files=model.fileMetadata;val filesPresentation=model.filesPresentationControl;val filesControl=files?.control;val filesEntry=model.filesEntryControl
    val workReturn=links?.profile?.workReturnControl
    val clientActive = current && clientRequest != null && clientRequest.business == business && clientRequest.id == state.selectedID && clientState?.selectedID != null
    val draftSelection=model.reply.state.selection?.takeIf { current && it.context.business==business && it.context.conversation==state.selectedID && it.context.epoch==state.scopeEpoch }
    val handoffSelection=model.handoff.state.selection
    val handoffReturn=model.handoff.returnControl
    val handoffEntry=model.handoff.entryControl
    val replyReturn=model.reply.returnControl
    val replyEntry=model.reply.entryControl
    fun ownsReply()=ownsControl() && model.threadSelection==threadSelection && model.state.thread!=null && !model.state.threadLoading && model.state.threadProblem==null && links?.presentation==presentation && links?.state?.selectedID==null && model.handoff.control==null && model.fileMetadata?.presented!=true && model.messageMetadata?.presented!=true
    fun back() {
        if(!ownsControl() || model.returnControl!=rootReturn || threadSelection==null || model.threadSelection!=threadSelection || model.reply.state.selection!=draftSelection)return
        if(messageFiles?.presented==true) {if(messageFiles.selected!=null)messageFiles.back(messageControl)else model.closeMessageFiles(messagePresentation);return}
        if(files?.presented==true) {if(files.selected!=null)files.back(filesControl)else model.closeFiles(filesPresentation);return}
        if(handoffSelection!=null) {model.handoff.back(handoffReturn);return}
        if(draftSelection!=null) {if(model.reply.returnControl==replyReturn)model.reply.back(expected=replyReturn);return}
        if(links?.presentation!=presentation)return
        if(presentation?.selectedID!=null && links!=null) {
            if(!links.profile.backEdit(workReturn) && links.profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)links.closeInspector(inspectorReturn)
        } else model.backToThreadList(rootReturn)
    }
    val messageScroll = key(business,state.selectedID) { rememberLazyListState() }
    val listScroll = rememberLazyListState()
    var menu by remember { mutableStateOf(false) }
    val readScope=text("inbox");val bootstrapScope=readScope+": "+text("business");val threadScope=readScope+": "+text("details");val clientScope=readScope+": "+text("senderClient")+": "+text("details")
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    val loading = Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val threadProgress = Modifier.semantics { contentDescription = threadScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val clientProgress = Modifier.semantics { contentDescription = clientScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    LaunchedEffect(business,ownerEpoch) {if(agenda.state.selection?.business?.id==business && agenda.state.businessEpoch==ownerEpoch && (!current || (!state.loaded && !state.loading && state.problem==null)))model.load(business,ownerEpoch)}
    BackHandler(enabled = current && state.selectedID != null, onBack = ::back)
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
        Text(text("inbox"), style = MaterialTheme.typography.titleLarge)
        if (scope != null) Box {
            OutlinedButton(onClick = { menu = true }) { Text(scope.business.name) }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==scope.business.id},text = { Text(member.name) }, onClick = { menu = false; agenda.load(member.id, scope.day) }) }
            }
        }
        when {
            business == null && agenda.state.problem != null -> {
                Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)})
                Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) }
            }
            business == null || !current || state.loading -> CircularProgressIndicator(loading)
            state.selectedID != null -> {
                TextButton(modifier=Modifier.semantics {contentDescription=threadScope+": "+text("back")},onClick = ::back) { Text(text("back")) }
                when {
                    messageFiles?.presented==true -> InboxMessageFilesContent(messageFiles,copy,isCurrent={ownsControl() && model.matchesMessageFiles(messagePresentation)},modifier=Modifier.weight(1f))
                    files?.presented==true -> InboxConversationFilesContent(files,copy,isCurrent={ownsControl() && model.matchesFiles(filesPresentation)},modifier=Modifier.weight(1f))
                    handoffSelection != null -> InboxHandoffContent(model.handoff,handoffSelection,copy,Modifier.weight(1f),isCurrent={ownsControl() && model.threadSelection==threadSelection && model.state.thread!=null && !model.state.threadLoading && model.state.threadProblem==null && model.reply.control==null && links?.state?.selectedID==null && model.fileMetadata?.presented!=true && model.messageMetadata?.presented!=true})
                    draftSelection != null -> ReplyDraftContent(model.reply,draftSelection,copy,Modifier.weight(1f),isCurrent={ownsReply()})
                    clientActive && links != null && clientState != null && clientRequest != null -> {
                        if (clientState.loading) CircularProgressIndicator(clientProgress)
                        else ClientProfileContent(links.profile,business,clientState.selectedID!!,copy,scope.business.timezone,language,Modifier.weight(1f),onContact={ _,_ -> },onRetry={if(ownsControl())model.retryClient(inspectorControl,control)},isCurrent={ownsControl() && model.reply.control==null && model.handoff.control==null && links.control==inspectorControl && model.fileMetadata?.presented!=true && model.messageMetadata?.presented!=true})
                    }
                    state.threadLoading -> CircularProgressIndicator(threadProgress)
                    state.threadProblem != null -> {
                        Text(error(state.threadProblem), modifier = announcement.semantics {contentDescription=threadScope+": "+error(state.threadProblem)})
                        Button(modifier=Modifier.semantics {contentDescription=threadScope+": "+text("retry")},onClick = { if(ownsControl())model.retryThreadWindow(threadRetry) }) { Text(text("retry")) }
                    }
                    state.thread != null -> {
                        val thread = state.thread
                        if(filesEntry!=null)TextButton(onClick={if(ownsControl())model.openFiles(filesEntry)}) {Text(text("inboxFilesTitle"))}
                        Text(value(thread.conversation.title), style = MaterialTheme.typography.titleMedium)
                        Text("${text("channel")}: ${ReadChannelText.label(thread.conversation.channel,::text)}")
                        model.handoffState?.let {handoff->Text("${text("handoffReadTitle")}: ${text(handoff.copyKey)}",modifier=announcement)}
                        if (links != null && clientRequest != null && inspectorEntry != null) {
                            TextButton(onClick = { if(ownsControl())model.openClientEntry(inspectorEntry,control) }) { Text("${text("openTarget")} · ${text("senderClient")}") }
                        }
                        if(handoffEntry!=null && !model.reply.submissionBlocked && !model.retryCommandsBlocked)TextButton(onClick={if(ownsControl())model.openHandoff(handoffEntry,control)}) {Text(text("handoffTestAction"))}
                        if(model.retryCommandsBlocked)Text(text("inboxRetryBlocked"),modifier=announcement) else replyEntry?.let { entry -> TextButton(onClick={if(ownsReply() && model.reply.entryControl==entry)model.openReply(entry.context,control)}){Text(text("replyDraftTitle"))} }
                        if (thread.windowCapped) Text(text("partial"), modifier = announcement)
                        if (thread.messages.isEmpty()) Text(text("messagesEmpty"), modifier = announcement)
                        LazyColumn(Modifier.weight(1f), state = messageScroll, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            items(thread.messages, key = { it.id }) { message ->
                                Column(Modifier.fillMaxWidth().wrapContentWidth(if (message.direction == "outbound") Alignment.End else Alignment.Start).padding(vertical = 8.dp)) {
                                    Text(sender(message.senderType), style = MaterialTheme.typography.labelMedium)
                                    model.messageFilesEntryControl(message)?.let {entry->TextButton(onClick={if(ownsControl())model.openMessageFiles(entry)}) {Text(text("inboxMessageReadTitle"))}}
                                    Text(value(message.text))
                                    Text("${text("messageStateTitle")}: ${text(message.sourceState.copyKey)}",style=MaterialTheme.typography.labelSmall)
                                    Text(message.createdAt?.let { formatAppointmentDate(it, scope.business.timezone, language) } ?: text("notAvailable"), style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }
            }
            else -> {
                OutlinedTextField(value = state.query, onValueChange = {if(ownsControl())model.searchInput(it,input)}, label = { Text(text("inboxSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                FilterChip(selected = state.unreadOnly, onClick = { if(ownsControl())model.filterUnreadList(!state.unreadOnly,list) }, label = { Text(text("unread")) })
                if (state.problem != null) {
                    Text(error(state.problem), modifier = announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
                    Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryListWindow(list) }) { Text(text("retry")) }
                } else {
                    if (state.partial) Text(text("partial"), modifier = announcement)
                    if (state.showsEmpty) Text(text(if (state.query.isBlank() && !state.unreadOnly) "inboxEmpty" else "noResults"), modifier = announcement)
                    if (state.visible.isEmpty()) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryListWindow(list) }) { Text(text("retry")) }
                    LazyColumn(Modifier.weight(1f),state = listScroll) {
                        items(state.visible, key = { it.id }) { item ->
                            ListItem(headlineContent = { Text(value(item.title)) }, supportingContent = {
                                Column { Text(value(item.preview?.text)); Text("${text("unread")}: ${item.unreadCount}", style = MaterialTheme.typography.labelSmall) }
                            }, modifier = Modifier.clickable(role = Role.Button) { if(ownsControl())model.openList(item.id,list) })
                        }
                    }
                }
            }
        }
    }
}
