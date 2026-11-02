package kz.zani.mobile.core

import java.time.Instant

// Fake-only capability configured independently of GET and comment capabilities.
data class SyntheticTaskCancelGrant(val business: Int,val task: Int,val actor: Int,val update: Boolean) {
    fun authorization(context: TaskCommentContext): SyntheticTaskCancelAuthorization? = if(context.valid && context.business==business && context.task==task && actor>0 && update)SyntheticTaskCancelAuthorization(context,actor) else null
}
data class SyntheticTaskCancelAuthorization internal constructor(val context: TaskCommentContext,val actor: Int)
data class TaskCancelAttempt(val localID: Int,val authorization: SyntheticTaskCancelAuthorization,val review: TaskCancelReasonReview,val raw: String,val fromStatus: String)
sealed interface SyntheticTaskCancelOutcome {
    data class Response(val status: Int,val task: WorkTask): SyntheticTaskCancelOutcome
    data object RejectedWithoutWrite: SyntheticTaskCancelOutcome
    data object Unknown: SyntheticTaskCancelOutcome
}
interface SyntheticTaskCancelPort {
    val grants: List<SyntheticTaskCancelGrant>
    suspend fun execute(attempt: TaskCancelAttempt): SyntheticTaskCancelOutcome
}
enum class TaskCancelAttemptPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskCancelAttemptRecord(val attempt: TaskCancelAttempt,val phase: TaskCancelAttemptPhase,val task: WorkTask?=null)
class TaskCancelAttemptLedger {
    // Local RAM correlation only, no wire key/version/header.
    var records: List<TaskCancelAttemptRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(context: TaskCommentContext)=context.business to context.task
    fun blocked(context: TaskCommentContext)=active.containsKey(key(context))
    fun visible(authorization: SyntheticTaskCancelAuthorization?): TaskCancelAttemptRecord? {
        if(authorization==null)return null
        val record=active[key(authorization.context)]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==authorization}
    }
    fun begin(review: TaskCancelReasonReview,raw: String,status: String,authorization: SyntheticTaskCancelAuthorization): TaskCancelAttempt? {
        val context=review.selection.read.context
        if(context!=authorization.context || !context.valid || authorization.actor<=0 || review.selection.read.revision<=0 || status !in listOf("open","in_progress") || TaskCancelReasonText.problem(raw)!=null || TaskCancelReasonText.preview(raw)!=review.text || blocked(context))return null
        val attempt=TaskCancelAttempt(records.size+1,authorization,review,raw,status)
        active[key(context)]=records.size;records=records+TaskCancelAttemptRecord(attempt,TaskCancelAttemptPhase.PENDING);return attempt
    }
    fun complete(attempt: TaskCancelAttempt,outcome: SyntheticTaskCancelOutcome) {
        val index=records.indexOfFirst {it.attempt==attempt};if(index<0 || records[index].phase!=TaskCancelAttemptPhase.PENDING)return
        var phase=TaskCancelAttemptPhase.UNKNOWN;var accepted: WorkTask?=null
        when(outcome) {
            SyntheticTaskCancelOutcome.RejectedWithoutWrite->phase=TaskCancelAttemptPhase.REJECTED
            SyntheticTaskCancelOutcome.Unknown->Unit
            is SyntheticTaskCancelOutcome.Response->{val t=outcome.task
                if(outcome.status==200 && t.valid() && t.id==attempt.authorization.context.task && t.business==attempt.authorization.context.business && t.status=="cancelled" && t.cancelledBy==attempt.authorization.actor && t.cancelReason==attempt.review.text && t.cancelledAt!=null && runCatching {Instant.parse(t.cancelledAt)}.isSuccess && t.updatedAt!=null && runCatching {Instant.parse(t.updatedAt)}.isSuccess) {phase=TaskCancelAttemptPhase.CONFIRMED;accepted=t}
            }
        }
        records=records.mapIndexed {n,record->if(n==index)record.copy(phase=phase,task=accepted) else record}
    }
    fun acknowledge(authorization: SyntheticTaskCancelAuthorization): Boolean {
        val record=visible(authorization) ?: return false
        if(record.phase!=TaskCancelAttemptPhase.CONFIRMED && record.phase!=TaskCancelAttemptPhase.REJECTED)return false
        active.remove(key(authorization.context));return true
    }
}
