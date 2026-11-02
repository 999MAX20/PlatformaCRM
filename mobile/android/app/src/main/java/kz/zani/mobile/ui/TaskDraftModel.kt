package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientSearchRepository

data class TaskDraftEntryControl(val context:TaskDraftContext,val visit:Int)
data class TaskDraftControl(val selection:TaskDraftSelection,val visit:Int)
data class TaskDraftInputControl(val control:TaskDraftControl)
data class TaskDraftClearConfirmation(val id:Int,val control:TaskDraftControl,val contentRevision:Int)
data class TaskDraftClientPickerOwner(val control:TaskDraftControl,val contentRevision:Int)
data class TaskDraftAppointmentPickerOwner(val control:TaskDraftControl,val contentRevision:Int)
data class TaskDraftParentPickerOwner(val control:TaskDraftControl,val contentRevision:Int)
data class TaskDraftReturnControl(val editor:TaskDraftControl?,val clear:TaskDraftClearConfirmation?)
class TaskDraftModel(private val port: SyntheticTaskCreatePort?=null,private val ownerScope: CoroutineScope?=null,clients:ClientSearchRepository?=null,appointments:kz.zani.mobile.data.AgendaRepository?=null,parents:kz.zani.mobile.data.TaskReadRepository?=null) {
    private val session=TaskDraftSession()
    private val ledger=TaskCreateAttemptLedger()
    var state by mutableStateOf(session.state);private set
    var submission by mutableStateOf<TaskCreateAttemptRecord?>(null);private set
    var submissionBlocked by mutableStateOf(false);private set
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var clearConfirmation by mutableStateOf<TaskDraftClearConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val clients=if(ownerScope!=null && clients!=null)ClientSearchModel(clients,ownerScope) else null
    val appointments=if(ownerScope!=null && appointments!=null)TaskAppointmentPickerModel(appointments,ownerScope) else null
    val parents=if(ownerScope!=null && parents!=null)TaskParentPickerModel(parents,ownerScope) else null
    var parentPickerOwner by mutableStateOf<TaskDraftParentPickerOwner?>(null);private set
    var appointmentPickerOwner by mutableStateOf<TaskDraftAppointmentPickerOwner?>(null);private set
    var clientPickerOwner by mutableStateOf<TaskDraftClientPickerOwner?>(null);private set
    val entryControl get()=state.context?.takeIf {state.selection==null}?.let {TaskDraftEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {TaskDraftControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {!submissionBlocked && clientPickerOwner==null && appointmentPickerOwner==null && parentPickerOwner==null && state.phase==TaskDraftPhase.EDITING}?.let {TaskDraftInputControl(it)}
    val returnControl get()=TaskDraftReturnControl(control,clearConfirmation)
    private fun invalidateVisit() {entryVisit++;viewVisit++;clearConfirmation=null}
    private fun authorization(): SyntheticTaskCreateAuthorization? {
        val context=session.state.context ?: return null
        return port?.grants?.firstNotNullOfOrNull {it.authorization(context)}
    }
    val canSubmit get()=authorization()!=null && !submissionBlocked && state.phase==TaskDraftPhase.REVIEW
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {state=session.state;submission=ledger.visible(authorization());submissionBlocked=state.context?.let {ledger.blocked(it)} ?: false}
    fun bind(context: TaskDraftContext?) {val before=state.context;session.bind(context);sync();if(state.context!=before){resetClientPicker();resetAppointmentPicker();resetParentPicker();invalidateVisit()}}
    fun open(context: TaskDraftContext) {resetClientPicker();resetAppointmentPicker();resetParentPicker();if(session.open(context)) {sync();invalidateVisit()}}
    fun update(field: TaskDraftField,value: String,selection: TaskDraftSelection) {if(submissionBlocked || clientPickerOwner!=null || appointmentPickerOwner!=null || parentPickerOwner!=null)return;val before=state.values;session.update(field,value,selection);sync();if(state.values!=before) {contentRevision++;clearConfirmation=null}}
    fun chooseDue(mode:TaskDraftDueMode,input:TaskDraftInputControl?) {if(input==null || inputControl!=input || submissionBlocked)return;val before=state.values;session.chooseDue(mode,input.control.selection);sync();if(state.values!=before){contentRevision++;invalidateVisit()}}
    fun chooseReminder(mode:TaskDraftDueMode,input:TaskDraftInputControl?) {if(input==null || inputControl!=input || submissionBlocked)return;val before=state.values;session.chooseReminder(mode,input.control.selection);sync();if(state.values!=before){contentRevision++;invalidateVisit()}}
    fun prepare(selection: TaskDraftSelection) {if(submissionBlocked || clientPickerOwner!=null || appointmentPickerOwner!=null || parentPickerOwner!=null)return;val accepted=session.prepare(selection);sync();if(accepted)invalidateVisit()}
    fun back(selection: TaskDraftSelection) {if(state.selection!=selection)return;clientPickerOwner?.let {closeClientPicker(it);return};appointmentPickerOwner?.let {closeAppointmentPicker(it);return};parentPickerOwner?.let {closeParentPicker(it);return};if(submissionBlocked)session.close(selection) else session.back(selection);sync();invalidateVisit()}
    fun close(selection: TaskDraftSelection) {if(state.selection!=selection)return;resetClientPicker();resetAppointmentPicker();resetParentPicker();session.close(selection);sync();invalidateVisit()}
    fun discard(selection: TaskDraftSelection) {if(submissionBlocked || state.selection!=selection)return;resetClientPicker();resetAppointmentPicker();resetParentPicker();session.discard(selection);sync();contentRevision++;invalidateVisit()}
    fun launchSubmit(review: TaskDraftReview) {ownerScope?.launch {submit(review)}}
    suspend fun submit(expected: TaskDraftReview) {
        if(state.selection!=expected.selection || state.context!=expected.selection.context || state.phase!=TaskDraftPhase.REVIEW || state.review!=expected || state.values!=expected.values)return
        val authorization=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(expected,authorization) ?: return;sync();invalidateVisit()
        try {val outcome=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,outcome)}
        catch(error: Exception) {ledger.complete(attempt,SyntheticTaskCreateOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync();if(submission?.attempt==attempt)invalidateVisit()}
    }
    fun acknowledge(selection: TaskDraftSelection,attemptID: Int) {
        if(state.selection!=selection)return
        val authorization=authorization() ?: return;val record=submission?.takeIf {it.attempt.localID==attemptID} ?: return
        if(!ledger.acknowledge(authorization))return
        if(record.phase==TaskCreateAttemptPhase.CONFIRMED) {session.discard(selection);contentRevision++} else if(state.phase==TaskDraftPhase.REVIEW)session.back(selection)
        sync();invalidateVisit()
    }
    val clientPickerAvailable get()=clients!=null
    fun matchesClientPicker(owner:TaskDraftClientPickerOwner?)=owner!=null && clientPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && state.phase==TaskDraftPhase.EDITING && !submissionBlocked
    private fun resetClientPicker() {clients?.bind(null);clientPickerOwner=null}
    fun openClientPicker(input:TaskDraftInputControl?) {
        if(input==null || inputControl!=input || clearConfirmation!=null)return
        val clients=clients ?: return;invalidateVisit();val control=control ?: return
        val context=ClientSearchContext(control.selection.context.business,control.selection.context.epoch)
        clients.bind(null);clients.bind(context);clients.open(context);clientPickerOwner=TaskDraftClientPickerOwner(control,contentRevision)
    }
    fun closeClientPicker(owner:TaskDraftClientPickerOwner?) {if(!matchesClientPicker(owner))return;resetClientPicker();invalidateVisit()}
    fun confirmClient(owner:TaskDraftClientPickerOwner?,search:ClientSearchControl?) {
        if(owner==null || !matchesClientPicker(owner))return
        val clients=clients ?: return;if(search==null || !clients.matches(search))return
        val selected=clients.state.profileSelection ?: return;val profile=clients.profile.state.detail ?: return
        if(selected!=search.profile || clients.profile.readSelection!=search.read || clients.profile.state.loading || clients.profile.state.problem!=null)return
        val choice=TaskDraftClientChoice.make(profile,owner.control.selection.context.business,selected.id) ?: return
        val before=state.values;session.chooseClient(choice,owner.control.selection);sync();if(state.values!=before)++contentRevision
        resetClientPicker();invalidateVisit()
    }
    fun clearClient(input:TaskDraftInputControl?) {if(input==null || inputControl!=input || state.values.client==null)return;session.chooseClient(null,input.control.selection);sync();++contentRevision;invalidateVisit()}
    val appointmentPickerAvailable get()=appointments!=null
    fun matchesAppointmentPicker(owner:TaskDraftAppointmentPickerOwner?)=owner!=null && appointmentPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && state.phase==TaskDraftPhase.EDITING && !submissionBlocked
    private fun resetAppointmentPicker() {appointments?.begin(null);appointmentPickerOwner=null}
    fun openAppointmentPicker(input:TaskDraftInputControl?) {
        if(input==null || inputControl!=input || clearConfirmation!=null)return
        val appointments=appointments ?: return;invalidateVisit();val control=control ?: return
        appointmentPickerOwner=TaskDraftAppointmentPickerOwner(control,contentRevision);appointments.begin(control.selection.context)
    }
    fun closeAppointmentPicker(owner:TaskDraftAppointmentPickerOwner?) {if(!matchesAppointmentPicker(owner))return;resetAppointmentPicker();invalidateVisit()}
    fun confirmAppointment(owner:TaskDraftAppointmentPickerOwner?,read:TaskAppointmentPickerControl?) {
        if(owner==null || !matchesAppointmentPicker(owner))return
        val choice=appointments?.choice(read) ?: return;if(!choice.validFor(owner.control.selection.context.business))return
        val before=state.values;session.chooseAppointment(choice,owner.control.selection);sync();if(state.values!=before)++contentRevision
        resetAppointmentPicker();invalidateVisit()
    }
    fun clearAppointment(input:TaskDraftInputControl?) {if(input==null || inputControl!=input || state.values.appointment==null)return;session.chooseAppointment(null,input.control.selection);sync();++contentRevision;invalidateVisit()}
    val parentPickerAvailable get()=parents!=null
    fun matchesParentPicker(owner:TaskDraftParentPickerOwner?)=owner!=null && parentPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && state.phase==TaskDraftPhase.EDITING && !submissionBlocked
    private fun resetParentPicker() {parents?.begin(null);parentPickerOwner=null}
    fun openParentPicker(input:TaskDraftInputControl?) {
        if(input==null || inputControl!=input || clearConfirmation!=null)return
        val parents=parents ?: return;invalidateVisit();val control=control ?: return
        parentPickerOwner=TaskDraftParentPickerOwner(control,contentRevision);parents.begin(control.selection.context)
    }
    fun closeParentPicker(owner:TaskDraftParentPickerOwner?) {if(!matchesParentPicker(owner))return;resetParentPicker();invalidateVisit()}
    fun confirmParent(owner:TaskDraftParentPickerOwner?,read:TaskParentPickerControl?) {
        if(owner==null || !matchesParentPicker(owner))return
        val choice=parents?.choice(read) ?: return;if(!choice.validFor(owner.control.selection.context.business))return
        val before=state.values;session.chooseParent(choice,owner.control.selection);sync();if(state.values!=before)++contentRevision
        resetParentPicker();invalidateVisit()
    }
    fun clearParent(input:TaskDraftInputControl?) {if(input==null || inputControl!=input || state.values.parentTask==null)return;session.chooseParent(null,input.control.selection);sync();++contentRevision;invalidateVisit()}
    fun open(expected:TaskDraftEntryControl?) {if(expected!=null && entryControl==expected)open(expected.context)}
    fun update(field:TaskDraftField,value:String,input:TaskDraftInputControl?) {if(input!=null && inputControl==input)update(field,value,input.control.selection)}
    fun prepare(expected:TaskDraftControl?) {if(expected!=null && control==expected)prepare(expected.selection)}
    fun back(expected:TaskDraftReturnControl?) {if(expected==null || returnControl!=expected)return;val question=expected.clear;val editor=expected.editor;if(question!=null)dismissClear(question) else if(editor!=null)back(editor.selection)}
    fun close(expected:TaskDraftReturnControl?) {if(expected!=null && returnControl==expected)expected.editor?.let {close(it.selection)}}
    fun launchSubmit(review:TaskDraftReview,expected:TaskDraftControl?) {ownerScope?.launch {submit(review,expected)}}
    suspend fun submit(review:TaskDraftReview,expected:TaskDraftControl?) {if(expected==null || control!=expected || clearConfirmation!=null || !canSubmit)return;submit(review)}
    fun acknowledge(expected:TaskDraftControl?,record:TaskCreateAttemptRecord) {if(expected!=null && control==expected && submission==record)acknowledge(expected.selection,record.attempt.localID)}
    fun askClear(expected:TaskDraftControl?) {if(expected==null || control!=expected || submissionBlocked || clientPickerOwner!=null || appointmentPickerOwner!=null || parentPickerOwner!=null)return;clearConfirmation=TaskDraftClearConfirmation(++dialogRevision,expected,contentRevision)}
    fun dismissClear(expected:TaskDraftClearConfirmation) {if(clearConfirmation==expected)clearConfirmation=null}
    fun confirmClear(expected:TaskDraftClearConfirmation) {if(clearConfirmation==expected && control==expected.control && contentRevision==expected.contentRevision && !submissionBlocked)discard(expected.control.selection)}
}
