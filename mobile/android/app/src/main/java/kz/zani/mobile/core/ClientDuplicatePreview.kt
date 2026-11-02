package kz.zani.mobile.core

import org.json.JSONObject

// Exact generic response fields; no bounded ClientProfile, authority or transport.
data class ClientDuplicateRow(val id: Int,val fullName: String,val phone: String,val email: String,val matchedFields: List<String>) {
    val valid get()=id>0 && matchedFields.distinct().size==matchedFields.size && matchedFields.all {it in setOf("phone","email","whatsapp_id","telegram_id","instagram_id")}
}
data class ClientDuplicateResponse(val duplicates: List<ClientDuplicateRow>) {
    val valid get()=duplicates.all {it.valid} && duplicates.map {it.id}.distinct().size==duplicates.size
    companion object {
        fun decode(raw: String):ClientDuplicateResponse {
            val rows=JSONObject(raw).getJSONArray("duplicates")
            val value=ClientDuplicateResponse((0 until rows.length()).map {index->
                val row=rows.getJSONObject(index)
                fun text(key:String)=row.get(key).let {require(it is String);it}
                val id=row.get("id");require(id is Int)
                val fields=row.getJSONArray("matched_fields")
                ClientDuplicateRow(id,text("full_name"),text("phone"),text("email"),(0 until fields.length()).map {n->fields.get(n).let {require(it is String);it}})
            })
            require(value.valid);return value
        }
    }
}
// Local fixture lookup context only; not a wire request or permission.
data class ClientDuplicatePreviewInput(val context:ClientDraftContext,val phone:String,val email:String)
interface SyntheticClientDuplicatePreviewSource {suspend fun preview(input:ClientDuplicatePreviewInput):ClientDuplicateResponse?}
