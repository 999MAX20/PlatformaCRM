package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class TaskDateEditControl(val source:TaskDateEditSource,val visit:Int,val draft:TaskDateDraft,val editing:Boolean,val review:TaskDateEditReview?,val record:TaskDateEditRecord?,val clearID:Int?)
data class TaskDateEditInputControl(val source:TaskDateEditSource,val visit:Int,val field:TaskDateField)
data class TaskDateEditClear(val id:Int,val read:TaskCommentRead,val visit:Int,val draft:TaskDateDraft)
class TaskDateEditModel(private val port:SyntheticTaskDateEditPort,private val scope:CoroutineScope) {
    var source:TaskDateEditSource? by mutableStateOf(null);private set
    var review:TaskDateEditReview? by mutableStateOf(null);private set
    var draft by mutableStateOf(TaskDateDraft());private set
    var editing by mutableStateOf(false);private set
    var showsIssue by mutableStateOf(false);private set
    var clearConfirmation:TaskDateEditClear? by mutableStateOf(null);private set
    private val ledger=TaskDateEditLedger();private val consumedReads=mutableListOf<TaskCommentRead>();private val buffers=mutableMapOf<String,TaskDateDraft>()
    private var visit by mutableStateOf(0);private var dialog=0;private var ownerBusiness:Int?=null;private var ownerEpoch:Int?=null
    private fun key(c:TaskCommentContext)="${c.business}/${c.task}/${c.epoch}"
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskDateEditControl(it,visit,draft,editing,review,submission,clearConfirmation?.id)}
    val inputControl get()=source?.let {s->draft.field?.takeIf {draft.mode==TaskDateMode.SET && editing && !blocked && !consumed && review==null && clearConfirmation==null}?.let {TaskDateEditInputControl(s,visit,it)}}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.valid==true || blocked || consumed)
    val canOpen get()=source?.valid==true && authorization!=null && !blocked && !consumed && !editing && review==null
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && editing && review==null && clearConfirmation==null
    val ownsEditor get()=editing || review!=null || clearConfirmation!=null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    private fun stash() {source?.let {buffers[key(it.read.context)]=draft}}
    fun bind(next:TaskDateEditSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;if(valid!=null){val c=valid.read.context;if(ownerBusiness!=c.business || ownerEpoch!=c.epoch)buffers.clear();ownerBusiness=c.business;ownerEpoch=c.epoch};source=valid;draft=valid?.let {buffers[key(it.read.context)]} ?: TaskDateDraft();editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun retainOwner(business:Int?,epoch:Int?) {if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null)buffers.clear();ownerBusiness=business;ownerEpoch=epoch;bind(null)}
    fun interrupt() {if(blocked)return;editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun open(expected:TaskDateEditControl?) {if(expected==null || control!=expected || !canOpen)return;visit++;editing=true;showsIssue=false}
    fun select(field:TaskDateField,expected:TaskDateEditControl?) {if(expected==null || control!=expected || !canPrepare)return;draft=draft.select(field);stash();visit++;showsIssue=false}
    fun choose(mode:TaskDateMode,expected:TaskDateEditControl?) {if(expected==null || control!=expected || !canPrepare || draft.field==null)return;draft=draft.choose(mode);stash();visit++;showsIssue=false}
    fun update(raw:String,input:TaskDateEditInputControl?) {if(input==null || inputControl!=input)return;draft=draft.update(raw);stash();showsIssue=false}
    fun prepare(expected:TaskDateEditControl?) {if(expected==null || control!=expected || !canPrepare)return;val change=draft.change;if(change==null){showsIssue=true;return};visit++;review=TaskDateEditReview(expected.source,visit,change);showsIssue=false}
    fun back(expected:TaskDateEditControl?) {if(expected==null || control!=expected || blocked)return;clearConfirmation?.let {dismissClear(it);return};if(review!=null)review=null else editing=false;showsIssue=false;visit++}
    fun askClear(expected:TaskDateEditControl?) {if(expected==null || control!=expected || !canPrepare)return;++dialog;++visit;clearConfirmation=TaskDateEditClear(dialog,expected.source.read,visit,draft)}
    fun dismissClear(expected:TaskDateEditClear) {if(clearConfirmation!=expected)return;clearConfirmation=null;visit++}
    fun confirmClear(expected:TaskDateEditClear) {if(clearConfirmation!=expected || source?.read!=expected.read || visit!=expected.visit || draft!=expected.draft || blocked || consumed)return;draft=TaskDateDraft();stash();clearConfirmation=null;showsIssue=false;visit++}
    suspend fun submit(expected:TaskDateEditControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || clearConfirmation!=null)return
        val review=review?.takeIf {it.source==source && it.change==draft.change} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskDateEditOutcome.Unknown} catch(_:Exception) {SyntheticTaskDateEditOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskDateEditControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskDateEditControl?,record:TaskDateEditRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskDateEditPhase.CONFIRMED){consumedReads+=expected.source.read;draft=TaskDateDraft();stash();editing=false}else editing=true;review=null;clearConfirmation=null;showsIssue=false;visit++}
}
