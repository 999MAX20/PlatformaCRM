package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing undo-cancel: server chooses target; no client audit/target/key fields.
data class TaskUndoCancelSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status=="cancelled"
}
data class SyntheticTaskUndoCancelGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskUndoCancelAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskUndoCancelAuthorization(context,actor) else null}
data class SyntheticTaskUndoCancelAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskUndoCancelReview(val source:TaskUndoCancelSource,val visit:Int)
data class TaskUndoCancelAttempt(val localID:Int,val authorization:SyntheticTaskUndoCancelAuthorization,val review:TaskUndoCancelReview)
sealed interface SyntheticTaskUndoCancelOutcome {data class Response(val status:Int,val body:String):SyntheticTaskUndoCancelOutcome;data object RejectedWithoutWrite:SyntheticTaskUndoCancelOutcome;data object Unknown:SyntheticTaskUndoCancelOutcome}
interface SyntheticTaskUndoCancelPort {val grants:List<SyntheticTaskUndoCancelGrant>;suspend fun execute(attempt:TaskUndoCancelAttempt):SyntheticTaskUndoCancelOutcome}
enum class TaskUndoCancelPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskUndoCancelResult(val id:Int,val business:Int,val status:String,val updatedAt:String,val completedAt:String?,val completedBy:Int?) {
    companion object {fun decode(body:String):TaskUndoCancelResult?=runCatching {
        val o=JSONObject(body)
        listOf("cancelled_at","cancelled_by").forEach {require(o.has(it) && o.get(it)==JSONObject.NULL)};require(o.get("cancel_reason")=="")
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        val completedAt=if(o.get("completed_at")==JSONObject.NULL)null else string("completed_at").also {Instant.parse(it)}
        val completedBy=if(o.get("completed_by")==JSONObject.NULL)null else integer("completed_by")
        TaskUndoCancelResult(integer("id"),integer("business"),string("status"),string("updated_at"),completedAt,completedBy)
    }.getOrNull()}
}
data class TaskUndoCancelRecord(val attempt:TaskUndoCancelAttempt,val phase:TaskUndoCancelPhase,val result:TaskUndoCancelResult?=null)
class TaskUndoCancelLedger {
    var records:List<TaskUndoCancelRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskUndoCancelAuthorization?):TaskUndoCancelRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskUndoCancelReview,authorization:SyntheticTaskUndoCancelAuthorization):TaskUndoCancelAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskUndoCancelAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskUndoCancelRecord(a,TaskUndoCancelPhase.PENDING);return a
    }
    fun complete(attempt:TaskUndoCancelAttempt,outcome:SyntheticTaskUndoCancelOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskUndoCancelPhase.PENDING)return
        var phase=TaskUndoCancelPhase.UNKNOWN;var result:TaskUndoCancelResult?=null
        when(outcome) {
            SyntheticTaskUndoCancelOutcome.Unknown->Unit
            SyntheticTaskUndoCancelOutcome.RejectedWithoutWrite->phase=TaskUndoCancelPhase.REJECTED
            is SyntheticTaskUndoCancelOutcome.Response->{val r=TaskUndoCancelResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status in setOf("open","in_progress","done") && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskUndoCancelPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskUndoCancelAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskUndoCancelPhase.CONFIRMED && r.phase!=TaskUndoCancelPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
