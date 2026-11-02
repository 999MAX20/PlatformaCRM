package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*

data class InboxExistingClientControl(val context:InboxConversationFilesContext,val visit:Int,val source:InboxExistingClientSource?,val review:InboxExistingClientReview?,val record:InboxExistingClientRecord?)
class InboxExistingClientModel(private val repository:InboxExistingClientRepository,private val port:SyntheticInboxExistingClientPort?) {
    var context by mutableStateOf<InboxConversationFilesContext?>(null);private set
    var presented by mutableStateOf(false);private set
    var source by mutableStateOf<InboxExistingClientSource?>(null);private set
    var loading by mutableStateOf(false);private set
    var failure by mutableStateOf<ReadProblem?>(null);private set
    var review by mutableStateOf<InboxExistingClientReview?>(null);private set
    private val ledger=InboxExistingClientLedger();private var ledgerRevision by mutableStateOf(0);private var visit by mutableStateOf(0);private var generation=0
    var commandsBlocked:()->Boolean={true}
    private val authorization get()=context?.let {c->port?.grants?.mapNotNull {it.authorization(c)}?.firstOrNull()}
    val record get()=ledgerRevision.let {ledger.visible(authorization)}
    val retainedAttemptCount get()=ledgerRevision.let {ledger.records.size}
    fun blocks(business:Int,conversation:Int)=ledgerRevision.let {ledger.blocked(business,conversation)}
    val blocked get()=context?.let {blocks(it.business,it.conversation)} ?: false
    private val pending get()=ledgerRevision.let {context?.let {c->ledger.records.any {it.phase==InboxExistingClientPhase.PENDING && it.attempt.review.source.context.business==c.business && it.attempt.review.source.context.conversation==c.conversation}} ?: false}
    val ownsEditor get()=loading || review!=null || pending
    val control get()=context?.let {InboxExistingClientControl(it,visit,source,review,record)}
    val canLoad get()=presented && !loading && review==null && !pending
    private val existingClientEligible get()=source?.valid==true && (source?.client ?: 0)>0
    val canPrepare get()=presented && !loading && failure==null && source!=null && source?.context==context && authorization!=null && existingClientEligible && review==null && !blocked && !commandsBlocked()
    val canSubmit get()=review?.let {r->presented && !loading && failure==null && !blocked && !commandsBlocked() && r.valid && r.source==source && r.authorization==authorization} ?: false
    fun hide(){++generation;++visit;presented=false;source=null;loading=false;failure=null;review=null}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==context)return;hide();context=next}
    fun show(){if(context!=null){presented=true;++visit}}
    suspend fun load(expected:InboxExistingClientControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canLoad)return;val c=context ?: return;val ticket=++generation;++visit;loading=true;source=null;failure=null
        try {val s=repository.source(c);if(!currentCoroutineContext().isActive)throw CancellationException();if(ticket!=generation || context!=c || !presented)return;if(s.context!=c)throw ReadException(ReadProblem.INVALID_PAYLOAD);source=s;loading=false;++visit}catch(e:Exception){if(ticket!=generation || context!=c || !presented)return;loading=false;source=null;failure=if(e is CancellationException)null else (e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit}}
    fun prepare(expected:InboxExistingClientControl?){if(expected==null || control!=expected || !canPrepare)return;val s=source ?: return;val auth=authorization ?: return;++visit;review=InboxExistingClientReview(s,auth,visit)}
    fun back(expected:InboxExistingClientControl?){if(expected==null || control!=expected || review==null || blocked)return;review=null;++visit}
    suspend fun submit(expected:InboxExistingClientControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit)return;val r=review ?: return;val p=port ?: return;val a=ledger.begin(r) ?: return;review=null;++visit;++ledgerRevision
        val outcome=try {val value=p.execute(a);if(currentCoroutineContext().isActive)value else SyntheticInboxExistingClientOutcome.Unknown}catch(_:Exception){SyntheticInboxExistingClientOutcome.Unknown};ledger.complete(a,outcome);++ledgerRevision;if(context==a.review.source.context)++visit}
    fun acknowledge(record:InboxExistingClientRecord,expected:InboxExistingClientControl?){if(expected==null || control!=expected)return;val a=authorization ?: return;if(ledger.acknowledge(a,record)){if(record.phase==InboxExistingClientPhase.RESPONSE){source=null};review=null;++ledgerRevision;++visit}}
}
