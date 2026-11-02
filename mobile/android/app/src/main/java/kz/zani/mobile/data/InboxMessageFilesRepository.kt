package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Separate stages let the owner reject a late anchor before the dependent GET.
interface InboxMessageFilesRepository {suspend fun anchor(context:InboxMessageFilesContext):InboxFilesConversationAnchor;suspend fun messages(context:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor):InboxMessageFileWindow}
class APIInboxMessageFilesRepository(private val transport:ReadTransport):InboxMessageFilesRepository {
    private suspend fun response(request:ReadRequest):String {val r=transport.get(request);if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return r.body}
    override suspend fun anchor(context:InboxMessageFilesContext):InboxFilesConversationAnchor {if(!context.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);return InboxFilesConversationAnchor.decode(response(ReadRequest("/api/inbox/conversations/${context.conversation}/")),context) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
    override suspend fun messages(context:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor):InboxMessageFileWindow {if(!context.valid || !anchor.matches(context))throw ReadException(ReadProblem.INVALID_CONTEXT);return InboxMessageFileWindow.decode(response(ReadRequest("/api/inbox/conversations/${context.conversation}/messages/",mapOf("limit" to context.limit.toString()))),context)}
}
class FixtureInboxMessageFilesTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-message-files.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val o=JSONObject(catalog);if(o.opt("fixture_only")!=true)throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=o.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {val query=it.getJSONObject("query");it.getString("path")==request.path && query.keys().asSequence().associateWith {key->query.getString(key)}==request.query} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxMessageFilesTransport(raw)}
}
