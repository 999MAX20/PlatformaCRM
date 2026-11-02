package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing web TaskSerializer complete outcome; no wire route or production authority.
data class TaskCompletionSource(val read:TaskCommentRead,val task:WorkTask) {val valid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business) && task.status in listOf("open","in_progress")}
data class SyntheticTaskCompleteGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskCompleteAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskCompleteAuthorization(context,actor) else null}
data class SyntheticTaskCompleteAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskCompletionReview(val source:TaskCompletionSource,val visit:Int)
data class TaskCompletionAttempt(val localID:Int,val authorization:SyntheticTaskCompleteAuthorization,val review:TaskCompletionReview)
sealed interface SyntheticTaskCompleteOutcome {data class Response(val status:Int,val body:String):SyntheticTaskCompleteOutcome;data object RejectedWithoutWrite:SyntheticTaskCompleteOutcome;data object Unknown:SyntheticTaskCompleteOutcome}
interface SyntheticTaskCompletePort {val grants:List<SyntheticTaskCompleteGrant>;suspend fun execute(attempt:TaskCompletionAttempt):SyntheticTaskCompleteOutcome}
enum class TaskCompletionPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskCompletionResult(val id:Int,val business:Int,val status:String,val completedBy:Int,val completedAt:String,val updatedAt:String,val snoozeCleared:Boolean) {
    companion object {fun decode(body:String):TaskCompletionResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskCompletionResult(integer("id"),integer("business"),string("status"),integer("completed_by"),string("completed_at"),string("updated_at"),o.has("snoozed_until") && o.isNull("snoozed_until"))
    }.getOrNull()}
}
data class TaskCompletionRecord(val attempt:TaskCompletionAttempt,val phase:TaskCompletionPhase,val result:TaskCompletionResult?=null)
class TaskCompletionLedger {
    var records:List<TaskCompletionRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskCompleteAuthorization?):TaskCompletionRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskCompletionReview,authorization:SyntheticTaskCompleteAuthorization):TaskCompletionAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskCompletionAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskCompletionRecord(a,TaskCompletionPhase.PENDING);return a
    }
    fun complete(attempt:TaskCompletionAttempt,outcome:SyntheticTaskCompleteOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskCompletionPhase.PENDING)return
        var phase=TaskCompletionPhase.UNKNOWN;var result:TaskCompletionResult?=null
        when(outcome) {
            SyntheticTaskCompleteOutcome.Unknown->Unit
            SyntheticTaskCompleteOutcome.RejectedWithoutWrite->phase=TaskCompletionPhase.REJECTED
            is SyntheticTaskCompleteOutcome.Response->{val r=TaskCompletionResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status=="done" && r.completedBy==attempt.authorization.actor && r.snoozeCleared && runCatching {Instant.parse(r.completedAt)}.isSuccess && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskCompletionPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskCompleteAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskCompletionPhase.CONFIRMED && r.phase!=TaskCompletionPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
