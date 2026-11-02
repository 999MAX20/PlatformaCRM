package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Existing Team member detail lens. User identity does not grant membership/command permission.
data class TeamMemberReadSource private constructor(val id:Int,val business:Int,val user:MobileUserItem,val isActive:Boolean,val updatedAt:String) {
    fun validFor(scope:Int,id:Int)=scope>0 && id>0 && business==scope && this.id==id && user.valid && updatedAt.isNotEmpty()
    companion object {fun decode(raw:String,business:Int,id:Int):TeamMemberReadSource?=runCatching {require(business>0 && id>0);val t=JSONTokener(raw);val o=t.nextValue();require(t.nextClean()=='\u0000' && o is JSONObject);require(directoryReadInteger(o.get("id"))==id.toLong() && directoryReadInteger(o.get("business"))==business.toLong());val u=o.getJSONObject("user");val uid=directoryReadInteger(u.get("id"))!!;require(uid>0 && uid<=Int.MAX_VALUE);val email=u.get("email");val name=u.get("full_name");val active=o.get("is_active");val updated=o.get("updated_at");require(email is String && name is String && active is Boolean && updated is String && updated.isNotEmpty());TeamMemberReadSource(id,business,MobileUserItem(uid.toInt(),email,name),active,updated)}.getOrNull()}
}
object MemberReferenceIdentifier {fun parse(raw:String):Int?=raw.takeIf {it.isNotEmpty() && it.all {c->c in '0'..'9'}}?.toIntOrNull()?.takeIf {it>0}}
data class MemberReferenceControl(val context:InboxConversationFilesContext,val visit:Int)
data class MemberReferenceInput(val context:InboxConversationFilesContext,val generation:Int)
data class MemberReferenceTicket(val context:InboxConversationFilesContext,val revision:Int,val rawInput:String,val id:Int)
data class QualifiedMemberReference internal constructor(val context:InboxConversationFilesContext,val readRevision:Int,val rawInput:String,val source:TeamMemberReadSource) {val valid get()=context.valid && readRevision>0 && MemberReferenceIdentifier.parse(rawInput)==source.id && source.validFor(context.business,source.id) && source.isActive}
data class MemberReferenceState(val context:InboxConversationFilesContext?=null,val presented:Boolean=false,val rawInput:String="",val loading:Boolean=false,val source:TeamMemberReadSource?=null,val problem:ReadProblem?=null,val choice:QualifiedMemberReference?=null) {
    val invalidIdentifier get()=rawInput.isNotEmpty() && MemberReferenceIdentifier.parse(rawInput)==null
    val canRead get()=presented && !loading && MemberReferenceIdentifier.parse(rawInput)!=null
}
class MemberReferenceSession {
    var state=MemberReferenceState();private set
    private var pending:MemberReferenceTicket?=null;private var revision=0;private var visit=0;private var inputGeneration=0;private var sourceRevision=0
    val control get()=state.context?.let {MemberReferenceControl(it,visit)}
    val input get()=state.context?.let {if(state.presented)MemberReferenceInput(it,inputGeneration)else null}
    val canUse get()=state.presented && !state.loading && state.problem==null && sourceRevision>0 && state.source?.let {MemberReferenceIdentifier.parse(state.rawInput)==it.id && it.validFor(state.context?.business ?: 0,it.id) && it.isActive}==true
    private fun invalidate(){++revision;++visit;sourceRevision=0;pending=null;state=state.copy(loading=false,source=null,problem=null,choice=null)}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==state.context)return;hide();state=state.copy(context=next,rawInput="")}
    fun show(){if(state.context==null || state.presented)return;invalidate();++inputGeneration;state=state.copy(presented=true)}
    fun hide(){invalidate();++inputGeneration;state=state.copy(presented=false)}
    fun update(raw:String,input:MemberReferenceInput?){if(input==null || this.input!=input || raw==state.rawInput)return;invalidate();state=state.copy(rawInput=raw)}
    fun clear(expected:MemberReferenceControl?){if(expected==null || control!=expected || !state.presented)return;invalidate();++inputGeneration;state=state.copy(rawInput="")}
    fun begin(expected:MemberReferenceControl?):MemberReferenceTicket? {val c=state.context ?: return null;val id=MemberReferenceIdentifier.parse(state.rawInput) ?: return null;if(expected==null || control!=expected || !state.canRead)return null;invalidate();state=state.copy(loading=true);return MemberReferenceTicket(c,revision,state.rawInput,id).also {pending=it}}
    fun accept(source:TeamMemberReadSource,ticket:MemberReferenceTicket):Boolean {if(pending!=ticket || !state.presented || state.context!=ticket.context)return false;if(!source.validFor(ticket.context.business,ticket.id)){fail(ReadProblem.INVALID_PAYLOAD,ticket);return false};pending=null;sourceRevision=ticket.revision;state=state.copy(loading=false,problem=null,source=source);++visit;return true}
    fun fail(problem:ReadProblem,ticket:MemberReferenceTicket){if(pending!=ticket || !state.presented || state.context!=ticket.context)return;pending=null;sourceRevision=0;state=state.copy(loading=false,source=null,problem=problem,choice=null);++visit}
    fun cancel(ticket:MemberReferenceTicket){if(pending!=ticket)return;pending=null;sourceRevision=0;state=state.copy(loading=false,source=null,problem=null,choice=null);++visit}
    fun use(expected:MemberReferenceControl?){val c=state.context ?: return;val source=state.source ?: return;if(expected==null || control!=expected || !canUse)return;state=state.copy(choice=QualifiedMemberReference(c,sourceRevision,state.rawInput,source));++visit}
    fun clearChoice(expected:MemberReferenceControl?){if(expected==null || control!=expected || !state.presented || state.loading)return;state=state.copy(choice=null);++visit}
}
