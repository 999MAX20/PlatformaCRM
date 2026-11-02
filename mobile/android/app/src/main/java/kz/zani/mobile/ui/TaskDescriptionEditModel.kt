package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class TaskDescriptionEditControl(val source:TaskDescriptionEditSource,val visit:Int,val raw:String,val mode:TaskDescriptionMode?,val editing:Boolean,val review:TaskDescriptionEditReview?,val record:TaskDescriptionEditRecord?,val clearID:Int?)
data class TaskDescriptionEditInputControl(val source:TaskDescriptionEditSource,val visit:Int)
data class TaskDescriptionEditClear(val id:Int,val read:TaskCommentRead,val visit:Int,val raw:String)
class TaskDescriptionEditModel(private val port:SyntheticTaskDescriptionEditPort,private val scope:CoroutineScope) {
    var source:TaskDescriptionEditSource? by mutableStateOf(null);private set
    var review:TaskDescriptionEditReview? by mutableStateOf(null);private set
    var raw by mutableStateOf("");private set
    var mode:TaskDescriptionMode? by mutableStateOf(null);private set
    var editing by mutableStateOf(false);private set
    var showsIssue by mutableStateOf(false);private set
    var clearConfirmation:TaskDescriptionEditClear? by mutableStateOf(null);private set
    private val ledger=TaskDescriptionEditLedger();private val consumedReads=mutableListOf<TaskCommentRead>();private val buffers=mutableMapOf<String,String>();private val modes=mutableMapOf<String,TaskDescriptionMode>()
    private var visit by mutableStateOf(0);private var dialog=0;private var ownerBusiness:Int?=null;private var ownerEpoch:Int?=null
    private fun key(c:TaskCommentContext)="${c.business}/${c.task}/${c.epoch}"
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskDescriptionEditControl(it,visit,raw,mode,editing,review,submission,clearConfirmation?.id)}
    val inputControl get()=source?.takeIf {mode==TaskDescriptionMode.REPLACE && editing && !blocked && !consumed && review==null && clearConfirmation==null}?.let {TaskDescriptionEditInputControl(it,visit)}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.valid==true || blocked || consumed)
    val canOpen get()=source?.valid==true && authorization!=null && !blocked && !consumed && !editing && review==null
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && editing && review==null && clearConfirmation==null
    val ownsEditor get()=editing || review!=null || clearConfirmation!=null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    fun bind(next:TaskDescriptionEditSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;if(valid!=null){val c=valid.read.context;if(ownerBusiness!=c.business || ownerEpoch!=c.epoch){buffers.clear();modes.clear()};ownerBusiness=c.business;ownerEpoch=c.epoch};mode=valid?.let {modes[key(it.read.context)]};source=valid;raw=valid?.let {buffers[key(it.read.context)]} ?: "";editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun retainOwner(business:Int?,epoch:Int?) {if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null){buffers.clear();modes.clear()};ownerBusiness=business;ownerEpoch=epoch;bind(null)}
    fun interrupt() {if(blocked)return;editing=false;review=null;clearConfirmation=null;showsIssue=false;visit++}
    fun open(expected:TaskDescriptionEditControl?) {if(expected==null || control!=expected || !canOpen)return;visit++;editing=true;showsIssue=false}
    fun update(value:String,input:TaskDescriptionEditInputControl?) {if(input==null || inputControl!=input)return;raw=value;buffers[key(input.source.read.context)]=value;showsIssue=false}
    fun choose(value:TaskDescriptionMode,expected:TaskDescriptionEditControl?) {if(expected==null || control!=expected || !canPrepare)return;mode=value;modes[key(expected.source.read.context)]=value;showsIssue=false;visit++}
    fun prepare(expected:TaskDescriptionEditControl?) {if(expected==null || control!=expected || !canPrepare)return;val value=TaskDescriptionValue.make(mode,raw);if(value==null){showsIssue=true;return};visit++;review=TaskDescriptionEditReview(expected.source,visit,value);showsIssue=false}
    fun back(expected:TaskDescriptionEditControl?) {if(expected==null || control!=expected || blocked)return;clearConfirmation?.let {dismissClear(it);return};if(review!=null)review=null else editing=false;showsIssue=false;visit++}
    fun askClear(expected:TaskDescriptionEditControl?) {if(expected==null || control!=expected || !canPrepare)return;++dialog;++visit;clearConfirmation=TaskDescriptionEditClear(dialog,expected.source.read,visit,raw)}
    fun dismissClear(expected:TaskDescriptionEditClear) {if(clearConfirmation!=expected)return;clearConfirmation=null;visit++}
    fun confirmClear(expected:TaskDescriptionEditClear) {if(clearConfirmation!=expected || source?.read!=expected.read || visit!=expected.visit || raw!=expected.raw || blocked || consumed)return;mode=null;modes.remove(key(expected.read.context));raw="";buffers[key(expected.read.context)]="";clearConfirmation=null;showsIssue=false;visit++}
    suspend fun submit(expected:TaskDescriptionEditControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || clearConfirmation!=null)return
        val review=review?.takeIf {it.source==source && it.value.raw==raw && it.value.mode==mode} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskDescriptionEditOutcome.Unknown} catch(_:Exception) {SyntheticTaskDescriptionEditOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskDescriptionEditControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskDescriptionEditControl?,record:TaskDescriptionEditRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskDescriptionEditPhase.CONFIRMED){consumedReads+=expected.source.read;mode=null;modes.remove(key(expected.source.read.context));raw="";buffers[key(expected.source.read.context)]="";editing=false}else editing=true;review=null;clearConfirmation=null;showsIssue=false;visit++}
}
