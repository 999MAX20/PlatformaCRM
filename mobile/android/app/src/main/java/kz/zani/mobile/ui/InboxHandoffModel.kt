package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class HandoffEntryControl(val context:ReplyDraftContext,val visit:Int)
data class HandoffControl(val selection:ReplyDraftSelection,val visit:Int)
data class HandoffInputControl(val editor:HandoffControl)
data class HandoffClearConfirmation(val id:Int,val editor:HandoffControl,val contentRevision:Int)
data class HandoffReturnControl(val editor:HandoffControl?,val clear:HandoffClearConfirmation?)
class InboxHandoffModel(private val port:SyntheticHandoffPort?=null,private val ownerScope:CoroutineScope?=null) {
    private val session=HandoffDraftSession();private val ledger=HandoffLedger()
    var state by mutableStateOf(session.state);private set
    var record:HandoffRecord? by mutableStateOf(null);private set
    var blocked by mutableStateOf(false);private set
    private var visit by mutableStateOf(0)
    var clearConfirmation:HandoffClearConfirmation? by mutableStateOf(null);private set
    private var contentRevision=0;private var dialogRevision=0
    private fun authorization():SyntheticHandoffAuthorization?=state.context?.let {c->port?.grants?.firstNotNullOfOrNull {it.authorization(c)}}
    val entryControl get()=state.context?.takeIf {state.available && state.selection==null && authorization()!=null}?.let {HandoffEntryControl(it,visit)}
    val control get()=state.selection?.let {HandoffControl(it,visit)}
    val inputControl get()=control?.takeIf {!blocked && state.phase==ReplyDraftPhase.EDITING}?.let {HandoffInputControl(it)}
    val returnControl get()=HandoffReturnControl(control,clearConfirmation)
    fun blocks(c:ReplyDraftContext)=ledger.blocked(c)
    val retainedAttemptCount get()=ledger.records.size
    var externalCommandBlocked:()->Boolean={false}
    val canSubmit get()=!externalCommandBlocked() && state.available && state.phase==ReplyDraftPhase.REVIEW && clearConfirmation==null && authorization()!=null && !blocked
    private fun sync() {state=session.state;record=ledger.visible(authorization());blocked=state.context?.let {ledger.blocked(it)} ?: false}
    private fun invalidateVisit() {visit++;clearConfirmation=null}
    fun retainOwner(business:Int?,epoch:Int?) {session.retainOwner(business,epoch);sync();invalidateVisit()}
    fun beginRead(business:Int,id:Int,epoch:Int?) {session.bind(epoch?.let {ReplyDraftContext(business,id,it)},false);sync();invalidateVisit()}
    fun verified(thread:InboxThread,business:Int,id:Int,epoch:Int?) {session.bind(epoch?.let {ReplyDraftContext(business,id,it)},thread.validFor(business,id));sync();invalidateVisit()}
    fun pause() {session.pause();sync();invalidateVisit()}
    fun clear() {session.clear();sync();invalidateVisit()}
    fun open(expected:HandoffEntryControl?) {if(expected!=null && entryControl==expected && session.open(expected.context)){sync();invalidateVisit()}}
    fun update(raw:String,input:HandoffInputControl?) {if(blocked || input==null || inputControl!=input)return;val old=state.raw;session.update(raw,input.editor.selection);sync();if(old!=state.raw){contentRevision++;clearConfirmation=null}}
    fun prepare(expected:HandoffControl?) {
        if(blocked || expected==null || control!=expected)return
        val accepted=session.prepare(expected.selection)
        sync()
        if(accepted)invalidateVisit()
    }
    fun back(expected:HandoffReturnControl?) {if(expected==null || returnControl!=expected)return;val clear=expected.clear;if(clear!=null){dismissClear(clear);return};val editor=expected.editor ?: return;if(blocked)session.close(editor.selection) else session.back(editor.selection);sync();invalidateVisit()}
    fun close(expected:HandoffReturnControl?) {if(expected==null || returnControl!=expected)return;val editor=expected.editor ?: return;session.close(editor.selection);sync();invalidateVisit()}
    fun askClear(expected:HandoffControl?) {if(!blocked && expected!=null && control==expected)clearConfirmation=HandoffClearConfirmation(++dialogRevision,expected,contentRevision)}
    fun dismissClear(expected:HandoffClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:HandoffClearConfirmation) {if(blocked || clearConfirmation!=expected || control!=expected.editor || contentRevision!=expected.contentRevision)return;session.discard(expected.editor.selection);contentRevision++;sync();invalidateVisit()}
    suspend fun submit(review:HandoffReview,expected:HandoffControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit || state.review!=review || state.selection!=review.selection || state.raw!=review.value.raw)return
        val a=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(review,a) ?: return;sync();invalidateVisit()
        try {val value=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,value)}
        catch(error:Exception){ledger.complete(attempt,SyntheticHandoffOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(record?.attempt==attempt)invalidateVisit()}
    }
    fun launchSubmit(review:HandoffReview,expected:HandoffControl?) {ownerScope?.launch {submit(review,expected)}}
    fun acknowledge(expected:HandoffControl?,record:HandoffRecord) {if(expected==null || control!=expected || this.record!=record)return;val a=authorization() ?: return;if(!ledger.acknowledge(a))return;if(record.phase==HandoffPhase.CONFIRMED){session.discard(expected.selection);contentRevision++}else session.back(expected.selection);sync();invalidateVisit()}
}
