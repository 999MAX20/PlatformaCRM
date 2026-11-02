package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.cancel
import kotlinx.coroutines.CancellationException
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AgendaRepository
import kz.zani.mobile.data.AppointmentReferenceRepository
import kz.zani.mobile.data.ClientProfileRepository
import kz.zani.mobile.data.ClientSearchRepository
import kz.zani.mobile.data.ServiceDirectoryRepository
import kz.zani.mobile.data.ResourceDirectoryRepository
import java.time.LocalDate
import java.time.ZoneId

// Existing read selections plus local presentation, not a wire version/grant.
data class AgendaControl(val selection:Selection?,val detail:DetailSelection?,val epoch:Int,val generation:Int,val mode:AgendaMode)

data class AppointmentLifecycleEntryControl(val parent:AgendaControl,val related:AppointmentRelationControl?)
data class AppointmentBookingEntryControl(val parent:AgendaControl,val related:AppointmentRelationControl?,val lifecycle:AppointmentLifecycleControl?)
data class AppointmentBookingCandidateControl(val parent:AgendaControl,val related:AppointmentRelationControl,val slot:AppointmentSlotControl,val review:AppointmentSlotCandidateReview,val booking:AppointmentBookingControl,val lifecycle:AppointmentLifecycleControl?,val time:AppointmentBookingCandidateTime)

data class AgendaUiState(val businesses: List<Business> = emptyList(), val selection: Selection? = null,
    val items: List<Appointment> = emptyList(), val detail: AppointmentDetail? = null,
    val loading: Boolean = false, val detailLoading: Boolean = false, val detailID: Int? = null,
    val problem: ReadProblem? = null, val detailProblem: ReadProblem? = null, val partial: Boolean = false,
    val responseDay: String? = null, val businessEpoch: Int = 0, val searchRevision: Int = 0, val mode: AgendaMode = AgendaMode.LIST) {
    val showsEmptyResult: Boolean
        get() = selection != null && !loading && problem == null && !partial && responseDay == selection.day && items.isEmpty()
}
class AgendaViewModel(
    private val repository: AgendaRepository,
    private val initialDay: (Business) -> String = { LocalDate.now(ZoneId.of(it.timezone)).toString() },
    val relations: AppointmentRelationsViewModel? = null,
    lifecyclePort:SyntheticAppointmentLifecyclePort?=null,
    lifecycleReferences:AppointmentReferenceRepository?=null,
    bookingPort:SyntheticAppointmentBookingPort?=null,
    bookingClients:ClientProfileRepository?=null,
    bookingReferences:AppointmentReferenceRepository?=null,
    serviceRepository:ServiceDirectoryRepository?=null,
    resourceRepository:ResourceDirectoryRepository?=null,
    bookingServices:ServiceDirectoryRepository?=null,
    bookingResources:ResourceDirectoryRepository?=null,
    bookingClientSearch:ClientSearchRepository?=null
) : ViewModel() {
    val resources=resourceRepository?.let {ResourceDirectoryModel(it)}
    val services=serviceRepository?.let {ServiceDirectoryModel(it)}
    val booking=bookingPort?.let {AppointmentBookingModel(it,bookingClients,bookingReferences,bookingServices,bookingResources,bookingClientSearch?.let {ClientSearchModel(it,viewModelScope)})}
    val lifecycle=lifecyclePort?.let {AppointmentLifecycleModel(it,lifecycleReferences)}
    private val session = AgendaSession()
    private var businessEpoch = 0
    private var searchRevision = 0
    private var presentationRevision by mutableStateOf(0)
    val control get()=AgendaControl(session.selection,session.detailSelection,businessEpoch,presentationRevision,state.mode)
    fun matches(expected:AgendaControl?)=expected!=null && control==expected
    var state by mutableStateOf(AgendaUiState()); private set
    private fun publish(loading: Boolean = false, problem: ReadProblem? = null) {
        state = AgendaUiState(session.businesses, session.selection, session.items, session.detail, loading = loading, problem = problem, partial = session.isPartial, responseDay = session.responseDay, businessEpoch = businessEpoch, searchRevision = searchRevision, mode = state.mode)
    }
    fun start() {
        if (state.businesses.isNotEmpty() || state.loading) return
        ++presentationRevision;state = state.copy(loading = true)
        viewModelScope.launch {
            try { val bootstrap = repository.bootstrap(); session.install(bootstrap); load(bootstrap.activeBusiness.id, initialDay(bootstrap.activeBusiness)) }
            catch (error: Exception) { publish(problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE); if (error is CancellationException) throw error }
        }
    }
    fun load(business: Int, day: String) {
        resources?.bind(null);services?.bind(null);booking?.bind(null);lifecycle?.bind(null);relations?.clear()
        val previousBusiness = session.selection?.business?.id
        val scope = try { session.begin(business, day) } catch (error: ReadException) { publish(problem = error.problem); return }
        if (previousBusiness != business) ++businessEpoch
        resources?.bind(resourceOwner);services?.bind(serviceOwner)
        ++presentationRevision;++searchRevision
        publish(loading = true)
        viewModelScope.launch {
            try { if (session.receive(repository.appointments(business, day), scope)) publish() }
            catch (error: Exception) { if (session.selection == scope) publish(problem = if (error is CancellationException) null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE); if (error is CancellationException) throw error }
        }
    }
    fun detail(id: Int) {
        resources?.bind(null);services?.bind(null);booking?.bind(null);lifecycle?.bind(null);relations?.clear()
        val scope = session.selection ?: return
        val request = try { session.beginDetail(id) } catch (error: ReadException) {
            state = state.copy(detail = null, detailID = id, detailLoading = false, detailProblem = error.problem); return
        }
        ++presentationRevision;state = state.copy(detail = null, detailID = id, detailLoading = true, detailProblem = null)
        viewModelScope.launch {
            try {
                val result = repository.appointment(scope.business.id, id)
                if (session.receive(result, request)) { state = state.copy(searchRevision = ++searchRevision, items = session.items, detail = session.detail, detailLoading = false); relations?.bind(result,request);lifecycle?.bind(lifecycleSource);booking?.bind(bookingSource) }
            } catch (error: Exception) { if (session.detailSelection == request) state = state.copy(detailLoading = false, detailProblem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE); if (error is CancellationException) throw error }
        }
    }
    fun setMode(mode: AgendaMode) { state = state.copy(mode = mode) }
    fun switchBusiness(id:Int,expected:AgendaControl?) {val scope=session.selection;if(matches(expected) && state.detailID==null && scope?.business?.id!=id && session.businesses.any {it.id==id})load(id,scope?.day ?: return)}
    fun changeDay(next:String,previous:String,expected:AgendaControl?) {val scope=session.selection;if(matches(expected) && state.detailID==null && scope!=null && scope.day==previous && next!=previous)load(scope.business.id,next)}
    fun setMode(next:AgendaMode,previous:AgendaMode,expected:AgendaControl?) {if(matches(expected) && session.selection!=null && state.detailID==null && state.mode==previous && next!=previous) {++presentationRevision;setMode(next)}}
    fun retryList(expected:AgendaControl?) {if(!matches(expected) || state.loading || state.detailID!=null)return;val scope=session.selection;if(scope!=null)load(scope.business.id,scope.day) else start()}
    fun openDetail(id:Int,expected:AgendaControl?) {if(matches(expected) && !state.loading && state.problem==null && state.detailID==null && state.items.any {it.id==id})detail(id)}
    fun retryDetail(expected:AgendaControl?) {val request=session.detailSelection;if(matches(expected) && !state.detailLoading && request!=null)detail(request.id)}
    fun back(expected:AgendaControl?) {if(matches(expected) && state.detailID!=null)back()}
    fun back() {booking?.bind(null);lifecycle?.bind(null);++presentationRevision;relations?.clear(); session.clearDetail();resources?.bind(resourceOwner);services?.bind(serviceOwner); state = state.copy(detail = null, detailID = null, detailProblem = null, detailLoading = false) }
    val lifecycleSource:AppointmentLifecycleSource? get() {
        val read=session.detailSelection ?: return null;val detail=session.detail ?: return null
        if(state.loading || state.detailLoading || state.detailProblem!=null || detail.business!=read.scope.business.id || detail.appointment.id!=read.id)return null
        return AppointmentLifecycleSource(read,businessEpoch,detail.appointment,detail.referenceID(AppointmentReferenceKind.RESOURCE))
    }
    val lifecycleEntryControl:AppointmentLifecycleEntryControl? get() {val source=lifecycleSource ?: return null;if(booking?.presented==true || lifecycle?.source!=source || relations?.state?.selected!=null)return null;return AppointmentLifecycleEntryControl(control,relations?.presentation)}
    fun matchesLifecycleEntry(expected:AppointmentLifecycleEntryControl?)=expected!=null && lifecycleEntryControl==expected
    fun prepareLifecycle(action:AppointmentLifecycleAction,entry:AppointmentLifecycleEntryControl?,child:AppointmentLifecycleControl?) {if(matchesLifecycleEntry(entry))lifecycle?.prepare(action,child)}
    val bookingSource:AppointmentBookingSource? get() {
        val read=session.detailSelection ?: return null;val detail=session.detail ?: return null
        if(state.loading || state.detailLoading || state.detailProblem!=null || detail.business!=read.scope.business.id || detail.appointment.id!=read.id)return null
        val client=detail.linkedClientID ?: return null;val service=detail.referenceID(AppointmentReferenceKind.SERVICE) ?: return null
        return AppointmentBookingSource(read,businessEpoch,client,service,detail.referenceID(AppointmentReferenceKind.RESOURCE))
    }
    val bookingEntryControl:AppointmentBookingEntryControl? get() {val booking=booking ?: return null;if(booking.source!=bookingSource || !booking.canPresent || relations?.state?.selected!=null || lifecycle?.review!=null || lifecycle?.reschedulePresented==true)return null;return AppointmentBookingEntryControl(control,relations?.presentation,lifecycle?.control)}
    fun matchesBookingEntry(expected:AppointmentBookingEntryControl?)=expected!=null && bookingEntryControl==expected
    fun openBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?) {if(matchesBookingEntry(entry) && booking?.open(child)==true)++presentationRevision}
    fun backBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?) {if(matchesBookingEntry(entry) && booking?.back(child)==true)++presentationRevision}
    fun acknowledgeBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?,record:AppointmentBookingRecord) {if(!matchesBookingEntry(entry))return;val booking=booking ?: return;if(booking.control!=child || booking.submission!=record)return;val before=booking.control;booking.acknowledge(child,record);if(before!=booking.control)++presentationRevision}
    fun bookingCandidateControl(parent:AgendaControl?,related:AppointmentRelationControl?,slot:AppointmentSlotControl?,review:AppointmentSlotCandidateReview):AppointmentBookingCandidateControl? {
        if(parent==null || !matches(parent))return null;val source=bookingSource ?: return null;val booking=booking ?: return null;val child=booking.control ?: return null;val links=relations ?: return null;val reference=links.state.reference ?: return null;val slots=links.slotReads;val state=slots.state
        if(booking.source!=source || !booking.canOpen || related==null || !links.matches(related) || links.state.request!=source.read || links.state.selected!=AppointmentRelatedTarget.Service(source.serviceID) || links.state.loading || links.state.problem!=null || !reference.validFor(source.read.scope.business.id,source.serviceID) || reference!=review.context.service || review.context.business!=source.read.scope.business || slot==null || !slots.matches(slot) || slot.owner!=source.read || !state.presented || state.loading || state.problem!=null || state.review!=review || state.context!=review.context || state.read!=review.context.read || !review.validFor(review.context) || lifecycle?.review!=null || lifecycle?.reschedulePresented==true)return null
        val time=AppointmentBookingCandidateTime.make(source,review) ?: return null;if(!booking.permitsCandidate(time))return null
        return AppointmentBookingCandidateControl(parent,related,slot,review,child,lifecycle?.control,time)
    }
    fun useBookingCandidate(expected:AppointmentBookingCandidateControl) {if(bookingCandidateControl(expected.parent,expected.related,expected.slot,expected.review)!=expected || booking?.openCandidate(expected.time,expected.booking)!=true)return;relations?.back(expected.related);++presentationRevision}
    val serviceOwner:ServiceDirectoryOwner? get()=session.selection?.takeIf {session.detailSelection==null}?.let {ServiceDirectoryOwner(it,businessEpoch)}
    val serviceEntry:AgendaControl? get()=services?.takeIf {resources?.presented!=true && serviceOwner!=null && it.owner==serviceOwner && !it.presented}?.let {control}
    fun openServices(expected:AgendaControl?,child:ServiceDirectoryControl?) {if(expected==null || serviceEntry!=expected || !matches(expected) || services?.open(child)!=true)return;++presentationRevision;val ticket=services.control;viewModelScope.launch {services.reload(ticket)}}
    fun closeServices(expected:ServiceDirectoryPresentation?) {if(services?.close(expected)==true)++presentationRevision}
    val resourceOwner:ResourceDirectoryOwner? get()=session.selection?.takeIf {session.detailSelection==null}?.let {ResourceDirectoryOwner(it,businessEpoch)}
    val resourceEntry:AgendaControl? get()=resources?.takeIf {services?.presented!=true && resourceOwner!=null && it.owner==resourceOwner && !it.presented}?.let {control}
    fun openResources(expected:AgendaControl?,child:ResourceDirectoryControl?) {if(expected==null || resourceEntry!=expected || !matches(expected) || resources?.open(child)!=true)return;++presentationRevision;val ticket=resources.control;viewModelScope.launch {resources.reload(ticket)}}
    fun closeResources(expected:ResourceDirectoryPresentation?) {if(resources?.close(expected)==true)++presentationRevision}
    override fun onCleared() { relations?.clear(); relations?.profile?.viewModelScope?.cancel(); relations?.viewModelScope?.cancel(); super.onCleared() }
}
