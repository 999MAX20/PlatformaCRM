package kz.zani.mobile.data

import kz.zani.mobile.core.*
import org.json.JSONArray
import org.json.JSONObject

// Debug/test producer, not an application fallback or server permission policy.
object FixtureClientSearch {
    private fun catalogue(data: String,business: Int): JSONObject {
        val source=JSONObject(data)
        if(business !in listOf(101,202) || source.getInt("business")!=business || !source.has("fixture_only"))throw ReadException(ReadProblem.INVALID_PAYLOAD)
        return source
    }
    fun list(data: String,business: Int,search: String): ReadResponse {
        val source=catalogue(data,business);val rows=source.getJSONArray("items");val query=SourceTextTrim.pythonStrip(search)
        val matches=(0 until rows.length()).map {rows.getJSONObject(it)}.filter {row->query.isEmpty() || listOf("title","phone","email","notes").any {row.optString(it,"").contains(query,ignoreCase=true)}}
        val response=JSONObject().put("business",business).put("generated_at",source.getString("generated_at")).put("limit",50)
            .put("items",JSONArray(matches.take(50))).put("summary",JSONObject().put("total",matches.size).put("with_phone",matches.count {it.optString("phone","").isNotEmpty()}).put("with_email",matches.count {it.optString("email","").isNotEmpty()}))
            .put("payload_budget",JSONObject().put("target_kb",100).put("max_items",50))
        return ReadResponse(200,response.toString())
    }
    fun profile(data: String,business: Int,id: Int): ReadResponse {
        val source=catalogue(data,business);val rows=source.getJSONArray("items")
        val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("id")==id} ?: return ReadResponse(404,"")
        return ReadResponse(200,JSONObject().put("business",business).put("generated_at",source.getString("generated_at")).put("client",row)
            .put("details",JSONObject().put("notes",row.optString("notes",""))).put("related",JSONObject().put("appointments",JSONArray()).put("tasks",JSONArray()).put("conversations",JSONArray()).put("leads",JSONArray()))
            .put("payload_budget",JSONObject().put("max_related_per_section",5)).toString())
    }
    fun isCatalogueID(id: Int)=id in 1701..1754 || id in 2701..2754
}
