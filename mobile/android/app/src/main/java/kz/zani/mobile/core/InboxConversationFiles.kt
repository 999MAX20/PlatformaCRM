package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Local read owner only; not a version, permission or command grant.
data class InboxConversationFilesContext(val business:Int,val conversation:Int,val epoch:Int,val revision:Int) {val valid get()=business>0 && conversation>0 && epoch>0 && revision>0}
data class InboxFileMetadata private constructor(val id:Int,val business:Int,val originalName:String,val contentType:String,val size:Long,val entityType:String,val entityID:String,val visibility:String,val createdAt:String) {
    fun validFor(c:InboxConversationFilesContext)=c.valid && id>0 && business==c.business && size>=0 && entityType=="bot_conversation" && entityID==c.conversation.toString() && visibility=="private" && TaskSnoozeValue.parse(createdAt)!=null
    fun validFor(c:InboxMessageFilesContext)=c.valid && id>0 && business==c.business && size>=0 && entityType=="bot_message" && entityID==c.message.toString() && visibility=="private" && TaskSnoozeValue.parse(createdAt)!=null
    companion object {
        internal fun rows(values:org.json.JSONArray,business:Int,entityType:String,entityID:String):List<InboxFileMetadata> {
            val ids=mutableSetOf<Int>()
            return (0 until values.length()).map {i->
                val row=values.getJSONObject(i);val id=directoryReadInteger(row.get("id"));require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && ids.add(id.toInt()));require(directoryReadInteger(row.get("business"))==business.toLong())
                fun text(key:String):String {val value=row.get(key);require(value is String);return value}
                val name=text("original_name");val type=text("content_type");val size=directoryReadInteger(row.get("size"));require(size!=null && size>=0)
                val entity=text("entity_type");val providedID=text("entity_id");val visibility=text("visibility");val created=text("created_at");require(entity==entityType && providedID==entityID && visibility=="private" && TaskSnoozeValue.parse(created)!=null)
                InboxFileMetadata(id.toInt(),business,name,type,size,entity,providedID,visibility,created)
            }
        }
        fun decode(body:String,c:InboxConversationFilesContext):List<InboxFileMetadata>?=runCatching {
            require(c.valid);val tokener=JSONTokener(body);val o=tokener.nextValue();require(tokener.nextClean()=='\u0000' && o is JSONObject)
            require(inboxFileAnchor(o,c.business,c.conversation));rows(o.getJSONArray("attachments"),c.business,"bot_conversation",c.conversation.toString())
        }.getOrNull()
    }
}
typealias InboxConversationFileMetadata=InboxFileMetadata
typealias InboxMessageFileMetadata=InboxFileMetadata
internal fun inboxFileAnchor(o:JSONObject,business:Int,conversation:Int)=directoryReadInteger(o.opt("id"))==conversation.toLong() && directoryReadInteger(o.opt("business"))==business.toLong()
