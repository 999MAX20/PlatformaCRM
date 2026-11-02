package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.CancellationException
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AppointmentReferenceRepository

data class AppointmentLifecycleControl(val source:AppointmentLifecycleSource,val visit:Int,val review:AppointmentLifecycleReview?,val record:AppointmentLifecycleRecord?)
data class AppointmentRescheduleInputControl(val source:AppointmentLifecycleSource,val visit:Int)
class AppointmentLifecycleModel(private val port:SyntheticAppointmentLifecyclePort,private val references:AppointmentReferenceRepository?=null) {
    var source by mutableStateOf<AppointmentLifecycleSource?>(null);private set
    var review by mutableStateOf<AppointmentLifecycleReview?>(null);private set
    private val ledger=AppointmentLifecycleLedger();private var visit by mutableStateOf(0);private var inputVisit by mutableStateOf(0)
    var reschedulePresented by mutableStateOf(false);private set
    var rawStart by mutableStateOf("");private set
    var rawReason by mutableStateOf("");private set
    var resourceChoice by mutableStateOf<AppointmentRescheduleResource?>(null);private set
    var resourceLoading by mutableStateOf(false);private set
    var resourceFailure by mutableStateOf<ReadProblem?>(null);private set
    private fun authorization(action:AppointmentLifecycleAction)=source?.let {s->(port.grants.distinct().mapNotNull {it.authorization(s,action)}+port.terminalGrants.distinct().mapNotNull {it.authorization(s,action)}).singleOrNull()}
    val submission get()=AppointmentLifecycleAction.entries.firstNotNullOfOrNull {authorization(it)?.let {a->ledger.visible(a)}}
    val blocked get()=source?.let {ledger.blocked(it)} ?: false
    val canPresent get()=source?.valid==true && AppointmentLifecycleAction.entries.any {authorization(it)!=null}
    val control get()=source?.let {AppointmentLifecycleControl(it,visit,review,submission)}
    val retainedAttemptCount get()=ledger.records.size
    fun used(action:AppointmentLifecycleAction)=source?.let {ledger.used(it,action)} ?: false
    fun canPrepare(action:AppointmentLifecycleAction)=canPresent && authorization(action)!=null && !blocked && review==null && !reschedulePresented && !used(action) && (action!=AppointmentLifecycleAction.RESCHEDULE || source?.canReschedule==true)
    val editingReschedule get()=reschedulePresented && review==null && !blocked && !resourceLoading
    val inputControl get()=source?.takeIf {editingReschedule}?.let {AppointmentRescheduleInputControl(it,inputVisit)}
    val linkedResourceAvailable get()=references!=null && source?.linkedResourceID!=null
    val preparedReschedule get()=source?.takeIf {editingReschedule}?.let {s->resourceChoice?.let {AppointmentRescheduleInput.prepare(s,rawStart,rawReason,it)}}
    val canReviewReschedule get()=preparedReschedule!=null && authorization(AppointmentLifecycleAction.RESCHEDULE)!=null && !used(AppointmentLifecycleAction.RESCHEDULE)
    val timeInputValid get()=TaskSnoozeValue.parse(rawStart)?.let {it.microseconds%1000L==0L} ?: false
    fun bind(next:AppointmentLifecycleSource?) {
        val valid=next?.takeIf {it.valid};if(source==valid)return;source=valid;review=null;++visit;++inputVisit
        reschedulePresented=false;rawStart="";rawReason="";resourceChoice=null;resourceLoading=false;resourceFailure=null
    }
    fun prepare(action:AppointmentLifecycleAction,expected:AppointmentLifecycleControl?) {
        if(expected==null || control!=expected || !canPrepare(action))return;++visit
        if(action==AppointmentLifecycleAction.RESCHEDULE) {reschedulePresented=true;++inputVisit;resourceFailure=null}else review=AppointmentLifecycleReview(expected.source,action,visit)
    }
    fun setStart(value:String,expected:AppointmentRescheduleInputControl?) {if(expected==null || inputControl!=expected || value==rawStart)return;rawStart=value;++visit}
    fun setReason(value:String,expected:AppointmentRescheduleInputControl?) {if(expected==null || inputControl!=expected || value==rawReason)return;rawReason=value;++visit}
    fun chooseClear(expected:AppointmentLifecycleControl?) {if(expected==null || control!=expected || !editingReschedule)return;resourceChoice=AppointmentRescheduleResource.Clear;resourceFailure=null;++visit}
    suspend fun loadLinkedResource(expected:AppointmentLifecycleControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !editingReschedule)return
        val s=source ?: return;val id=s.linkedResourceID ?: return;val repository=references ?: return
        ++visit;++inputVisit;val ticket=visit;resourceLoading=true;resourceChoice=null;resourceFailure=null
        try {
            val value=repository.reference(AppointmentReferenceKind.RESOURCE,s.read.scope.business.id,id)
            if(!currentCoroutineContext().isActive)throw CancellationException()
            if(source!=s || visit!=ticket)return
            if(!value.validFor(s.read.scope.business.id,id))throw ReadException(ReadProblem.INVALID_PAYLOAD)
            resourceChoice=AppointmentRescheduleResource.Linked(value);resourceLoading=false;++visit;++inputVisit
        } catch(error:Exception) {
            if(source!=s || visit!=ticket)return;resourceLoading=false;resourceFailure=if(error is CancellationException)null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit;++inputVisit
        }
    }
    fun reviewReschedule(expected:AppointmentLifecycleControl?) {
        if(expected==null || control!=expected || !canReviewReschedule)return;val value=preparedReschedule ?: return;++visit;++inputVisit
        review=AppointmentLifecycleReview(expected.source,AppointmentLifecycleAction.RESCHEDULE,visit,value)
    }
    fun back(expected:AppointmentLifecycleControl?) {
        if(expected==null || control!=expected || blocked)return
        if(review!=null)review=null else if(reschedulePresented) {reschedulePresented=false;resourceLoading=false;resourceFailure=null}else return
        ++visit;++inputVisit
    }
    suspend fun submit(expected:AppointmentLifecycleControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected)return
        val r=review?.takeIf {it.source==source} ?: return;val a=authorization(r.action) ?: return;val attempt=ledger.begin(r,a) ?: return;++visit;++inputVisit
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticAppointmentLifecycleOutcome.Unknown}catch(_:Exception) {SyntheticAppointmentLifecycleOutcome.Unknown}
        ledger.complete(attempt,outcome);++visit
    }
    fun acknowledge(expected:AppointmentLifecycleControl?,record:AppointmentLifecycleRecord) {
        if(expected==null || control!=expected || submission!=record || !ledger.acknowledge(record))return;review=null;++visit;++inputVisit
        reschedulePresented=record.attempt.review.action==AppointmentLifecycleAction.RESCHEDULE && record.phase==AppointmentLifecyclePhase.REJECTED_FIXTURE
    }
}
