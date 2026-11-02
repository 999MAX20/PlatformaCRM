package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

class NotificationMarkReadModel(private val port:SyntheticNotificationMarkReadPort?=null,private val ownerScope:CoroutineScope?=null) {
    private val ledger=NotificationMarkReadLedger()
    private var generation=0
    var read by mutableStateOf<NotificationMarkReadSource?>(null);private set
    var review by mutableStateOf<NotificationMarkReadReview?>(null);private set
    var submission by mutableStateOf<NotificationMarkReadRecord?>(null);private set
    private var ownBlocked by mutableStateOf(false)
    var peerBlocked:(NotificationMarkReadContext)->Boolean={false}
    var onDispatch:()->Unit={}
    fun invalidatePreparedReview() {++generation;review=null}
    val blocked get()=ownBlocked || read?.let {peerBlocked(it.context)}==true
    fun blocks(context:NotificationMarkReadContext)=ledger.blocked(context)
    private fun authorization():SyntheticNotificationMarkReadAuthorization? {val r=read ?: return null;return port?.grants?.firstNotNullOfOrNull {it.authorization(r.context)}}
    val canPrepare get()=read?.valid==true && authorization()!=null && !blocked && review==null
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {submission=ledger.visible(authorization());ownBlocked=read?.let {ledger.blocked(it.context)} ?: false}
    fun bind(next:NotificationMarkReadSource?) {if(read!=next){++generation;read=next;review=null};sync()}
    fun prepare(expected:NotificationMarkReadSource) {if(read!=expected || !canPrepare)return;review=NotificationMarkReadReview(expected,++generation)}
    fun back(expected:NotificationMarkReadReview) {if(review!=expected || read!=expected.source || blocked)return;++generation;review=null}
    fun launchSubmit(expected:NotificationMarkReadReview,stillCurrent:()->Boolean) {ownerScope?.launch {if(stillCurrent())submit(expected)}}
    suspend fun submit(expected:NotificationMarkReadReview) {
        currentCoroutineContext().ensureActive()
        if(review!=expected || read!=expected.source || peerBlocked(expected.source.context))return
        val auth=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(expected,auth) ?: return;sync();onDispatch()
        try {val result=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,result)}
        catch(error:Exception) {ledger.complete(attempt,SyntheticNotificationMarkReadOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync()}
    }
    fun acknowledge(expected:NotificationMarkReadSource,attemptID:Int) {
        if(read!=expected)return
        val auth=authorization() ?: return
        if(submission?.attempt?.localID!=attemptID || !ledger.acknowledge(auth))return
        ++generation;review=null;sync()
    }
}
