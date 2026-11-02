package kz.zani.mobile.core

import org.json.JSONObject

// Existing client_snapshot and dry-run fields; never bounded profile or a grant/outcome.
data class ClientMergeSnapshot(val id:Int,val fullName:String,val phone:String,val email:String,val whatsappId:String,val telegramId:String,val instagramId:String,val source:String,val isArchived:Boolean)
class ClientMergeTransferCounts(provided:Map<String,Int>) {
    private val values=provided.toMap()
    val provided get()=values.toMap()
    init {require(values.keys==fields.toSet() && values.values.all {it>=0})}
    override fun equals(other:Any?)=other is ClientMergeTransferCounts && values==other.values
    override fun hashCode()=values.hashCode()
    companion object {private val wireFields=listOf("leads","appointments","conversations","bot_conversations","tasks","deals","notes","activity_events","analytics_events","notifications","tags","attachments","custom_field_values");val fields get()=wireFields.toList()}
}
data class ClientMergePreview(val targetClientId:Int,val duplicate:ClientMergeSnapshot,val transferred:ClientMergeTransferCounts,val willDeleteDuplicate:Boolean,val policy:String) {
    val valid get()=targetClientId>0 && duplicate.id>0 && targetClientId!=duplicate.id && !willDeleteDuplicate && policy=="archive_duplicate_after_transfer"
    fun matches(context:ClientMergePreviewContext,id:Int)=context.valid && valid && targetClientId==context.target && duplicate.id==id
    companion object {
        fun decode(raw:String):ClientMergePreview {
            val root=JSONObject(raw)
            fun number(row:JSONObject,key:String)=row.get(key).let {require(it is Int);it}
            fun text(row:JSONObject,key:String)=row.get(key).let {require(it is String);it}
            fun flag(row:JSONObject,key:String)=row.get(key).let {require(it is Boolean);it}
            val s=root.getJSONObject("duplicate");val counts=root.getJSONObject("transferred")
            val keys=counts.keys().asSequence().toList()
            val value=ClientMergePreview(number(root,"target_client_id"),ClientMergeSnapshot(number(s,"id"),text(s,"full_name"),text(s,"phone"),text(s,"email"),text(s,"whatsapp_id"),text(s,"telegram_id"),text(s,"instagram_id"),text(s,"source"),flag(s,"is_archived")),ClientMergeTransferCounts(keys.associateWith {number(counts,it)}),flag(root,"will_delete_duplicate"),text(root,"policy"))
            require(value.valid);return value
        }
    }
}
// Local source context only, no server request/version or permission inference.
data class ClientMergePreviewContext(val business:Int,val target:Int,val epoch:Int,val readRevision:Int) {val valid get()=business>0 && target>0 && epoch>0 && readRevision>0}
interface SyntheticClientMergePreviewSource {
    suspend fun candidates(context:ClientMergePreviewContext):List<ClientMergeSnapshot>?
    suspend fun preview(context:ClientMergePreviewContext,duplicate:Int):ClientMergePreview?
}
