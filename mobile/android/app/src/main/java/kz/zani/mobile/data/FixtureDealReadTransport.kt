package kz.zani.mobile.data
import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

// Explicit fixture GET only; no full catalogue, fallback, inferred grant or write.
class FixtureDealReadTransport private constructor(private val raw:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/deal-read.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val o=JSONObject(raw);if(!o.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=o.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: return ReadResponse(404,"");return ReadResponse(row.getInt("status"),row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureDealReadTransport(raw)}
}
