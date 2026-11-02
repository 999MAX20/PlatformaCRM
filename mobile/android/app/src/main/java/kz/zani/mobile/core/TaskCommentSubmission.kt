package kz.zani.mobile.core

import java.time.Instant

// Fake-only capability, explicitly configured independently of GET/read visibility.
data class SyntheticTaskCommentGrant(val business: Int,val task: Int,val actor: Int,val update: Boolean) {
    fun authorization(context: TaskCommentContext): SyntheticTaskCommentAuthorization? =
        if(context.valid && context.business==business && context.task==task && actor>0 && update)SyntheticTaskCommentAuthorization(context,actor) else null
}
data class SyntheticTaskCommentAuthorization internal constructor(val context: TaskCommentContext,val actor: Int)
// Exact raw/text identity and echo matching retain the existing fake-only receipt contract.
data class TaskCommentAttempt(val localID: Int,val authorization: SyntheticTaskCommentAuthorization,val selection: TaskCommentSelection,val raw: String,val text: String)
sealed interface SyntheticTaskCommentOutcome {
    data class Response(val status: Int,val comment: TaskComment): SyntheticTaskCommentOutcome
    data object RejectedWithoutWrite: SyntheticTaskCommentOutcome
    data object Unknown: SyntheticTaskCommentOutcome
}
interface SyntheticTaskCommentPort {
    val grants: List<SyntheticTaskCommentGrant>
    suspend fun execute(attempt: TaskCommentAttempt): SyntheticTaskCommentOutcome
}
enum class TaskCommentAttemptPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class TaskCommentAttemptRecord(val attempt: TaskCommentAttempt,val phase: TaskCommentAttemptPhase,val comment: TaskComment?=null)
class TaskCommentAttemptLedger {
    // RAM correlation only, never a wire idempotency key/header/version.
    var records: List<TaskCommentAttemptRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(context: TaskCommentContext)=context.business to context.task
    fun blocked(context: TaskCommentContext)=active.containsKey(key(context))
    fun visible(authorization: SyntheticTaskCommentAuthorization?): TaskCommentAttemptRecord? {
        if(authorization==null)return null
        val record=active[key(authorization.context)]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==authorization}
    }
    fun begin(review: TaskCommentReview,raw: String,authorization: SyntheticTaskCommentAuthorization): TaskCommentAttempt? {
        val context=review.selection.read.context
        if(context!=authorization.context || !context.valid || authorization.actor<=0 || review.selection.read.revision<=0 || review.text.isEmpty() || TaskCommentText.preview(raw)!=review.text || blocked(context))return null
        val attempt=TaskCommentAttempt(records.size+1,authorization,review.selection,raw,review.text)
        active[key(context)]=records.size;records=records+TaskCommentAttemptRecord(attempt,TaskCommentAttemptPhase.PENDING);return attempt
    }
    fun complete(attempt: TaskCommentAttempt,outcome: SyntheticTaskCommentOutcome) {
        val index=records.indexOfFirst {it.attempt==attempt};if(index<0 || records[index].phase!=TaskCommentAttemptPhase.PENDING)return
        var phase=TaskCommentAttemptPhase.UNKNOWN;var accepted: TaskComment?=null
        when(outcome) {
            SyntheticTaskCommentOutcome.RejectedWithoutWrite->phase=TaskCommentAttemptPhase.REJECTED
            SyntheticTaskCommentOutcome.Unknown->Unit
            is SyntheticTaskCommentOutcome.Response->{val c=outcome.comment
                if(outcome.status==201 && c.id>0 && c.task==attempt.authorization.context.task && c.author==attempt.authorization.actor && c.text==attempt.text && c.createdAt!=null && runCatching {Instant.parse(c.createdAt)}.isSuccess && c.authorName!=null && c.authorEmail!=null) {phase=TaskCommentAttemptPhase.CONFIRMED;accepted=c}
            }
        }
        records=records.mapIndexed {n,record->if(n==index)record.copy(phase=phase,comment=accepted) else record}
    }
    // No text-reread proof, auto replay or release of pending/unknown attempts.
    fun acknowledge(authorization: SyntheticTaskCommentAuthorization): Boolean {
        val record=visible(authorization) ?: return false
        if(record.phase!=TaskCommentAttemptPhase.CONFIRMED && record.phase!=TaskCommentAttemptPhase.REJECTED)return false
        active.remove(key(authorization.context));return true
    }
}
