package kz.zani.mobile.core

import org.json.JSONObject

data class SyntheticAppointmentTerminalGrant(val business:Int,val appointment:Int,val actor:Int,val update:Boolean,val actions:List<AppointmentLifecycleAction>) {
    fun authorization(source:AppointmentLifecycleSource,action:AppointmentLifecycleAction):SyntheticAppointmentLifecycleAuthorization? {
        if(!source.valid || business!=source.read.scope.business.id || appointment!=source.read.id || actor<=0 || !update || !action.isGenericTerminal || action !in actions)return null
        return SyntheticAppointmentLifecycleAuthorization(business,appointment,source.epoch,actor,action,null)
    }
}
// Bounded plain AppointmentSerializer lens; provided updatedAt is not a lock/retry token.
data class AppointmentTerminalReceipt(val id:Int,val business:Int,val client:Int,val service:Int,val lead:Int?,val resource:Int?,val status:String,val startAt:String,val endAt:String,val createdAt:String,val updatedAt:String,val isArchived:Boolean,val raw:String) {
    fun matches(a:AppointmentLifecycleAttempt)=a.review.action.isGenericTerminal && a.authorization.key==null && id==a.authorization.appointment && business==a.authorization.business && status==a.review.action.expectedStatus
    companion object {
        fun decode(json:String):AppointmentTerminalReceipt?=runCatching {
            val o=JSONObject(json);require(listOf("ok","appointment","replayed").none {o.has(it)})
            fun integer(k:String):Int {val v=o.get(k);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1..Int.MAX_VALUE.toLong());return n.toInt()}
            fun nullableID(k:String):Int? {require(o.has(k));return if(o.isNull(k))null else integer(k)}
            fun text(k:String)=o.get(k) as? String ?: throw IllegalArgumentException()
            fun instant(k:String)=text(k).also {require(TaskSnoozeValue.parse(it)!=null)}
            AppointmentTerminalReceipt(integer("id"),integer("business"),integer("client"),integer("service"),nullableID("lead"),nullableID("resource"),text("status"),instant("start_at"),instant("end_at"),instant("created_at"),instant("updated_at"),o.get("is_archived") as? Boolean ?: throw IllegalArgumentException(),json)
        }.getOrNull()
    }
}
