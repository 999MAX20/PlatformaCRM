package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.QuickReplyRepository

data class ReplyDraftEntryControl(val context:ReplyDraftContext,val visit:Int)
data class ReplyDraftControl(val selection:ReplyDraftSelection,val visit:Int)
data class ReplyDraftInputControl(val control:ReplyDraftControl)
data class ReplyDraftClearConfirmation(val id:Int,val control:ReplyDraftControl,val contentRevision:Int)
data class ReplyDraftReturnControl(val editor:ReplyDraftControl?,val picker:QuickReplyControl?,val clear:ReplyDraftClearConfirmation?)
class ReplyDraftModel(source: QuickReplyRepository?=null,private val ownerScope: CoroutineScope?=null,private val port:SyntheticInboxReplyPort?=null) {
    private val session=ReplyDraftSession()
    private val ledger=InboxReplyLedger()
    var submission:InboxReplyRecord? by mutableStateOf(null);private set
    var submissionBlocked by mutableStateOf(false);private set
    var state by mutableStateOf(session.state); private set
    val quickReplies=if(source!=null && ownerScope!=null)QuickReplyModel(source,ownerScope) else null
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var clearConfirmation by mutableStateOf<ReplyDraftClearConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val entryControl get()=state.context?.takeIf {state.available && state.selection==null}?.let {ReplyDraftEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {ReplyDraftControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {!submissionBlocked && state.phase==ReplyDraftPhase.EDITING}?.let {ReplyDraftInputControl(it)}
    val returnControl get()=ReplyDraftReturnControl(control,quickReplies?.control,clearConfirmation)
    private fun invalidateVisit() {entryVisit++;viewVisit++;clearConfirmation=null}
    private var verifiedChannel: String?=null
    private fun authorization():SyntheticInboxReplyAuthorization?=state.context?.let {c->port?.grants?.firstNotNullOfOrNull {it.authorization(c)}}
    val retainedAttemptCount get()=ledger.records.size
    val hasTestPort get()=port!=null
    var externalCommandBlocked:()->Boolean={false}
    val canSubmit get()=!externalCommandBlocked() && state.available && state.phase==ReplyDraftPhase.REVIEW && clearConfirmation==null && quickReplies?.state?.selection==null && ledger.canBegin(authorization())
    suspend fun submit(review:ReplyDraftReview,expected:ReplyDraftControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit || state.selection!=review.selection || state.review!=review || state.text!=review.raw)return
        val a=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(review,a) ?: return;sync();invalidateVisit()
        try {val value=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,value)}
        catch(error:Exception){ledger.complete(attempt,SyntheticInboxReplyOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(submission?.attempt==attempt)invalidateVisit()}
    }
    fun launchSubmit(review:ReplyDraftReview,expected:ReplyDraftControl?) {ownerScope?.launch {submit(review,expected)}}
    fun acknowledge(expected:ReplyDraftControl?,record:InboxReplyRecord) {
        if(expected==null || control!=expected || submission!=record)return;val a=authorization() ?: return;if(!ledger.acknowledge(a))return
        if(record.phase==InboxReplyPhase.CONFIRMED){session.discard(expected.selection);contentRevision++}else session.back(expected.selection)
        sync();invalidateVisit()
    }
    private fun sync() {
        state=session.state
        val selection=state.selection;val channel=verifiedChannel
        quickReplies?.bind(if(state.available && state.phase==ReplyDraftPhase.EDITING && selection!=null && channel!=null)QuickReplyContext(selection,channel) else null)
        submission=ledger.visible(authorization());submissionBlocked=state.context?.let {ledger.blocked(it)} ?: false
    }
    fun retainOwner(business: Int?,epoch: Int?) {verifiedChannel=null;session.retainOwner(business,epoch);sync();invalidateVisit()}
    fun beginRead(business: Int,id: Int,epoch: Int?) {verifiedChannel=null;session.bind(epoch?.let {ReplyDraftContext(business,id,it)},false);sync();invalidateVisit()}
    fun verified(thread: InboxThread,business: Int,id: Int,epoch: Int?) {
        val available=thread.validFor(business,id) && thread.sourceStatus=="open"
        verifiedChannel=if(available)thread.conversation.channel else null
        session.bind(epoch?.let {ReplyDraftContext(business,id,it)},available);sync();invalidateVisit()
    }
    fun pause() {verifiedChannel=null;session.pause();sync();invalidateVisit()}
    fun clear() {verifiedChannel=null;session.clear();sync();invalidateVisit()}
    fun open(expected:ReplyDraftEntryControl?) {if(expected!=null && entryControl==expected)open(expected.context)}
    fun open(context: ReplyDraftContext) {if(session.open(context)) {sync();invalidateVisit()}}
    fun update(text: String,selection: ReplyDraftSelection) {if(submissionBlocked)return;val before=state.text;session.update(text,selection);sync();if(state.text!=before) {contentRevision++;clearConfirmation=null}}
    fun prepare(selection: ReplyDraftSelection) {if(submissionBlocked)return;val accepted=session.prepare(selection);sync();if(accepted)invalidateVisit()}
    fun back(selection: ReplyDraftSelection) {
        if(submissionBlocked){if(state.selection!=selection)return;session.close(selection);sync();invalidateVisit();return}
        val picker=quickReplies?.state?.selection
        if(picker!=null && picker.context.draft==selection) {quickReplies?.close(picker);return}
        if(state.selection!=selection)return;session.back(selection);sync();invalidateVisit()
    }
    fun close(selection: ReplyDraftSelection) {if(state.selection!=selection)return;session.close(selection);sync();invalidateVisit()}
    fun discard(selection: ReplyDraftSelection) {if(submissionBlocked || state.selection!=selection)return;session.discard(selection);sync();contentRevision++;invalidateVisit()}
    fun openQuickReplies(selection: ReplyDraftSelection) {
        if(submissionBlocked || state.selection!=selection || state.phase!=ReplyDraftPhase.EDITING)return
        quickReplies?.state?.context?.takeIf {it.draft==selection}?.let {quickReplies?.open(it)}
    }
    fun insert(choice: QuickReplyChoice,expected: ReplyDraftSelection): Boolean {
        if(submissionBlocked || state.selection!=expected || !state.available || state.phase!=ReplyDraftPhase.EDITING || choice.request.selection.context.draft!=expected || choice.request.selection.context.channel!=verifiedChannel)return false
        val text=quickReplies?.resolve(choice) ?: return false
        if(!session.insertTemplate(text,expected))return false
        sync();contentRevision++;invalidateVisit();return true
    }
    // Captured UI flow, still subject to the existing Core choice/selection rules.
    fun update(text:String,input:ReplyDraftInputControl?) {if(input!=null && inputControl==input && quickReplies?.state?.selection==null)update(text,input.control.selection)}
    fun prepare(expected:ReplyDraftControl?) {if(expected!=null && control==expected && quickReplies?.state?.selection==null)prepare(expected.selection)}
    fun back(expected:ReplyDraftReturnControl?) {
        if(expected==null || returnControl!=expected)return
        val question=expected.clear;val picker=expected.picker;val editor=expected.editor
        if(question!=null)dismissClear(question) else if(picker!=null)quickReplies?.close(expected=picker) else if(editor!=null)back(editor.selection)
    }
    fun close(expected:ReplyDraftReturnControl?) {if(expected!=null && returnControl==expected)expected.editor?.let {close(it.selection)}}
    fun openQuickReplies(expected:ReplyDraftControl?,entry:QuickReplyEntryControl?) {
        if(submissionBlocked || expected==null || control!=expected || !state.available || state.phase!=ReplyDraftPhase.EDITING || clearConfirmation!=null || entry==null || quickReplies?.entryControl!=entry || entry.context.draft!=expected.selection)return
        quickReplies?.open(entry)
    }
    fun insert(choice:QuickReplyChoice,expected:ReplyDraftControl?,picker:QuickReplyControl?):Boolean {
        if(expected==null || control!=expected || clearConfirmation!=null || quickReplies?.resolve(choice,picker)==null)return false
        return insert(choice,expected.selection)
    }
    fun askClear(expected:ReplyDraftControl?) {
        if(submissionBlocked || expected==null || control!=expected || !state.available || quickReplies?.state?.selection!=null)return
        clearConfirmation=ReplyDraftClearConfirmation(++dialogRevision,expected,contentRevision)
    }
    fun dismissClear(expected:ReplyDraftClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:ReplyDraftClearConfirmation) {if(!submissionBlocked && clearConfirmation==expected && control==expected.control && contentRevision==expected.contentRevision)discard(expected.control.selection)}
}
