package kz.zani.mobile.core

import org.json.JSONObject

// Existing bounded GET field only. Missing/malformed is not explicit null or UPDATE authority.
sealed interface TaskAppointmentOriginal {
    data object Unknown:TaskAppointmentOriginal
    data object NotSet:TaskAppointmentOriginal
    data class Appointment(val id:Int):TaskAppointmentOriginal
    val known:Boolean get()=this==NotSet || this is Appointment && id>0
    companion object {fun decode(raw:String):TaskAppointmentOriginal=runCatching {
        val fields=JSONObject(raw).getJSONObject("details");if(!fields.has("appointment_id"))return@runCatching Unknown;if(fields.isNull("appointment_id"))return@runCatching NotSet
        val v=fields.get("appointment_id");require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());Appointment(n.toInt())
    }.getOrDefault(Unknown)}
}
