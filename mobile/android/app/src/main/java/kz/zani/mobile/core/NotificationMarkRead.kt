package kz.zani.mobile.core

data class NotificationMarkReadContext(val business:Int,val notification:Int,val epoch:Int) {val valid get()=business>0 && notification>0 && epoch>0}
data class NotificationMarkReadSource(val context:NotificationMarkReadContext,val generation:Int,val notification:CRMNotification) {val valid get()=context.valid && generation>0 && notification.id==context.notification && notification.valid() && notification.readMarkerPresent}
data class SyntheticNotificationMarkReadGrant(val business:Int,val notification:Int,val actor:Int,val update:Boolean) {
    fun authorization(context:NotificationMarkReadContext):SyntheticNotificationMarkReadAuthorization?=if(context.valid && context.business==business && context.notification==notification && actor>0 && update)SyntheticNotificationMarkReadAuthorization(context,actor) else null
}
data class SyntheticNotificationMarkReadAuthorization internal constructor(val context:NotificationMarkReadContext,val actor:Int)
data class NotificationMarkReadReview(val source:NotificationMarkReadSource,val generation:Int)
// Existing MobileNotificationMarkReadView envelope, no invented Business/actor/version.
data class NotificationMarkReadReply(val ok:Boolean,val notification:CRMNotification,val replayed:Boolean)
data class NotificationMarkReadAttempt(val localID:Int,val authorization:SyntheticNotificationMarkReadAuthorization,val review:NotificationMarkReadReview)
sealed interface SyntheticNotificationMarkReadOutcome {
    data class Response(val status:Int,val reply:NotificationMarkReadReply):SyntheticNotificationMarkReadOutcome
    data object RejectedWithoutWrite:SyntheticNotificationMarkReadOutcome
    data object Unknown:SyntheticNotificationMarkReadOutcome
}
interface SyntheticNotificationMarkReadPort {val grants:List<SyntheticNotificationMarkReadGrant>;suspend fun execute(attempt:NotificationMarkReadAttempt):SyntheticNotificationMarkReadOutcome}
enum class NotificationMarkReadPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class NotificationMarkReadRecord(val attempt:NotificationMarkReadAttempt,val phase:NotificationMarkReadPhase,val reply:NotificationMarkReadReply?=null)
class NotificationMarkReadLedger {
    var records:List<NotificationMarkReadRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:NotificationMarkReadContext)=c.business to c.notification
    fun blocked(c:NotificationMarkReadContext)=active.containsKey(key(c))
    fun visible(auth:SyntheticNotificationMarkReadAuthorization?):NotificationMarkReadRecord? {
        if(auth==null)return null;val record=active[key(auth.context)]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==auth}
    }
    fun begin(review:NotificationMarkReadReview,authorization:SyntheticNotificationMarkReadAuthorization):NotificationMarkReadAttempt? {
        if(!review.source.valid || review.generation<=0 || review.source.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=NotificationMarkReadAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+NotificationMarkReadRecord(a,NotificationMarkReadPhase.PENDING);return a
    }
    fun complete(attempt:NotificationMarkReadAttempt,outcome:SyntheticNotificationMarkReadOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=NotificationMarkReadPhase.PENDING)return
        var phase=NotificationMarkReadPhase.UNKNOWN;var accepted:NotificationMarkReadReply?=null
        when(outcome) {
            SyntheticNotificationMarkReadOutcome.Unknown->Unit
            SyntheticNotificationMarkReadOutcome.RejectedWithoutWrite->phase=NotificationMarkReadPhase.REJECTED
            is SyntheticNotificationMarkReadOutcome.Response->{val reply=outcome.reply;val n=reply.notification;val s=attempt.review.source.notification
                if(outcome.status==200 && reply.ok && n.valid() && n.id==attempt.authorization.context.notification && n.readMarkerPresent && n.readAt!=null && (s.readAt==null || n.readAt==s.readAt) && n.text==s.text && n.category==s.category && n.priority==s.priority && n.status==s.status && n.channel==s.channel && n.sendAt==s.sendAt && n.actionURL==s.actionURL && n.appointmentID==s.appointmentID) {phase=NotificationMarkReadPhase.CONFIRMED;accepted=reply}
            }
        }
        records=records.mapIndexed {index,record->if(index==i)record.copy(phase=phase,reply=accepted) else record}
    }
    fun acknowledge(auth:SyntheticNotificationMarkReadAuthorization):Boolean {
        val record=visible(auth) ?: return false
        if(record.phase!=NotificationMarkReadPhase.CONFIRMED && record.phase!=NotificationMarkReadPhase.REJECTED)return false
        active.remove(key(auth.context));return true
    }
}
