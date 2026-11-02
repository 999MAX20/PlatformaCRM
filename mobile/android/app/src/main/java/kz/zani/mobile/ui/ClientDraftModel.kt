package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class ClientDraftEntryControl(val context:ClientDraftContext,val visit:Int)
data class ClientDraftControl(val selection:ClientDraftSelection,val visit:Int)
data class ClientDraftInputControl(val control:ClientDraftControl)
data class ClientDraftClearConfirmation(val id:Int,val control:ClientDraftControl,val contentRevision:Int)
data class ClientDraftReturnControl(val editor:ClientDraftControl?,val clear:ClientDraftClearConfirmation?)
class ClientDraftModel(private val port: SyntheticClientCreatePort?=null,private val ownerScope: CoroutineScope?=null,duplicateSource:SyntheticClientDuplicatePreviewSource?=null) {
    val duplicates=duplicateSource?.let {ClientDuplicatePreviewModel(it)}
    private val session=ClientDraftSession()
    private val ledger=ClientCreateAttemptLedger()
    var state by mutableStateOf(session.state);private set
    var submission by mutableStateOf<ClientCreateAttemptRecord?>(null);private set
    var submissionBlocked by mutableStateOf(false);private set
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var clearConfirmation by mutableStateOf<ClientDraftClearConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val entryControl get()=state.context?.takeIf {state.selection==null}?.let {ClientDraftEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {ClientDraftControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {!submissionBlocked && state.phase==ClientDraftPhase.EDITING}?.let {ClientDraftInputControl(it)}
    val returnControl get()=ClientDraftReturnControl(control,clearConfirmation)
    private fun invalidateVisit() {entryVisit++;viewVisit++;clearConfirmation=null;duplicates?.clear()}
    private fun authorization(): SyntheticClientCreateAuthorization? {
        val context=session.state.context ?: return null
        return port?.grants?.firstNotNullOfOrNull {it.authorization(context)}
    }
    val canSubmit get()=authorization()!=null && !submissionBlocked && state.phase==ClientDraftPhase.REVIEW
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {state=session.state;submission=ledger.visible(authorization());submissionBlocked=state.context?.let {ledger.blocked(it)} ?: false}
    fun bind(context: ClientDraftContext?) {val before=state.context;session.bind(context);sync();if(state.context!=before)invalidateVisit()}
    fun open(context: ClientDraftContext) {if(session.open(context)) {sync();invalidateVisit()}}
    fun update(field: ClientDraftField,value: String,selection: ClientDraftSelection) {if(submissionBlocked)return;val before=state.values;session.update(field,value,selection);sync();if(state.values!=before) {contentRevision++;clearConfirmation=null}}
    fun prepare(selection: ClientDraftSelection) {if(submissionBlocked)return;val accepted=session.prepare(selection);sync();if(accepted)invalidateVisit()}
    fun back(selection: ClientDraftSelection) {if(state.selection!=selection)return;if(submissionBlocked)session.close(selection) else session.back(selection);sync();invalidateVisit()}
    fun close(selection: ClientDraftSelection) {if(state.selection!=selection)return;session.close(selection);sync();invalidateVisit()}
    fun discard(selection: ClientDraftSelection) {if(submissionBlocked || state.selection!=selection)return;session.discard(selection);sync();contentRevision++;invalidateVisit()}
    fun launchSubmit(review: ClientDraftReview) {ownerScope?.launch {submit(review)}}
    suspend fun submit(expected: ClientDraftReview) {
        if(state.selection!=expected.selection || state.context!=expected.selection.context || state.phase!=ClientDraftPhase.REVIEW || state.review!=expected || state.values!=expected.values)return
        val authorization=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(expected,authorization) ?: return;sync();invalidateVisit()
        try {val outcome=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,outcome)}
        catch(error: Exception) {ledger.complete(attempt,SyntheticClientCreateOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(submission?.attempt==attempt)invalidateVisit()}
    }
    fun acknowledge(selection: ClientDraftSelection,attemptID: Int) {
        if(state.selection!=selection)return
        val authorization=authorization() ?: return;val record=submission?.takeIf {it.attempt.localID==attemptID} ?: return
        if(!ledger.acknowledge(authorization))return
        if(record.phase==ClientCreateAttemptPhase.CONFIRMED) {session.discard(selection);contentRevision++} else if(state.phase==ClientDraftPhase.REVIEW)session.back(selection)
        sync();invalidateVisit()
    }
    fun launchDuplicates(expected:ClientDraftControl?,visit:ClientDuplicatePreviewVisit) {ownerScope?.launch {loadDuplicates(expected,visit)}}
    suspend fun loadDuplicates(expected:ClientDraftControl?,visit:ClientDuplicatePreviewVisit) {
        if(expected==null || control!=expected || clearConfirmation!=null || submissionBlocked || state.phase!=ClientDraftPhase.REVIEW)return
        val review=state.review?.takeIf {it.selection==expected.selection} ?: return
        duplicates?.load(ClientDuplicatePreviewInput(expected.selection.context,review.values.phone,review.values.email),visit)
    }
    fun open(expected:ClientDraftEntryControl?) {if(expected!=null && entryControl==expected)open(expected.context)}
    fun update(field:ClientDraftField,value:String,input:ClientDraftInputControl?) {if(input!=null && inputControl==input)update(field,value,input.control.selection)}
    fun prepare(expected:ClientDraftControl?) {if(expected!=null && control==expected)prepare(expected.selection)}
    fun back(expected:ClientDraftReturnControl?) {if(expected==null || returnControl!=expected)return;val question=expected.clear;val editor=expected.editor;if(question!=null)dismissClear(question) else if(editor!=null)back(editor.selection)}
    fun close(expected:ClientDraftReturnControl?) {if(expected!=null && returnControl==expected)expected.editor?.let {close(it.selection)}}
    fun launchSubmit(review:ClientDraftReview,expected:ClientDraftControl?) {ownerScope?.launch {submit(review,expected)}}
    suspend fun submit(review:ClientDraftReview,expected:ClientDraftControl?) {if(expected==null || control!=expected || clearConfirmation!=null || !canSubmit)return;submit(review)}
    fun acknowledge(expected:ClientDraftControl?,record:ClientCreateAttemptRecord) {if(expected!=null && control==expected && submission==record)acknowledge(expected.selection,record.attempt.localID)}
    fun askClear(expected:ClientDraftControl?) {if(expected==null || control!=expected || submissionBlocked)return;duplicates?.clear();clearConfirmation=ClientDraftClearConfirmation(++dialogRevision,expected,contentRevision)}
    fun dismissClear(expected:ClientDraftClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:ClientDraftClearConfirmation) {if(clearConfirmation==expected && control==expected.control && contentRevision==expected.contentRevision && !submissionBlocked)discard(expected.control.selection)}
}
