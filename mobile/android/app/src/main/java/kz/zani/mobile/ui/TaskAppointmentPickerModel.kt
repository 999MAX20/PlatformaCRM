package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AgendaRepository

// Local read presentation only, no server version/booking key/CREATE grant.
data class TaskAppointmentPickerControl(val context:TaskDraftContext,val generation:Int)
// Input visit survives raw edits without relaxing read/choice generations.
data class TaskAppointmentPickerInputControl(val context:TaskDraftContext,val visit:Int)
data class TaskAppointmentPickerState(val context:TaskDraftContext?=null,val day:String="",val items:List<Appointment> = emptyList(),val total:Int=0,val loaded:Boolean=false,val loading:Boolean=false,val selectedID:Int?=null,val detail:AppointmentDetail?=null,val detailLoading:Boolean=false,val problem:ReadProblem?=null) {val partial get()=loaded && total>items.size}
class TaskAppointmentPickerModel(private val repository:AgendaRepository,private val ownerScope:CoroutineScope) {
    var state by mutableStateOf(TaskAppointmentPickerState());private set
    private var generation by mutableStateOf(0)
    private var inputVisit by mutableStateOf(0)
    val control:TaskAppointmentPickerControl? get()=state.context?.let {TaskAppointmentPickerControl(it,generation)}
    fun matches(expected:TaskAppointmentPickerControl?)=expected!=null && control==expected
    val inputControl get()=state.context?.takeIf {!state.loading && state.selectedID==null}?.let {TaskAppointmentPickerInputControl(it,inputVisit)}
    fun updateDay(raw:String,input:TaskAppointmentPickerInputControl?) {if(input==null || inputControl!=input)return;updateDay(raw,expected=control)}
    val canRead get()=state.context!=null && state.selectedID==null && !state.loading && TaskAppointmentDay.valid(state.day)
    fun begin(next:TaskDraftContext?) {++inputVisit;++generation;state=TaskAppointmentPickerState(context=next?.takeIf {it.valid})}
    fun updateDay(raw:String,expected:TaskAppointmentPickerControl?) {if(!matches(expected) || state.loading || state.selectedID!=null || state.day==raw)return;++generation;state=state.copy(day=raw,items=emptyList(),total=0,loaded=false,problem=null)}
    fun read(expected:TaskAppointmentPickerControl?) {
        if(!matches(expected) || !canRead)return
        val context=state.context ?: return;val raw=state.day;++inputVisit;val ticket=++generation;state=state.copy(loading=true,loaded=false,items=emptyList(),total=0,problem=null)
        ownerScope.launch {
            try {
                val page=repository.appointments(context.business,raw)
                currentCoroutineContext().ensureActive()
                if(ticket!=generation || state.context!=context)return@launch
                if(page.business!=context.business || page.date!=raw || page.items.size>50 || page.total<page.items.size || page.items.any {it.id<=0} || page.items.map {it.id}.distinct().size!=page.items.size)throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(items=page.items.toList(),total=page.total,loaded=true,loading=false)
            } catch(error:Exception) {
                if(ticket==generation && state.context==context)state=state.copy(loading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if(error is CancellationException){if(ticket==generation && state.context==context)++generation;throw error}
            }
            if(ticket==generation && state.context==context)++generation
        }
    }
    fun open(id:Int,expected:TaskAppointmentPickerControl?) {if(!matches(expected) || !state.loaded || state.loading || state.selectedID!=null || state.items.none {it.id==id})return;loadDetail(id)}
    private fun loadDetail(id:Int) {
        val context=state.context ?: return;++inputVisit;val ticket=++generation;state=state.copy(selectedID=id,detail=null,detailLoading=true,problem=null)
        ownerScope.launch {
            try {
                val value=repository.appointment(context.business,id)
                currentCoroutineContext().ensureActive()
                if(ticket!=generation || state.context!=context || state.selectedID!=id)return@launch
                if(TaskDraftAppointmentChoice.make(value,context.business,id)==null)throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(detail=value,detailLoading=false)
            } catch(error:Exception) {
                if(ticket==generation && state.context==context && state.selectedID==id)state=state.copy(detailLoading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if(error is CancellationException){if(ticket==generation && state.context==context)++generation;throw error}
            }
            if(ticket==generation && state.context==context)++generation
        }
    }
    fun retryDetail(expected:TaskAppointmentPickerControl?) {if(!matches(expected) || state.detailLoading)return;state.selectedID?.let {loadDetail(it)}}
    fun backDetail(expected:TaskAppointmentPickerControl?) {if(!matches(expected) || state.selectedID==null)return;++inputVisit;++generation;state=state.copy(selectedID=null,detail=null,detailLoading=false,problem=null)}
    fun choice(expected:TaskAppointmentPickerControl?):TaskDraftAppointmentChoice? {if(!matches(expected) || state.loading || state.detailLoading || state.problem!=null)return null;val context=state.context ?: return null;val id=state.selectedID ?: return null;val detail=state.detail ?: return null;return TaskDraftAppointmentChoice.make(detail,context.business,id)}
}
