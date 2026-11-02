package kz.zani.mobile.core

typealias NotificationMarkUnreadContext=NotificationMarkReadContext
typealias NotificationMarkUnreadSource=NotificationMarkReadSource
data class SyntheticNotificationMarkUnreadGrant(val business:Int,val notification:Int,val actor:Int,val update:Boolean) {
    fun authorization(context:NotificationMarkUnreadContext):SyntheticNotificationMarkUnreadAuthorization?=if(context.valid && context.business==business && context.notification==notification && actor>0 && update)SyntheticNotificationMarkUnreadAuthorization(context,actor) else null
}
data class SyntheticNotificationMarkUnreadAuthorization internal constructor(val context:NotificationMarkUnreadContext,val actor:Int)
data class NotificationMarkUnreadReview(val source:NotificationMarkUnreadSource,val generation:Int)
// Generic NotificationSerializer subset, separate from the mobile mark-read envelope.
// Presence/null/strict false decoding is enforced by JsonContracts.
data class NotificationMarkUnreadReply(val id:Int,val business:Int,val text:String,val category:String,val priority:String,val status:String,val channel:String,val sendAt:String,val actionURL:String,val appointment:Int?,val updatedAt:String) {
    fun matches(source:NotificationMarkUnreadSource):Boolean {
        val n=source.notification
        return source.valid && id==source.context.notification && business==source.context.business && runCatching {java.time.Instant.parse(updatedAt)}.isSuccess && (appointment==null || appointment>0) && text==n.text && category==n.category && priority==n.priority && status==n.status && channel==n.channel && sendAt==n.sendAt && actionURL==n.actionURL && appointment==n.appointmentID
    }
}
data class NotificationMarkUnreadAttempt(val localID:Int,val authorization:SyntheticNotificationMarkUnreadAuthorization,val review:NotificationMarkUnreadReview)
sealed interface SyntheticNotificationMarkUnreadOutcome {
    data class Response(val status:Int,val reply:NotificationMarkUnreadReply):SyntheticNotificationMarkUnreadOutcome
    data object RejectedWithoutWrite:SyntheticNotificationMarkUnreadOutcome
    data object Unknown:SyntheticNotificationMarkUnreadOutcome
}
interface SyntheticNotificationMarkUnreadPort {val grants:List<SyntheticNotificationMarkUnreadGrant>;suspend fun execute(attempt:NotificationMarkUnreadAttempt):SyntheticNotificationMarkUnreadOutcome}
enum class NotificationMarkUnreadPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class NotificationMarkUnreadRecord(val attempt:NotificationMarkUnreadAttempt,val phase:NotificationMarkUnreadPhase,val reply:NotificationMarkUnreadReply?=null)
class NotificationMarkUnreadLedger {
    var records:List<NotificationMarkUnreadRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:NotificationMarkUnreadContext)=c.business to c.notification
    fun blocked(c:NotificationMarkUnreadContext)=active.containsKey(key(c))
    fun visible(auth:SyntheticNotificationMarkUnreadAuthorization?):NotificationMarkUnreadRecord? {
        if(auth==null)return null;val record=active[key(auth.context)]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==auth}
    }
    fun begin(review:NotificationMarkUnreadReview,authorization:SyntheticNotificationMarkUnreadAuthorization):NotificationMarkUnreadAttempt? {
        if(!review.source.valid || review.generation<=0 || review.source.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=NotificationMarkUnreadAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+NotificationMarkUnreadRecord(a,NotificationMarkUnreadPhase.PENDING);return a
    }
    fun complete(attempt:NotificationMarkUnreadAttempt,outcome:SyntheticNotificationMarkUnreadOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=NotificationMarkUnreadPhase.PENDING)return
        var phase=NotificationMarkUnreadPhase.UNKNOWN;var accepted:NotificationMarkUnreadReply?=null
        when(outcome) {
            SyntheticNotificationMarkUnreadOutcome.Unknown->Unit
            SyntheticNotificationMarkUnreadOutcome.RejectedWithoutWrite->phase=NotificationMarkUnreadPhase.REJECTED
            is SyntheticNotificationMarkUnreadOutcome.Response->{val reply=outcome.reply
                if(outcome.status==200 && reply.matches(attempt.review.source)) {phase=NotificationMarkUnreadPhase.CONFIRMED;accepted=reply}
            }
        }
        records=records.mapIndexed {index,record->if(index==i)record.copy(phase=phase,reply=accepted) else record}
    }
    fun acknowledge(auth:SyntheticNotificationMarkUnreadAuthorization):Boolean {
        val record=visible(auth) ?: return false
        if(record.phase!=NotificationMarkUnreadPhase.CONFIRMED && record.phase!=NotificationMarkUnreadPhase.REJECTED)return false
        active.remove(key(auth.context));return true
    }
}
