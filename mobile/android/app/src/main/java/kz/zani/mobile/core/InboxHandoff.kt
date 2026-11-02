package kz.zani.mobile.core

import org.json.JSONObject

data class HandoffReason private constructor(val raw:String,val reason:String) {
    companion object {fun make(raw:String):HandoffReason? {val value=SourceTextTrim.pythonStrip(raw);return if(value.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})null else HandoffReason(raw,value)}}
}
data class HandoffReview(val selection:ReplyDraftSelection,val value:HandoffReason)
data class HandoffDraftState(val context:ReplyDraftContext?=null,val available:Boolean=false,val selection:ReplyDraftSelection?=null,val phase:ReplyDraftPhase=ReplyDraftPhase.CLOSED,val raw:String="",val inputError:Boolean=false,val review:HandoffReview?=null)
class HandoffDraftSession {
    var state=HandoffDraftState();private set;private var generation=0;private val buffers=mutableMapOf<Int,String>()
    private fun stash() {val c=state.context;if(state.available && c!=null)buffers[c.conversation]=state.raw}
    fun bind(next:ReplyDraftContext?,available:Boolean) {
        if(next==null || !next.valid){clear();return};if(state.context?.business==next.business && state.context?.epoch==next.epoch)stash() else buffers.clear()
        val changed=state.context!=next || !state.available || !available
        if(changed){generation++;state=state.copy(selection=null,review=null,phase=ReplyDraftPhase.CLOSED,inputError=false,raw=if(available)buffers[next.conversation].orEmpty() else "")};state=state.copy(context=next,available=available)
    }
    fun retainOwner(business:Int?,epoch:Int?) {val c=state.context;if(c==null || c.business!=business || c.epoch!=epoch)clear() else pause()}
    fun pause() {stash();generation++;state=state.copy(available=false,selection=null,review=null,phase=ReplyDraftPhase.CLOSED,raw="",inputError=false)}
    fun open(c:ReplyDraftContext):Boolean {if(!state.available || state.context!=c || state.selection!=null)return false;state=state.copy(selection=ReplyDraftSelection(c,++generation),phase=ReplyDraftPhase.EDITING,review=null,inputError=false);return true}
    fun update(raw:String,selection:ReplyDraftSelection) {if(state.selection!=selection || !state.available || state.phase!=ReplyDraftPhase.EDITING)return;state=state.copy(raw=raw,inputError=false);stash()}
    fun prepare(selection:ReplyDraftSelection):Boolean {if(state.selection!=selection || !state.available || state.phase!=ReplyDraftPhase.EDITING)return false;val value=HandoffReason.make(state.raw);if(value==null){state=state.copy(inputError=true);return false};state=state.copy(review=HandoffReview(selection,value),phase=ReplyDraftPhase.REVIEW,inputError=false);return true}
    fun back(selection:ReplyDraftSelection) {if(state.selection!=selection)return;if(state.phase==ReplyDraftPhase.REVIEW)state=state.copy(phase=ReplyDraftPhase.EDITING,review=null) else close(selection)}
    fun close(selection:ReplyDraftSelection) {if(state.selection!=selection)return;stash();generation++;state=state.copy(selection=null,review=null,phase=ReplyDraftPhase.CLOSED)}
    fun discard(selection:ReplyDraftSelection) {if(state.selection!=selection)return;state=state.copy(raw="",inputError=false);stash();close(selection)}
    fun clear() {generation++;state=HandoffDraftState();buffers.clear()}
}
data class SyntheticHandoffGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean) {
    fun authorization(c:ReplyDraftContext):SyntheticHandoffAuthorization?=if(c.valid && c.business==business && c.conversation==conversation && actor>0 && update)SyntheticHandoffAuthorization(c,actor) else null
}
data class SyntheticHandoffAuthorization internal constructor(val context:ReplyDraftContext,val actor:Int)
data class HandoffAttempt(val localID:Int,val authorization:SyntheticHandoffAuthorization,val review:HandoffReview) {
    val path get()="/api/inbox/conversations/${authorization.context.conversation}/handoff/"
    val preparedHeaders get()=emptyMap<String,String>()
    fun preparedBody():String=JSONObject().put("reason",review.value.reason).toString()
}
sealed interface SyntheticHandoffOutcome {data class Response(val status:Int,val body:String):SyntheticHandoffOutcome;data object RejectedWithoutWrite:SyntheticHandoffOutcome;data object Unknown:SyntheticHandoffOutcome}
interface SyntheticHandoffPort {val grants:List<SyntheticHandoffGrant>;suspend fun execute(attempt:HandoffAttempt):SyntheticHandoffOutcome}
enum class HandoffPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
data class HandoffReceipt(val business:Int,val conversation:Int,val reason:String,val updatedAt:String) {
    companion object {fun decode(body:String):HandoffReceipt?=runCatching {
        val o=JSONObject(body);val handoff=o.get("handoff_required");val enabled=o.get("bot_enabled");require(handoff is Boolean && handoff && enabled is Boolean && !enabled)
        fun integer(key:String):Int {val v=o.get(key);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        val reason=o.get("handoff_reason");val time=o.get("updated_at");require(reason is String && time is String && TaskSnoozeValue.parse(time)!=null);HandoffReceipt(integer("business"),integer("id"),reason,time)
    }.getOrNull()}
    fun matches(a:HandoffAttempt)=business==a.authorization.context.business && conversation==a.authorization.context.conversation && reason==a.review.value.reason
}
data class HandoffRecord(val attempt:HandoffAttempt,val phase:HandoffPhase,val receipt:HandoffReceipt?=null)
class HandoffLedger {
    var records:List<HandoffRecord> = emptyList();private set;private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun owner(c:ReplyDraftContext)=c.business to c.conversation
    fun blocked(c:ReplyDraftContext)=active.containsKey(owner(c))
    fun visible(a:SyntheticHandoffAuthorization?):HandoffRecord?=if(a==null)null else active[owner(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}
    fun begin(r:HandoffReview,a:SyntheticHandoffAuthorization):HandoffAttempt? {if(r.selection.context!=a.context || r.selection.generation<=0 || HandoffReason.make(r.value.raw)!=r.value || blocked(a.context))return null;val attempt=HandoffAttempt(records.size+1,a,r);active[owner(a.context)]=records.size;records=records+HandoffRecord(attempt,HandoffPhase.PENDING);return attempt}
    fun complete(a:HandoffAttempt,outcome:SyntheticHandoffOutcome) {
        val i=records.indexOfFirst {it.attempt==a};if(i<0 || records[i].phase!=HandoffPhase.PENDING)return;var phase=HandoffPhase.UNKNOWN;var receipt:HandoffReceipt?=null
        when(outcome) {SyntheticHandoffOutcome.Unknown->Unit;SyntheticHandoffOutcome.RejectedWithoutWrite->phase=HandoffPhase.REJECTED
            is SyntheticHandoffOutcome.Response->{val value=HandoffReceipt.decode(outcome.body);if(outcome.status==200 && value!=null && value.matches(a)){phase=HandoffPhase.CONFIRMED;receipt=value}}}
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,receipt=receipt) else r}
    }
    fun acknowledge(a:SyntheticHandoffAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=HandoffPhase.CONFIRMED && r.phase!=HandoffPhase.REJECTED)return false;active.remove(owner(a.context));return true}
}
