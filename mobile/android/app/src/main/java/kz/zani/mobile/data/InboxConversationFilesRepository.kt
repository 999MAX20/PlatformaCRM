package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxConversationFilesRepository {suspend fun files(context:InboxConversationFilesContext):List<InboxConversationFileMetadata>}
class APIInboxConversationFilesRepository(private val transport:ReadTransport):InboxConversationFilesRepository {
    override suspend fun files(context:InboxConversationFilesContext):List<InboxConversationFileMetadata> {
        if(!context.valid)throw ReadException(ReadProblem.INVALID_CONTEXT)
        val response=transport.get(ReadRequest("/api/inbox/conversations/${context.conversation}/"))
        if(response.status!=200)throw ReadException(when(response.status) {403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE})
        return InboxConversationFileMetadata.decode(response.body,context) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)
    }
}
// Explicit DEBUG/test transport only. No actual HTTP, credentials, URL or mutations.
class FixtureInboxConversationFilesTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-conversation-files.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {
        val o=JSONObject(catalog);if(!o.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT)
        val rows=o.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
        return ReadResponse(200,row.getString("response_json"))
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxConversationFilesTransport(raw)}
}
