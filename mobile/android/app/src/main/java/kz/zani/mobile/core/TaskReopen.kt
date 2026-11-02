package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing reopen action only; undo-cancel derives a different target from server AuditLog.
data class TaskReopenSource(val read:TaskCommentRead,val task:WorkTask,val assignee:MobileUserRead) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in setOf("done","cancelled")
    fun matchesAssignee(value:Int?)=when(val current=assignee) {MobileUserRead.NotSet->value==null;MobileUserRead.Unknown->false;is MobileUserRead.Person->current.user.valid && value==current.user.id}
}
data class SyntheticTaskReopenGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskReopenAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskReopenAuthorization(context,actor) else null}
data class SyntheticTaskReopenAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskReopenReview(val source:TaskReopenSource,val visit:Int)
data class TaskReopenAttempt(val localID:Int,val authorization:SyntheticTaskReopenAuthorization,val review:TaskReopenReview)
sealed interface SyntheticTaskReopenOutcome {data class Response(val status:Int,val body:String):SyntheticTaskReopenOutcome;data object RejectedWithoutWrite:SyntheticTaskReopenOutcome;data object Unknown:SyntheticTaskReopenOutcome}
interface SyntheticTaskReopenPort {val grants:List<SyntheticTaskReopenGrant>;suspend fun execute(attempt:TaskReopenAttempt):SyntheticTaskReopenOutcome}
enum class TaskReopenPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskReopenResult(val id:Int,val business:Int,val status:String,val assignee:Int?,val updatedAt:String) {
    companion object {fun decode(body:String):TaskReopenResult?=runCatching {
        val o=JSONObject(body)
        listOf("completed_at","completed_by","cancelled_at","cancelled_by").forEach {require(o.has(it) && o.get(it)==JSONObject.NULL)}
        require(o.get("cancel_reason")=="")
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskReopenResult(integer("id"),integer("business"),string("status"),if(o.get("assignee")==JSONObject.NULL)null else integer("assignee"),string("updated_at"))
    }.getOrNull()}
}
data class TaskReopenRecord(val attempt:TaskReopenAttempt,val phase:TaskReopenPhase,val result:TaskReopenResult?=null)
class TaskReopenLedger {
    var records:List<TaskReopenRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskReopenAuthorization?):TaskReopenRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskReopenReview,authorization:SyntheticTaskReopenAuthorization):TaskReopenAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskReopenAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskReopenRecord(a,TaskReopenPhase.PENDING);return a
    }
    fun complete(attempt:TaskReopenAttempt,outcome:SyntheticTaskReopenOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskReopenPhase.PENDING)return
        var phase=TaskReopenPhase.UNKNOWN;var result:TaskReopenResult?=null
        when(outcome) {
            SyntheticTaskReopenOutcome.Unknown->Unit
            SyntheticTaskReopenOutcome.RejectedWithoutWrite->phase=TaskReopenPhase.REJECTED
            is SyntheticTaskReopenOutcome.Response->{val r=TaskReopenResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status=="open" && attempt.review.source.matchesAssignee(r.assignee) && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskReopenPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskReopenAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskReopenPhase.CONFIRMED && r.phase!=TaskReopenPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
