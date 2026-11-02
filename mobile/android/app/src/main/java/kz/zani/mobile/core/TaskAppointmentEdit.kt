package kz.zani.mobile.core

import org.json.JSONObject

enum class TaskAppointmentEditMode { SET, CLEAR }
data class TaskAppointmentChange(val mode:TaskAppointmentEditMode,val choice:TaskDraftAppointmentChoice?) {
    fun body():String? {if(mode==TaskAppointmentEditMode.SET && (choice==null || !choice.validFor(choice.business)))return null;return JSONObject().put("appointment",if(mode==TaskAppointmentEditMode.CLEAR)JSONObject.NULL else choice!!.id).toString()}
}
data class TaskAppointmentEditDraft(val mode:TaskAppointmentEditMode?=null,val choice:TaskDraftAppointmentChoice?=null,val choiceRead:TaskCommentRead?=null,val day:String="") {
    fun change(source:TaskAppointmentEditSource):TaskAppointmentChange? {
        if(!source.valid || mode==null)return null
        if(mode==TaskAppointmentEditMode.SET && (!TaskAppointmentDay.valid(day) || choice==null || !choice.validFor(source.read.context.business) || choiceRead!=source.read))return null
        return TaskAppointmentChange(mode,if(mode==TaskAppointmentEditMode.SET)choice else null)
    }
}
data class TaskAppointmentEditSource(val read:TaskCommentRead,val task:WorkTask,val original:TaskAppointmentOriginal) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val statusValid get()=identityValid && task.status in setOf("open","in_progress")
    val valid get()=statusValid && original.known
}
data class SyntheticTaskAppointmentEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskAppointmentEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskAppointmentEditAuthorization(context,actor) else null}
data class SyntheticTaskAppointmentEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskAppointmentEditReview(val source:TaskAppointmentEditSource,val visit:Int,val draft:TaskAppointmentEditDraft) {val change get()=draft.change(source)}
data class TaskAppointmentEditAttempt(val localID:Int,val authorization:SyntheticTaskAppointmentEditAuthorization,val review:TaskAppointmentEditReview) {fun preparedBody():String?=if(review.source.valid && review.source.read.context==authorization.context)review.change?.body() else null}
sealed interface SyntheticTaskAppointmentEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskAppointmentEditOutcome;data object RejectedWithoutWrite:SyntheticTaskAppointmentEditOutcome;data object Unknown:SyntheticTaskAppointmentEditOutcome}
interface SyntheticTaskAppointmentEditPort {val grants:List<SyntheticTaskAppointmentEditGrant>;suspend fun execute(attempt:TaskAppointmentEditAttempt):SyntheticTaskAppointmentEditOutcome}
enum class TaskAppointmentEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskAppointmentEditResult(val id:Int,val business:Int,val status:String,val value:Int?,val updatedAt:String) {
    fun matches(change:TaskAppointmentChange)=if(change.mode==TaskAppointmentEditMode.CLEAR)value==null else value==change.choice?.id
    companion object {fun decode(data:String):TaskAppointmentEditResult?=runCatching {
        val o=JSONObject(data);fun integer(key:String):Int {val raw=o.get(key);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        val id=integer("id");val business=integer("business");val status=o.get("status") as String;val updated=o.get("updated_at") as String;require(TaskSnoozeValue.parse(updated)!=null)
        val value=when(val read=TaskCreateAppointmentRead.decode(data)){TaskCreateAppointmentRead.Unknown->error("Unknown selected appointment");TaskCreateAppointmentRead.NotSet->null;is TaskCreateAppointmentRead.Appointment->read.id}
        TaskAppointmentEditResult(id,business,status,value,updated)
    }.getOrNull()}
}
data class TaskAppointmentEditRecord(val attempt:TaskAppointmentEditAttempt,val phase:TaskAppointmentEditPhase,val result:TaskAppointmentEditResult?=null)
class TaskAppointmentEditLedger {
    var records:List<TaskAppointmentEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskAppointmentEditAuthorization?):TaskAppointmentEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskAppointmentEditReview,authorization:SyntheticTaskAppointmentEditAuthorization):TaskAppointmentEditAttempt? {
        if(!review.source.valid || review.visit<=0 || review.change==null || review.change?.body()==null || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskAppointmentEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskAppointmentEditRecord(a,TaskAppointmentEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskAppointmentEditAttempt,outcome:SyntheticTaskAppointmentEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskAppointmentEditPhase.PENDING)return
        var phase=TaskAppointmentEditPhase.UNKNOWN;var result:TaskAppointmentEditResult?=null
        when(outcome) {
            SyntheticTaskAppointmentEditOutcome.Unknown->Unit
            SyntheticTaskAppointmentEditOutcome.RejectedWithoutWrite->phase=TaskAppointmentEditPhase.REJECTED
            is SyntheticTaskAppointmentEditOutcome.Response->{val r=TaskAppointmentEditResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && attempt.review.change?.let {r.matches(it)}==true) {phase=TaskAppointmentEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskAppointmentEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskAppointmentEditPhase.CONFIRMED && r.phase!=TaskAppointmentEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
