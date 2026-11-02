package kz.zani.mobile.core

import org.json.JSONObject

// Existing ServiceSerializer fields, no inferred write authority, currency or eligibility defaults.
data class ServiceDirectoryItem(val id:Int,val business:Int,val name:String,val description:String,val durationMinutes:Int,val priceFrom:String?,val isActive:Boolean,val createdAt:String,val updatedAt:String) {
    val reference get()=AppointmentReferenceDetail(id,business,name,isActive,null)
    companion object {
        internal fun item(value:Any?):ServiceDirectoryItem?=runCatching {
            require(value is JSONObject)
            fun text(key:String):String {val v=value.get(key);require(v is String);return v}
            val id=directoryReadInteger(value.opt("id"));val business=directoryReadInteger(value.opt("business"));val duration=directoryReadInteger(value.opt("duration_minutes"))
            require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && business!=null && business in 1L..Int.MAX_VALUE.toLong() && duration!=null && duration in 0L..Int.MAX_VALUE.toLong())
            require(value.has("price_from"));val price=if(value.isNull("price_from"))null else text("price_from")
            val active=value.get("is_active");require(active is Boolean)
            val created=text("created_at");val updated=text("updated_at");require(TaskSnoozeValue.parse(created)!=null && TaskSnoozeValue.parse(updated)!=null)
            ServiceDirectoryItem(id.toInt(),business.toInt(),text("name"),text("description"),duration.toInt(),price,active,created,updated)
        }.getOrNull()
        fun decode(body:String):ServiceDirectoryItem?=runCatching {item(JSONObject(body))}.getOrNull()
    }
}
typealias ServiceDirectoryLinkPresence=DirectoryReadLinkPresence
typealias ServiceDirectoryShape=DirectoryReadShape
data class ServiceDirectoryWindow(val business:Int,val items:List<ServiceDirectoryItem>,val shape:ServiceDirectoryShape,val receivedCount:Int,val observedCount:Long?,val next:ServiceDirectoryLinkPresence,val previous:ServiceDirectoryLinkPresence) {
    companion object {fun decode(body:String,business:Int):ServiceDirectoryWindow?=runCatching {
        require(business>0);val envelope=DirectoryReadEnvelope.decode(body);require(envelope!=null);val rows=envelope.rows
        val ids=mutableSetOf<Int>();val projected=mutableListOf<ServiceDirectoryItem>()
        for(i in 0 until rows.length()) {val item=ServiceDirectoryItem.item(rows.get(i));require(item!=null && ids.add(item.id));if(item.business==business)projected.add(item)}
        ServiceDirectoryWindow(business,projected.toList(),envelope.shape,rows.length(),envelope.count,envelope.next,envelope.previous)
    }.getOrNull()}
}
