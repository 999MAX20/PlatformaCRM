package kz.zani.mobile.core

import org.json.JSONObject

// Independently scoped profile identity only, not a command grant or hidden relation proof.
data class TaskDraftClientChoice private constructor(val business:Int,val id:Int,val title:String?) {
    fun validFor(business:Int)=business>0 && this.business==business && id>0
    companion object {fun make(profile:ClientProfile,business:Int,id:Int):TaskDraftClientChoice?=if(business>0 && id>0 && profile.validFor(business,id))TaskDraftClientChoice(business,id,profile.client.title) else null}
}
// Existing generic action field client, explicitly separate from bounded GET client_id.
sealed interface TaskCreateClientRead {
    data object Unknown:TaskCreateClientRead
    data object NotSet:TaskCreateClientRead
    data class Client(val id:Int):TaskCreateClientRead
    fun matches(selected:Int?)=selected==null || (selected>0 && this==Client(selected))
    companion object {fun decode(raw:String):TaskCreateClientRead=runCatching {
        val o=JSONObject(raw)
        if(!o.has("client"))return@runCatching Unknown
        if(o.isNull("client"))return@runCatching NotSet
        val v=o.get("client");require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());Client(n.toInt())
    }.getOrDefault(Unknown)}
}
