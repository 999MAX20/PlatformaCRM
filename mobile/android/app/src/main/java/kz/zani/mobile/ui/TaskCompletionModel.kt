package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

data class TaskCompletionControl(val source:TaskCompletionSource,val visit:Int,val review:TaskCompletionReview?,val record:TaskCompletionRecord?)
class TaskCompletionModel(private val port:SyntheticTaskCompletePort,private val scope:CoroutineScope) {
    var source:TaskCompletionSource? by mutableStateOf(null);private set
    var review:TaskCompletionReview? by mutableStateOf(null);private set
    private val ledger=TaskCompletionLedger();private val consumedReads=mutableListOf<TaskCommentRead>()
    private var visit by mutableStateOf(0)
    private val authorization get()=source?.let {s->port.grants.firstNotNullOfOrNull {it.authorization(s.read.context)}}
    val submission get()=ledger.visible(authorization)
    val blocked get()=source?.let {ledger.blocked(it.read.context)} ?: false
    val consumed get()=source?.let {consumedReads.contains(it.read)} ?: false
    val control get()=source?.let {TaskCompletionControl(it,visit,review,submission)}
    val canPresent get()=source?.valid==true && authorization!=null
    fun interrupt() {review=null;visit++}
    val canPrepare get()=source?.valid==true && authorization!=null && !blocked && !consumed && review==null
    fun blocks(context:TaskCommentContext?)=context?.takeIf {it.valid}?.let {ledger.blocked(it)} ?: false
    fun hasConsumed(read:TaskCommentRead?)=read?.let {consumedReads.contains(it)} ?: false
    val retainedAttemptCount get()=ledger.records.size
    fun bind(next:TaskCompletionSource?) {val valid=next?.takeIf {it.valid};if(source==valid)return;source=valid;review=null;visit++}
    fun prepare(expected:TaskCompletionControl?) {if(expected==null || control!=expected || !canPrepare)return;visit++;review=TaskCompletionReview(expected.source,visit)}
    fun back(expected:TaskCompletionControl?) {if(expected==null || control!=expected || blocked || review==null)return;review=null;visit++}
    suspend fun submit(expected:TaskCompletionControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected)return
        val review=review?.takeIf {it.source==source} ?: return;val a=authorization ?: return;val attempt=ledger.begin(review,a) ?: return;visit++
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticTaskCompleteOutcome.Unknown} catch(_:Exception) {SyntheticTaskCompleteOutcome.Unknown}
        ledger.complete(attempt,outcome);if(submission?.attempt==attempt)visit++
    }
    fun launchSubmit(expected:TaskCompletionControl?) {scope.launch {submit(expected)}}
    fun acknowledge(expected:TaskCompletionControl?,record:TaskCompletionRecord) {if(expected==null || control!=expected || submission!=record)return;val a=authorization ?: return;if(!ledger.acknowledge(a))return;if(record.phase==TaskCompletionPhase.CONFIRMED)consumedReads+=expected.source.read;review=null;visit++}
}
