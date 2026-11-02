package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ServiceDirectoryRepository

data class ServiceDirectoryOwner(val scope:Selection,val epoch:Int)
data class ServiceDirectoryControl(val owner:ServiceDirectoryOwner,val visit:Int)
data class ServiceDirectoryPresentation(val owner:ServiceDirectoryOwner,val visit:Int)
data class ServiceDirectoryReadChoice(val owner:ServiceDirectoryOwner,val listVisit:Int,val detailVisit:Int,val listed:ServiceDirectoryItem,val item:ServiceDirectoryItem)
class ServiceDirectoryModel(private val repository:ServiceDirectoryRepository) {
    var owner by mutableStateOf<ServiceDirectoryOwner?>(null);private set
    var presented by mutableStateOf(false);private set
    var loading by mutableStateOf(false);private set
    var problem by mutableStateOf<ReadProblem?>(null);private set
    var window by mutableStateOf<ServiceDirectoryWindow?>(null);private set
    var selected by mutableStateOf<ServiceDirectoryItem?>(null);private set
    var detail by mutableStateOf<ServiceDirectoryItem?>(null);private set
    var choice by mutableStateOf<ServiceDirectoryReadChoice?>(null);private set
    private var visit by mutableStateOf(0)
    private var presentationVisit by mutableStateOf(0)
    private var listVisit=0
    val control get()=owner?.let {ServiceDirectoryControl(it,visit)}
    val presentation get()=owner?.takeIf {presented}?.let {ServiceDirectoryPresentation(it,presentationVisit)}
    fun matches(expected:ServiceDirectoryControl?)=expected!=null && control==expected
    fun matchesPresentation(expected:ServiceDirectoryPresentation?)=expected!=null && presentation==expected
    private fun clear() {loading=false;problem=null;window=null;selected=null;detail=null;choice=null}
    fun bind(next:ServiceDirectoryOwner?) {++visit;++presentationVisit;presented=false;owner=next;clear()}
    fun open(expected:ServiceDirectoryControl?):Boolean {if(!matches(expected) || owner==null || presented)return false;++visit;++presentationVisit;clear();presented=true;return true}
    fun close(expected:ServiceDirectoryPresentation?):Boolean {if(!matchesPresentation(expected))return false;++visit;++presentationVisit;presented=false;clear();return true}
    suspend fun reload(expected:ServiceDirectoryControl?) {
        val owner=owner ?: return;if(!matches(expected) || !presented || loading || selected!=null)return
        ++visit;clear();loading=true;val ticket=control
        try {val value=repository.services(owner.scope.business.id);if(!matches(ticket) || !presented)return
            if(value.business!=owner.scope.business.id || value.items.any {it.business!=value.business} || value.items.map {it.id}.toSet().size!=value.items.size)throw ReadException(ReadProblem.INVALID_PAYLOAD)
            window=value;listVisit=visit;loading=false
        } catch(error:Exception) {if(!matches(ticket) || !presented)return;window=null;loading=false;problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE}
    }
    suspend fun select(row:ServiceDirectoryItem,expected:ServiceDirectoryControl?) {
        val owner=owner ?: return;val window=window ?: return
        if(!matches(expected) || !presented || loading || selected!=null || window.business!=owner.scope.business.id || !window.items.contains(row))return
        ++visit;selected=row;detail=null;choice=null;problem=null;loading=true;val ticket=control
        try {val value=repository.service(owner.scope.business.id,row.id);if(!matches(ticket) || !presented)return
            if(value.business!=owner.scope.business.id || value.id!=row.id)throw ReadException(ReadProblem.INVALID_PAYLOAD);detail=value;loading=false
        } catch(error:Exception) {if(!matches(ticket) || !presented)return;detail=null;choice=null;loading=false;problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE}
    }
    fun backToWindow(expected:ServiceDirectoryControl?) {if(!matches(expected) || !presented || selected==null)return;++visit;selected=null;detail=null;choice=null;problem=null;loading=false}
    fun choose(expected:ServiceDirectoryControl?) {val owner=owner ?: return;val listed=selected ?: return;val item=detail ?: return;if(!matches(expected) || !presented || loading || problem!=null || choice!=null || item.business!=owner.scope.business.id || item.id!=listed.id)return;val value=ServiceDirectoryReadChoice(owner,listVisit,visit,listed,item);++visit;choice=value}
}
