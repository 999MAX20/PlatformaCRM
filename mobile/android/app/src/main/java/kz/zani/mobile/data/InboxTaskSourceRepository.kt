package kz.zani.mobile.data
import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxTaskSourceRepository {suspend fun source(c:InboxConversationFilesContext):InboxTaskSource}
class APIInboxTaskSourceRepository(private val transport:ReadTransport):InboxTaskSourceRepository {
    override suspend fun source(c:InboxConversationFilesContext):InboxTaskSource {if(!c.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/inbox/conversations/${c.conversation}/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return InboxTaskSource.decode(r.body,c) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class FixtureInboxTaskSourceTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-task-source.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(row.getInt("status"),row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxTaskSourceTransport(raw)}
}
