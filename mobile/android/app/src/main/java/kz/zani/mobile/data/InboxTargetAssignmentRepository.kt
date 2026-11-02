package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

interface InboxTargetAssignmentRepository {suspend fun source(c:InboxConversationFilesContext):InboxTargetAssignmentSource}
class APIInboxTargetAssignmentRepository(private val transport:ReadTransport):InboxTargetAssignmentRepository {
    override suspend fun source(c:InboxConversationFilesContext):InboxTargetAssignmentSource {if(!c.valid)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/inbox/conversations/${c.conversation}/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return InboxTargetAssignmentSource.decode(r.body,c) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
class FixtureInboxTargetAssignmentPort private constructor(private val catalog:String):SyntheticInboxTargetAssignmentPort {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-target-assignment.json").bufferedReader().use {it.readText()})
    private val root=JSONObject(catalog)
    override val grants:List<SyntheticInboxTargetAssignmentGrant> = if(root.optBoolean("fixture_only"))root.getJSONArray("grants").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxTargetAssignmentGrant(it.getInt("business"),it.getInt("conversation"),it.getInt("actor"),it.getBoolean("manage"))}}else emptyList()
    override val targetMemberships:List<SyntheticInboxTargetMembershipContext> = if(root.optBoolean("fixture_only"))root.getJSONArray("target_memberships").let {rows->(0 until rows.length()).map {rows.getJSONObject(it)}.map {SyntheticInboxTargetMembershipContext(it.getInt("business"),it.getInt("user"),it.getBoolean("active_member"))}}else emptyList()
    override suspend fun execute(a:InboxTargetAssignmentAttempt):SyntheticInboxTargetAssignmentOutcome {
        val auth=a.review.authorization;val c=auth.context;if(!a.review.valid || grants.mapNotNull {it.authorization(c)}.none {it==auth} || a.review.targetMembership !in targetMemberships)return SyntheticInboxTargetAssignmentOutcome.RejectedWithoutWrite
        val rows=root.getJSONArray("scenarios");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getInt("business")==c.business && it.getInt("conversation")==c.conversation && it.getInt("actor")==auth.actor && it.getInt("user_id")==a.review.candidate.reference.source.user.id && it.getInt("member_id")==a.review.candidate.reference.source.id && (if(it.isNull("original_assigned_to"))null else it.getInt("original_assigned_to"))==a.review.source.assignedTo} ?: return SyntheticInboxTargetAssignmentOutcome.RejectedWithoutWrite
        return when(row.getString("outcome")){"response"->SyntheticInboxTargetAssignmentOutcome.Response(row.getInt("status"),row.getString("response_json"));"rejected"->SyntheticInboxTargetAssignmentOutcome.RejectedWithoutWrite;else->SyntheticInboxTargetAssignmentOutcome.Unknown}
    }
    companion object {fun fromJSON(raw:String)=FixtureInboxTargetAssignmentPort(raw)}
}
class FixtureInboxTargetAssignmentReadTransport private constructor(private val catalog:String):ReadTransport {
    constructor(assets:AssetManager):this(assets.open("fixtures/inbox-target-assignment.json").bufferedReader().use {it.readText()})
    override suspend fun get(request:ReadRequest):ReadResponse {val root=JSONObject(catalog);if(!root.getBoolean("fixture_only") || request.query.isNotEmpty())throw ReadException(ReadProblem.INVALID_CONTEXT);val rows=root.getJSONArray("reads");val row=(0 until rows.length()).map {rows.getJSONObject(it)}.firstOrNull {it.getString("path")==request.path} ?: throw ReadException(ReadProblem.INVALID_CONTEXT);return ReadResponse(200,row.getString("response_json"))}
    companion object {fun fromJSON(raw:String)=FixtureInboxTargetAssignmentReadTransport(raw)}
}
