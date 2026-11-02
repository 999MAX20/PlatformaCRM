package kz.zani.mobile.ui

import androidx.compose.runtime.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kz.zani.mobile.core.*

// Local catalog/selection/result visit only; never source version or command attempt.
data class ClientMergePreviewControl(val context:ClientMergePreviewContext,val visit:Int,val duplicate:Int?)
class ClientMergePreviewModel(private val source:SyntheticClientMergePreviewSource) {
    var context by mutableStateOf<ClientMergePreviewContext?>(null);private set
    var candidates by mutableStateOf<List<ClientMergeSnapshot>>(emptyList());private set
    var selected by mutableStateOf<Int?>(null);private set
    var result by mutableStateOf<ClientMergePreview?>(null);private set
    var loading by mutableStateOf(false);private set
    var catalogReady by mutableStateOf(false);private set
    var problem by mutableStateOf<ReadProblem?>(null);private set
    private var visit by mutableStateOf(0)
    val control get()=context?.let {ClientMergePreviewControl(it,visit,selected)}
    fun clear() {visit++;context=null;candidates=emptyList();selected=null;result=null;loading=false;catalogReady=false;problem=null}
    suspend fun open(next:ClientMergePreviewContext) {
        clear();if(!next.valid)return;context=next;val ticket=visit;loading=true
        try {
            val rows=source.candidates(next);currentCoroutineContext().ensureActive();if(ticket!=visit)return
            if(rows==null)throw ReadException(ReadProblem.UNAVAILABLE)
            if(rows.any {it.id<=0 || it.id==next.target} || rows.map {it.id}.distinct().size!=rows.size)throw ReadException(ReadProblem.INVALID_PAYLOAD)
            candidates=rows.toList();catalogReady=true;loading=false
        } catch(error:Exception) {if(ticket==visit) {loading=false;if(error !is CancellationException)problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE};if(error is CancellationException)throw error}
    }
    fun choose(id:Int,expected:ClientMergePreviewControl?) {
        if(expected==null || control!=expected || !catalogReady || candidates.none {it.id==id})return
        visit++;selected=id;result=null;problem=null;loading=false
    }
    suspend fun preview(expected:ClientMergePreviewControl?) {
        if(expected==null || control!=expected || loading || !catalogReady)return
        val id=selected?.takeIf {id->candidates.any {it.id==id}} ?: return
        val ticket=++visit;result=null;problem=null;loading=true
        try {
            val value=source.preview(expected.context,id);currentCoroutineContext().ensureActive();if(ticket!=visit)return
            if(value==null)throw ReadException(ReadProblem.UNAVAILABLE)
            if(!value.matches(expected.context,id) || value.duplicate!=candidates.firstOrNull {it.id==id})throw ReadException(ReadProblem.INVALID_PAYLOAD)
            result=value;loading=false
        } catch(error:Exception) {if(ticket==visit) {loading=false;if(error !is CancellationException)problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE};if(error is CancellationException)throw error}
    }
}
