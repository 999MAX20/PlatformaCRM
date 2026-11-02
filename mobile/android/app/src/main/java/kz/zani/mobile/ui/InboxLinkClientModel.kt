package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*

data class InboxLinkClientControl(val context:InboxConversationFilesContext,val visit:Int,val source:InboxLinkClientSource?,val editing:Boolean,val picker:ClientSearchControl?,val candidate:InboxLinkClientCandidate?,val review:InboxLinkClientReview?,val record:InboxLinkClientRecord?)
data class InboxLinkClientInput(val context:InboxConversationFilesContext,val editor:Int,val authorization:SyntheticInboxLinkClientAuthorization,val child:ClientSearchInputControl)
class InboxLinkClientModel(private val repository:InboxLinkClientRepository,clients:ClientSearchRepository?,private val port:SyntheticInboxLinkClientPort?,scope:CoroutineScope) {
    var context by mutableStateOf<InboxConversationFilesContext?>(null);private set
    var presented by mutableStateOf(false);private set
    var source by mutableStateOf<InboxLinkClientSource?>(null);private set
    var loading by mutableStateOf(false);private set
    var failure by mutableStateOf<ReadProblem?>(null);private set
    var editing by mutableStateOf(false);private set
    var candidate by mutableStateOf<InboxLinkClientCandidate?>(null);private set
    var review by mutableStateOf<InboxLinkClientReview?>(null);private set
    private val ledger=InboxLinkClientLedger();private var ledgerRevision by mutableStateOf(0);private var visit by mutableStateOf(0);private var generation=0;private var editor=0
    private var query="";private var queryOwner:SyntheticInboxLinkClientAuthorization?=null
    val picker=clients?.let {ClientSearchModel(it,scope)}
    var commandsBlocked:()->Boolean={true}
    private val authorization get()=context?.let {c->port?.grants?.mapNotNull {it.authorization(c)}?.firstOrNull()}
    val record get()=ledgerRevision.let {ledger.visible(authorization)}
    val retainedAttemptCount get()=ledgerRevision.let {ledger.records.size}
    fun blocks(business:Int,conversation:Int)=ledgerRevision.let {ledger.blocked(business,conversation)}
    val blocked get()=context?.let {blocks(it.business,it.conversation)} ?: false
    val ownsEditor get()=loading || editing || review!=null
    val control get()=context?.let {InboxLinkClientControl(it,visit,source,editing,picker?.control,candidate,review,record)}
    private val pending get()=ledgerRevision.let {context?.let {c->ledger.records.any {it.phase==InboxLinkClientPhase.PENDING && it.attempt.review.source.context.business==c.business && it.attempt.review.source.context.conversation==c.conversation}} ?: false}
    val canLoad get()=presented && !loading && !editing && review==null && !pending
    val canOpen get()=presented && !loading && failure==null && source!=null && source?.context==context && authorization!=null && picker!=null && !editing && review==null && !blocked && !commandsBlocked()
    val canEdit get()=presented && editing && review==null && !loading && !blocked && !commandsBlocked() && source?.context==context && authorization!=null
    val input get()=context?.let {c->val p=picker;val a=authorization;val child=p?.inputControl;if(canEdit && a!=null && p!=null && child!=null && !p.state.loading && p.state.profileSelection==null)InboxLinkClientInput(c,editor,a,child)else null}
    private val candidateCurrent:Boolean get() {val c=candidate ?: return false;val p=picker ?: return false;val profile=p.profile.state.detail ?: return false;return c.source==source && c.selected==p.state.profileSelection && c.read==p.profile.readSelection && c.rawQuery==p.state.query && p.profile.state.problem==null && TaskDraftClientChoice.make(profile,c.choice.business,c.choice.id)==c.choice}
    val canPrepare get()=canEdit && candidateCurrent && picker?.state?.loading==false && picker?.profile?.state?.loading==false
    val canSubmit get()=review?.let {r->presented && editing && !loading && !blocked && !commandsBlocked() && r.valid && candidateCurrent && r.source==source && r.authorization==authorization && r.candidate==candidate} ?: false
    private fun stash(){if(editing && picker!=null){query=picker.state.query;queryOwner=authorization}}
    fun hide(){stash();++generation;++editor;++visit;presented=false;source=null;loading=false;failure=null;editing=false;candidate=null;review=null;picker?.bind(null)}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==context)return;hide();context=next;query="";queryOwner=null}
    fun show(){if(context!=null){presented=true;++visit}}
    suspend fun load(expected:InboxLinkClientControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canLoad)return;val c=context ?: return;val ticket=++generation;++visit;source=null;candidate=null;failure=null;loading=true
        try{val s=repository.source(c);if(!currentCoroutineContext().isActive)throw CancellationException();if(ticket!=generation || context!=c || !presented)return;if(s.context!=c)throw ReadException(ReadProblem.INVALID_PAYLOAD);source=s;loading=false;++visit}catch(e:Exception){if(ticket!=generation || context!=c || !presented)return;source=null;loading=false;failure=if(e is CancellationException)null else (e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit}}
    fun open(expected:InboxLinkClientControl?){if(expected==null || control!=expected || !canOpen)return;val p=picker ?: return;val c=context ?: return;++editor;++visit;editing=true;candidate=null;val scope=ClientSearchContext(c.business,c.epoch);p.bind(null);p.bind(scope);p.open(scope);p.update(if(queryOwner==authorization)query else "",p.inputControl)}
    fun update(raw:String,input:InboxLinkClientInput?){if(input==null || this.input!=input)return;val p=picker ?: return;val before=p.state.query;p.update(raw,input.child);if(before!=p.state.query){candidate=null;query=p.state.query;queryOwner=authorization}}
    fun search(expected:InboxLinkClientControl?,child:ClientSearchControl?){if(expected==null || control!=expected || !canEdit)return;val p=picker ?: return;if(!p.matches(child))return;++visit;candidate=null;p.submit(child)}
    fun openClient(id:Int,expected:InboxLinkClientControl?,child:ClientSearchControl?){if(expected==null || control!=expected || !canEdit)return;val p=picker ?: return;if(!p.matches(child))return;++visit;candidate=null;p.openClient(id,child)}
    fun retryClient(expected:InboxLinkClientControl?,child:ClientSearchControl?){if(expected==null || control!=expected || !canEdit)return;val p=picker ?: return;if(!p.matches(child) || p.profile.state.loading)return;candidate=null;++visit;p.retryProfile(child)}
    fun backClient(expected:InboxLinkClientControl?,child:ClientSearchControl?){if(expected==null || control!=expected || !canEdit)return;val p=picker ?: return;if(!p.matches(child))return;p.backProfile(child);candidate=null;++visit}
    fun useClient(expected:InboxLinkClientControl?,child:ClientSearchControl?){if(expected==null || control!=expected || !canEdit || child==null)return;val s=source ?: return;val p=picker ?: return;val selected=p.state.profileSelection ?: return;val read=p.profile.readSelection ?: return;val profile=p.profile.state.detail ?: return;if(!p.matches(child) || selected!=child.profile || read!=child.read || p.profile.state.loading || p.profile.state.problem!=null)return;val value=InboxLinkClientCandidate.make(s,selected,read,p.state.query,profile) ?: return;candidate=value;stash();++visit}
    fun clearChoice(expected:InboxLinkClientControl?){if(expected!=null && control==expected && canEdit){candidate=null;++visit}}
    fun prepare(expected:InboxLinkClientControl?){if(expected==null || control!=expected || !canPrepare)return;val s=source ?: return;val c=candidate ?: return;val a=authorization ?: return;++visit;++editor;review=InboxLinkClientReview(s,a,c,visit)}
    fun back(expected:InboxLinkClientControl?){if(expected==null || control!=expected || blocked)return;if(review!=null){review=null;++editor}else{stash();editing=false;candidate=null;picker?.bind(null);++editor};++visit}
    suspend fun submit(expected:InboxLinkClientControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit)return;val r=review ?: return;val p=port ?: return;val a=ledger.begin(r) ?: return;stash();++visit;++editor;++ledgerRevision;review=null;editing=false;picker?.bind(null)
        val outcome=try{val value=p.execute(a);if(currentCoroutineContext().isActive)value else SyntheticInboxLinkClientOutcome.Unknown}catch(_:Exception){SyntheticInboxLinkClientOutcome.Unknown};ledger.complete(a,outcome);++ledgerRevision;if(context==a.review.source.context)++visit}
    fun acknowledge(record:InboxLinkClientRecord,expected:InboxLinkClientControl?){if(expected==null || control!=expected)return;val a=authorization ?: return;if(ledger.acknowledge(a,record)){if(record.phase==InboxLinkClientPhase.RESPONSE)source=null;candidate=null;review=null;++ledgerRevision;++visit}}
}
