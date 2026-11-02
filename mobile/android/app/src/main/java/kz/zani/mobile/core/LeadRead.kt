package kz.zani.mobile.core

// Exact bounded mobile _lead_item projection. No generic serializer aliases or authority.
data class LeadReadClient(val id:Int,val name:String,val phone:String,val email:String)
data class LeadReadItem(val id:Int,val client_id:Int,val title:String,val client:LeadReadClient,val status:String,val source:String,val message:String,val created_at:String) {val valid get()=id>0 && client_id>0 && client.id==client_id}
data class LeadReadPage(val business:Int,val limit:Int,val total:Int,val items:List<LeadReadItem>) {fun validFor(scope:Int)=scope>0 && business==scope && limit==50 && total>=items.size && items.size<=limit && items.all {it.valid} && items.map {it.id}.distinct().size==items.size}
data class LeadReadDetail(val business:Int,val lead:LeadReadItem,val message:String) {fun validFor(scope:Int,id:Int)=scope>0 && id>0 && business==scope && lead.id==id && lead.valid}
data class LeadReadControl(val context:InboxConversationFilesContext,val visit:Int)
data class LeadReadInput(val context:InboxConversationFilesContext,val generation:Int)
data class LeadReadTicket(val context:InboxConversationFilesContext,val revision:Int,val query:String,val id:Int?)
data class QualifiedLeadReference internal constructor(val context:InboxConversationFilesContext,val readRevision:Int,val rawQuery:String,val detail:LeadReadDetail)
data class LeadReadState(val context:InboxConversationFilesContext?=null,val presented:Boolean=false,val query:String="",val submitted:String?=null,val items:List<LeadReadItem> = emptyList(),val total:Int=0,val loaded:Boolean=false,val loading:Boolean=false,val problem:ReadProblem?=null,val selectedID:Int?=null,val detail:LeadReadDetail?=null,val choice:QualifiedLeadReference?=null) {
    val partial get()=loaded && total>items.size
    val showsEmpty get()=loaded && !loading && problem==null && items.isEmpty() && !partial
    val canUse get()=presented && !loading && problem==null && detail?.validFor(context?.business ?: 0,selectedID ?: 0)==true
}
class LeadReadSession {
    var state=LeadReadState();private set
    private var visit=0;private var revision=0;private var inputGeneration=0;private var pending:LeadReadTicket?=null
    val control get()=state.context?.let {LeadReadControl(it,visit)}
    val input get()=state.context?.let {if(state.presented && !state.loading && state.selectedID==null)LeadReadInput(it,inputGeneration)else null}
    private fun invalidate(){++visit;++revision;pending=null;state=state.copy(items=emptyList(),total=0,loaded=false,loading=false,problem=null,selectedID=null,detail=null,choice=null,submitted=null)}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==state.context)return;hide();state=state.copy(context=next,query="")}
    fun show(){if(state.context!=null && !state.presented){invalidate();++inputGeneration;state=state.copy(presented=true)}}
    fun hide(){invalidate();++inputGeneration;state=state.copy(presented=false)}
    fun update(value:String,input:LeadReadInput?){if(input==null || this.input!=input || value==state.query)return;invalidate();state=state.copy(query=value)}
    fun clear(expected:LeadReadControl?){if(expected==null || control!=expected || !state.presented || state.loading || state.selectedID!=null)return;invalidate();++inputGeneration;state=state.copy(query="")}
    fun beginList(expected:LeadReadControl?):LeadReadTicket? {val c=state.context ?: return null;if(expected==null || control!=expected || !state.presented || state.loading || state.selectedID!=null)return null;invalidate();++inputGeneration;val query=SourceTextTrim.pythonStrip(state.query);state=state.copy(loading=true,submitted=query);return LeadReadTicket(c,revision,query,null).also {pending=it}}
    fun accept(page:LeadReadPage,ticket:LeadReadTicket):Boolean {if(pending!=ticket || !state.presented || state.context!=ticket.context || ticket.id!=null)return false;if(!page.validFor(ticket.context.business)){fail(ReadProblem.INVALID_PAYLOAD,ticket);return false};pending=null;state=state.copy(items=page.items,total=page.total,loading=false,loaded=true,problem=null);++visit;return true}
    fun beginProfile(id:Int,expected:LeadReadControl?):LeadReadTicket? {val c=state.context ?: return null;if(expected==null || control!=expected || !state.presented || state.loading || !state.loaded || state.items.none {it.id==id} || (state.selectedID!=null && state.selectedID!=id))return null;++revision;++visit;++inputGeneration;state=state.copy(detail=null,choice=null,selectedID=id,loading=true,problem=null);return LeadReadTicket(c,revision,SourceTextTrim.pythonStrip(state.query),id).also {pending=it}}
    fun accept(profile:LeadReadDetail,ticket:LeadReadTicket):Boolean {val id=ticket.id ?: return false;if(pending!=ticket || !state.presented || state.context!=ticket.context || state.selectedID!=id)return false;if(!profile.validFor(ticket.context.business,id)){fail(ReadProblem.INVALID_PAYLOAD,ticket);return false};pending=null;state=state.copy(detail=profile,loading=false,problem=null);++visit;return true}
    fun fail(problem:ReadProblem,ticket:LeadReadTicket){if(pending!=ticket || !state.presented || state.context!=ticket.context)return;pending=null;state=state.copy(loading=false,problem=problem,detail=null,choice=null);++visit;if(ticket.id==null)state=state.copy(items=emptyList(),total=0,loaded=false)}
    fun cancel(ticket:LeadReadTicket){if(pending!=ticket)return;pending=null;state=state.copy(loading=false,detail=null,choice=null,problem=null);++visit;if(ticket.id==null)state=state.copy(items=emptyList(),total=0,loaded=false)}
    fun backProfile(expected:LeadReadControl?){if(expected==null || control!=expected || !state.presented || state.selectedID==null)return;++revision;++visit;++inputGeneration;pending=null;state=state.copy(loading=false,problem=null,selectedID=null,detail=null,choice=null)}
    fun use(expected:LeadReadControl?){val c=state.context ?: return;val detail=state.detail ?: return;if(expected==null || control!=expected || !state.canUse)return;state=state.copy(choice=QualifiedLeadReference(c,revision,state.query,detail));++visit}
    fun clearChoice(expected:LeadReadControl?){if(expected==null || control!=expected || !state.presented || state.loading)return;state=state.copy(choice=null);++visit}
}
