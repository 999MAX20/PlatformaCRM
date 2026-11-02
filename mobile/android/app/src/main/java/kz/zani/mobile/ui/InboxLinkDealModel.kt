package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*

data class InboxLinkDealControl(val context:InboxConversationFilesContext,val visit:Int,val source:InboxLinkDealSource?,val picker:DealReferenceControl?,val review:InboxLinkDealReview?,val record:InboxLinkDealRecord?)
class InboxLinkDealModel(private val repository:InboxLinkDealRepository,val picker:DealReferenceModel?,private val port:SyntheticInboxLinkDealPort?) {
    var context by mutableStateOf<InboxConversationFilesContext?>(null);private set
    var presented by mutableStateOf(false);private set
    var source by mutableStateOf<InboxLinkDealSource?>(null);private set
    var loading by mutableStateOf(false);private set
    var failure by mutableStateOf<ReadProblem?>(null);private set
    var review by mutableStateOf<InboxLinkDealReview?>(null);private set
    private val ledger=InboxLinkDealLedger();private var ledgerRevision by mutableStateOf(0);private var visit by mutableStateOf(0);private var generation=0
    var commandsBlocked:()->Boolean={true}
    init {picker?.controlsBlocked={review!=null || pending}}
    private val authorization get()=context?.let {c->port?.grants?.mapNotNull {it.authorization(c)}?.firstOrNull()}
    val record get()=ledgerRevision.let {ledger.visible(authorization)}
    val retainedAttemptCount get()=ledgerRevision.let {ledger.records.size}
    fun blocks(business:Int,conversation:Int)=ledgerRevision.let {ledger.blocked(business,conversation)}
    val blocked get()=context?.let {blocks(it.business,it.conversation)} ?: false
    private val pending get()=ledgerRevision.let {context?.let {c->ledger.records.any {it.phase==InboxLinkDealPhase.PENDING && it.attempt.review.source.context.business==c.business && it.attempt.review.source.context.conversation==c.conversation}} ?: false}
    val ownsEditor get()=loading || review!=null
    val control get()=context?.let {InboxLinkDealControl(it,visit,source,picker?.control,review,record)}
    private val currentReference:QualifiedDealReference? get() {val c=context ?: return null;val s=picker?.state ?: return null;val choice=s.choice ?: return null;return choice.takeIf {s.presented && s.context==c && !s.loading && s.problem==null && picker?.canUse==true && choice.context==c && choice.valid && choice.source==s.source && choice.rawInput==s.rawInput}}
    val canLoad get()=presented && !loading && review==null && !pending
    val canPrepare get()=presented && !loading && failure==null && source!=null && source?.context==context && authorization!=null && currentReference!=null && review==null && !blocked && !commandsBlocked()
    val canSubmit get()=review?.let {r->presented && !loading && failure==null && !blocked && !commandsBlocked() && r.valid && r.source==source && r.authorization==authorization && r.candidate.reference==currentReference} ?: false
    fun hide(){++generation;++visit;presented=false;source=null;loading=false;failure=null;review=null}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==context)return;hide();context=next}
    fun show(){if(context!=null){presented=true;++visit}}
    suspend fun load(expected:InboxLinkDealControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canLoad)return;val c=context ?: return;val ticket=++generation;++visit;loading=true;source=null;failure=null
        try {val s=repository.source(c);if(!currentCoroutineContext().isActive)throw CancellationException();if(ticket!=generation || context!=c || !presented)return;if(s.context!=c)throw ReadException(ReadProblem.INVALID_PAYLOAD);source=s;loading=false;++visit}catch(e:Exception){if(ticket!=generation || context!=c || !presented)return;loading=false;source=null;failure=if(e is CancellationException)null else (e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit}}
    fun prepare(expected:InboxLinkDealControl?){if(expected==null || control!=expected || !canPrepare)return;val s=source ?: return;val ref=currentReference ?: return;val a=authorization ?: return;val candidate=InboxLinkDealCandidate.make(s,ref) ?: return;++visit;review=InboxLinkDealReview(s,a,candidate,visit)}
    fun back(expected:InboxLinkDealControl?){if(expected==null || control!=expected || review==null || blocked)return;review=null;++visit}
    suspend fun submit(expected:InboxLinkDealControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit)return;val r=review ?: return;val p=port ?: return;val a=ledger.begin(r) ?: return;review=null;++visit;++ledgerRevision
        val outcome=try {val value=p.execute(a);if(currentCoroutineContext().isActive)value else SyntheticInboxLinkDealOutcome.Unknown}catch(_:Exception){SyntheticInboxLinkDealOutcome.Unknown};ledger.complete(a,outcome);++ledgerRevision;if(context==a.review.source.context)++visit}
    fun acknowledge(record:InboxLinkDealRecord,expected:InboxLinkDealControl?){if(expected==null || control!=expected)return;val a=authorization ?: return;if(ledger.acknowledge(a,record)){if(record.phase==InboxLinkDealPhase.RESPONSE){source=null;picker?.hide();picker?.show()};review=null;++ledgerRevision;++visit}}
}
