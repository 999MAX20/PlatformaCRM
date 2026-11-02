package kz.zani.mobile.data

import kz.zani.mobile.core.*
import org.json.JSONObject
import org.json.JSONArray

// Same precomputed clocked producer pages as Swift. No device clock/filter.
object FixtureTaskQueries {
    fun response(data: String,business: Int,query: Map<String,String>,id: Int?=null): ReadResponse {
        val source=JSONObject(data)
        if(!source.getBoolean("fixture_only") || source.getInt("business")!=business)throw ReadException(ReadProblem.INVALID_PAYLOAD)
        val value=if(id!=null)source.getJSONObject("profiles").optJSONObject("$id") else {
            if(!setOf("business","limit","status","due").containsAll(query.keys) || query["limit"]!="50" || TaskDueFilter.entries.none {it.wire==(query["due"] ?: "")})return ReadResponse(400,"")
            val pages=source.getJSONObject("queries");val due=query["due"] ?: ""
            pages.optJSONObject((query["status"] ?: "")+"|"+due) ?: if(!query["status"].isNullOrEmpty())JSONObject(pages.getJSONObject("|$due").toString()).put("items",JSONArray()).put("summary",JSONObject().put("total",0).put("open",0).put("today",0).put("overdue",0)) else null
        }
        return if(value==null)ReadResponse(404,"") else ReadResponse(200,value.toString())
    }
}
