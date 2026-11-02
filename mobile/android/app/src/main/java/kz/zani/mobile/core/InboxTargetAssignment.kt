package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
// Same exact generic assigned_to read lens, independent command/ledger.
typealias InboxTargetAssignmentSource = InboxSelfAssignmentSource
data class InboxTargetAssignmentCandidate private constructor(val source:InboxTargetAssignmentSource,val reference:QualifiedMemberReference) {
    val valid get()=source.valid && reference.valid && reference.context==source.context
    companion object {fun make(source:InboxTargetAssignmentSource,reference:QualifiedMemberReference):InboxTargetAssignmentCandidate? {if(!source.valid || !reference.valid || reference.context!=source.context)return null;return InboxTargetAssignmentCandidate(source,reference)}}
}
data class SyntheticInboxTargetAssignmentGrant(val business:Int,val conversation:Int,val actor:Int,val manage:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && manage)SyntheticInboxTargetAssignmentAuthorization.create(c,actor)else null
}
data class SyntheticInboxTargetAssignmentAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxTargetAssignmentAuthorization(c,actor)}}
// Separate synthetic context; observed membership/role/account fields never grant commands.
data class SyntheticInboxTargetMembershipContext(val business:Int,val user:Int,val activeMember:Boolean) {fun matches(ref:QualifiedMemberReference)=ref.valid && business==ref.context.business && user==ref.source.user.id && activeMember}
data class InboxTargetAssignmentReview(val source:InboxTargetAssignmentSource,val authorization:SyntheticInboxTargetAssignmentAuthorization,val candidate:InboxTargetAssignmentCandidate,val targetMembership:SyntheticInboxTargetMembershipContext,val visit:Int) {val valid get()=source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && targetMembership.matches(candidate.reference) && visit>0}
data class InboxTargetAssignmentAttempt internal constructor(val localID:Int,val review:InboxTargetAssignmentReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/assign/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{\"user_id\":${review.candidate.reference.source.user.id}}"
}
data class InboxTargetAssignmentReceipt private constructor(val source:InboxTargetAssignmentSource) {companion object {fun decode(body:String,a:InboxTargetAssignmentAttempt):InboxTargetAssignmentReceipt? {if(!a.review.valid)return null;val s=InboxTargetAssignmentSource.decode(body,a.review.source.context) ?: return null;return if(s.assignedTo==a.review.candidate.reference.source.user.id)InboxTargetAssignmentReceipt(s)else null}}}
sealed interface SyntheticInboxTargetAssignmentOutcome {data class Response(val status:Int,val body:String):SyntheticInboxTargetAssignmentOutcome;data object RejectedWithoutWrite:SyntheticInboxTargetAssignmentOutcome;data object Unknown:SyntheticInboxTargetAssignmentOutcome}
interface SyntheticInboxTargetAssignmentPort {val grants:List<SyntheticInboxTargetAssignmentGrant>;val targetMemberships:List<SyntheticInboxTargetMembershipContext>;suspend fun execute(a:InboxTargetAssignmentAttempt):SyntheticInboxTargetAssignmentOutcome}
enum class InboxTargetAssignmentPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxTargetAssignmentRecord(val attempt:InboxTargetAssignmentAttempt,val phase:InboxTargetAssignmentPhase,val result:InboxTargetAssignmentReceipt?=null)
class InboxTargetAssignmentLedger {
    private val history=mutableListOf<InboxTargetAssignmentRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxTargetAssignmentAuthorization?):InboxTargetAssignmentRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxTargetAssignmentReview):InboxTargetAssignmentAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxTargetAssignmentAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxTargetAssignmentRecord(a,InboxTargetAssignmentPhase.PENDING));return a}
    fun complete(a:InboxTargetAssignmentAttempt,outcome:SyntheticInboxTargetAssignmentOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxTargetAssignmentPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxTargetAssignmentOutcome.Unknown->history[i].copy(phase=InboxTargetAssignmentPhase.UNKNOWN);SyntheticInboxTargetAssignmentOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxTargetAssignmentPhase.REJECTED);is SyntheticInboxTargetAssignmentOutcome.Response->{val r=if(outcome.status==200)InboxTargetAssignmentReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxTargetAssignmentPhase.UNKNOWN else InboxTargetAssignmentPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxTargetAssignmentAuthorization,record:InboxTargetAssignmentRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxTargetAssignmentPhase.RESPONSE,InboxTargetAssignmentPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
