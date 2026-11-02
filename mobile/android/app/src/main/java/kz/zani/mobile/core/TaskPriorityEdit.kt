package kz.zani.mobile.core

import org.json.JSONObject

// Reuse only existing exact choices; no CREATE default or grant.
data class TaskPriorityValue private constructor(val raw:String) {
    companion object {fun parse(raw:String):TaskPriorityValue?=if(raw in TaskDraftValues.priorities)TaskPriorityValue(raw) else null}
    fun body():String=JSONObject().put("priority",raw).toString()
}
data class TaskPriorityEditSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
}
data class SyntheticTaskPriorityEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskPriorityEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskPriorityEditAuthorization(context,actor) else null}
data class SyntheticTaskPriorityEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskPriorityEditReview(val source:TaskPriorityEditSource,val visit:Int,val value:TaskPriorityValue)
data class TaskPriorityEditAttempt(val localID:Int,val authorization:SyntheticTaskPriorityEditAuthorization,val review:TaskPriorityEditReview)
sealed interface SyntheticTaskPriorityEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskPriorityEditOutcome;data object RejectedWithoutWrite:SyntheticTaskPriorityEditOutcome;data object Unknown:SyntheticTaskPriorityEditOutcome}
interface SyntheticTaskPriorityEditPort {val grants:List<SyntheticTaskPriorityEditGrant>;suspend fun execute(attempt:TaskPriorityEditAttempt):SyntheticTaskPriorityEditOutcome}
enum class TaskPriorityEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskPriorityEditResult(val id:Int,val business:Int,val status:String,val priority:String,val updatedAt:String) {
    companion object {fun decode(body:String):TaskPriorityEditResult?=runCatching {
        val o=JSONObject(body)
        fun integer(key:String):Int {val raw=o.get(key);require(raw is Int || raw is Long);val v=(raw as Number).toLong();require(v in 1L..Int.MAX_VALUE.toLong());return v.toInt()}
        fun string(key:String):String {val v=o.get(key);require(v is String);return v}
        val priority=string("priority");require(TaskPriorityValue.parse(priority)!=null);val updated=string("updated_at");require(TaskSnoozeValue.parse(updated)!=null)
        TaskPriorityEditResult(integer("id"),integer("business"),string("status"),priority,updated)
    }.getOrNull()}
}
data class TaskPriorityEditRecord(val attempt:TaskPriorityEditAttempt,val phase:TaskPriorityEditPhase,val result:TaskPriorityEditResult?=null)
class TaskPriorityEditLedger {
    var records:List<TaskPriorityEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskPriorityEditAuthorization?):TaskPriorityEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskPriorityEditReview,authorization:SyntheticTaskPriorityEditAuthorization):TaskPriorityEditAttempt? {
        if(!review.source.valid || review.visit<=0 || TaskPriorityValue.parse(review.value.raw)!=review.value || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskPriorityEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskPriorityEditRecord(a,TaskPriorityEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskPriorityEditAttempt,outcome:SyntheticTaskPriorityEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskPriorityEditPhase.PENDING)return
        var phase=TaskPriorityEditPhase.UNKNOWN;var result:TaskPriorityEditResult?=null
        when(outcome) {
            SyntheticTaskPriorityEditOutcome.Unknown->Unit
            SyntheticTaskPriorityEditOutcome.RejectedWithoutWrite->phase=TaskPriorityEditPhase.REJECTED
            is SyntheticTaskPriorityEditOutcome.Response->{val r=TaskPriorityEditResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && r.priority==attempt.review.value.raw) {phase=TaskPriorityEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskPriorityEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskPriorityEditPhase.CONFIRMED && r.phase!=TaskPriorityEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
