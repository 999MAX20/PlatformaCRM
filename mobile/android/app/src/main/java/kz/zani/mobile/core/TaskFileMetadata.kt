package kz.zani.mobile.core

import java.time.Instant
import org.json.JSONArray
import org.json.JSONObject

// Local read/window identity, never permission or a server entity version.
data class TaskFileMetadataContext(val business:Int,val task:Int,val epoch:Int,val revision:Int) {val valid get()=business>0 && task>0 && epoch>0 && revision>0}
// Exact existing metadata subset; URL/bytes/uploader/scan extras are deliberately not retained.
data class TaskFileMetadata(val id:Int,val business:Int,val originalName:String,val contentType:String,val size:Long,val entityType:String,val entityID:String,val visibility:String,val createdAt:String) {
    fun valid(c:TaskFileMetadataContext)=c.valid && id>0 && business==c.business && entityType=="task" && entityID==c.task.toString() && visibility=="private" && originalName.isNotEmpty() && size>=0 && runCatching {Instant.parse(createdAt)}.isSuccess
    companion object {
        private fun decode(o:JSONObject):TaskFileMetadata {
            fun integer(name:String):Int {val raw=o.get(name);require(raw is Int || raw is Long);val n=(raw as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
            fun string(name:String):String {val raw=o.get(name);require(raw is String);return raw}
            val raw=o.get("size");require(raw is Int || raw is Long);val size=(raw as Number).toLong();require(size>=0)
            return TaskFileMetadata(integer("id"),integer("business"),string("original_name"),string("content_type"),size,string("entity_type"),string("entity_id"),string("visibility"),string("created_at"))
        }
        fun window(body:String,context:TaskFileMetadataContext):List<TaskFileMetadata> {
            require(context.valid);val rows=if(body.trimStart().startsWith("["))JSONArray(body) else JSONObject(body).getJSONArray("results")
            val items=(0 until rows.length()).map {decode(rows.getJSONObject(it))};require(items.all {it.valid(context)} && items.map {it.id}.distinct().size==items.size);return items
        }
    }
}
interface TaskFileMetadataPort {suspend fun read(context:TaskFileMetadataContext):String}
