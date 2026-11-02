package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class TaskPriorityEditControl(val source:TaskPriorityEditSource,val visit:Int,val raw:String,val editing:Boolean,val review:TaskPriorityEditReview?,val record:TaskPriorityEditRecord?,val clearID:Int?)
data class TaskPriorityEditClear(val id:Int,val read:TaskCommentRead,val visit:Int,val raw:String)
class TaskPriorityEditModel(private val port:SyntheticTaskPriorityEditPort,private val scope:CoroutineScope) {
    var source:TaskPriorityEditSource? by mutableStateOf(null);private set
    var review:TaskPriorityEditReview? by mutableStateOf(null);private set
    var raw by mutableStateOf("");private set
    var editing by mutableStateOf(false);private set
    var showsIssue by mutableStateOf(false);private set
    var clearConfirmation:TaskPriorityEditClear? by mutableStateOf(null);private set
    private val ledger=TaskPriorityEditLedger();private val consumedReads=mutableListOf<TaskCommentRead>();private val buffers=mutableMapOf<String,String>()
    private var visit by mutableStateOf(0);private var dialog=0;private var ownerBusiness:Int?=null;private var ownerEpoch:Int?=null
    private fun key(c:TaskCommentContext)="${c.business}/${c.task}/${c.epoch}"
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskPriorityEditControl(it,visit,raw,editing,review,submission,clearConfirmation?.id)}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.valid==true || blocked || consumed)
    val canOpen get()=source?.valid==true && authorization!=null && !blocked && !consumed && !editing && review==null
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && editing && review==null && clearConfirmation==null
    val ownsEditor get()=editing || review!=null || clearConfirmation!=null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    fun bind(next:TaskPriorityEditSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;if(valid!=null){val c=valid.read.context;if(ownerBusiness!=c.business || ownerEpoch!=c.epoch)buffers.clear();ownerBusiness=c.business;ownerEpoch=c.epoch};source=valid;raw=valid?.let {buffers[key(it.read.context)]} ?: "";editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun retainOwner(business:Int?,epoch:Int?) {if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null)buffers.clear();ownerBusiness=business;ownerEpoch=epoch;bind(null)}
    fun interrupt() {if(blocked)return;editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun open(expected:TaskPriorityEditControl?) {if(expected==null || control!=expected || !canOpen)return;visit++;editing=true;showsIssue=false}
    fun choose(value:String,expected:TaskPriorityEditControl?) {if(expected==null || control!=expected || !canPrepare || TaskPriorityValue.parse(value)==null)return;raw=value;buffers[key(expected.source.read.context)]=value;showsIssue=false;visit++}
    fun prepare(expected:TaskPriorityEditControl?) {if(expected==null || control!=expected || !canPrepare)return;val value=TaskPriorityValue.parse(raw);if(value==null){showsIssue=true;return};visit++;review=TaskPriorityEditReview(expected.source,visit,value);showsIssue=false}
    fun back(expected:TaskPriorityEditControl?) {if(expected==null || control!=expected || blocked)return;clearConfirmation?.let {dismissClear(it);return};if(review!=null)review=null else editing=false;showsIssue=false;visit++}
    fun askClear(expected:TaskPriorityEditControl?) {if(expected==null || control!=expected || !canPrepare)return;++dialog;++visit;clearConfirmation=TaskPriorityEditClear(dialog,expected.source.read,visit,raw)}
    fun dismissClear(expected:TaskPriorityEditClear) {if(clearConfirmation!=expected)return;clearConfirmation=null;visit++}
    fun confirmClear(expected:TaskPriorityEditClear) {if(clearConfirmation!=expected || source?.read!=expected.read || visit!=expected.visit || raw!=expected.raw || blocked || consumed)return;raw="";buffers[key(expected.read.context)]="";clearConfirmation=null;showsIssue=false;visit++}
    suspend fun submit(expected:TaskPriorityEditControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || clearConfirmation!=null)return
        val review=review?.takeIf {it.source==source && it.value.raw==raw} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskPriorityEditOutcome.Unknown} catch(_:Exception) {SyntheticTaskPriorityEditOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskPriorityEditControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskPriorityEditControl?,record:TaskPriorityEditRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskPriorityEditPhase.CONFIRMED){consumedReads+=expected.source.read;raw="";buffers[key(expected.source.read.context)]="";editing=false}else editing=true;review=null;clearConfirmation=null;showsIssue=false;visit++}
}
