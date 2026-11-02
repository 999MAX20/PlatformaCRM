package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.AppointmentReferenceKind
import java.io.FileNotFoundException
import java.time.LocalDate
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

// Debug composition only. Never a fallback after a real API error.
class FixtureTransport(private val assets: AssetManager,private val taskQueries: Boolean=false) : ReadTransport {
    override suspend fun get(request: ReadRequest): ReadResponse = withContext(Dispatchers.IO) {
        val file = when {
            request.query.isEmpty() && request.path.trimEnd('/').substringAfterLast('/').toIntOrNull()?.let {id->AppointmentReferenceKind.entries.any {it.path(id)==request.path}}==true -> {
                val id=request.path.trimEnd('/').substringAfterLast('/').toInt();val kind=AppointmentReferenceKind.entries.single {it.path(id)==request.path};"${if(kind==AppointmentReferenceKind.SERVICE)"service" else "resource"}-reference-$id"
            }
            request.path == "/api/mobile/v1/bootstrap/" -> "bootstrap"
            request.path == "/api/mobile/v1/actions/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                "actions-$business"
            }
            request.path == "/api/mobile/v1/home/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                "home-$business"
            }
            request.path == "/api/mobile/v1/today/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202) || request.query["date"] != "2026-10-28") return@withContext ReadResponse(404, "")
                "today-$business"
            }
            request.path == "/api/mobile/v1/notifications/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                "notifications-$business"
            }
            request.path == "/api/mobile/v1/tasks/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                if(taskQueries)return@withContext FixtureTaskQueries.response(assets.open("fixtures/task-query-source-$business.json").bufferedReader().use {it.readText()},business!!,request.query)
                if(request.query["status"]!=null || request.query["due"]!=null)return@withContext ReadResponse(400,"")
                "tasks-$business"
            }
            request.path.startsWith("/api/mobile/v1/tasks/") -> {
                val business = request.query["business"]?.toIntOrNull() ?: return@withContext ReadResponse(404, "")
                val id = request.path.trimEnd('/').substringAfterLast('/').toIntOrNull() ?: return@withContext ReadResponse(404, "")
                if(taskQueries && business in listOf(101,202))return@withContext FixtureTaskQueries.response(assets.open("fixtures/task-query-source-$business.json").bufferedReader().use {it.readText()},business,request.query,id)
                "task-$business-$id"
            }
            request.path == "/api/mobile/v1/inbox/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                "inbox-$business"
            }
            request.path.startsWith("/api/mobile/v1/inbox/") -> {
                val business = request.query["business"]?.toIntOrNull() ?: return@withContext ReadResponse(404, "")
                val id = request.path.trimEnd('/').substringAfterLast('/').toIntOrNull() ?: return@withContext ReadResponse(404, "")
                "inbox-$business-$id"
            }
            request.path == "/api/mobile/v1/clients/" -> {
                val business = request.query["business"]?.toIntOrNull()
                if (business !in listOf(101, 202)) return@withContext ReadResponse(404, "")
                request.query["search"]?.let {search->return@withContext FixtureClientSearch.list(assets.open("fixtures/client-search-catalogue-$business.json").bufferedReader().use {it.readText()},business!!,search)}
                "clients-$business"
            }
            request.path.startsWith("/api/mobile/v1/clients/") -> {
                val business = request.query["business"]?.toIntOrNull() ?: return@withContext ReadResponse(404, "")
                val id = request.path.trimEnd('/').substringAfterLast('/').toIntOrNull() ?: return@withContext ReadResponse(404, "")
                if(FixtureClientSearch.isCatalogueID(id) && business in listOf(101,202))return@withContext FixtureClientSearch.profile(assets.open("fixtures/client-search-catalogue-$business.json").bufferedReader().use {it.readText()},business,id)
                "client-$business-$id"
            }
            request.path == "/api/mobile/v1/appointments/" -> {
                val business = request.query["business"]?.toIntOrNull()
                val day = request.query["date"]
                if (business !in listOf(101, 202) || day == null || runCatching { LocalDate.parse(day) }.isFailure) return@withContext ReadResponse(404, "")
                if (day == "2026-10-29" && business == 101) "appointments-agenda-edge-101"
                else if (day == "2026-10-27") "appointments-history-$business"
                else if (day == "2026-10-28") "appointments-$business"
                else return@withContext ReadResponse(200, """{"business":$business,"date":"$day","items":[],"summary":{"total":0}}""")
            }
            request.path.startsWith("/api/mobile/v1/appointments/") -> {
                val business = request.query["business"]?.toIntOrNull() ?: return@withContext ReadResponse(404, "")
                val id = request.path.trimEnd('/').substringAfterLast('/').toIntOrNull() ?: return@withContext ReadResponse(404, "")
                "appointment-$business-$id"
            }
            else -> return@withContext ReadResponse(404, "")
        }
        try { ReadResponse(200, assets.open("fixtures/$file.json").bufferedReader().use { it.readText() }) }
        catch (_: FileNotFoundException) { ReadResponse(404, "") }
    }
}
