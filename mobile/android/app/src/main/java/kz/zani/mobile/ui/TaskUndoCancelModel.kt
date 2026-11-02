package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

data class TaskUndoCancelControl(val source:TaskUndoCancelSource,val visit:Int,val review:TaskUndoCancelReview?,val record:TaskUndoCancelRecord?)
class TaskUndoCancelModel(private val port:SyntheticTaskUndoCancelPort,private val scope:CoroutineScope) {
    var source:TaskUndoCancelSource? by mutableStateOf(null);private set
    var review:TaskUndoCancelReview? by mutableStateOf(null);private set
    private val ledger=TaskUndoCancelLedger();private val consumedReads=mutableListOf<TaskCommentRead>()
    private var visit by mutableStateOf(0)
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskUndoCancelControl(it,visit,review,submission)}
    val canPresent get()=source?.identityValid==true && authorization!=null && (source?.valid==true || blocked || consumed)
    fun interrupt() {review=null;visit++}
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && review==null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    fun bind(next:TaskUndoCancelSource?) {val valid=next?.takeIf {it.identityValid};if(source==valid)return;source=valid;review=null;visit++}
    fun prepare(expected:TaskUndoCancelControl?) {if(expected==null || control!=expected || !canPrepare)return;visit++;review=TaskUndoCancelReview(expected.source,visit)}
    fun back(expected:TaskUndoCancelControl?) {if(expected==null || control!=expected || blocked || review==null)return;review=null;visit++}
    suspend fun submit(expected:TaskUndoCancelControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected)return
        val review=review?.takeIf {it.source==source} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskUndoCancelOutcome.Unknown} catch(_:Exception) {SyntheticTaskUndoCancelOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskUndoCancelControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskUndoCancelControl?,record:TaskUndoCancelRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskUndoCancelPhase.CONFIRMED)consumedReads+=expected.source.read;review=null;visit++}
}
