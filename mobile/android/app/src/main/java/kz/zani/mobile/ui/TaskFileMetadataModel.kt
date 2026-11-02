package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

data class TaskFileMetadataControl(val context:TaskFileMetadataContext,val visit:Int,val selected:TaskFileMetadata?)
class TaskFileMetadataModel(private val port:TaskFileMetadataPort,private val scope:CoroutineScope) {
    var context:TaskFileMetadataContext? by mutableStateOf(null);private set
    var items:List<TaskFileMetadata> by mutableStateOf(emptyList());private set
    var selected:TaskFileMetadata? by mutableStateOf(null);private set
    var loading by mutableStateOf(false);private set
    var loaded by mutableStateOf(false);private set
    var failed by mutableStateOf(false);private set
    private var visit by mutableStateOf(0);private var generation=0
    val control get()=context?.let {TaskFileMetadataControl(it,visit,selected)}
    fun bind(next:TaskFileMetadataContext?) {val next=next?.takeIf {it.valid};if(context==next)return;context=next;generation++;visit++;items=emptyList();selected=null;loading=false;loaded=false;failed=false}
    suspend fun load(expected:TaskFileMetadataControl?) {
        if(!currentCoroutineContext().isActive || expected==null || control!=expected || selected!=null || loading)return
        val ticket=++generation;visit++;items=emptyList();selected=null;loading=true;loaded=false;failed=false
        try {val body=port.read(expected.context);check(currentCoroutineContext().isActive);val rows=TaskFileMetadata.window(body,expected.context)
            if(generation!=ticket || context!=expected.context)return;items=rows;loaded=true;loading=false;visit++
        } catch(_:Exception) {if(generation!=ticket || context!=expected.context)return;items=emptyList();selected=null;loading=false;loaded=false;failed=true;visit++}
    }
    fun launchLoad(expected:TaskFileMetadataControl?) {scope.launch {load(expected)}}
    fun select(row:TaskFileMetadata,expected:TaskFileMetadataControl?) {if(expected==null || control!=expected || !loaded || loading || failed || selected!=null || row !in items)return;selected=row;visit++}
    fun back(expected:TaskFileMetadataControl?) {if(expected==null || control!=expected || selected==null)return;selected=null;visit++}
}
