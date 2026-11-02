package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing start action only. Current actor is correlation, never a new assignee/response echo.
data class TaskStartSource(val read:TaskCommentRead,val task:WorkTask,val assignee:MobileUserRead) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status=="open"
    fun matchesAssignee(value:Int?)=when(val current=assignee) {MobileUserRead.NotSet->value==null;MobileUserRead.Unknown->false;is MobileUserRead.Person->current.user.valid && value==current.user.id}
}
data class SyntheticTaskStartGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskStartAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskStartAuthorization(context,actor) else null}
data class SyntheticTaskStartAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskStartReview(val source:TaskStartSource,val visit:Int)
data class TaskStartAttempt(val localID:Int,val authorization:SyntheticTaskStartAuthorization,val review:TaskStartReview)
sealed interface SyntheticTaskStartOutcome {data class Response(val status:Int,val body:String):SyntheticTaskStartOutcome;data object RejectedWithoutWrite:SyntheticTaskStartOutcome;data object Unknown:SyntheticTaskStartOutcome}
interface SyntheticTaskStartPort {val grants:List<SyntheticTaskStartGrant>;suspend fun execute(attempt:TaskStartAttempt):SyntheticTaskStartOutcome}
enum class TaskStartPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskStartResult(val id:Int,val business:Int,val status:String,val assignee:Int?,val updatedAt:String) {
    companion object {fun decode(body:String):TaskStartResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskStartResult(integer("id"),integer("business"),string("status"),if(o.get("assignee")==JSONObject.NULL)null else integer("assignee"),string("updated_at"))
    }.getOrNull()}
}
data class TaskStartRecord(val attempt:TaskStartAttempt,val phase:TaskStartPhase,val result:TaskStartResult?=null)
class TaskStartLedger {
    var records:List<TaskStartRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskStartAuthorization?):TaskStartRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskStartReview,authorization:SyntheticTaskStartAuthorization):TaskStartAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskStartAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskStartRecord(a,TaskStartPhase.PENDING);return a
    }
    fun complete(attempt:TaskStartAttempt,outcome:SyntheticTaskStartOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskStartPhase.PENDING)return
        var phase=TaskStartPhase.UNKNOWN;var result:TaskStartResult?=null
        when(outcome) {
            SyntheticTaskStartOutcome.Unknown->Unit
            SyntheticTaskStartOutcome.RejectedWithoutWrite->phase=TaskStartPhase.REJECTED
            is SyntheticTaskStartOutcome.Response->{val r=TaskStartResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status=="in_progress" && attempt.review.source.matchesAssignee(r.assignee) && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskStartPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskStartAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskStartPhase.CONFIRMED && r.phase!=TaskStartPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
