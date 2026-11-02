package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.InboxRepository
import kz.zani.mobile.data.InboxClientRepository
import kz.zani.mobile.data.QuickReplyRepository
import kz.zani.mobile.data.InboxConversationFilesRepository
import kz.zani.mobile.data.InboxMessageFilesRepository
import kz.zani.mobile.data.InboxSelfAssignmentRepository
import kz.zani.mobile.data.InboxReadMarkerRepository
import kz.zani.mobile.data.InboxPriorityRepository
import kz.zani.mobile.data.InboxLifecycleRepository
import kz.zani.mobile.data.InboxLinkClientRepository
import kz.zani.mobile.data.ClientSearchRepository
import kz.zani.mobile.data.LeadReadRepository
import kz.zani.mobile.data.InboxLinkLeadRepository
import kz.zani.mobile.data.DealReadRepository
import kz.zani.mobile.data.InboxLinkDealRepository
import kz.zani.mobile.data.TeamMemberReadRepository
import kz.zani.mobile.data.InboxTaskSourceRepository
import kz.zani.mobile.data.InboxExistingClientRepository
import kz.zani.mobile.data.InboxExistingLeadRepository
import kz.zani.mobile.data.InboxExistingDealRepository
import kz.zani.mobile.data.InboxTargetAssignmentRepository

// Local captured presentation only, never wire/entity-version/permission metadata.
data class InboxControl(val business:Int,val epoch:Int,val generation:Int,val thread:InboxReadSelection?)

data class InboxState(
    val scopeEpoch: Int? = null, val searchRevision: Int = 0,
    val business: Int? = null, val items: List<InboxConversation> = emptyList(), val total: Int = 0,
    val query: String = "", val unreadOnly: Boolean = false,
    val loading: Boolean = false, val loaded: Boolean = false, val problem: ReadProblem? = null,
    val selectedID: Int? = null, val thread: InboxThread? = null, val threadLoading: Boolean = false, val threadProblem: ReadProblem? = null
) {
    val partial: Boolean get() = total > items.size
    val visible: List<InboxConversation> get() = items.filter { item ->
        (!unreadOnly || item.unreadCount > 0) && (query.isBlank() || listOfNotNull(item.title, item.preview?.text).any { it.contains(query.trim(), ignoreCase = true) })
    }
    val showsEmpty: Boolean get() = loaded && !loading && problem == null && !partial && visible.isEmpty()
}

data class InboxListInputControl(val parent:InboxControl,val window:Int)
data class InboxListControl(val input:InboxListInputControl,val revision:Int)
data class InboxThreadRetryControl(val parent:InboxReturnControl,val failure:ReadProblem)

data class InboxReturnControl(val parent:InboxControl?,val thread:InboxReadSelection?,val reply:ReplyDraftReturnControl,val client:InboxClientReturnControl?,val handoff:HandoffReturnControl,val files:InboxConversationFilesControl?=null,val messageFiles:InboxMessageFilesControl?=null)
data class InboxFilesEntryControl(val parent:InboxReturnControl,val child:InboxConversationFilesControl)
data class InboxFilesPresentationControl(val parent:InboxControl,val thread:InboxReadSelection,val child:InboxConversationFilesPresentation,val reply:ReplyDraftReturnControl,val client:InboxClientReturnControl?,val handoff:HandoffReturnControl)
data class InboxMessageFilesEntryControl(val parent:InboxReturnControl,val row:InboxMessage,val child:InboxMessageFilesControl)
data class InboxMessageFilesPresentationControl(val parent:InboxControl,val thread:InboxReadSelection,val child:InboxMessageFilesPresentation,val reply:ReplyDraftReturnControl,val client:InboxClientReturnControl?,val handoff:HandoffReturnControl,val files:InboxConversationFilesControl?)
class InboxViewModel(private val repository: InboxRepository,quickReplies: QuickReplyRepository?=null,replySubmission:SyntheticInboxReplyPort?=null,handoffSubmission:SyntheticHandoffPort?=null,files:InboxConversationFilesRepository?=null,messageFiles:InboxMessageFilesRepository?=null,retrySubmission:SyntheticInboxRetryPort?=null,assignmentRead:InboxSelfAssignmentRepository?=null,assignmentSubmission:SyntheticInboxSelfAssignmentPort?=null,markerRead:InboxReadMarkerRepository?=null,markerSubmission:SyntheticInboxReadMarkerPort?=null,priorityRead:InboxPriorityRepository?=null,prioritySubmission:SyntheticInboxPriorityPort?=null,lifecycleRead:InboxLifecycleRepository?=null,lifecycleSubmission:SyntheticInboxLifecyclePort?=null,linkRead:InboxLinkClientRepository?=null,linkClients:ClientSearchRepository?=null,linkSubmission:SyntheticInboxLinkClientPort?=null,leads:LeadReadRepository?=null,leadLinkRead:InboxLinkLeadRepository?=null,leadLinkSubmission:SyntheticInboxLinkLeadPort?=null,deals:DealReadRepository?=null,dealLinkRead:InboxLinkDealRepository?=null,dealLinkSubmission:SyntheticInboxLinkDealPort?=null,members:TeamMemberReadRepository?=null,targetAssignmentRead:InboxTargetAssignmentRepository?=null,targetAssignmentSubmission:SyntheticInboxTargetAssignmentPort?=null,taskSourceRead:InboxTaskSourceRepository?=null,taskCreateSubmission:SyntheticInboxCreateTaskPort?=null,existingClientRead:InboxExistingClientRepository?=null,existingClientSubmission:SyntheticInboxExistingClientPort?=null,existingLeadRead:InboxExistingLeadRepository?=null,existingLeadSubmission:SyntheticInboxExistingLeadPort?=null,existingDealRead:InboxExistingDealRepository?=null,existingDealSubmission:SyntheticInboxExistingDealPort?=null) : ViewModel() {
    val messageMetadata=messageFiles?.let {InboxMessageFilesModel(it,retrySubmission)}
    val fileMetadata=files?.let {InboxConversationFilesModel(it,assignmentRead,assignmentSubmission,markerRead,markerSubmission,priorityRead,prioritySubmission,lifecycleRead,lifecycleSubmission,linkRead,linkClients,linkSubmission,viewModelScope,leads,leadLinkRead,leadLinkSubmission,deals,dealLinkRead,dealLinkSubmission,members,targetAssignmentRead,targetAssignmentSubmission,taskSourceRead,taskCreateSubmission,existingClientRead,existingClientSubmission,existingLeadRead,existingLeadSubmission,existingDealRead,existingDealSubmission)}
    var state by mutableStateOf(InboxState()); private set
    val reply = ReplyDraftModel(quickReplies,viewModelScope,replySubmission)
    val handoff=InboxHandoffModel(handoffSubmission,viewModelScope)
    val clientLinks = (repository as? InboxClientRepository)?.let { InboxClientModel(it,viewModelScope) }
    init {
        messageMetadata?.commandsBlocked={conversationCommandsBlocked || reply.submissionBlocked || handoff.blocked || reply.control!=null || handoff.control!=null || clientLinks?.state?.selectedID!=null}
        fileMetadata?.commandsBlocked={retryCommandsBlocked || reply.submissionBlocked || handoff.blocked || reply.control!=null || handoff.control!=null || clientLinks?.state?.selectedID!=null}
        reply.externalCommandBlocked={retryCommandsBlocked || conversationCommandsBlocked};handoff.externalCommandBlocked={retryCommandsBlocked || conversationCommandsBlocked}
    }
    val assignmentCommandsBlocked get()=conversationCommandsBlocked
    val conversationCommandsBlocked get()=state.business?.let {b->state.selectedID?.let {c->fileMetadata?.blocksCommands(b,c)==true}} ?: false
    val retryCommandsBlocked get()=state.business?.let {b->state.selectedID?.let {c->messageMetadata?.blocksCommands(b,c)==true}} ?: false
    private var searchRevision = 0
    private var controlGeneration by mutableStateOf(0)
    val control:InboxControl? get() {val b=state.business ?: return null;val e=state.scopeEpoch ?: return null;return if(b>0 && e>0)InboxControl(b,e,controlGeneration,threadSelection) else null}
    fun matches(expected:InboxControl?)=expected!=null && control==expected
    val returnControl get()=InboxReturnControl(control,threadSelection,reply.returnControl,clientLinks?.returnControl,handoff.returnControl,fileMetadata?.control,messageMetadata?.control)
    private var listViewRevision by mutableStateOf(0)
    val listInputControl:InboxListInputControl? get()=control?.takeIf {messageMetadata?.presented!=true && fileMetadata?.presented!=true && !state.loading && state.selectedID==null && reply.control==null && handoff.control==null && clientLinks?.state?.selectedID==null}?.let {InboxListInputControl(it,listRevision)}
    val listControl get()=listInputControl?.let {InboxListControl(it,listViewRevision)}
    val threadRetryControl:InboxThreadRetryControl? get() {val failure=state.threadProblem ?: return null;return if(messageMetadata?.presented!=true && fileMetadata?.presented!=true && control!=null && threadSelection!=null && !state.threadLoading && state.thread==null && reply.control==null && handoff.control==null && clientLinks?.state?.selectedID==null)InboxThreadRetryControl(returnControl,failure) else null}
    private var listRevision = 0
    private var threadRevision = 0
    val threadSelection: InboxReadSelection? get() {val business=state.business ?: return null;val id=state.selectedID ?: return null;return InboxReadSelection(business,id,threadRevision)}
    val handoffState: HandoffReadState? get() {
        val business=state.business ?: return null;val id=state.selectedID ?: return null;val epoch=state.scopeEpoch ?: return null;val thread=state.thread ?: return null
        return if(epoch>0 && !state.threadLoading && state.threadProblem==null && thread.validFor(business,id))thread.conversation.handoffState else null
    }
    fun load(business: Int?, epoch: Int? = null) {
        reply.retainOwner(business,epoch);handoff.retainOwner(business,epoch)
        messageMetadata?.bind(null);fileMetadata?.bind(null);clientLinks?.clear()
        ++searchRevision;++controlGeneration
        val ticket = ++listRevision; ++threadRevision
        state = InboxState(scopeEpoch = epoch, searchRevision = searchRevision, business = business, query = if (state.business == business && state.scopeEpoch == epoch) state.query else "",
            unreadOnly = state.business == business && state.scopeEpoch == epoch && state.unreadOnly, loading = business != null)
        if (business == null) return
        if (business <= 0) { state = state.copy(loading = false, problem = ReadProblem.INVALID_CONTEXT); return }
        viewModelScope.launch {
            try {
                val page = repository.inbox(business)
                if (ticket != listRevision) return@launch
                if (!page.validFor(business)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(items = page.items, total = page.total, loading = false, loaded = true)
            } catch (error: Exception) {
                if (error is CancellationException) {
                    if (ticket == listRevision) state = state.copy(loading = false)
                    throw error
                }
                if (ticket == listRevision) state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    // Every exact raw edit revokes list actions; continuous input keeps its independent owner.
    fun search(query:String) {if(query!=state.query)++listViewRevision;state=state.copy(query=query)}
    fun back(expected: InboxReadSelection?) {if(expected!=null && threadSelection==expected)back()}
    fun retryThread(expected: InboxReadSelection?) {if(expected!=null && threadSelection==expected)open(expected.id)}
    fun reconcileHandoffOwner(business: Int?,epoch: Int) {if(state.business==business && state.scopeEpoch==epoch)return;load(null)}
    fun unreadOnly(enabled:Boolean) {if(enabled!=state.unreadOnly)++listViewRevision;state=state.copy(unreadOnly=enabled)}
    fun open(id: Int) {
        val business = state.business ?: return
        if (state.items.none { it.id == id }) return
        ++controlGeneration
        messageMetadata?.bind(null);fileMetadata?.bind(null);clientLinks?.clear()
        reply.beginRead(business,id,state.scopeEpoch);handoff.beginRead(business,id,state.scopeEpoch)
        val ticket = ++threadRevision; val scope = listRevision
        state = state.copy(selectedID = id, thread = null, threadLoading = true, threadProblem = null)
        viewModelScope.launch {
            try {
                val detail = repository.thread(business, id)
                if (ticket != threadRevision || scope != listRevision) return@launch
                if (!detail.validFor(business, id)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(searchRevision = ++searchRevision, thread = detail, items = state.items.map { if (it.id == id) detail.conversation else it }, threadLoading = false)
                bindFiles();reply.verified(detail,business,id,state.scopeEpoch);handoff.verified(detail,business,id,state.scopeEpoch)
                clientLinks?.bind(detail,InboxReadSelection(business,id,ticket)) { fresh,problem ->
                    if (ticket == threadRevision && scope == listRevision) {
                        messageMetadata?.bind(null);fileMetadata?.bind(null)
                        if (fresh != null) {reply.verified(fresh,business,id,state.scopeEpoch);handoff.verified(fresh,business,id,state.scopeEpoch)} else {reply.pause();handoff.pause()}
                        state = if (fresh != null) state.copy(searchRevision=++searchRevision,thread=fresh,items=state.items.map { if (it.id==id) fresh.conversation else it },threadProblem=null)
                        else state.copy(thread=null,threadProblem=problem)
                        if(fresh!=null)bindFiles()
                    }
                }
            } catch (error: Exception) {
                if (error is CancellationException) {
                    if (ticket == threadRevision && scope == listRevision) back()
                    throw error
                }
                if (ticket == threadRevision && scope == listRevision) { reply.pause();handoff.pause();state = state.copy(threadLoading = false, threadProblem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE) }
            }
        }
    }
    fun backReply(): Boolean { val selection=reply.state.selection ?: return false; reply.back(selection);return true }
    fun backClient(): Boolean = clientLinks?.let { if (it.profile.backWork()) true else it.back() } ?: false
    fun back() {messageMetadata?.bind(null);fileMetadata?.bind(null);++controlGeneration; reply.pause();handoff.pause(); clientLinks?.clear(); ++threadRevision; state = state.copy(selectedID = null, thread = null, threadLoading = false, threadProblem = null) }
    fun back(expected:InboxControl?,thread:InboxReadSelection?) {if(messageMetadata?.presented!=true && fileMetadata?.presented!=true && matches(expected) && thread!=null && threadSelection==thread)back()}
    fun retryThread(expected:InboxReadSelection?,control:InboxControl?) {if(matches(control))retryThread(expected)}
    fun search(text:String,expected:InboxControl?) {if(matches(expected) && !state.loading && state.selectedID==null)search(text)}
    fun filterUnread(value:Boolean,previous:Boolean,expected:InboxControl?) {if(matches(expected) && !state.loading && state.selectedID==null && state.unreadOnly==previous)unreadOnly(value)}
    fun open(id:Int,expected:InboxControl?) {if(matches(expected) && state.loaded && !state.loading && state.problem==null && state.selectedID==null && state.visible.any {it.id==id})open(id)}
    fun retryList(expected:InboxControl?) {if(expected!=null && matches(expected) && !state.loading && state.selectedID==null)load(expected.business,expected.epoch)}
    fun openReply(context:ReplyDraftContext,expected:InboxControl?) {
        if(conversationCommandsBlocked || retryCommandsBlocked || messageMetadata?.presented==true || fileMetadata?.presented==true || !matches(expected) || state.threadLoading || state.threadProblem!=null || state.thread==null || handoff.control!=null || handoff.blocks(context) || !reply.state.available || reply.state.context!=context || reply.state.selection!=null || clientLinks?.state?.selectedID!=null)return
        ++controlGeneration;clientLinks?.back(threadSelection);reply.open(context)
    }
    fun openClient(presentation:InboxClientPresentation?,expected:InboxControl?) {
        val links=clientLinks ?: return
        if(messageMetadata?.presented==true || fileMetadata?.presented==true || !matches(expected) || state.threadLoading || state.threadProblem!=null || state.thread==null || reply.state.selection!=null || handoff.control!=null || presentation==null || links.presentation!=presentation || presentation.request!=threadSelection)return
        ++controlGeneration;links.open(presentation=presentation)
    }

    // Input stays continuous; action controls expire at every changed query/filter window.
    fun searchInput(text:String,input:InboxListInputControl?) {if(input!=null && listInputControl==input)search(text)}
    fun filterUnreadList(value:Boolean,list:InboxListControl?) {if(list!=null && listControl==list)unreadOnly(value)}
    fun openList(id:Int,list:InboxListControl?) {if(list!=null && listControl==list)open(id,list.input.parent)}
    fun retryListWindow(list:InboxListControl?) {if(list!=null && listControl==list)load(list.input.parent.business,list.input.parent.epoch)}
    fun retryThreadWindow(expected:InboxThreadRetryControl?) {if(expected!=null && threadRetryControl==expected)retryThread(expected.parent.thread)}

    fun openClientEntry(entry:InboxClientEntryControl?,expected:InboxControl?) {if(entry!=null && clientLinks?.entryControl==entry)openClient(entry.presentation,expected)}
    fun retryClient(expected:InboxClientControl?,parent:InboxControl?) {
        if(messageMetadata?.presented==true || fileMetadata?.presented==true || !matches(parent) || reply.state.selection!=null || handoff.control!=null || state.threadLoading || state.threadProblem!=null || state.thread==null || expected==null || expected.presentation.request!=threadSelection)return
        clientLinks?.retry(expected)
    }
    fun openHandoff(entry:HandoffEntryControl?,expected:InboxControl?) {
        val thread=state.thread ?: return;val b=state.business ?: return;val id=state.selectedID ?: return
        if(conversationCommandsBlocked || retryCommandsBlocked || messageMetadata?.presented==true || fileMetadata?.presented==true || !matches(expected) || state.threadLoading || state.threadProblem!=null || !thread.validFor(b,id) || reply.control!=null || reply.submissionBlocked || clientLinks?.state?.selectedID!=null || entry==null || handoff.entryControl!=entry || entry.context.business!=b || entry.context.conversation!=id || entry.context.epoch!=state.scopeEpoch)return
        ++controlGeneration;clientLinks?.back(threadSelection);handoff.open(entry)
    }
    fun backToThreadList(expected:InboxReturnControl?) {
        if(messageMetadata?.presented==true || fileMetadata?.presented==true || expected==null || returnControl!=expected || expected.parent==null || expected.thread==null || reply.state.selection!=null || handoff.control!=null || clientLinks?.state?.selectedID!=null)return
        back(expected.parent,expected.thread)
    }
    private val filesContext:InboxConversationFilesContext? get() {
        val read=threadSelection ?: return null;val epoch=state.scopeEpoch ?: return null;val thread=state.thread ?: return null
        return if(epoch>0 && !state.threadLoading && state.threadProblem==null && thread.validFor(read.business,read.id))InboxConversationFilesContext(read.business,read.id,epoch,read.revision)else null
    }
    private val messageFilesOwner:InboxMessageFilesOwner? get() {val read=filesContext ?: return null;val thread=state.thread ?: return null;return InboxMessageFilesOwner(read,thread.maxMessages).takeIf {it.valid}}
    private fun bindFiles() {fileMetadata?.bind(filesContext);messageMetadata?.bind(messageFilesOwner)}
    val filesEntryControl:InboxFilesEntryControl? get() {
        val files=fileMetadata ?: return null;val child=files.control ?: return null
        return if(messageMetadata?.presented!=true && filesContext==files.context && reply.control==null && handoff.control==null && clientLinks?.state?.selectedID==null && !files.presented)InboxFilesEntryControl(returnControl,child)else null
    }
    val filesPresentationControl:InboxFilesPresentationControl? get() {
        val parent=control ?: return null;val read=threadSelection ?: return null;val files=fileMetadata ?: return null;val child=files.presentation ?: return null
        return if(messageMetadata?.presented!=true && filesContext==files.context && reply.control==null && handoff.control==null && clientLinks?.state?.selectedID==null)InboxFilesPresentationControl(parent,read,child,reply.returnControl,clientLinks?.returnControl,handoff.returnControl)else null
    }
    fun matchesFiles(expected:InboxFilesPresentationControl?)=expected!=null && filesPresentationControl==expected
    fun openFiles(expected:InboxFilesEntryControl?) {if(expected==null || filesEntryControl!=expected || returnControl!=expected.parent || fileMetadata?.open(expected.child)!=true)return;++controlGeneration}
    fun closeFiles(expected:InboxFilesPresentationControl?) {if(expected==null || !matchesFiles(expected))return;fileMetadata?.close(expected.child);++controlGeneration}
    fun messageFilesEntryControl(row:InboxMessage):InboxMessageFilesEntryControl? {
        val owner=messageFilesOwner ?: return null;val model=messageMetadata ?: return null;val current=state.thread?.messages?.firstOrNull {it.id==row.id} ?: return null;val child=model.control ?: return null
        if(model.owner!=owner || model.presented || fileMetadata?.presented==true || reply.control!=null || handoff.control!=null || clientLinks?.state?.selectedID!=null || row.id<=0 || row.conversationID!=owner.read.conversation || !InboxMessageFileSourceIdentity.same(current,row))return null
        return InboxMessageFilesEntryControl(returnControl,row,child)
    }
    val messageFilesPresentationControl:InboxMessageFilesPresentationControl? get() {
        val owner=messageFilesOwner ?: return null;val model=messageMetadata ?: return null;val parent=control ?: return null;val read=threadSelection ?: return null;val child=model.presentation ?: return null
        if(model.owner!=owner || fileMetadata?.presented==true || reply.control!=null || handoff.control!=null || clientLinks?.state?.selectedID!=null || state.thread?.messages?.none {it.id==child.context.message}!=false)return null
        return InboxMessageFilesPresentationControl(parent,read,child,reply.returnControl,clientLinks?.returnControl,handoff.returnControl,fileMetadata?.control)
    }
    fun matchesMessageFiles(expected:InboxMessageFilesPresentationControl?)=expected!=null && messageFilesPresentationControl==expected
    fun openMessageFiles(expected:InboxMessageFilesEntryControl?) {if(expected==null || messageFilesEntryControl(expected.row)!=expected || returnControl!=expected.parent || messageMetadata?.open(expected.row.id,expected.child)!=true)return;++controlGeneration}
    fun closeMessageFiles(expected:InboxMessageFilesPresentationControl?) {if(expected==null || !matchesMessageFiles(expected))return;messageMetadata?.close(expected.child);++controlGeneration}
}
