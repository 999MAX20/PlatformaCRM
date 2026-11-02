package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kz.zani.mobile.core.*
import kz.zani.mobile.data.TaskReadRepository

// Explicit existing Task list/detail presentation only, no lifecycle/CREATE authority.
data class TaskParentPickerControl(val context:TaskDraftContext,val generation:Int)
data class TaskParentPickerState(val context:TaskDraftContext?=null,val items:List<WorkTask> = emptyList(),val total:Int=0,val loaded:Boolean=false,val loading:Boolean=false,val selectedID:Int?=null,val detail:TaskDetails?=null,val detailLoading:Boolean=false,val problem:ReadProblem?=null) {val partial get()=loaded && total>items.size}
class TaskParentPickerModel(private val repository:TaskReadRepository,private val ownerScope:CoroutineScope) {
    var state by mutableStateOf(TaskParentPickerState());private set
    private var generation by mutableStateOf(0)
    val control:TaskParentPickerControl? get()=state.context?.let {TaskParentPickerControl(it,generation)}
    fun matches(expected:TaskParentPickerControl?)=expected!=null && control==expected
    val canRead get()=state.context!=null && state.selectedID==null && !state.loading
    fun begin(next:TaskDraftContext?) {++generation;state=TaskParentPickerState(context=next?.takeIf {it.valid})}
    fun read(expected:TaskParentPickerControl?) {
        if(!matches(expected) || !canRead)return
        val context=state.context ?: return;val ticket=++generation;state=state.copy(loading=true,loaded=false,items=emptyList(),total=0,problem=null)
        ownerScope.launch {
            try {
                val page=repository.tasks(context.business)
                currentCoroutineContext().ensureActive()
                if(ticket!=generation || state.context!=context)return@launch
                if(!page.validFor(context.business) || page.items.size>50 || page.items.any {it.id<=0} || page.items.map {it.id}.distinct().size!=page.items.size)throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(items=page.items.toList(),total=page.total,loaded=true,loading=false)
            } catch(error:Exception) {
                if(ticket==generation && state.context==context)state=state.copy(loading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if(error is CancellationException){if(ticket==generation && state.context==context)++generation;throw error}
            }
            if(ticket==generation && state.context==context)++generation
        }
    }
    fun open(id:Int,expected:TaskParentPickerControl?) {if(!matches(expected) || !state.loaded || state.loading || state.selectedID!=null || state.items.none {it.id==id})return;loadDetail(id)}
    private fun loadDetail(id:Int) {
        val context=state.context ?: return;val ticket=++generation;state=state.copy(selectedID=id,detail=null,detailLoading=true,problem=null)
        ownerScope.launch {
            try {
                val value=repository.taskDetails(context.business,id)
                currentCoroutineContext().ensureActive()
                if(ticket!=generation || state.context!=context || state.selectedID!=id)return@launch
                if(TaskDraftParentChoice.make(value,context.business,id)==null)throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(detail=value,detailLoading=false)
            } catch(error:Exception) {
                if(ticket==generation && state.context==context && state.selectedID==id)state=state.copy(detailLoading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if(error is CancellationException){if(ticket==generation && state.context==context)++generation;throw error}
            }
            if(ticket==generation && state.context==context)++generation
        }
    }
    fun retryDetail(expected:TaskParentPickerControl?) {if(!matches(expected) || state.detailLoading)return;state.selectedID?.let {loadDetail(it)}}
    fun backDetail(expected:TaskParentPickerControl?) {if(!matches(expected) || state.selectedID==null)return;++generation;state=state.copy(selectedID=null,detail=null,detailLoading=false,problem=null)}
    fun choice(expected:TaskParentPickerControl?):TaskDraftParentChoice? {if(!matches(expected) || state.loading || state.detailLoading || state.problem!=null)return null;val context=state.context ?: return null;val id=state.selectedID ?: return null;val detail=state.detail ?: return null;return TaskDraftParentChoice.make(detail,context.business,id)}
}
