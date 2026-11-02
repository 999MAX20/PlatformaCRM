package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*

data class InboxCreateTaskControl(val context:InboxConversationFilesContext,val visit:Int,val reader:InboxTaskSourceControl?,val review:InboxCreateTaskReview?,val record:InboxCreateTaskRecord?)
class InboxCreateTaskModel(val reader:InboxTaskSourceModel?,private val port:SyntheticInboxCreateTaskPort?) {
    var context by mutableStateOf<InboxConversationFilesContext?>(null);private set
    var presented by mutableStateOf(false);private set
    var review by mutableStateOf<InboxCreateTaskReview?>(null);private set
    private val ledger=InboxCreateTaskLedger();private var ledgerRevision by mutableStateOf(0);private var visit by mutableStateOf(0)
    var commandsBlocked:()->Boolean={true}
    init {reader?.controlsBlocked={review!=null || pending}}
    private val authorization get()=context?.let {c->port?.grants?.mapNotNull {it.authorization(c)}?.firstOrNull()}
    private val currentReference:QualifiedInboxTaskSource? get() {val c=context ?: return null;val s=reader?.state ?: return null;val choice=s.choice ?: return null;return choice.takeIf {s.presented && s.context==c && !s.loading && s.problem==null && reader?.canUse==true && choice.context==c && choice.valid && choice.source==s.source}}
    val source get()=currentReference?.source
    val record get()=ledgerRevision.let {ledger.visible(authorization)}
    val retainedAttemptCount get()=ledgerRevision.let {ledger.records.size}
    fun blocks(business:Int,conversation:Int)=ledgerRevision.let {ledger.blocked(business,conversation)}
    val blocked get()=context?.let {blocks(it.business,it.conversation)} ?: false
    private val pending get()=ledgerRevision.let {context?.let {c->ledger.records.any {it.phase==InboxCreateTaskPhase.PENDING && it.attempt.review.source.context.business==c.business && it.attempt.review.source.context.conversation==c.conversation}} ?: false}
    val ownsEditor get()=review!=null || pending
    val control get()=context?.let {InboxCreateTaskControl(it,visit,reader?.control,review,record)}
    val canPrepare get()=presented && review==null && authorization!=null && currentReference!=null && !blocked && !commandsBlocked()
    val canSubmit get()=review?.let {r->presented && !blocked && !commandsBlocked() && r.valid && r.authorization==authorization && r.reference==currentReference} ?: false
    fun hide(){++visit;presented=false;review=null}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==context)return;hide();context=next}
    fun show(){if(context!=null){presented=true;++visit}}
    fun prepare(expected:InboxCreateTaskControl?){if(expected==null || control!=expected || !canPrepare)return;val ref=currentReference ?: return;val auth=authorization ?: return;++visit;review=InboxCreateTaskReview(ref,auth,visit)}
    fun back(expected:InboxCreateTaskControl?){if(expected==null || control!=expected || review==null || blocked)return;review=null;++visit}
    suspend fun submit(expected:InboxCreateTaskControl?){if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmit)return;val r=review ?: return;val p=port ?: return;val a=ledger.begin(r) ?: return;review=null;++visit;++ledgerRevision
        val outcome=try {val value=p.execute(a);if(currentCoroutineContext().isActive)value else SyntheticInboxCreateTaskOutcome.Unknown}catch(_:Exception){SyntheticInboxCreateTaskOutcome.Unknown};ledger.complete(a,outcome);++ledgerRevision;if(context==a.review.source.context)++visit}
    fun acknowledge(record:InboxCreateTaskRecord,expected:InboxCreateTaskControl?){if(expected==null || control!=expected)return;val auth=authorization ?: return;if(ledger.acknowledge(auth,record)){if(record.phase==InboxCreateTaskPhase.RESPONSE){reader?.hide();reader?.show()};review=null;++ledgerRevision;++visit}}
}
