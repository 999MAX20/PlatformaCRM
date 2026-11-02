package kz.zani.mobile.core

import org.json.JSONObject

// Explicit new whole replacement; no excerpt prefill or silent original roundtrip.
enum class TaskDescriptionMode {REPLACE,CLEAR}
data class TaskDescriptionValue private constructor(val mode:TaskDescriptionMode,val raw:String,val description:String) {
    companion object {fun make(mode:TaskDescriptionMode?,raw:String):TaskDescriptionValue? {
        if(mode==null)return null
        if(mode==TaskDescriptionMode.CLEAR)return TaskDescriptionValue(mode,raw,"")
        val value=SourceTextTrim.pythonStrip(raw)
        if(value.isEmpty() || value.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})return null
        return TaskDescriptionValue(mode,raw,value)
    }}
    fun body():String=JSONObject().put("description",description).toString()
}
data class TaskDescriptionEditSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
}
data class SyntheticTaskDescriptionEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskDescriptionEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskDescriptionEditAuthorization(context,actor) else null}
data class SyntheticTaskDescriptionEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskDescriptionEditReview(val source:TaskDescriptionEditSource,val visit:Int,val value:TaskDescriptionValue)
data class TaskDescriptionEditAttempt(val localID:Int,val authorization:SyntheticTaskDescriptionEditAuthorization,val review:TaskDescriptionEditReview)
sealed interface SyntheticTaskDescriptionEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskDescriptionEditOutcome;data object RejectedWithoutWrite:SyntheticTaskDescriptionEditOutcome;data object Unknown:SyntheticTaskDescriptionEditOutcome}
interface SyntheticTaskDescriptionEditPort {val grants:List<SyntheticTaskDescriptionEditGrant>;suspend fun execute(attempt:TaskDescriptionEditAttempt):SyntheticTaskDescriptionEditOutcome}
enum class TaskDescriptionEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskDescriptionEditResult(val id:Int,val business:Int,val status:String,val description:String,val updatedAt:String) {
    companion object {fun decode(body:String):TaskDescriptionEditResult?=runCatching {
        val o=JSONObject(body)
        fun integer(key:String):Int {val raw=o.get(key);require(raw is Int || raw is Long);val v=(raw as Number).toLong();require(v in 1L..Int.MAX_VALUE.toLong());return v.toInt()}
        fun string(key:String):String {val v=o.get(key);require(v is String);return v}
        val description=string("description");val updated=string("updated_at");require(TaskSnoozeValue.parse(updated)!=null)
        TaskDescriptionEditResult(integer("id"),integer("business"),string("status"),description,updated)
    }.getOrNull()}
}
data class TaskDescriptionEditRecord(val attempt:TaskDescriptionEditAttempt,val phase:TaskDescriptionEditPhase,val result:TaskDescriptionEditResult?=null)
class TaskDescriptionEditLedger {
    var records:List<TaskDescriptionEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskDescriptionEditAuthorization?):TaskDescriptionEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskDescriptionEditReview,authorization:SyntheticTaskDescriptionEditAuthorization):TaskDescriptionEditAttempt? {
        if(!review.source.valid || review.visit<=0 || TaskDescriptionValue.make(review.value.mode,review.value.raw)!=review.value || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskDescriptionEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskDescriptionEditRecord(a,TaskDescriptionEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskDescriptionEditAttempt,outcome:SyntheticTaskDescriptionEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskDescriptionEditPhase.PENDING)return
        var phase=TaskDescriptionEditPhase.UNKNOWN;var result:TaskDescriptionEditResult?=null
        when(outcome) {
            SyntheticTaskDescriptionEditOutcome.Unknown->Unit
            SyntheticTaskDescriptionEditOutcome.RejectedWithoutWrite->phase=TaskDescriptionEditPhase.REJECTED
            is SyntheticTaskDescriptionEditOutcome.Response->{val r=TaskDescriptionEditResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && r.description==attempt.review.value.description) {phase=TaskDescriptionEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskDescriptionEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskDescriptionEditPhase.CONFIRMED && r.phase!=TaskDescriptionEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
