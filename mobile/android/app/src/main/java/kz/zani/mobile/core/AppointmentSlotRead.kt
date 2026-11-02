package kz.zani.mobile.core

import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.Instant
import org.json.JSONArray
import org.json.JSONTokener

// Local read context only; no booking grant, reservation or reschedule command.
data class AppointmentSlotIntent private constructor(val business:Int,val service:Int,val resource:Int?,val day:String,val timezone:String) {
    val valid:Boolean get()=business>0 && service>0 && (resource==null || resource>0) && validDay(day) && runCatching {ZoneId.of(timezone)}.isSuccess
    val query:Map<String,String> get()=mutableMapOf("business_id" to business.toString(),"service_id" to service.toString(),"date" to day).also {q->resource?.let {q["resource_id"]=it.toString()}}
    companion object {
        fun validDay(raw:String)=Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}").matches(raw) && !raw.startsWith("0000") && runCatching {LocalDate.parse(raw).toString()==raw}.getOrDefault(false)
        fun make(business:Business,service:AppointmentReferenceDetail,resource:AppointmentReferenceDetail?,day:String):AppointmentSlotIntent?=runCatching {
            require(business.id>0 && service.validFor(business.id,service.id) && validDay(day));ZoneId.of(business.timezone)
            require(resource==null || resource.validFor(business.id,resource.id));AppointmentSlotIntent(business.id,service.id,resource?.id,day,business.timezone)
        }.getOrNull()
    }
}
data class AppointmentSlotCandidate(val startAt:String,val endAt:String) {
    companion object {fun instant(raw:String):Instant?=runCatching {
        require(Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})").matches(raw) && AppointmentSlotIntent.validDay(raw.take(10)) && !raw.endsWith("-00:00"))
        require(raw.substring(11,13).toInt()<24 && raw.substring(14,16).toInt()<60 && raw.substring(17,19).toInt()<60)
        OffsetDateTime.parse(raw).toInstant()
    }.getOrNull()}
}
data class AppointmentSlotRead(val intent:AppointmentSlotIntent,val candidates:List<AppointmentSlotCandidate>) {
    fun validFor(expected:AppointmentSlotIntent)=runCatching {require(expected.valid && intent==expected);val zone=ZoneId.of(expected.timezone);candidates.all {val a=AppointmentSlotCandidate.instant(it.startAt);val b=AppointmentSlotCandidate.instant(it.endAt);a!=null && b!=null && b>a && a.atZone(zone).toLocalDate().toString()==expected.day}}.getOrDefault(false)
    companion object {fun decode(raw:String,intent:AppointmentSlotIntent):AppointmentSlotRead?=runCatching {
        require(intent.valid)
        val token=JSONTokener(raw);val array=token.nextValue();require(array is JSONArray && token.nextClean()=='\u0000');val zone=ZoneId.of(intent.timezone)
        val candidates=(0 until array.length()).map {i->val o=array.getJSONObject(i);val start=o.get("start_at");val end=o.get("end_at");require(start is String && end is String)
            val a=AppointmentSlotCandidate.instant(start);val b=AppointmentSlotCandidate.instant(end);require(a!=null && b!=null && b>a && a.atZone(zone).toLocalDate().toString()==intent.day)
            AppointmentSlotCandidate(start,end)
        };AppointmentSlotRead(intent,candidates)
    }.getOrNull()}
}
