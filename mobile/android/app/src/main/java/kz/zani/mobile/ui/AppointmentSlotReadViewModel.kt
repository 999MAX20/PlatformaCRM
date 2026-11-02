package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*

enum class AppointmentSlotResourceMode {UNSPECIFIED,LINKED}
data class AppointmentSlotControl(val owner:DetailSelection,val generation:Int)
data class AppointmentSlotInputControl(val owner:DetailSelection,val visit:Int)
data class AppointmentSlotState(val presented:Boolean=false,val day:String="",val resourceMode:AppointmentSlotResourceMode?=null,val loading:Boolean=false,val read:AppointmentSlotRead?=null,val problem:ReadProblem?=null,val context:AppointmentSlotReadContext?=null,val review:AppointmentSlotCandidateReview?=null)
class AppointmentSlotReadViewModel(private val repository:AppointmentSlotRepository?,private val references:AppointmentReferenceRepository?):ViewModel() {
    var state by mutableStateOf(AppointmentSlotState());private set
    private var owner:DetailSelection?=null;private var service:AppointmentReferenceDetail?=null;private var linkedID:Int?=null
    private var generation by mutableStateOf(0);private var inputVisit by mutableStateOf(0)
    fun bind(service:AppointmentReferenceDetail,owner:DetailSelection,linkedID:Int?) {
        clear();if(owner.revision<=0 || owner.scope.revision<=0 || !service.validFor(owner.scope.business.id,service.id))return
        this.owner=owner;this.service=service;this.linkedID=linkedID?.takeIf {it>0}
    }
    val presentation:AppointmentSlotControl? get()=owner?.let {AppointmentSlotControl(it,generation)}
    fun matches(expected:AppointmentSlotControl?)=expected!=null && presentation==expected
    val available get()=repository!=null && owner!=null && service!=null
    val inputControl get()=owner?.takeIf {editing}?.let {AppointmentSlotInputControl(it,inputVisit)}
    fun setDayInput(value:String,input:AppointmentSlotInputControl?) {if(input==null || inputControl!=input || value==state.day)return;++generation;state=state.copy(day=value)}
    val linkedResourceAvailable get()=references!=null && linkedID!=null
    val editing get()=state.presented && !state.loading && state.read==null && state.problem==null
    val canRead:Boolean get() {
        val owner=owner ?: return false;val service=service ?: return false;val mode=state.resourceMode ?: return false
        return editing && repository!=null && AppointmentSlotIntent.make(owner.scope.business,service,null,state.day)!=null && (mode==AppointmentSlotResourceMode.UNSPECIFIED || linkedResourceAvailable)
    }
    fun open(expected:AppointmentSlotControl?) {if(!matches(expected) || !available || state.presented)return;++generation;++inputVisit;state=AppointmentSlotState(presented=true)}
    fun setDay(value:String,expected:AppointmentSlotControl?) {if(!matches(expected) || !editing)return;++generation;state=state.copy(day=value)}
    fun choose(mode:AppointmentSlotResourceMode,expected:AppointmentSlotControl?) {if(!matches(expected) || !editing || (mode==AppointmentSlotResourceMode.LINKED && !linkedResourceAvailable))return;++generation;state=state.copy(resourceMode=mode)}
    fun edit(expected:AppointmentSlotControl?) {if(!matches(expected) || !state.presented || state.loading)return;++generation;++inputVisit;state=state.copy(read=null,problem=null,context=null,review=null)}
    fun close(expected:AppointmentSlotControl?) {if(!matches(expected) || !state.presented)return;reset()}
    private fun reset() {++generation;++inputVisit;state=AppointmentSlotState()}
    fun clear() {reset();owner=null;service=null;linkedID=null}
    fun retry(expected:AppointmentSlotControl?) {if(!matches(expected) || state.problem==null || state.loading)return;edit(expected);submit(presentation)}
    fun selectCandidate(index:Int,expected:AppointmentSlotControl?) {
        if(!matches(expected) || !state.presented || state.loading || state.problem!=null || state.review!=null)return
        val context=state.context ?: return;if(state.read!=context.read)return
        val selected=context.review(index) ?: return;++generation;state=state.copy(review=selected)
    }
    fun backToCandidates(expected:AppointmentSlotControl?) {
        if(!matches(expected) || state.loading)return
        val context=state.context ?: return;if(state.review?.validFor(context)!=true)return
        ++generation;state=state.copy(review=null)
    }
    fun refresh(expected:AppointmentSlotControl?) {
        if(!matches(expected) || !state.presented || state.loading || state.problem!=null || state.context==null)return
        edit(expected);submit(presentation)
    }
    fun submit(expected:AppointmentSlotControl?) {
        if(!matches(expected) || !canRead)return
        val repository=repository ?: return;val owner=owner ?: return;val service=service ?: return;val mode=state.resourceMode ?: return;val rawDay=state.day
        ++generation;++inputVisit;val ticket=generation;state=state.copy(loading=true)
        viewModelScope.launch {
            try {
                val resource=if(mode==AppointmentSlotResourceMode.LINKED) {
                    val references=references ?: throw ReadException(ReadProblem.INVALID_CONTEXT);val id=linkedID ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
                    val result=references.reference(AppointmentReferenceKind.RESOURCE,owner.scope.business.id,id)
                    if(ticket!=generation || this@AppointmentSlotReadViewModel.owner!=owner)return@launch
                    if(!result.validFor(owner.scope.business.id,id))throw ReadException(ReadProblem.INVALID_PAYLOAD)
                    result
                }else null
                val intent=AppointmentSlotIntent.make(owner.scope.business,service,resource,rawDay) ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
                val result=repository.slots(intent)
                if(ticket!=generation || this@AppointmentSlotReadViewModel.owner!=owner)return@launch
                if(!result.validFor(intent))throw ReadException(ReadProblem.INVALID_PAYLOAD)
                val context=AppointmentSlotReadContext.make(owner.scope.business,service,resource,result) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(read=context.read,context=context,review=null,loading=false)
            } catch(error:Exception) {
                if(ticket==generation && this@AppointmentSlotReadViewModel.owner==owner)state=state.copy(loading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if(error is CancellationException)throw error
            }
        }
    }
    override fun onCleared() {clear();super.onCleared()}
}
