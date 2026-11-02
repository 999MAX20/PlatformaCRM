package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class TaskAppointmentEditControl(val source:TaskAppointmentEditSource,val visit:Int,val draft:TaskAppointmentEditDraft,val editing:Boolean,val review:TaskAppointmentEditReview?,val record:TaskAppointmentEditRecord?,val clearID:Int?)
data class TaskAppointmentEditInputControl(val source:TaskAppointmentEditSource,val visit:Int,val child:TaskAppointmentPickerInputControl)
data class TaskAppointmentEditClear(val id:Int,val read:TaskCommentRead,val visit:Int,val draft:TaskAppointmentEditDraft)
class TaskAppointmentEditModel(private val port:SyntheticTaskAppointmentEditPort,private val scope:CoroutineScope,appointments:kz.zani.mobile.data.AgendaRepository) {
    val picker=TaskAppointmentPickerModel(appointments,scope)
    var source:TaskAppointmentEditSource? by mutableStateOf(null);private set
    var review:TaskAppointmentEditReview? by mutableStateOf(null);private set
    var draft by mutableStateOf(TaskAppointmentEditDraft());private set
    var editing by mutableStateOf(false);private set
    var showsIssue by mutableStateOf(false);private set
    var clearConfirmation:TaskAppointmentEditClear? by mutableStateOf(null);private set
    private val ledger=TaskAppointmentEditLedger();private val consumedReads=mutableListOf<TaskCommentRead>();private val buffers=mutableMapOf<String,TaskAppointmentEditDraft>()
    private var visit by mutableStateOf(0);private var dialog=0;private var ownerBusiness:Int?=null;private var ownerEpoch:Int?=null
    private fun key(c:TaskCommentContext)="${c.business}/${c.task}/${c.epoch}"
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskAppointmentEditControl(it,visit,draft,editing,review,submission,clearConfirmation?.id)}
    val inputControl get()=source?.takeIf {draft.mode==TaskAppointmentEditMode.SET && editing && !blocked && !consumed && review==null && clearConfirmation==null}?.let {source->picker.inputControl?.let {TaskAppointmentEditInputControl(source,visit,it)}}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.statusValid==true || blocked || consumed)
    val canOpen get()=source?.valid==true && authorization!=null && !blocked && !consumed && !editing && review==null
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && editing && review==null && clearConfirmation==null
    val ownsEditor get()=editing || review!=null || clearConfirmation!=null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    private fun stash() {source?.let {buffers[key(it.read.context)]=draft}}
    fun bind(next:TaskAppointmentEditSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;if(valid!=null){val c=valid.read.context;if(ownerBusiness!=c.business || ownerEpoch!=c.epoch)buffers.clear();ownerBusiness=c.business;ownerEpoch=c.epoch};picker.begin(null);source=valid;draft=valid?.let {buffers[key(it.read.context)]} ?: TaskAppointmentEditDraft();editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun retainOwner(business:Int?,epoch:Int?) {if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null)buffers.clear();ownerBusiness=business;ownerEpoch=epoch;bind(null)}
    private fun resumePicker() {val source=source ?: return;picker.begin(TaskDraftContext(source.read.context.business,source.read.context.epoch));picker.updateDay(draft.day,picker.control)}
    fun interrupt() {if(blocked)return;editing=false;review=null;clearConfirmation=null;showsIssue=false;picker.begin(null);visit++}
    fun open(expected:TaskAppointmentEditControl?) {if(expected==null || control!=expected || !canOpen)return;visit++;editing=true;resumePicker();showsIssue=false}
    fun choose(mode:TaskAppointmentEditMode,expected:TaskAppointmentEditControl?) {if(expected==null || control!=expected || !canPrepare)return;draft=draft.copy(mode=mode);stash();visit++;showsIssue=false}
    fun updateDay(raw:String,input:TaskAppointmentEditInputControl?) {if(input==null || inputControl!=input)return;val before=picker.state.day;picker.updateDay(raw,input=input.child);if(picker.state.day!=before){draft=draft.copy(day=picker.state.day,choiceRead=null);stash();showsIssue=false}}
    fun readAppointments(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskAppointmentEditMode.SET)return;picker.read(child)}
    fun openAppointment(id:Int,expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskAppointmentEditMode.SET)return;picker.open(id,child)}
    fun retryAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskAppointmentEditMode.SET)return;picker.retryDetail(child)}
    fun backAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskAppointmentEditMode.SET)return;picker.backDetail(child)}
    fun useAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskAppointmentEditMode.SET)return;val choice=picker.choice(child) ?: return;if(!choice.validFor(expected.source.read.context.business))return;draft=draft.copy(choice=choice,choiceRead=expected.source.read);stash();showsIssue=false;visit++}
    fun prepare(expected:TaskAppointmentEditControl?) {if(expected==null || control!=expected || !canPrepare)return;val change=draft.change(expected.source);if(change==null){showsIssue=true;return};visit++;review=TaskAppointmentEditReview(expected.source,visit,draft);showsIssue=false}
    fun back(expected:TaskAppointmentEditControl?) {if(expected==null || control!=expected || blocked)return;clearConfirmation?.let {dismissClear(it);return};if(review!=null)review=null else {editing=false;picker.begin(null)};showsIssue=false;visit++}
    fun askClear(expected:TaskAppointmentEditControl?) {if(expected==null || control!=expected || !canPrepare)return;++dialog;++visit;clearConfirmation=TaskAppointmentEditClear(dialog,expected.source.read,visit,draft)}
    fun dismissClear(expected:TaskAppointmentEditClear) {if(clearConfirmation!=expected)return;clearConfirmation=null;visit++}
    fun confirmClear(expected:TaskAppointmentEditClear) {if(clearConfirmation!=expected || source?.read!=expected.read || visit!=expected.visit || draft!=expected.draft || blocked || consumed)return;draft=TaskAppointmentEditDraft();stash();resumePicker();clearConfirmation=null;showsIssue=false;visit++}
    suspend fun submit(expected:TaskAppointmentEditControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || clearConfirmation!=null)return
        val review=review?.takeIf {it.source==source && it.draft==draft} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskAppointmentEditOutcome.Unknown} catch(_:Exception) {SyntheticTaskAppointmentEditOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskAppointmentEditControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskAppointmentEditControl?,record:TaskAppointmentEditRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskAppointmentEditPhase.CONFIRMED){consumedReads+=expected.source.read;draft=TaskAppointmentEditDraft();stash();editing=false;picker.begin(null)}else editing=true;review=null;clearConfirmation=null;showsIssue=false;visit++}
}
