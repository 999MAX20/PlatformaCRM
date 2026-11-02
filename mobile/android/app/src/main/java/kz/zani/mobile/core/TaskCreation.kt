package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONObject

// Fake CREATE grant independent of VIEW/UPDATE/displayed member names.
data class SyntheticTaskCreateGrant(val business: Int,val actor: Int,val create: Boolean) {
    fun authorization(context: TaskDraftContext): SyntheticTaskCreateAuthorization? = if(context.valid && context.business==business && actor>0 && create)SyntheticTaskCreateAuthorization(context,actor) else null
}
data class SyntheticTaskCreateAuthorization internal constructor(val context: TaskDraftContext,val actor: Int)
data class TaskCreateAttempt(val localID: Int,val authorization: SyntheticTaskCreateAuthorization,val review: TaskDraftReview) {
    fun preparedBody():String? {
        if(authorization.context!=review.selection.context || review.values.issues.isNotEmpty() || !review.values.validClient(authorization.context.business) || !review.values.validAppointment(authorization.context.business) || !review.values.validParent(authorization.context.business) || review.preview!=review.values.preview)return null
        val v=review.preview;val fields=sortedMapOf<String,Any>("business" to authorization.context.business,"title" to v.title,"description" to v.description,"priority" to v.priority)
        v.dueAt?.let {fields["due_at"]=it};v.reminderAt?.let {fields["reminder_at"]=it};v.clientID?.let {fields["client"]=it};v.appointmentID?.let {fields["appointment"]=it};v.parentTaskID?.let {fields["parent_task"]=it}
        if(fields.values.any {it !is Int && it !is String})return null
        return fields.entries.joinToString(separator=",",prefix="{",postfix="}") {entry->JSONObject.quote(entry.key)+":"+(if(entry.value is Int)entry.value.toString() else JSONObject.quote(entry.value as String))}
    }
}
sealed interface SyntheticTaskCreateOutcome {
    data class Response(val status: Int,val task: WorkTask,val reminderAt:String?=null,val clientRead:TaskCreateClientRead=TaskCreateClientRead.Unknown,val appointmentRead:TaskCreateAppointmentRead=TaskCreateAppointmentRead.Unknown,val parentRead:TaskCreateParentRead=TaskCreateParentRead.Unknown): SyntheticTaskCreateOutcome
    data object RejectedWithoutWrite:SyntheticTaskCreateOutcome
    data object Unknown:SyntheticTaskCreateOutcome
}
interface SyntheticTaskCreatePort {
    val grants: List<SyntheticTaskCreateGrant>
    suspend fun execute(attempt: TaskCreateAttempt): SyntheticTaskCreateOutcome
}
enum class TaskCreateAttemptPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskCreateAttemptRecord(val attempt: TaskCreateAttempt,val phase: TaskCreateAttemptPhase,val task: WorkTask?=null,val reminderAt:String?=null,val clientID:Int?=null,val appointmentID:Int?=null,val parentTaskID:Int?=null)
class TaskCreateAttemptLedger {
    // Local RAM correlation only, never HTTP/idempotency metadata/version.
    var records: List<TaskCreateAttemptRecord> = emptyList();private set
    private val active=mutableMapOf<Int,Int>()
    fun blocked(context: TaskDraftContext)=active.containsKey(context.business)
    fun visible(authorization: SyntheticTaskCreateAuthorization?): TaskCreateAttemptRecord? {
        if(authorization==null)return null
        val record=active[authorization.context.business]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==authorization}
    }
    fun begin(review: TaskDraftReview,authorization: SyntheticTaskCreateAuthorization): TaskCreateAttempt? {
        val context=review.selection.context
        if(!context.valid || context!=authorization.context || authorization.actor<=0 || review.values.issues.isNotEmpty() || !review.values.validClient(context.business) || !review.values.validAppointment(context.business) || !review.values.validParent(context.business) || review.preview!=review.values.preview || blocked(context))return null
        val attempt=TaskCreateAttempt(records.size+1,authorization,review);active[context.business]=records.size;records=records+TaskCreateAttemptRecord(attempt,TaskCreateAttemptPhase.PENDING);return attempt
    }
    fun complete(attempt: TaskCreateAttempt,outcome: SyntheticTaskCreateOutcome) {
        val index=records.indexOfFirst {it.attempt==attempt};if(index<0 || records[index].phase!=TaskCreateAttemptPhase.PENDING)return
        var phase=TaskCreateAttemptPhase.UNKNOWN;var accepted: WorkTask?=null;var confirmedReminder:String?=null
        when(outcome) {
            SyntheticTaskCreateOutcome.RejectedWithoutWrite->phase=TaskCreateAttemptPhase.REJECTED
            SyntheticTaskCreateOutcome.Unknown->Unit
            is SyntheticTaskCreateOutcome.Response->{val t=outcome.task;val v=attempt.review.preview
                if(outcome.status==201 && t.id>0 && t.business==attempt.authorization.context.business && t.createdBy==attempt.authorization.actor && t.title==v.title && t.description==v.description && t.priority==v.priority && t.status=="open" && attempt.review.values.dueDate.matches(t.dueAt) && attempt.review.values.reminderDate.matches(outcome.reminderAt) && outcome.clientRead.matches(v.clientID) && outcome.appointmentRead.matches(v.appointmentID) && outcome.parentRead.matches(v.parentTaskID) && t.createdAt!=null && runCatching {Instant.parse(t.createdAt)}.isSuccess && t.updatedAt!=null && runCatching {Instant.parse(t.updatedAt)}.isSuccess) {phase=TaskCreateAttemptPhase.CONFIRMED;accepted=t;confirmedReminder=if(v.reminderAt!=null)outcome.reminderAt else null}
            }
        }
        records=records.mapIndexed {n,record->if(n==index)record.copy(phase=phase,task=accepted,reminderAt=confirmedReminder,clientID=if(phase==TaskCreateAttemptPhase.CONFIRMED)attempt.review.preview.clientID else null,appointmentID=if(phase==TaskCreateAttemptPhase.CONFIRMED)attempt.review.preview.appointmentID else null,parentTaskID=if(phase==TaskCreateAttemptPhase.CONFIRMED)attempt.review.preview.parentTaskID else null) else record}
    }
    fun acknowledge(authorization: SyntheticTaskCreateAuthorization): Boolean {
        val record=visible(authorization) ?: return false
        if(record.phase!=TaskCreateAttemptPhase.CONFIRMED && record.phase!=TaskCreateAttemptPhase.REJECTED)return false
        active.remove(authorization.context.business);return true
    }
}
