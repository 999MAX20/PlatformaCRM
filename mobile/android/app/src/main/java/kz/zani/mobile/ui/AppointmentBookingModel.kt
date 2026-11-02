package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.CancellationException
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientProfileRepository
import kz.zani.mobile.data.AppointmentReferenceRepository
import kz.zani.mobile.data.ServiceDirectoryRepository
import kz.zani.mobile.data.ResourceDirectoryRepository

enum class AppointmentBookingReadKind {CLIENT,SERVICE,RESOURCE}
data class AppointmentBookingControl(val source:AppointmentBookingSource,val visit:Int,val review:AppointmentBookingReview?,val record:AppointmentBookingRecord?)
data class AppointmentBookingInputControl(val source:AppointmentBookingSource,val visit:Int)
enum class AppointmentBookingDirectoryKind {SERVICE,RESOURCE}
data class AppointmentBookingDirectoryControl(val source:AppointmentBookingSource,val visit:Int,val kind:AppointmentBookingDirectoryKind,val authorization:SyntheticAppointmentBookingAuthorization,val service:ServiceDirectoryPresentation?,val resource:ResourceDirectoryPresentation?)
data class AppointmentBookingClientPickerOwner(val source:AppointmentBookingSource,val visit:Int,val authorization:SyntheticAppointmentBookingAuthorization,val selection:ClientSearchSelection)
class AppointmentBookingModel(private val port:SyntheticAppointmentBookingPort,private val clients:ClientProfileRepository?,private val references:AppointmentReferenceRepository?,services:ServiceDirectoryRepository?=null,resources:ResourceDirectoryRepository?=null,val clientChoices:ClientSearchModel?=null) {
    var clientPickerOwner by mutableStateOf<AppointmentBookingClientPickerOwner?>(null);private set
    var clientSelection by mutableStateOf<AppointmentBookingClientSelection?>(null);private set
    val serviceChoices=services?.let {ServiceDirectoryModel(it)}
    val resourceChoices=resources?.let {ResourceDirectoryModel(it)}
    var selector by mutableStateOf<AppointmentBookingDirectoryKind?>(null);private set
    var directory by mutableStateOf<AppointmentBookingDirectorySelection?>(null);private set
    private var selectorAuthorization:SyntheticAppointmentBookingAuthorization?=null
    var source by mutableStateOf<AppointmentBookingSource?>(null);private set
    var presented by mutableStateOf(false);private set
    var rawStart by mutableStateOf("");private set
    var client by mutableStateOf<TaskDraftClientChoice?>(null);private set
    var service by mutableStateOf<AppointmentReferenceDetail?>(null);private set
    var resource by mutableStateOf<AppointmentRescheduleResource?>(null);private set
    var loading by mutableStateOf<AppointmentBookingReadKind?>(null);private set
    var failure by mutableStateOf<ReadProblem?>(null);private set
    var review by mutableStateOf<AppointmentBookingReview?>(null);private set
    private var visit by mutableStateOf(0);private var inputVisit by mutableStateOf(0);private val ledger=AppointmentBookingLedger()
    private val authorization get()=source?.let {s->port.grants.distinct().mapNotNull {it.authorization(s)}.singleOrNull()}
    val submission get()=authorization?.let {ledger.visible(it)}
    val blocked get()=source?.let {ledger.blocked(it)} ?: false
    val used get()=source?.let {ledger.used(it)} ?: false
    val canPresent get()=source?.valid==true && clients!=null && references!=null && authorization!=null && (!used || blocked)
    val canOpen get()=canPresent && !presented && !blocked && !used
    val editing get()=presented && review==null && !blocked && loading==null && selector==null && clientPickerOwner==null
    val control get()=source?.let {AppointmentBookingControl(it,visit,review,submission)}
    val inputControl get()=source?.takeIf {editing}?.let {AppointmentBookingInputControl(it,inputVisit)}
    val retainedAttemptCount get()=ledger.records.size
    val linkedResourceAvailable get()=source?.resourceID!=null && references!=null
    val timeValid get()=TaskSnoozeValue.parse(rawStart)?.let {it.microseconds%1000L==0L} ?: false
    val prepared get():AppointmentBookingInput? {val s=source ?: return null;val c=client ?: return null;val v=service ?: return null;val r=resource ?: return null;return if(editing)AppointmentBookingInput.prepare(s,c,v,r,rawStart,directory,clientSelection)else null}
    val canReview get()=prepared!=null && authorization!=null && !used
    fun bind(next:AppointmentBookingSource?) {val valid=next?.takeIf {it.valid};if(source==valid)return;clearSelectors();directory=null;clientSelection=null;source=valid;presented=false;rawStart="";client=null;service=null;resource=null;loading=null;failure=null;review=null;++visit;++inputVisit}
    fun open(expected:AppointmentBookingControl?):Boolean {if(expected==null || control!=expected || !canOpen)return false;presented=true;failure=null;++visit;++inputVisit;return true}
    fun openCandidate(value:AppointmentBookingCandidateTime,expected:AppointmentBookingControl?):Boolean {if(!permitsCandidate(value) || !open(expected))return false;rawStart=value.rawStart;++visit;++inputVisit;return true}
    fun setStart(value:String,expected:AppointmentBookingInputControl?) {if(expected==null || inputControl!=expected || value==rawStart)return;rawStart=value;++visit}
    fun chooseClear(expected:AppointmentBookingControl?) {if(expected==null || control!=expected || !editing)return;resource=AppointmentRescheduleResource.Clear;directory=source?.let {AppointmentBookingDirectorySelection.make(it,directory?.service,null)};failure=null;++visit}
    suspend fun load(kind:AppointmentBookingReadKind,expected:AppointmentBookingControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || !editing)return
        val s=source ?: return;val clients=clients ?: return;val refs=references ?: return;if(kind==AppointmentBookingReadKind.RESOURCE && s.resourceID==null)return
        ++visit;++inputVisit;val ticket=visit;loading=kind;failure=null
        when(kind) {AppointmentBookingReadKind.CLIENT->{client=null;clientSelection=null};AppointmentBookingReadKind.SERVICE->{service=null;directory=AppointmentBookingDirectorySelection.make(s,null,directory?.resource)};AppointmentBookingReadKind.RESOURCE->{resource=null;directory=AppointmentBookingDirectorySelection.make(s,directory?.service,null)}}
        try {
            if(kind==AppointmentBookingReadKind.CLIENT) {
                val profile=clients.clientProfile(s.read.scope.business.id,s.clientID);if(!currentCoroutineContext().isActive)throw CancellationException();if(source!=s || visit!=ticket)return
                client=TaskDraftClientChoice.make(profile,s.read.scope.business.id,s.clientID) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)
            } else {
                val id=if(kind==AppointmentBookingReadKind.SERVICE)s.serviceID else s.resourceID!!;val value=refs.reference(if(kind==AppointmentBookingReadKind.SERVICE)AppointmentReferenceKind.SERVICE else AppointmentReferenceKind.RESOURCE,s.read.scope.business.id,id)
                if(!currentCoroutineContext().isActive)throw CancellationException();if(source!=s || visit!=ticket)return;if(!value.validFor(s.read.scope.business.id,id))throw ReadException(ReadProblem.INVALID_PAYLOAD)
                if(kind==AppointmentBookingReadKind.SERVICE)service=value else resource=AppointmentRescheduleResource.Linked(value)
            }
            loading=null;++visit;++inputVisit
        } catch(error:Exception) {if(source!=s || visit!=ticket)return;loading=null;failure=if(error is CancellationException)null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE;++visit;++inputVisit}
    }
    fun prepareReview(expected:AppointmentBookingControl?) {if(expected==null || control!=expected || !canReview)return;val input=prepared ?: return;++visit;++inputVisit;review=AppointmentBookingReview(expected.source,input,visit)}
    fun back(expected:AppointmentBookingControl?):Boolean {if(expected==null || control!=expected || blocked || !presented)return false;clientPickerOwner?.let {closeClientPicker(it);return false};if(selector!=null) {closeSelector(selectorControl);return false};val closed=review==null;if(closed) {clearSelectors();presented=false;loading=null;failure=null}else review=null;++visit;++inputVisit;return closed}
    suspend fun submit(expected:AppointmentBookingControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected)return;val r=review?.takeIf {it.source==source} ?: return;val a=authorization ?: return;val attempt=ledger.begin(r,a) ?: return;++visit;++inputVisit
        val outcome=try {val reply=port.execute(attempt);if(currentCoroutineContext().isActive)reply else SyntheticAppointmentBookingOutcome.Unknown}catch(_:Exception) {SyntheticAppointmentBookingOutcome.Unknown};ledger.complete(attempt,outcome);++visit
    }
    fun acknowledge(expected:AppointmentBookingControl?,record:AppointmentBookingRecord) {if(expected==null || control!=expected || submission!=record || !ledger.acknowledge(record))return;review=null;presented=record.phase==AppointmentBookingPhase.REJECTED_FIXTURE;++visit;++inputVisit}
    val selectorControl:AppointmentBookingDirectoryControl? get() {
        val source=source ?: return null;val kind=selector ?: return null;val auth=selectorAuthorization ?: return null;val s=serviceChoices?.presentation;val r=resourceChoices?.presentation
        if(if(kind==AppointmentBookingDirectoryKind.SERVICE)s==null || r!=null else r==null || s!=null)return null
        return AppointmentBookingDirectoryControl(source,visit,kind,auth,s,r)
    }
    fun matchesSelector(expected:AppointmentBookingDirectoryControl?)=expected!=null && selectorControl==expected && source==expected.source && presented
    private fun clearSelectors() {clientChoices?.bind(null);clientPickerOwner=null;serviceChoices?.bind(null);resourceChoices?.bind(null);selector=null;selectorAuthorization=null}
    suspend fun openSelector(kind:AppointmentBookingDirectoryKind,expected:AppointmentBookingControl?,serviceChild:ServiceDirectoryControl?,resourceChild:ResourceDirectoryControl?) {
        if(expected==null || control!=expected || !editing || !canPresent || used)return;val source=source ?: return;val auth=authorization ?: return
        if(kind==AppointmentBookingDirectoryKind.SERVICE) {val child=serviceChoices ?: return;if(child.control!=serviceChild)return} else {val child=resourceChoices ?: return;if(child.control!=resourceChild)return}
        clearSelectors();++visit;++inputVisit;failure=null;selectorAuthorization=auth
        if(kind==AppointmentBookingDirectoryKind.SERVICE) {val child=serviceChoices ?: return;child.bind(ServiceDirectoryOwner(source.read.scope,source.epoch));if(!child.open(child.control))return;selector=kind;child.reload(child.control)}
        else {val child=resourceChoices ?: return;child.bind(ResourceDirectoryOwner(source.read.scope,source.epoch));if(!child.open(child.control))return;selector=kind;child.reload(child.control)}
    }
    fun closeSelector(expected:AppointmentBookingDirectoryControl?) {if(!matchesSelector(expected))return;clearSelectors();++visit;++inputVisit}
    fun useService(choice:ServiceDirectoryReadChoice,child:ServiceDirectoryControl?,expected:AppointmentBookingDirectoryControl?) {
        val source=source ?: return;val model=serviceChoices ?: return
        if(!matchesSelector(expected) || expected?.kind!=AppointmentBookingDirectoryKind.SERVICE || authorization!=expected.authorization || blocked || used || review!=null || loading!=null || !model.matches(child) || model.choice!=choice || model.detail!=choice.item || model.selected!=choice.listed || choice.owner!=ServiceDirectoryOwner(source.read.scope,source.epoch))return
        val proof=AppointmentBookingDirectorySelection.make(source,choice.item,directory?.resource) ?: return;service=choice.item.reference;directory=proof;failure=null;closeSelector(expected)
    }
    fun useResource(choice:ResourceDirectoryReadChoice,child:ResourceDirectoryControl?,expected:AppointmentBookingDirectoryControl?) {
        val source=source ?: return;val model=resourceChoices ?: return
        if(!matchesSelector(expected) || expected?.kind!=AppointmentBookingDirectoryKind.RESOURCE || authorization!=expected.authorization || blocked || used || review!=null || loading!=null || !model.matches(child) || model.choice!=choice || model.detail!=choice.item || model.selected!=choice.listed || choice.owner!=ResourceDirectoryOwner(source.read.scope,source.epoch))return
        val proof=AppointmentBookingDirectorySelection.make(source,directory?.service,choice.item) ?: return;resource=AppointmentRescheduleResource.Linked(choice.item.reference);directory=proof;failure=null;closeSelector(expected)
    }
    fun matchesClientPicker(expected:AppointmentBookingClientPickerOwner?):Boolean {
        if(expected==null || clientPickerOwner!=expected || source!=expected.source || visit!=expected.visit || !presented || selector!=null || review!=null || loading!=null || blocked || used)return false
        return clientChoices?.state?.selection==expected.selection
    }
    fun openClientPicker(expected:AppointmentBookingControl?,child:ClientSearchControl?) {
        if(expected==null || control!=expected || !editing || !canPresent || used)return
        val source=source ?: return;val auth=authorization ?: return;val search=clientChoices ?: return;if(search.control!=child)return
        clearSelectors();++visit;++inputVisit;failure=null
        val context=ClientSearchContext(source.read.scope.business.id,source.epoch);search.bind(context);search.open(context)
        val selection=search.state.selection ?: return;clientPickerOwner=AppointmentBookingClientPickerOwner(source,visit,auth,selection)
    }
    fun closeClientPicker(expected:AppointmentBookingClientPickerOwner?) {if(!matchesClientPicker(expected))return;clearSelectors();++visit;++inputVisit}
    fun confirmClient(expected:AppointmentBookingClientPickerOwner?,control:ClientSearchControl?) {
        if(!matchesClientPicker(expected) || expected==null || authorization!=expected.authorization)return
        val search=clientChoices ?: return;val selected=search.state.profileSelection ?: return;val read=control?.read ?: return;val profile=search.profile.state.detail ?: return
        if(!search.matches(control) || control.selection!=expected.selection || !search.state.loaded || search.state.loading || search.state.problem!=null || selected!=control.profile || search.state.items.none {it.id==selected.id} || read!=search.profile.readSelection || search.profile.state.loading || search.profile.state.problem!=null)return
        val proof=AppointmentBookingClientSelection.make(expected.source,selected,read,search.state.query,profile) ?: return
        client=proof.choice;clientSelection=proof;failure=null;closeClientPicker(expected)
    }
    fun permitsCandidate(value:AppointmentBookingCandidateTime):Boolean {
        val source=source ?: return false;if(!value.validFor(source) || !canOpen)return false
        if(service!=null && service!=value.review.context.service)return false
        val candidate=value.review.context.resource;val selected=resource
        if(candidate!=null && selected!=null) {when(selected) {AppointmentRescheduleResource.Clear->return false;is AppointmentRescheduleResource.Linked->if(selected.detail!=candidate)return false}}
        return true
    }

}
