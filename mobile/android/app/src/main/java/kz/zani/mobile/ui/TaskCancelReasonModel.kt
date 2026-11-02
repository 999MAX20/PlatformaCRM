package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

// Local UI visits only; the fake authorization and retained ledger stay separate.
data class TaskCancelReasonEntryControl(val read:TaskCommentRead,val visit:Int)
data class TaskCancelReasonControl(val selection:TaskCancelReasonSelection,val visit:Int)
data class TaskCancelReasonInputControl(val control:TaskCancelReasonControl)
data class TaskCancelReasonClearConfirmation(val id:Int,val control:TaskCancelReasonControl,val contentRevision:Int)
data class TaskCancelReasonReturnControl(val editor:TaskCancelReasonControl?,val clear:TaskCancelReasonClearConfirmation?)
class TaskCancelReasonModel(private val port: SyntheticTaskCancelPort?=null,private val ownerScope: CoroutineScope?=null) {
    private var sourceStatus:String?=null
    private val session=TaskCancelReasonSession()
    private val ledger=TaskCancelAttemptLedger()
    var state by mutableStateOf(session.state);private set
    var submission by mutableStateOf<TaskCancelAttemptRecord?>(null);private set
    val currentReadConfirmed get()=state.read?.let {read->ledger.records.any {it.phase==TaskCancelAttemptPhase.CONFIRMED && it.attempt.review.selection.read==read}} ?: false
    var submissionBlocked by mutableStateOf(false);private set
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var clearConfirmation by mutableStateOf<TaskCancelReasonClearConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val entryControl get()=state.read?.takeIf {state.available && state.selection==null}?.let {TaskCancelReasonEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {TaskCancelReasonControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {!submissionBlocked && state.phase==TaskCommentPhase.EDITING}?.let {TaskCancelReasonInputControl(it)}
    val returnControl get()=TaskCancelReasonReturnControl(control,clearConfirmation)
    private fun invalidateVisit() {entryVisit++;viewVisit++;clearConfirmation=null}
    private fun authorization(): SyntheticTaskCancelAuthorization? {
        if(!session.state.available || sourceStatus !in listOf("open","in_progress"))return null
        val context=session.state.read?.context ?: return null
        return port?.grants?.firstNotNullOfOrNull {it.authorization(context)}
    }
    val canSubmit get()=authorization()!=null && !submissionBlocked && state.phase==TaskCommentPhase.REVIEW
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {state=session.state;submission=ledger.visible(authorization());submissionBlocked=state.read?.let {ledger.blocked(it.context)} ?: false}
    fun retainOwner(business: Int?,epoch: Int?) {sourceStatus=null;session.retainOwner(business,epoch);sync();invalidateVisit()}
    fun begin(read: TaskCommentRead?) {sourceStatus=null;session.begin(read);sync();invalidateVisit()}
    fun receive(verified:Boolean,status:String?,read:TaskCommentRead) {if(state.read!=read)return;session.receive(verified,status,read);sourceStatus=if(session.state.available)status else null;sync();invalidateVisit()}
    fun pause() {sourceStatus=null;session.pause();sync();invalidateVisit()}
    fun open(read: TaskCommentRead) {if(session.open(read)) {sync();invalidateVisit()}}
    fun update(text: String,selection: TaskCancelReasonSelection) {if(submissionBlocked)return;val before=state.text;session.update(text,selection);sync();if(state.text!=before) {contentRevision++;clearConfirmation=null}}
    fun prepare(selection: TaskCancelReasonSelection) {if(submissionBlocked)return;val accepted=session.prepare(selection);sync();if(accepted)invalidateVisit()}
    fun back(selection: TaskCancelReasonSelection) {if(state.selection!=selection)return;if(submissionBlocked)session.close(selection) else session.back(selection);sync();invalidateVisit()}
    fun close(selection: TaskCancelReasonSelection) {if(state.selection!=selection)return;session.close(selection);sync();invalidateVisit()}
    fun discard(selection: TaskCancelReasonSelection) {if(submissionBlocked || state.selection!=selection)return;session.discard(selection);sync();contentRevision++;invalidateVisit()}
    // Owner VM scope survives closing this editor; Back does not cancel or replay the attempt.
    fun launchSubmit(review: TaskCancelReasonReview) {ownerScope?.launch {submit(review)}}
    suspend fun submit(expected: TaskCancelReasonReview) {
        val selection=expected.selection
        if(state.selection!=selection || !state.available || state.phase!=TaskCommentPhase.REVIEW)return
        val review=state.review?.takeIf {it==expected} ?: return
        val authorization=authorization() ?: return;val port=port ?: return
        val status=sourceStatus ?: return
        val attempt=ledger.begin(review,state.text,status,authorization) ?: return;sync();invalidateVisit()
        try {val result=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,result)}
        catch(error: Exception) {ledger.complete(attempt,SyntheticTaskCancelOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(submission?.attempt==attempt)invalidateVisit()}
    }
    fun acknowledge(selection: TaskCancelReasonSelection,attemptID: Int) {
        if(state.selection!=selection)return
        val authorization=authorization() ?: return;val record=submission?.takeIf {it.attempt.localID==attemptID} ?: return
        if(!ledger.acknowledge(authorization))return
        if(record.phase==TaskCancelAttemptPhase.CONFIRMED) {session.discard(selection);contentRevision++} else if(state.phase==TaskCommentPhase.REVIEW)session.back(selection)
        sync();invalidateVisit()
    }
    fun open(expected:TaskCancelReasonEntryControl?) {if(expected!=null && entryControl==expected)open(expected.read)}
    fun update(text:String,input:TaskCancelReasonInputControl?) {if(input!=null && inputControl==input)update(text,input.control.selection)}
    fun prepare(expected:TaskCancelReasonControl?) {if(expected!=null && control==expected)prepare(expected.selection)}
    fun back(expected:TaskCancelReasonReturnControl?) {
        if(expected==null || returnControl!=expected)return
        val question=expected.clear;val editor=expected.editor
        if(question!=null)dismissClear(question) else if(editor!=null)back(editor.selection)
    }
    fun close(expected:TaskCancelReasonReturnControl?) {if(expected!=null && returnControl==expected)expected.editor?.let {close(it.selection)}}
    fun launchSubmit(review:TaskCancelReasonReview,expected:TaskCancelReasonControl?) {ownerScope?.launch {submit(review,expected)}}
    suspend fun submit(review:TaskCancelReasonReview,expected:TaskCancelReasonControl?) {if(expected==null || control!=expected || clearConfirmation!=null || !canSubmit)return;submit(review)}
    fun acknowledge(expected:TaskCancelReasonControl?,record:TaskCancelAttemptRecord) {if(expected!=null && control==expected && submission==record)acknowledge(expected.selection,record.attempt.localID)}
    fun askClear(expected:TaskCancelReasonControl?) {
        if(expected==null || control!=expected || !state.available || submissionBlocked)return
        clearConfirmation=TaskCancelReasonClearConfirmation(++dialogRevision,expected,contentRevision)
    }
    fun dismissClear(expected:TaskCancelReasonClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:TaskCancelReasonClearConfirmation) {if(clearConfirmation==expected && control==expected.control && contentRevision==expected.contentRevision && !submissionBlocked)discard(expected.control.selection)}
}
