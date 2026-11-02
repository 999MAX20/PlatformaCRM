package kz.zani.mobile.data

import android.content.res.AssetManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import kz.zani.mobile.core.*

interface ResourceDirectoryRepository {
    suspend fun resources(business:Int):ResourceDirectoryWindow
    suspend fun resource(business:Int,id:Int):ResourceDirectoryItem
}
class APIResourceDirectoryRepository(private val transport:ReadTransport):ResourceDirectoryRepository {
    private suspend fun get(path:String):String {val r=transport.get(ReadRequest(path));return when(r.status) {200->r.body;403->throw ReadException(ReadProblem.DENIED);404->throw ReadException(ReadProblem.NOT_FOUND);else->throw ReadException(ReadProblem.UNAVAILABLE)}}
    override suspend fun resources(business:Int):ResourceDirectoryWindow {if(business<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);return ResourceDirectoryWindow.decode(get("/api/resources/"),business) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
    override suspend fun resource(business:Int,id:Int):ResourceDirectoryItem {if(business<=0 || id<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);return ResourceDirectoryItem.decode(get("/api/resources/$id/"))?.takeIf {it.business==business && it.id==id} ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
// Explicit DEBUG fixture read port, independent from command grants and no network fallback.
class FixtureResourceDirectoryTransport(private val assets:AssetManager):ReadTransport {
    override suspend fun get(request:ReadRequest):ReadResponse=withContext(Dispatchers.IO) {
        if(request.query.isNotEmpty())return@withContext ReadResponse(404,"")
        val c=JSONObject(assets.open("fixtures/resource-directory.json").bufferedReader().use {it.readText()});if(c.opt("fixture_only")!=true)return@withContext ReadResponse(404,"")
        val rows=c.getJSONArray("reads")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);if(row.getString("path")==request.path)return@withContext ReadResponse(200,row.getString("response_json"))}
        ReadResponse(404,"")
    }
}
