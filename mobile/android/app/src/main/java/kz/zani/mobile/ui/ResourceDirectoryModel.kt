package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ResourceDirectoryRepository

data class ResourceDirectoryOwner(val scope:Selection,val epoch:Int)
data class ResourceDirectoryControl(val owner:ResourceDirectoryOwner,val visit:Int)
data class ResourceDirectoryPresentation(val owner:ResourceDirectoryOwner,val visit:Int)
data class ResourceDirectoryReadChoice(val owner:ResourceDirectoryOwner,val listVisit:Int,val detailVisit:Int,val listed:ResourceDirectoryItem,val item:ResourceDirectoryItem)
class ResourceDirectoryModel(private val repository:ResourceDirectoryRepository) {
    var owner by mutableStateOf<ResourceDirectoryOwner?>(null);private set
    var presented by mutableStateOf(false);private set
    var loading by mutableStateOf(false);private set
    var problem by mutableStateOf<ReadProblem?>(null);private set
    var window by mutableStateOf<ResourceDirectoryWindow?>(null);private set
    var selected by mutableStateOf<ResourceDirectoryItem?>(null);private set
    var detail by mutableStateOf<ResourceDirectoryItem?>(null);private set
    var choice by mutableStateOf<ResourceDirectoryReadChoice?>(null);private set
    private var visit by mutableStateOf(0)
    private var presentationVisit by mutableStateOf(0)
    private var listVisit=0
    val control get()=owner?.let {ResourceDirectoryControl(it,visit)}
    val presentation get()=owner?.takeIf {presented}?.let {ResourceDirectoryPresentation(it,presentationVisit)}
    fun matches(expected:ResourceDirectoryControl?)=expected!=null && control==expected
    fun matchesPresentation(expected:ResourceDirectoryPresentation?)=expected!=null && presentation==expected
    private fun clear() {loading=false;problem=null;window=null;selected=null;detail=null;choice=null}
    fun bind(next:ResourceDirectoryOwner?) {++visit;++presentationVisit;presented=false;owner=next;clear()}
    fun open(expected:ResourceDirectoryControl?):Boolean {if(!matches(expected) || owner==null || presented)return false;++visit;++presentationVisit;clear();presented=true;return true}
    fun close(expected:ResourceDirectoryPresentation?):Boolean {if(!matchesPresentation(expected))return false;++visit;++presentationVisit;presented=false;clear();return true}
    suspend fun reload(expected:ResourceDirectoryControl?) {
        val owner=owner ?: return;if(!matches(expected) || !presented || loading || selected!=null)return
        ++visit;clear();loading=true;val ticket=control
        try {val value=repository.resources(owner.scope.business.id);if(!matches(ticket) || !presented)return
            if(value.business!=owner.scope.business.id || value.items.any {it.business!=value.business} || value.items.map {it.id}.toSet().size!=value.items.size)throw ReadException(ReadProblem.INVALID_PAYLOAD)
            window=value;listVisit=visit;loading=false
        } catch(error:Exception) {if(!matches(ticket) || !presented)return;window=null;loading=false;problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE}
    }
    suspend fun select(row:ResourceDirectoryItem,expected:ResourceDirectoryControl?) {
        val owner=owner ?: return;val window=window ?: return
        if(!matches(expected) || !presented || loading || selected!=null || window.business!=owner.scope.business.id || !window.items.contains(row))return
        ++visit;selected=row;detail=null;choice=null;problem=null;loading=true;val ticket=control
        try {val value=repository.resource(owner.scope.business.id,row.id);if(!matches(ticket) || !presented)return
            if(value.business!=owner.scope.business.id || value.id!=row.id)throw ReadException(ReadProblem.INVALID_PAYLOAD);detail=value;loading=false
        } catch(error:Exception) {if(!matches(ticket) || !presented)return;detail=null;choice=null;loading=false;problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE}
    }
    fun backToWindow(expected:ResourceDirectoryControl?) {if(!matches(expected) || !presented || selected==null)return;++visit;selected=null;detail=null;choice=null;problem=null;loading=false}
    fun choose(expected:ResourceDirectoryControl?) {val owner=owner ?: return;val listed=selected ?: return;val item=detail ?: return;if(!matches(expected) || !presented || loading || problem!=null || choice!=null || item.business!=owner.scope.business.id || item.id!=listed.id)return;val value=ResourceDirectoryReadChoice(owner,listVisit,visit,listed,item);++visit;choice=value}
}
