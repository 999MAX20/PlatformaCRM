package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.CancellationException
import kz.zani.mobile.core.*
import kz.zani.mobile.data.InboxMessageFilesRepository

data class InboxMessageFilesOwner(val read:InboxConversationFilesContext,val limit:Int) {val valid get()=read.valid && limit in 1..300}
data class InboxMessageFilesControl(val owner:InboxMessageFilesOwner,val visit:Int,val context:InboxMessageFilesContext?,val selected:InboxMessageFileMetadata?)
data class InboxMessageFilesPresentation(val context:InboxMessageFilesContext,val visit:Int)
class InboxMessageFilesModel(private val repository:InboxMessageFilesRepository,private val retryPort:SyntheticInboxRetryPort?=null) {
    var owner by mutableStateOf<InboxMessageFilesOwner?>(null);private set
    var context by mutableStateOf<InboxMessageFilesContext?>(null);private set
    var presented by mutableStateOf(false);private set
    var window by mutableStateOf<InboxMessageFileWindow?>(null);private set
    var selected by mutableStateOf<InboxMessageFileMetadata?>(null);private set
    var loading by mutableStateOf(false);private set
    var failure by mutableStateOf<ReadProblem?>(null);private set
    private val retryLedger=InboxRetryLedger()
    private var retryRevision by mutableStateOf(0)
    var retryReview by mutableStateOf<InboxRetryReview?>(null);private set
    var commandsBlocked:()->Boolean={true}
    private val retryAuthorization get()=owner?.read?.let {read->val o=InboxRetryOwner(read.business,read.conversation,read.epoch);retryPort?.grants?.mapNotNull {it.authorization(o)}?.firstOrNull()}
    val retryRecord get()=retryRevision.let {retryLedger.visible(retryAuthorization)}
    val retainedRetryCount get()=retryRevision.let {retryLedger.records.size}
    fun blocksCommands(business:Int,conversation:Int)=retryRevision.let {retryLedger.blocked(business,conversation)}
    val retryBlocked get()=owner?.read?.let {blocksCommands(it.business,it.conversation)} ?: false
    val canPrepareRetry get()=presented && !loading && failure==null && selected==null && retryReview==null && !retryBlocked && !commandsBlocked() && retryAuthorization!=null && window?.retrySource?.eligible==true
    val canSubmitRetry get()=retryReview?.let {r->presented && !loading && selected==null && failure==null && !retryBlocked && !commandsBlocked() && r.valid && r.authorization==retryAuthorization && window?.retrySource==r.source && context==r.source.context} ?: false
    fun prepareRetry(expected:InboxMessageFilesControl?) {if(expected==null || control!=expected || !canPrepareRetry)return;val source=window?.retrySource ?: return;val auth=retryAuthorization ?: return;retryReview=InboxRetryReview(source,auth,++visit)}
    fun backRetry(expected:InboxMessageFilesControl?) {if(expected==null || control!=expected || retryReview==null || retryBlocked)return;retryReview=null;++visit}
    suspend fun submitRetry(review:InboxRetryReview,expected:InboxMessageFilesControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !canSubmitRetry || retryReview!=review)return;val port=retryPort ?: return;val attempt=retryLedger.begin(review) ?: return
        retryReview=null;++retryRevision;++visit
        val outcome=try {val value=port.execute(attempt);if(currentCoroutineContext().isActive)value else SyntheticInboxRetryOutcome.Unknown}catch(_:Exception){SyntheticInboxRetryOutcome.Unknown}
        retryLedger.complete(attempt,outcome);++retryRevision;++visit
    }
    fun acknowledgeRetry(record:InboxRetryRecord,expected:InboxMessageFilesControl?) {if(expected==null || control!=expected)return;val auth=retryAuthorization ?: return;if(retryLedger.acknowledge(auth,record)){++retryRevision;++visit}}
    private var visit by mutableStateOf(0);private var presentationVisit by mutableStateOf(0);private var generation=0
    val control get()=owner?.let {InboxMessageFilesControl(it,visit,context,selected)}
    val presentation get()=context?.takeIf {presented}?.let {InboxMessageFilesPresentation(it,presentationVisit)}
    private fun reset() {++generation;++visit;window=null;selected=null;loading=false;failure=null;retryReview=null}
    fun bind(next:InboxMessageFilesOwner?) {val next=next?.takeIf {it.valid};if(owner==next)return;reset();owner=next;context=null;presented=false;++presentationVisit}
    fun open(message:Int,expected:InboxMessageFilesControl?):Boolean {if(expected==null || control!=expected || presented)return false;val owner=owner ?: return false;val r=owner.read;val c=InboxMessageFilesContext(r.business,r.conversation,message,r.epoch,r.revision,owner.limit);if(!c.valid)return false;reset();context=c;presented=true;++presentationVisit;return true}
    private fun current(ticket:Int,c:InboxMessageFilesContext)=generation==ticket && context==c && presented
    suspend fun load(expected:InboxMessageFilesControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !presented || loading || selected!=null || retryReview!=null || retryRecord?.phase==InboxRetryPhase.PENDING)return;val c=context ?: return;reset();val ticket=generation;loading=true
        try {
            val anchor=repository.anchor(c);if(!currentCoroutineContext().isActive)throw CancellationException();if(!current(ticket,c))return;if(!anchor.matches(c))throw ReadException(ReadProblem.INVALID_PAYLOAD)
            val value=repository.messages(c,anchor);if(!currentCoroutineContext().isActive)throw CancellationException();if(!current(ticket,c))return;if(!value.validFor(c))throw ReadException(ReadProblem.INVALID_PAYLOAD)
            window=value;loading=false;++visit
        } catch(error:Exception) {if(!current(ticket,c))return;window=null;selected=null;loading=false;failure=if(error is CancellationException)null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit}
    }
    fun select(row:InboxMessageFileMetadata,expected:InboxMessageFilesControl?) {if(expected==null || control!=expected || !presented || loading || failure!=null || selected!=null || retryReview!=null || window?.items?.contains(row)!=true)return;selected=row;++visit}
    fun back(expected:InboxMessageFilesControl?) {if(expected==null || control!=expected || !presented || selected==null)return;selected=null;++visit}
    fun close(expected:InboxMessageFilesPresentation?) {if(expected==null || presentation!=expected)return;reset();context=null;presented=false;++presentationVisit}
}
