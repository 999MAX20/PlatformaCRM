package kz.zani.mobile.core

import org.json.JSONObject

// Existing bounded GET field only. Missing/malformed is not explicit null or UPDATE authority.
sealed interface TaskClientOriginal {
    data object Unknown:TaskClientOriginal
    data object NotSet:TaskClientOriginal
    data class Client(val id:Int):TaskClientOriginal
    val known:Boolean get()=this==NotSet || this is Client && id>0
    companion object {fun decode(raw:String):TaskClientOriginal=runCatching {
        val fields=JSONObject(raw).getJSONObject("task");if(!fields.has("client_id"))return@runCatching Unknown;if(fields.isNull("client_id"))return@runCatching NotSet
        val v=fields.get("client_id");require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());Client(n.toInt())
    }.getOrDefault(Unknown)}
}
