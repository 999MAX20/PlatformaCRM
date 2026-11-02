package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Existing add-watcher actor fallback; separate fake UPDATE/member grant, never GET authority.
data class TaskWatcherSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in setOf("open","in_progress")
}
data class SyntheticTaskWatcherGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean,val activeMember:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskWatcherAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update && activeMember)SyntheticTaskWatcherAuthorization(context,actor) else null}
data class SyntheticTaskWatcherAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskWatcherReview(val source:TaskWatcherSource,val visit:Int)
data class TaskWatcherAttempt(val localID:Int,val authorization:SyntheticTaskWatcherAuthorization,val review:TaskWatcherReview)
sealed interface SyntheticTaskWatcherOutcome {data class Response(val status:Int,val body:String):SyntheticTaskWatcherOutcome;data object RejectedWithoutWrite:SyntheticTaskWatcherOutcome;data object Unknown:SyntheticTaskWatcherOutcome}
interface SyntheticTaskWatcherPort {val grants:List<SyntheticTaskWatcherGrant>;suspend fun execute(attempt:TaskWatcherAttempt):SyntheticTaskWatcherOutcome}
enum class TaskWatcherPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskWatcherResult(val id:Int,val business:Int,val status:String,val watchers:List<Int>,val updatedAt:String) {
    companion object {fun decode(body:String):TaskWatcherResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        TaskWatcherResult(integer("id"),integer("business"),string("status"),o.getJSONArray("watchers").let {array->(0 until array.length()).map {i->val raw=array.get(i);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());n.toInt()}},string("updated_at"))
    }.getOrNull()}
}
data class TaskWatcherRecord(val attempt:TaskWatcherAttempt,val phase:TaskWatcherPhase,val result:TaskWatcherResult?=null)
class TaskWatcherLedger {
    var records:List<TaskWatcherRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskWatcherAuthorization?):TaskWatcherRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskWatcherReview,authorization:SyntheticTaskWatcherAuthorization):TaskWatcherAttempt? {
        if(!review.source.valid || review.visit<=0 || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskWatcherAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskWatcherRecord(a,TaskWatcherPhase.PENDING);return a
    }
    fun complete(attempt:TaskWatcherAttempt,outcome:SyntheticTaskWatcherOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskWatcherPhase.PENDING)return
        var phase=TaskWatcherPhase.UNKNOWN;var result:TaskWatcherResult?=null
        when(outcome) {
            SyntheticTaskWatcherOutcome.Unknown->Unit
            SyntheticTaskWatcherOutcome.RejectedWithoutWrite->phase=TaskWatcherPhase.REJECTED
            is SyntheticTaskWatcherOutcome.Response->{val r=TaskWatcherResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && attempt.authorization.actor in r.watchers && r.watchers.all {it>0} && r.watchers.distinct().size==r.watchers.size && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskWatcherPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskWatcherAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskWatcherPhase.CONFIRMED && r.phase!=TaskWatcherPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
