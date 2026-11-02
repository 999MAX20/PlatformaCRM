package kz.zani.mobile.core

import org.json.JSONObject

// Same existing native supported title-only rules; full installed DRF acceptance remains separate.
data class TaskTitleValue private constructor(val raw:String,val title:String) {
    companion object {fun parse(raw:String):TaskTitleValue? {
        val value=SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(raw))
        if(value.isEmpty() || value.codePointCount(0,value.length)>255 || value.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})return null
        return TaskTitleValue(raw,value)
    }}
    fun body():String=JSONObject().put("title",title).toString()
}
data class TaskTitleEditSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
}
data class SyntheticTaskTitleEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskTitleEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskTitleEditAuthorization(context,actor) else null}
data class SyntheticTaskTitleEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskTitleEditReview(val source:TaskTitleEditSource,val visit:Int,val value:TaskTitleValue)
data class TaskTitleEditAttempt(val localID:Int,val authorization:SyntheticTaskTitleEditAuthorization,val review:TaskTitleEditReview)
sealed interface SyntheticTaskTitleEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskTitleEditOutcome;data object RejectedWithoutWrite:SyntheticTaskTitleEditOutcome;data object Unknown:SyntheticTaskTitleEditOutcome}
interface SyntheticTaskTitleEditPort {val grants:List<SyntheticTaskTitleEditGrant>;suspend fun execute(attempt:TaskTitleEditAttempt):SyntheticTaskTitleEditOutcome}
enum class TaskTitleEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskTitleEditResult(val id:Int,val business:Int,val status:String,val title:String,val updatedAt:String) {
    companion object {fun decode(body:String):TaskTitleEditResult?=runCatching {
        val o=JSONObject(body)
        fun integer(key:String):Int {val raw=o.get(key);require(raw is Int || raw is Long);val v=(raw as Number).toLong();require(v in 1L..Int.MAX_VALUE.toLong());return v.toInt()}
        fun string(key:String):String {val v=o.get(key);require(v is String);return v}
        val title=string("title");val updated=string("updated_at");require(TaskSnoozeValue.parse(updated)!=null)
        TaskTitleEditResult(integer("id"),integer("business"),string("status"),title,updated)
    }.getOrNull()}
}
data class TaskTitleEditRecord(val attempt:TaskTitleEditAttempt,val phase:TaskTitleEditPhase,val result:TaskTitleEditResult?=null)
class TaskTitleEditLedger {
    var records:List<TaskTitleEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskTitleEditAuthorization?):TaskTitleEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskTitleEditReview,authorization:SyntheticTaskTitleEditAuthorization):TaskTitleEditAttempt? {
        if(!review.source.valid || review.visit<=0 || TaskTitleValue.parse(review.value.raw)!=review.value || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskTitleEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskTitleEditRecord(a,TaskTitleEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskTitleEditAttempt,outcome:SyntheticTaskTitleEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskTitleEditPhase.PENDING)return
        var phase=TaskTitleEditPhase.UNKNOWN;var result:TaskTitleEditResult?=null
        when(outcome) {
            SyntheticTaskTitleEditOutcome.Unknown->Unit
            SyntheticTaskTitleEditOutcome.RejectedWithoutWrite->phase=TaskTitleEditPhase.REJECTED
            is SyntheticTaskTitleEditOutcome.Response->{val r=TaskTitleEditResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && r.title==attempt.review.value.title) {phase=TaskTitleEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskTitleEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskTitleEditPhase.CONFIRMED && r.phase!=TaskTitleEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
