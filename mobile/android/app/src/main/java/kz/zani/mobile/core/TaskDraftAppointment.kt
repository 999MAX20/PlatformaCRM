package kz.zani.mobile.core

import java.time.LocalDate
import org.json.JSONObject

object TaskAppointmentDay {fun valid(raw:String)=Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}").matches(raw) && !raw.startsWith("0000") && runCatching {LocalDate.parse(raw).toString()==raw}.getOrDefault(false)}
// Manual Task relation only. No inferred Client/date, built-in follow-up or booking grant.
data class TaskDraftAppointmentChoice private constructor(val business:Int,val id:Int,val title:String?,val startAt:String?,val endAt:String?,val status:String) {
    fun validFor(business:Int)=business>0 && this.business==business && id>0
    companion object {fun make(detail:AppointmentDetail,business:Int,id:Int):TaskDraftAppointmentChoice?=if(business>0 && id>0 && detail.business==business && detail.appointment.id==id)TaskDraftAppointmentChoice(business,id,detail.appointment.title,detail.appointment.startAt,detail.appointment.endAt,detail.appointment.status) else null}
}
sealed interface TaskCreateAppointmentRead {
    data object Unknown:TaskCreateAppointmentRead
    data object NotSet:TaskCreateAppointmentRead
    data class Appointment(val id:Int):TaskCreateAppointmentRead
    fun matches(selected:Int?)=selected==null || (selected>0 && this==Appointment(selected))
    companion object {fun decode(raw:String):TaskCreateAppointmentRead=runCatching {
        val o=JSONObject(raw);if(!o.has("appointment"))return@runCatching Unknown;if(o.isNull("appointment"))return@runCatching NotSet
        val v=o.get("appointment");require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());Appointment(n.toInt())
    }.getOrDefault(Unknown)}
}

// Existing safe presentation categories only, never raw provider error details.
object TaskAppointmentReadFeedback {fun copyKey(problem:ReadProblem)=when(problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}}
