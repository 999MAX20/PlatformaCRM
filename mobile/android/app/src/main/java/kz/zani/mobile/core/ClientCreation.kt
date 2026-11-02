package kz.zani.mobile.core

import java.time.Instant

// Fake CREATE grant independent of VIEW/UPDATE/displayed member names.
data class SyntheticClientCreateGrant(val business: Int,val actor: Int,val create: Boolean) {
    fun authorization(context: ClientDraftContext): SyntheticClientCreateAuthorization? = if(context.valid && context.business==business && actor>0 && create)SyntheticClientCreateAuthorization(context,actor) else null
}
data class SyntheticClientCreateAuthorization internal constructor(val context: ClientDraftContext,val actor: Int)
data class ClientCreateAttempt(val localID: Int,val authorization: SyntheticClientCreateAuthorization,val review: ClientDraftReview)
sealed interface SyntheticClientCreateOutcome {
    data class Response(val status: Int,val client: ClientContact): SyntheticClientCreateOutcome
    data object RejectedWithoutWrite:SyntheticClientCreateOutcome
    data object Unknown:SyntheticClientCreateOutcome
}
interface SyntheticClientCreatePort {
    val grants: List<SyntheticClientCreateGrant>
    suspend fun execute(attempt: ClientCreateAttempt): SyntheticClientCreateOutcome
}
enum class ClientCreateAttemptPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class ClientCreateAttemptRecord(val attempt: ClientCreateAttempt,val phase: ClientCreateAttemptPhase,val client: ClientContact?=null)
class ClientCreateAttemptLedger {
    // Local RAM correlation only, never HTTP/idempotency metadata/version.
    var records: List<ClientCreateAttemptRecord> = emptyList();private set
    private val active=mutableMapOf<Int,Int>()
    fun blocked(context: ClientDraftContext)=active.containsKey(context.business)
    fun visible(authorization: SyntheticClientCreateAuthorization?): ClientCreateAttemptRecord? {
        if(authorization==null)return null
        val record=active[authorization.context.business]?.let {records[it]} ?: return null
        return record.takeIf {it.attempt.authorization==authorization}
    }
    fun begin(review: ClientDraftReview,authorization: SyntheticClientCreateAuthorization): ClientCreateAttempt? {
        val context=review.selection.context
        if(!context.valid || context!=authorization.context || authorization.actor<=0 || review.values.issues.isNotEmpty() || review.preview!=review.values.preview || blocked(context))return null
        val attempt=ClientCreateAttempt(records.size+1,authorization,review);active[context.business]=records.size;records=records+ClientCreateAttemptRecord(attempt,ClientCreateAttemptPhase.PENDING);return attempt
    }
    fun complete(attempt: ClientCreateAttempt,outcome: SyntheticClientCreateOutcome) {
        val index=records.indexOfFirst {it.attempt==attempt};if(index<0 || records[index].phase!=ClientCreateAttemptPhase.PENDING)return
        var phase=ClientCreateAttemptPhase.UNKNOWN;var accepted: ClientContact?=null
        when(outcome) {
            SyntheticClientCreateOutcome.RejectedWithoutWrite->phase=ClientCreateAttemptPhase.REJECTED
            SyntheticClientCreateOutcome.Unknown->Unit
            is SyntheticClientCreateOutcome.Response->{val t=outcome.client;val v=attempt.review.preview
                // ClientSerializer does not echo actor; keep that correlation local.
                if(outcome.status==201 && t.id>0 && t.business==attempt.authorization.context.business && t.fullName==v.fullName && t.phone==v.phone && t.email==v.email && t.source==v.source && t.notes==v.notes && t.createdAt!=null && runCatching {Instant.parse(t.createdAt)}.isSuccess && t.updatedAt!=null && runCatching {Instant.parse(t.updatedAt)}.isSuccess) {phase=ClientCreateAttemptPhase.CONFIRMED;accepted=t}
            }
        }
        records=records.mapIndexed {n,record->if(n==index)record.copy(phase=phase,client=accepted) else record}
    }
    fun acknowledge(authorization: SyntheticClientCreateAuthorization): Boolean {
        val record=visible(authorization) ?: return false
        if(record.phase!=ClientCreateAttemptPhase.CONFIRMED && record.phase!=ClientCreateAttemptPhase.REJECTED)return false
        active.remove(authorization.context.business);return true
    }
}
