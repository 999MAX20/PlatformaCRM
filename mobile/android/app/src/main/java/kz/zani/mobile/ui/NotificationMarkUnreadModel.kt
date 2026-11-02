package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

class NotificationMarkUnreadModel(private val port:SyntheticNotificationMarkUnreadPort?=null,private val ownerScope:CoroutineScope?=null) {
    private val ledger=NotificationMarkUnreadLedger()
    private var generation=0
    var read by mutableStateOf<NotificationMarkUnreadSource?>(null);private set
    var review by mutableStateOf<NotificationMarkUnreadReview?>(null);private set
    var submission by mutableStateOf<NotificationMarkUnreadRecord?>(null);private set
    private var ownBlocked by mutableStateOf(false)
    var peerBlocked:(NotificationMarkReadContext)->Boolean={false}
    var onDispatch:()->Unit={}
    fun invalidatePreparedReview() {++generation;review=null}
    val blocked get()=ownBlocked || read?.let {peerBlocked(it.context)}==true
    fun blocks(context:NotificationMarkReadContext)=ledger.blocked(context)
    private fun authorization():SyntheticNotificationMarkUnreadAuthorization? {val r=read ?: return null;return port?.grants?.firstNotNullOfOrNull {it.authorization(r.context)}}
    val canPrepare get()=read?.valid==true && authorization()!=null && !blocked && review==null
    val retainedAttemptCount get()=ledger.records.size
    private fun sync() {submission=ledger.visible(authorization());ownBlocked=read?.let {ledger.blocked(it.context)} ?: false}
    fun bind(next:NotificationMarkUnreadSource?) {if(read!=next){++generation;read=next;review=null};sync()}
    fun prepare(expected:NotificationMarkUnreadSource) {if(read!=expected || !canPrepare)return;review=NotificationMarkUnreadReview(expected,++generation)}
    fun back(expected:NotificationMarkUnreadReview) {if(review!=expected || read!=expected.source || blocked)return;++generation;review=null}
    fun launchSubmit(expected:NotificationMarkUnreadReview,stillCurrent:()->Boolean) {ownerScope?.launch {if(stillCurrent())submit(expected)}}
    suspend fun submit(expected:NotificationMarkUnreadReview) {
        currentCoroutineContext().ensureActive()
        if(review!=expected || read!=expected.source || peerBlocked(expected.source.context))return
        val auth=authorization() ?: return;val port=port ?: return;val attempt=ledger.begin(expected,auth) ?: return;sync();onDispatch()
        try {val result=port.execute(attempt);currentCoroutineContext().ensureActive();ledger.complete(attempt,result)}
        catch(error:Exception) {ledger.complete(attempt,SyntheticNotificationMarkUnreadOutcome.Unknown);if(error is CancellationException)throw error}
        finally {sync()}
    }
    fun acknowledge(expected:NotificationMarkUnreadSource,attemptID:Int) {
        if(read!=expected)return
        val auth=authorization() ?: return
        if(submission?.attempt?.localID!=attemptID || !ledger.acknowledge(auth))return
        ++generation;review=null;sync()
    }
}
