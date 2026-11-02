package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class TaskClientEditControl(val source:TaskClientEditSource,val visit:Int,val draft:TaskClientEditDraft,val editing:Boolean,val review:TaskClientEditReview?,val record:TaskClientEditRecord?,val clearID:Int?)
data class TaskClientEditInputControl(val source:TaskClientEditSource,val visit:Int,val child:ClientSearchInputControl)
data class TaskClientEditClear(val id:Int,val read:TaskCommentRead,val visit:Int,val draft:TaskClientEditDraft)
class TaskClientEditModel(private val port:SyntheticTaskClientEditPort,private val scope:CoroutineScope,clients:kz.zani.mobile.data.ClientSearchRepository) {
    val picker=ClientSearchModel(clients,scope)
    var source:TaskClientEditSource? by mutableStateOf(null);private set
    var review:TaskClientEditReview? by mutableStateOf(null);private set
    var draft by mutableStateOf(TaskClientEditDraft());private set
    var editing by mutableStateOf(false);private set
    var showsIssue by mutableStateOf(false);private set
    var clearConfirmation:TaskClientEditClear? by mutableStateOf(null);private set
    private val ledger=TaskClientEditLedger();private val consumedReads=mutableListOf<TaskCommentRead>();private val buffers=mutableMapOf<String,TaskClientEditDraft>()
    private var visit by mutableStateOf(0);private var dialog=0;private var ownerBusiness:Int?=null;private var ownerEpoch:Int?=null
    private fun key(c:TaskCommentContext)="${c.business}/${c.task}/${c.epoch}"
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskClientEditControl(it,visit,draft,editing,review,submission,clearConfirmation?.id)}
    val inputControl get()=source?.takeIf {draft.mode==TaskClientEditMode.SET && editing && !blocked && !consumed && review==null && clearConfirmation==null && !picker.state.loading && picker.state.profileSelection==null}?.let {source->picker.inputControl?.let {TaskClientEditInputControl(source,visit,it)}}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.statusValid==true || blocked || consumed)
    val canOpen get()=source?.valid==true && authorization!=null && !blocked && !consumed && !editing && review==null
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && editing && review==null && clearConfirmation==null
    val ownsEditor get()=editing || review!=null || clearConfirmation!=null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    private fun stash() {source?.let {buffers[key(it.read.context)]=draft}}
    fun bind(next:TaskClientEditSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;if(valid!=null){val c=valid.read.context;if(ownerBusiness!=c.business || ownerEpoch!=c.epoch)buffers.clear();ownerBusiness=c.business;ownerEpoch=c.epoch};picker.bind(null);source=valid;draft=valid?.let {buffers[key(it.read.context)]} ?: TaskClientEditDraft();editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun retainOwner(business:Int?,epoch:Int?) {if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null)buffers.clear();ownerBusiness=business;ownerEpoch=epoch;bind(null)}
    private fun resumePicker() {val source=source ?: return;val context=ClientSearchContext(source.read.context.business,source.read.context.epoch);picker.bind(null);picker.bind(context);picker.open(context);picker.update(draft.query,picker.inputControl)}
    fun interrupt() {if(blocked)return;editing=false;review=null;clearConfirmation=null;showsIssue=false;picker.bind(null);visit++}
    fun open(expected:TaskClientEditControl?) {if(expected==null || control!=expected || !canOpen)return;visit++;editing=true;resumePicker();showsIssue=false}
    fun choose(mode:TaskClientEditMode,expected:TaskClientEditControl?) {if(expected==null || control!=expected || !canPrepare)return;draft=draft.copy(mode=mode);stash();visit++;showsIssue=false}
    fun updateQuery(raw:String,input:TaskClientEditInputControl?) {if(input==null || inputControl!=input)return;val before=picker.state.query;picker.update(raw,input.child);if(picker.state.query!=before){draft=draft.copy(query=picker.state.query,choiceRead=null);stash();showsIssue=false}}
    fun readClients(expected:TaskClientEditControl?,child:ClientSearchControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskClientEditMode.SET || !picker.matches(child))return;visit++;picker.submit(child)}
    fun openClient(id:Int,expected:TaskClientEditControl?,child:ClientSearchControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskClientEditMode.SET || !picker.matches(child))return;visit++;picker.openClient(id,child)}
    fun retryClient(expected:TaskClientEditControl?,child:ClientSearchControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskClientEditMode.SET || !picker.matches(child))return;visit++;picker.retryProfile(child)}
    fun backClient(expected:TaskClientEditControl?,child:ClientSearchControl?) {if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskClientEditMode.SET || !picker.matches(child))return;visit++;picker.backProfile(child)}
    fun useClient(expected:TaskClientEditControl?,child:ClientSearchControl?) {
        if(expected==null || control!=expected || !canPrepare || draft.mode!=TaskClientEditMode.SET || child==null || !picker.matches(child))return
        val selected=picker.state.profileSelection ?: return;val profile=picker.profile.state.detail ?: return
        if(selected!=child.profile || picker.profile.readSelection!=child.read || picker.profile.state.loading || picker.profile.state.problem!=null)return
        val choice=TaskDraftClientChoice.make(profile,expected.source.read.context.business,selected.id) ?: return
        draft=draft.copy(choice=choice,choiceRead=expected.source.read);stash();showsIssue=false;visit++
    }
    fun prepare(expected:TaskClientEditControl?) {if(expected==null || control!=expected || !canPrepare)return;val change=draft.change(expected.source);if(change==null){showsIssue=true;return};visit++;review=TaskClientEditReview(expected.source,visit,draft);showsIssue=false}
    fun back(expected:TaskClientEditControl?) {if(expected==null || control!=expected || blocked)return;clearConfirmation?.let {dismissClear(it);return};if(review!=null)review=null else {editing=false;picker.bind(null)};showsIssue=false;visit++}
    fun askClear(expected:TaskClientEditControl?) {if(expected==null || control!=expected || !canPrepare)return;++dialog;++visit;clearConfirmation=TaskClientEditClear(dialog,expected.source.read,visit,draft)}
    fun dismissClear(expected:TaskClientEditClear) {if(clearConfirmation!=expected)return;clearConfirmation=null;visit++}
    fun confirmClear(expected:TaskClientEditClear) {if(clearConfirmation!=expected || source?.read!=expected.read || visit!=expected.visit || draft!=expected.draft || blocked || consumed)return;draft=TaskClientEditDraft();stash();resumePicker();clearConfirmation=null;showsIssue=false;visit++}
    suspend fun submit(expected:TaskClientEditControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || clearConfirmation!=null)return
        val review=review?.takeIf {it.source==source && it.draft==draft} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskClientEditOutcome.Unknown} catch(_:Exception) {SyntheticTaskClientEditOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskClientEditControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskClientEditControl?,record:TaskClientEditRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskClientEditPhase.CONFIRMED){consumedReads+=expected.source.read;draft=TaskClientEditDraft();stash();editing=false;picker.bind(null)}else editing=true;review=null;clearConfirmation=null;showsIssue=false;visit++}
}
