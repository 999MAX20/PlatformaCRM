package kz.zani.mobile.data
import android.content.res.AssetManager
import kotlinx.coroutines.*
import org.json.*
import kz.zani.mobile.core.SourceTextTrim

// Explicit debug/test GET adapter. No fallback, permissions or commands.
class FixtureLeadReadTransport(private val assets:AssetManager):ReadTransport {
    override suspend fun get(request:ReadRequest)=withContext(Dispatchers.IO){response(assets.open("fixtures/lead-read.json").bufferedReader().use {it.readText()},request)}
    companion object {
        fun response(raw:String,request:ReadRequest):ReadResponse {
            val all=JSONObject(raw).getJSONArray("catalogues");val b=request.query["business"]?.toIntOrNull() ?: return ReadResponse(404,"")
            val c=(0 until all.length()).map {all.getJSONObject(it)}.firstOrNull {it.getInt("business")==b} ?: return ReadResponse(404,"");val rows=c.getJSONArray("rows");val visible=(0 until rows.length()).map {rows.getJSONObject(it)}.filter {!it.getBoolean("is_archived")}
            val result=if(request.path=="/api/mobile/v1/leads/" && request.query["limit"]=="50" && request.query.keys==setOf("business","limit","search")) {
                val query=SourceTextTrim.pythonStrip(request.query["search"] ?: "");val filtered=visible.filter {r->val item=r.getJSONObject("item");val client=item.getJSONObject("client");query.isEmpty() || listOf(client.getString("name"),client.getString("phone"),client.getString("email"),r.getString("message"),item.getJSONObject("service").getString("name")).any {it.contains(query,ignoreCase=true)}};val items=filtered.map {it.getJSONObject("item")}
                JSONObject().put("business",b).put("generated_at","2026-10-28T10:00:00Z").put("limit",50).put("summary",JSONObject().put("total",items.size).put("new",items.count {it.getString("status")=="new"}).put("unassigned",items.count {it.isNull("responsible_user_id")}).put("in_progress",items.count {it.getString("status") in listOf("contacted","in_progress")})).put("items",JSONArray(items.take(50))).put("payload_budget",JSONObject().put("target_kb",100).put("max_items",50))
            } else {
                val id=request.path.trimEnd('/').substringAfterLast('/').toIntOrNull() ?: return ReadResponse(404,"")
                if(request.query.keys!=setOf("business") || request.path!="/api/mobile/v1/leads/$id/")return ReadResponse(404,"")
                val r=visible.firstOrNull {it.getJSONObject("item").getInt("id")==id} ?: return ReadResponse(404,"")
                JSONObject().put("business",b).put("generated_at","2026-10-28T10:00:00Z").put("lead",r.getJSONObject("item")).put("details",JSONObject().put("message",r.getString("message"))).put("related",JSONObject().put("tasks",JSONArray()).put("appointments",JSONArray()).put("conversations",JSONArray())).put("payload_budget",JSONObject().put("target_kb",80).put("max_related_per_section",5))
            }
            return ReadResponse(200,result.toString())
        }
    }
}
