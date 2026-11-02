package kz.zani.mobile.core

import org.json.JSONObject

// Exactly ResourceSerializer seven fields, preserving unknown raw type and observed timestamps.
data class ResourceDirectoryItem(val id:Int,val business:Int,val name:String,val resourceType:String,val isActive:Boolean,val createdAt:String,val updatedAt:String) {
    val reference get()=AppointmentReferenceDetail(id,business,name,isActive,resourceType)
    val hasKnownType get()=resourceType in listOf("staff","room","hall","box","equipment","other")
    val typeCopyKey get()=AppointmentReferenceDetail(id,business,name,isActive,resourceType).resourceTypeCopyKey
    companion object {
        internal fun item(value:Any?):ResourceDirectoryItem?=runCatching {
            require(value is JSONObject)
            fun text(key:String):String {val v=value.get(key);require(v is String);return v}
            val id=directoryReadInteger(value.opt("id"));val business=directoryReadInteger(value.opt("business"));require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && business!=null && business in 1L..Int.MAX_VALUE.toLong())
            val active=value.get("is_active");require(active is Boolean);val created=text("created_at");val updated=text("updated_at");require(TaskSnoozeValue.parse(created)!=null && TaskSnoozeValue.parse(updated)!=null)
            ResourceDirectoryItem(id.toInt(),business.toInt(),text("name"),text("resource_type"),active,created,updated)
        }.getOrNull()
        fun decode(body:String):ResourceDirectoryItem?=runCatching {item(JSONObject(body))}.getOrNull()
    }
}
typealias ResourceDirectoryLinkPresence=DirectoryReadLinkPresence
typealias ResourceDirectoryShape=DirectoryReadShape
data class ResourceDirectoryWindow(val business:Int,val items:List<ResourceDirectoryItem>,val shape:ResourceDirectoryShape,val receivedCount:Int,val observedCount:Long?,val next:ResourceDirectoryLinkPresence,val previous:ResourceDirectoryLinkPresence) {
    companion object {fun decode(body:String,business:Int):ResourceDirectoryWindow?=runCatching {
        require(business>0);val envelope=DirectoryReadEnvelope.decode(body);require(envelope!=null);val rows=envelope.rows
        val ids=mutableSetOf<Int>();val projected=mutableListOf<ResourceDirectoryItem>()
        for(i in 0 until rows.length()) {val item=ResourceDirectoryItem.item(rows.get(i));require(item!=null && ids.add(item.id));if(item.business==business)projected.add(item)}
        ResourceDirectoryWindow(business,projected.toList(),envelope.shape,rows.length(),envelope.count,envelope.next,envelope.previous)
    }.getOrNull()}
}
