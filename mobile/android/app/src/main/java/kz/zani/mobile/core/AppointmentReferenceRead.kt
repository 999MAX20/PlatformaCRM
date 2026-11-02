package kz.zani.mobile.core

import org.json.JSONObject

enum class AppointmentReferenceKind {SERVICE,RESOURCE
    fun path(id:Int):String?=if(id>0)"/api/${if(this==SERVICE)"services" else "resources"}/$id/" else null
}
data class AppointmentReferenceDetail(val id:Int,val business:Int,val name:String,val isActive:Boolean?,val resourceType:String?) {
    companion object {fun decode(body:String,kind:AppointmentReferenceKind):AppointmentReferenceDetail?=runCatching {
        val o=JSONObject(body)
        fun integer(key:String):Int {val v=o.get(key);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        val name=o.get("name");require(name is String);AppointmentReferenceDetail(integer("id"),integer("business"),name,o.opt("is_active") as? Boolean,if(kind==AppointmentReferenceKind.RESOURCE)o.opt("resource_type") as? String else null)
    }.getOrNull()}
    fun validFor(business:Int,id:Int)=business>0 && id>0 && this.business==business && this.id==id
    val activityCopyKey get()=when(isActive){true->"referenceActive";false->"referenceInactive";null->"referenceActivityUnknown"}
    val resourceTypeCopyKey get()=when(resourceType){"staff"->"referenceTypeStaff";"room"->"referenceTypeRoom";"hall"->"referenceTypeHall";"box"->"referenceTypeBox";"equipment"->"referenceTypeEquipment";"other"->"referenceTypeOther";else->"notAvailable"}
}
fun AppointmentDetail.referenceID(kind:AppointmentReferenceKind):Int?=(if(kind==AppointmentReferenceKind.SERVICE)service?.id else resource?.id)?.takeIf {it>0}
