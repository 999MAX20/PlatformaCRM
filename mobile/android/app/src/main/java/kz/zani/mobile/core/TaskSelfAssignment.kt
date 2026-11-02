package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing self-assignment service/result; separate fake UPDATE and active-member grant, never GET authority.
data class TaskSelfAssignmentSource(val read:TaskCommentRead,val task:WorkTask) {val valid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business) && task.status in listOf("open","in_progress")}
data class SyntheticTaskSelfAssignGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean,val activeMember:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskSelfAssignAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update && activeMember)SyntheticTaskSelfAssignAuthorization(context,actor) else null}
data class SyntheticTaskSelfAssignAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskSelfAssignmentReview(val source:TaskSelfAssignmentSource,val visit:Int)
data class TaskSelfAssignmentAttempt(val localID:Int,val authorization:SyntheticTaskSelfAssignAuthorization,val review:TaskSelfAssignmentReview)
sealed interface SyntheticTaskSelfAssignOutcome {data class Response(val status:Int,val body:String):SyntheticTaskSelfAssignOutcome;data object RejectedWithoutWrite:SyntheticTaskSelfAssignOutcome;data object Unknown:SyntheticTaskSelfAssignOutcome}
interface SyntheticTaskSelfAssignPort {val grants:List<SyntheticTaskSelfAssignGrant>;suspend fun execute(attempt:TaskSelfAssignmentAttempt):SyntheticTaskSelfAssignOutcome}
enum class TaskSelfAssignmentPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskSelfAssignmentResult(val id:Int,val business:Int,val status:String,val assignee:Int,val updatedAt:String) {
    companion object {fun decode(body:String):TaskSelfAssignmentResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskSelfAssignmentResult(integer("id"),integer("business"),string("status"),integer("assignee"),string("updated_at"))
    }.getOrNull()}
}
data class TaskSelfAssignmentRecord(val attempt:TaskSelfAssignmentAttempt,val phase:TaskSelfAssignmentPhase,val result:TaskSelfAssignmentResult?=null)
class TaskSelfAssignmentLedger {
    var records:List<TaskSelfAssignmentRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskSelfAssignAuthorization?):TaskSelfAssignmentRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskSelfAssignmentReview,authorization:SyntheticTaskSelfAssignAuthorization):TaskSelfAssignmentAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskSelfAssignmentAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskSelfAssignmentRecord(a,TaskSelfAssignmentPhase.PENDING);return a
    }
    fun complete(attempt:TaskSelfAssignmentAttempt,outcome:SyntheticTaskSelfAssignOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskSelfAssignmentPhase.PENDING)return
        var phase=TaskSelfAssignmentPhase.UNKNOWN;var result:TaskSelfAssignmentResult?=null
        when(outcome) {
            SyntheticTaskSelfAssignOutcome.Unknown->Unit
            SyntheticTaskSelfAssignOutcome.RejectedWithoutWrite->phase=TaskSelfAssignmentPhase.REJECTED
            is SyntheticTaskSelfAssignOutcome.Response->{val r=TaskSelfAssignmentResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status=="in_progress" && r.assignee==attempt.authorization.actor && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskSelfAssignmentPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskSelfAssignAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskSelfAssignmentPhase.CONFIRMED && r.phase!=TaskSelfAssignmentPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
