package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

// Local UI visits only; the fake authorization and retained ledger stay separate.
data class TaskCommentEntryControl(val read:TaskCommentRead,val visit:Int)
data class TaskCommentControl(val selection:TaskCommentSelection,val visit:Int)
data class TaskCommentInputControl(val control:TaskCommentControl)
data class TaskCommentClearConfirmation(val id:Int,val control:TaskCommentControl,val contentRevision:Int)
data class TaskCommentReturnControl(val editor:TaskCommentControl?,val clear:TaskCommentClearConfirmation?)
class TaskCommentModel(private val port: SyntheticTaskCommentPort?=null,private val ownerScope: CoroutineScope?=null) {
    private val session=TaskCommentSession()
    private val ledger=TaskCommentAttemptLedger()
    var state by mutableStateOf(session.state);private set
    var submission by mutableStateOf<TaskCommentAttemptRecord?>(null);private set
    var submissionBlocked by mutableStateOf(false);private set
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var clearConfirmation by mutableStateOf<TaskCommentClearConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val entryControl get()=state.read?.takeIf {state.available && state.selection==null}?.let {TaskCommentEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {TaskCommentControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {!submissionBlocked && state.phase==TaskCommentPhase.EDITING}?.let {TaskCommentInputControl(it)}
    val returnControl get()=TaskCommentReturnControl(control,clearConfirmation)
    private fun invalidateVisit() {entryVisit++;viewVisit++;clearConfirmation=null}
    private fun authorization(): SyntheticTaskCommentAuthorization? {
        if(!session.state.available)return null
        val context=session.state.read?.context ?: return null
        return port?.grants?.firstNotNullOfOrNull {it.authorization(context)}
    }
    val canSubmit get()=authorization()!=null && !submissionBlocked && state.phase==TaskCommentPhase.REVIEW
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {state=session.state;submission=ledger.visible(authorization());submissionBlocked=state.read?.let {ledger.blocked(it.context)} ?: false}
    fun retainOwner(business: Int?,epoch: Int?) {session.retainOwner(business,epoch);sync();invalidateVisit()}
    fun begin(read: TaskCommentRead?) {session.begin(read);sync();invalidateVisit()}
    fun receive(verified: Boolean,read: TaskCommentRead) {if(state.read!=read)return;session.receive(verified,read);sync();invalidateVisit()}
    fun pause() {session.pause();sync();invalidateVisit()}
    fun open(read: TaskCommentRead) {if(session.open(read)) {sync();invalidateVisit()}}
    // Any exact raw edit revokes prior destructive-clear consent, including NFC/NFD changes.
    fun update(text: String,selection: TaskCommentSelection) {if(submissionBlocked)return;val before=state.text;session.update(text,selection);sync();if(state.text!=before) {contentRevision++;clearConfirmation=null}}
    fun prepare(selection: TaskCommentSelection) {if(submissionBlocked)return;val accepted=session.prepare(selection);sync();if(accepted)invalidateVisit()}
    fun back(selection: TaskCommentSelection) {if(state.selection!=selection)return;if(submissionBlocked)session.close(selection) else session.back(selection);sync();invalidateVisit()}
    fun close(selection: TaskCommentSelection) {if(state.selection!=selection)return;session.close(selection);sync();invalidateVisit()}
    fun discard(selection: TaskCommentSelection) {if(submissionBlocked || state.selection!=selection)return;session.discard(selection);sync();contentRevision++;invalidateVisit()}
    // Owner VM scope survives closing this editor; Back does not cancel or replay the attempt.
    fun launchSubmit(review: TaskCommentReview) {ownerScope?.launch {submit(review)}}
    suspend fun submit(expected: TaskCommentReview) {
        val selection=expected.selection
        if(state.selection!=selection || !state.available || state.phase!=TaskCommentPhase.REVIEW)return
        val review=state.review?.takeIf {it==expected} ?: return
        val authorization=authorization() ?: return;val port=port ?: return
        val attempt=ledger.begin(review,state.text,authorization) ?: return;sync();invalidateVisit()
        try {val result=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,result)}
        catch(error: Exception) {ledger.complete(attempt,SyntheticTaskCommentOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(submission?.attempt==attempt)invalidateVisit()}
    }
    fun acknowledge(selection: TaskCommentSelection,attemptID: Int) {
        if(state.selection!=selection)return
        val authorization=authorization() ?: return;val record=submission?.takeIf {it.attempt.localID==attemptID} ?: return
        if(!ledger.acknowledge(authorization))return
        if(record.phase==TaskCommentAttemptPhase.CONFIRMED) {session.discard(selection);contentRevision++} else if(state.phase==TaskCommentPhase.REVIEW)session.back(selection)
        sync();invalidateVisit()
    }
    fun open(expected:TaskCommentEntryControl?) {if(expected!=null && entryControl==expected)open(expected.read)}
    fun update(text:String,input:TaskCommentInputControl?) {if(input!=null && inputControl==input)update(text,input.control.selection)}
    fun prepare(expected:TaskCommentControl?) {if(expected!=null && control==expected)prepare(expected.selection)}
    fun back(expected:TaskCommentReturnControl?) {
        if(expected==null || returnControl!=expected)return
        val question=expected.clear;val editor=expected.editor
        if(question!=null)dismissClear(question) else if(editor!=null)back(editor.selection)
    }
    fun close(expected:TaskCommentReturnControl?) {if(expected!=null && returnControl==expected)expected.editor?.let {close(it.selection)}}
    fun launchSubmit(review:TaskCommentReview,expected:TaskCommentControl?) {ownerScope?.launch {submit(review,expected)}}
    suspend fun submit(review:TaskCommentReview,expected:TaskCommentControl?) {if(expected==null || control!=expected || clearConfirmation!=null || !canSubmit)return;submit(review)}
    fun acknowledge(expected:TaskCommentControl?,record:TaskCommentAttemptRecord) {if(expected!=null && control==expected && submission==record)acknowledge(expected.selection,record.attempt.localID)}
    fun askClear(expected:TaskCommentControl?) {
        if(expected==null || control!=expected || !state.available || submissionBlocked)return
        clearConfirmation=TaskCommentClearConfirmation(++dialogRevision,expected,contentRevision)
    }
    fun dismissClear(expected:TaskCommentClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:TaskCommentClearConfirmation) {if(clearConfirmation==expected && control==expected.control && contentRevision==expected.contentRevision && !submissionBlocked)discard(expected.control.selection)}
}
