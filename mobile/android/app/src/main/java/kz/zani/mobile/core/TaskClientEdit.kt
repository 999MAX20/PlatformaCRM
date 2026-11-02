package kz.zani.mobile.core

import org.json.JSONObject

enum class TaskClientEditMode { SET, CLEAR }
data class TaskClientChange(val mode:TaskClientEditMode,val choice:TaskDraftClientChoice?) {
    fun body():String? {if(mode==TaskClientEditMode.SET && (choice==null || !choice.validFor(choice.business)))return null;return JSONObject().put("client",if(mode==TaskClientEditMode.CLEAR)JSONObject.NULL else choice!!.id).toString()}
}
data class TaskClientEditDraft(val mode:TaskClientEditMode?=null,val choice:TaskDraftClientChoice?=null,val choiceRead:TaskCommentRead?=null,val query:String="") {
    fun change(source:TaskClientEditSource):TaskClientChange? {
        if(!source.valid || mode==null)return null
        if(mode==TaskClientEditMode.SET && (choice==null || !choice.validFor(source.read.context.business) || choiceRead!=source.read))return null
        return TaskClientChange(mode,if(mode==TaskClientEditMode.SET)choice else null)
    }
}
data class TaskClientEditSource(val read:TaskCommentRead,val task:WorkTask,val original:TaskClientOriginal) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val statusValid get()=identityValid && task.status in setOf("open","in_progress")
    val valid get()=statusValid && original.known
}
data class SyntheticTaskClientEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskClientEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskClientEditAuthorization(context,actor) else null}
data class SyntheticTaskClientEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskClientEditReview(val source:TaskClientEditSource,val visit:Int,val draft:TaskClientEditDraft) {val change get()=draft.change(source)}
data class TaskClientEditAttempt(val localID:Int,val authorization:SyntheticTaskClientEditAuthorization,val review:TaskClientEditReview) {fun preparedBody():String?=if(review.source.valid && review.source.read.context==authorization.context)review.change?.body() else null}
sealed interface SyntheticTaskClientEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskClientEditOutcome;data object RejectedWithoutWrite:SyntheticTaskClientEditOutcome;data object Unknown:SyntheticTaskClientEditOutcome}
interface SyntheticTaskClientEditPort {val grants:List<SyntheticTaskClientEditGrant>;suspend fun execute(attempt:TaskClientEditAttempt):SyntheticTaskClientEditOutcome}
enum class TaskClientEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskClientEditResult(val id:Int,val business:Int,val status:String,val value:Int?,val updatedAt:String) {
    fun matches(change:TaskClientChange)=if(change.mode==TaskClientEditMode.CLEAR)value==null else value==change.choice?.id
    companion object {fun decode(data:String):TaskClientEditResult?=runCatching {
        val o=JSONObject(data);fun integer(key:String):Int {val raw=o.get(key);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        val id=integer("id");val business=integer("business");val status=o.get("status") as String;val updated=o.get("updated_at") as String;require(TaskSnoozeValue.parse(updated)!=null)
        val value=when(val read=TaskCreateClientRead.decode(data)){TaskCreateClientRead.Unknown->error("Unknown selected client");TaskCreateClientRead.NotSet->null;is TaskCreateClientRead.Client->read.id}
        TaskClientEditResult(id,business,status,value,updated)
    }.getOrNull()}
}
data class TaskClientEditRecord(val attempt:TaskClientEditAttempt,val phase:TaskClientEditPhase,val result:TaskClientEditResult?=null)
class TaskClientEditLedger {
    var records:List<TaskClientEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskClientEditAuthorization?):TaskClientEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskClientEditReview,authorization:SyntheticTaskClientEditAuthorization):TaskClientEditAttempt? {
        if(!review.source.valid || review.visit<=0 || review.change==null || review.change?.body()==null || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskClientEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskClientEditRecord(a,TaskClientEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskClientEditAttempt,outcome:SyntheticTaskClientEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskClientEditPhase.PENDING)return
        var phase=TaskClientEditPhase.UNKNOWN;var result:TaskClientEditResult?=null
        when(outcome) {
            SyntheticTaskClientEditOutcome.Unknown->Unit
            SyntheticTaskClientEditOutcome.RejectedWithoutWrite->phase=TaskClientEditPhase.REJECTED
            is SyntheticTaskClientEditOutcome.Response->{val r=TaskClientEditResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && attempt.review.change?.let {r.matches(it)}==true) {phase=TaskClientEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskClientEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskClientEditPhase.CONFIRMED && r.phase!=TaskClientEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
