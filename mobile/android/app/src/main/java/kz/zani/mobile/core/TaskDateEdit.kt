package kz.zani.mobile.core

import org.json.JSONObject

enum class TaskDateField(val wire:String) {DUE("due_at"),REMINDER("reminder_at")}
enum class TaskDateMode {SET,CLEAR}
data class TaskDateChange(val field:TaskDateField,val mode:TaskDateMode,val raw:String) {
    val valid get()=mode==TaskDateMode.CLEAR || TaskSnoozeValue.parse(raw)!=null
    fun body():String?=if(valid)JSONObject().put(field.wire,if(mode==TaskDateMode.CLEAR)JSONObject.NULL else raw).toString() else null
}
data class TaskDateDraft(val field:TaskDateField?=null,val dueMode:TaskDateMode?=null,val reminderMode:TaskDateMode?=null,val dueRaw:String="",val reminderRaw:String="") {
    val mode get()=when(field){TaskDateField.DUE->dueMode;TaskDateField.REMINDER->reminderMode;null->null}
    val raw get()=when(field){TaskDateField.DUE->dueRaw;TaskDateField.REMINDER->reminderRaw;null->""}
    fun select(field:TaskDateField)=copy(field=field)
    fun choose(mode:TaskDateMode)=when(field){TaskDateField.DUE->copy(dueMode=mode);TaskDateField.REMINDER->copy(reminderMode=mode);null->this}
    fun update(raw:String)=when(field){TaskDateField.DUE->copy(dueRaw=raw);TaskDateField.REMINDER->copy(reminderRaw=raw);null->this}
    val change get()=field?.let {f->mode?.let {m->TaskDateChange(f,m,raw).takeIf {it.valid}}}
}
data class TaskDateEditSource(val read:TaskCommentRead,val task:WorkTask) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
}
data class SyntheticTaskDateEditGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskDateEditAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskDateEditAuthorization(context,actor) else null}
data class SyntheticTaskDateEditAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskDateEditReview(val source:TaskDateEditSource,val visit:Int,val change:TaskDateChange)
data class TaskDateEditAttempt(val localID:Int,val authorization:SyntheticTaskDateEditAuthorization,val review:TaskDateEditReview)
sealed interface SyntheticTaskDateEditOutcome {data class Response(val status:Int,val body:String):SyntheticTaskDateEditOutcome;data object RejectedWithoutWrite:SyntheticTaskDateEditOutcome;data object Unknown:SyntheticTaskDateEditOutcome}
interface SyntheticTaskDateEditPort {val grants:List<SyntheticTaskDateEditGrant>;suspend fun execute(attempt:TaskDateEditAttempt):SyntheticTaskDateEditOutcome}
enum class TaskDateEditPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
// Selected existing TaskSerializer field only; local field correlation is not wire data.
data class TaskDateEditResult private constructor(val id:Int,val business:Int,val status:String,val field:TaskDateField,val value:String?,val updatedAt:String) {
    fun matches(change:TaskDateChange):Boolean {if(!change.valid || change.field!=field)return false;if(change.mode==TaskDateMode.CLEAR)return value==null;val raw=value ?: return false;return TaskSnoozeValue.parse(raw)?.microseconds==TaskSnoozeValue.parse(change.raw)?.microseconds}
    companion object {fun decode(body:String,field:TaskDateField):TaskDateEditResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        require(o.has(field.wire));val value=if(o.isNull(field.wire))null else string(field.wire).also {require(TaskSnoozeValue.parse(it)!=null)}
        val updated=string("updated_at");require(TaskSnoozeValue.parse(updated)!=null)
        TaskDateEditResult(integer("id"),integer("business"),string("status"),field,value,updated)
    }.getOrNull()}
}
data class TaskDateEditRecord(val attempt:TaskDateEditAttempt,val phase:TaskDateEditPhase,val result:TaskDateEditResult?=null)
class TaskDateEditLedger {
    var records:List<TaskDateEditRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskDateEditAuthorization?):TaskDateEditRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskDateEditReview,authorization:SyntheticTaskDateEditAuthorization):TaskDateEditAttempt? {
        if(!review.source.valid || review.visit<=0 || !review.change.valid || review.change.body()==null || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskDateEditAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskDateEditRecord(a,TaskDateEditPhase.PENDING);return a
    }
    fun complete(attempt:TaskDateEditAttempt,outcome:SyntheticTaskDateEditOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskDateEditPhase.PENDING)return
        var phase=TaskDateEditPhase.UNKNOWN;var result:TaskDateEditResult?=null
        when(outcome) {
            SyntheticTaskDateEditOutcome.Unknown->Unit
            SyntheticTaskDateEditOutcome.RejectedWithoutWrite->phase=TaskDateEditPhase.REJECTED
            is SyntheticTaskDateEditOutcome.Response->{val r=TaskDateEditResult.decode(outcome.body,attempt.review.change.field)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && r.matches(attempt.review.change)) {phase=TaskDateEditPhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskDateEditAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskDateEditPhase.CONFIRMED && r.phase!=TaskDateEditPhase.REJECTED)return false;active.remove(key(a.context));return true}
}
