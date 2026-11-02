package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Explicit input subset; no implicit timezone/default date/future-only policy.
data class TaskSnoozeValue private constructor(val raw:String,val microseconds:Long) {
    companion object {
        fun parse(raw:String):TaskSnoozeValue? {
            val m=Regex("""([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})""").matchEntire(raw) ?: return null
            val v=m.groupValues;val year=v[1].toInt();val month=v[2].toInt();val day=v[3].toInt();val hour=v[4].toInt();val minute=v[5].toInt();val second=v[6].toInt();val fraction=v[7];val zone=v[8]
            if(year !in 1..9999 || month !in 1..12 || hour>=24 || minute>=60 || second>=60 || zone=="-00:00")return null
            val leap=year%4==0 && (year%100!=0 || year%400==0);val lengths=listOf(31,if(leap)29 else 28,31,30,31,30,31,31,30,31,30,31)
            if(day<=0 || day>lengths[month-1])return null
            var offset=0
            if(zone!="Z") {val h=zone.substring(1,3).toInt();val minuteOffset=zone.substring(4,6).toInt();if(h>=24 || minuteOffset>=60)return null;offset=(h*3600+minuteOffset*60)*(if(zone[0]=='-')-1 else 1)}
            val y=year-if(month<=2)1 else 0;val era=y/400;val yoe=y-era*400;val doy=(153*(month+if(month>2)-3 else 9)+2)/5+day-1
            val days=era*146097+yoe*365+yoe/4-yoe/100+doy-719468
            val micros=(days.toLong()*86400+hour*3600+minute*60+second-offset)*1_000_000+fraction.padEnd(6,'0').toLong()
            if(micros < -62135596800000000L || micros>253402300799999999L)return null
            return TaskSnoozeValue(raw,micros)
        }
    }
}
data class TaskSnoozeSource(val read:TaskCommentRead,val task:WorkTask,val reminder:TaskScheduleValue) {
    val identityValid get()=read.context.valid && read.revision>0 && task.valid() && task.id==read.context.task && (task.business==null || task.business==read.context.business)
    val valid get()=identityValid && task.status in listOf("open","in_progress")
    fun matchesSchedule(value:String?,source:String?):Boolean {if(value==null || source==null)return value==null && source==null;val a=TaskSnoozeValue.parse(value) ?: return false;val b=TaskSnoozeValue.parse(source) ?: return false;return a.microseconds==b.microseconds}
    fun matchesReminder(value:String?)=when(val r=reminder) {TaskScheduleValue.NotSet->value==null;TaskScheduleValue.Unknown->false;is TaskScheduleValue.At->matchesSchedule(value,r.raw)}
}
data class SyntheticTaskSnoozeGrant(val business:Int,val task:Int,val actor:Int,val update:Boolean) {fun authorization(context:TaskCommentContext):SyntheticTaskSnoozeAuthorization?=if(context.valid && business==context.business && task==context.task && actor>0 && update)SyntheticTaskSnoozeAuthorization(context,actor) else null}
data class SyntheticTaskSnoozeAuthorization internal constructor(val context:TaskCommentContext,val actor:Int)
data class TaskSnoozeReview(val source:TaskSnoozeSource,val visit:Int,val value:TaskSnoozeValue)
data class TaskSnoozeAttempt(val localID:Int,val authorization:SyntheticTaskSnoozeAuthorization,val review:TaskSnoozeReview)
sealed interface SyntheticTaskSnoozeOutcome {data class Response(val status:Int,val body:String):SyntheticTaskSnoozeOutcome;data object RejectedWithoutWrite:SyntheticTaskSnoozeOutcome;data object Unknown:SyntheticTaskSnoozeOutcome}
interface SyntheticTaskSnoozePort {val grants:List<SyntheticTaskSnoozeGrant>;suspend fun execute(attempt:TaskSnoozeAttempt):SyntheticTaskSnoozeOutcome}
enum class TaskSnoozePhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskSnoozeResult(val id:Int,val business:Int,val status:String,val snoozedUntil:String,val dueAt:String?,val reminderAt:String?,val updatedAt:String) {
    companion object {fun decode(body:String):TaskSnoozeResult?=runCatching {
        val o=JSONObject(body)
        fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
        fun nullable(name:String):String? {require(o.has(name));return if(o.isNull(name))null else string(name)}
        TaskSnoozeResult(integer("id"),integer("business"),string("status"),string("snoozed_until"),nullable("due_at"),nullable("reminder_at"),string("updated_at"))
    }.getOrNull()}
}
data class TaskSnoozeRecord(val attempt:TaskSnoozeAttempt,val phase:TaskSnoozePhase,val result:TaskSnoozeResult?=null)
class TaskSnoozeLedger {
    var records:List<TaskSnoozeRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:TaskCommentContext)=c.business to c.task
    fun blocked(c:TaskCommentContext)=active.containsKey(key(c))
    fun visible(a:SyntheticTaskSnoozeAuthorization?):TaskSnoozeRecord? {if(a==null)return null;return active[key(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun begin(review:TaskSnoozeReview,authorization:SyntheticTaskSnoozeAuthorization):TaskSnoozeAttempt? {
        if(!review.source.valid || review.visit<=0 || TaskSnoozeValue.parse(review.value.raw)!=review.value || review.source.read.context!=authorization.context || authorization.actor<=0 || blocked(authorization.context))return null
        val a=TaskSnoozeAttempt(records.size+1,authorization,review);active[key(authorization.context)]=records.size;records=records+TaskSnoozeRecord(a,TaskSnoozePhase.PENDING);return a
    }
    fun complete(attempt:TaskSnoozeAttempt,outcome:SyntheticTaskSnoozeOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=TaskSnoozePhase.PENDING)return
        var phase=TaskSnoozePhase.UNKNOWN;var result:TaskSnoozeResult?=null
        when(outcome) {
            SyntheticTaskSnoozeOutcome.Unknown->Unit
            SyntheticTaskSnoozeOutcome.RejectedWithoutWrite->phase=TaskSnoozePhase.REJECTED
            is SyntheticTaskSnoozeOutcome.Response->{val r=TaskSnoozeResult.decode(outcome.body)
                if(outcome.status==200 && r!=null && r.id==attempt.authorization.context.task && r.business==attempt.authorization.context.business && r.status==attempt.review.source.task.status && TaskSnoozeValue.parse(r.snoozedUntil)?.microseconds==attempt.review.value.microseconds && attempt.review.source.matchesSchedule(r.dueAt,attempt.review.source.task.dueAt) && attempt.review.source.matchesReminder(r.reminderAt) && runCatching {Instant.parse(r.updatedAt)}.isSuccess) {phase=TaskSnoozePhase.CONFIRMED;result=r}
            }
        }
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,result=result) else r}
    }
    fun acknowledge(a:SyntheticTaskSnoozeAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=TaskSnoozePhase.CONFIRMED && r.phase!=TaskSnoozePhase.REJECTED)return false;active.remove(key(a.context));return true}
}
