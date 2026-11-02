package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

// Separate explicit DEBUG/test read catalogue, no live fallback or date/resource default.
class FixtureAppointmentSlotTransport(private val assets:AssetManager):ReadTransport {
    override suspend fun get(request:ReadRequest):ReadResponse=withContext(Dispatchers.IO) {
        if(request.path!="/api/appointments/available-slots/")return@withContext ReadResponse(404,"")
        val catalog=JSONObject(assets.open("fixtures/appointment-slot-read-fixtures.json").bufferedReader().use {it.readText()})
        if(catalog.opt("fixture_only")!=true)return@withContext ReadResponse(404,"")
        val rows=catalog.getJSONArray("reads")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val query=row.getJSONObject("query");val keys=query.keys().asSequence().toList();if(keys.size==request.query.size && keys.all {query.get(it) is String && query.getString(it)==request.query[it]})return@withContext ReadResponse(200,row.getString("response_json"))}
        ReadResponse(404,"")
    }
}
