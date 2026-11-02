package kz.zani.mobile.core

import org.json.JSONObject

// Explicit supported ID subset, never a default actor or GET membership authority.
data class TaskAssignValue private constructor(val raw:String,val userID:Long) {
    companion object {fun parse(raw:String):TaskAssignValue? {
        if(raw.isEmpty() || raw.any {it !in '0'..'9'})return null
        val id=raw.toLongOrNull()?.takeIf {it>0 && it.toString()==raw} ?: return null
        return TaskAssignValue(raw,id)
    }}
}
data class TaskAssignSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
}
// eligibleMembers is explicit synthetic port context, not a live catalogue/DTO.
data class SyntheticTaskAssignGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean,val eligibleMembers:List<Long>) {
    fun authorization(context:TaskCommentContext):SyntheticTaskAssignAuthorization?=if(context.valid && context.business==business && context.task==task && actor>0 && update && eligibleMembers.isNotEmpty() && eligibleMembers.all {it>0} && eligibleMembers.distinct().size==eligibleMembers.size)SyntheticTaskAssignAuthorization(context,actor,eligibleMembers) else null
}
data class SyntheticTaskAssignAuthorization internal constructor(val context:TaskCommentContext,val actor:Int,val eligibleMembers:List<Long>)
data class TaskAssignReview(val source:TaskAssignSource,val visit:Int,val value:TaskAssignValue)
data class TaskAssignAttempt(val localID:Int,val authorization:SyntheticTaskAssignAuthorization,val review:TaskAssignReview)
sealed interface SyntheticTaskAssignOutcome {data class Response(val status:Int,val body:String):SyntheticTaskAssignOutcome;data object RejectedWithoutWrite:SyntheticTaskAssignOutcome;data object Unknown:SyntheticTaskAssignOutcome}
interface SyntheticTaskAssignPort {val grants:List<SyntheticTaskAssignGrant>;suspend fun execute(attempt:TaskAssignAttempt):SyntheticTaskAssignOutcome}
enum class TaskAssignPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskAssignResult(val id:Int,val business:Int,val status:String,val assignee:Long,val updatedAt:String) {
    companion object {fun decode(body:String):TaskAssignResult?=runCatching {
        val o=JSONObject(body)
        fun positive(name:String):Long {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n>0);return n}
        fun integer(name:String):Int {val n=positive(name);require(n<=Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskAssignResult(integer("id"),integer("business"),string("status"),positive("assignee"),string("updated_at"))
    }.getOrNull()}
}
data class TaskAssignRecord(val attempt:TaskAssignAttempt,val phase:TaskAssignPhase,val result:TaskAssignResult?=null)
class TaskAssignLedger {
    var records:List<TaskAssignRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskAssignAuthorization?):TaskAssignRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskAssignReview,authorization:SyntheticTaskAssignAuthorization):TaskAssignAttempt? {
        if(!review.source.valid || review.visit<=0 || TaskAssignValue.parse(review.value.raw)!=review.value || review.source.read.context!=authorization.context || authorization.actor<=0 || review.value.userID !in authorization.eligibleMembers || blocked(authorization.context))return null
        val a=TaskAssignAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskAssignRecord(a,TaskAssignPhase.PENDING);return a
    }
    fun complete(attempt:TaskAssignAttempt,outcome:SyntheticTaskAssignOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskAssignPhase.PENDING)return
        var phase=TaskAssignPhase.UNKNOWN;var result:TaskAssignResult?=null
        when(outcome) {
            SyntheticTaskAssignOutcome.Unknown->Unit
            SyntheticTaskAssignOutcome.RejectedWithoutWrite->phase=TaskAssignPhase.REJECTED
            is SyntheticTaskAssignOutcome.Response->{val r=TaskAssignResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && r.assignee==attempt.review.value.userID && TaskSnoozeValue.parse(r.updatedAt)!=null) {phase=TaskAssignPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskAssignAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskAssignPhase.CONFIRMED && r.phase!=TaskAssignPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
