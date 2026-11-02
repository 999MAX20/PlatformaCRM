package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// No transport or HTTP dependency. Injected only by the DEBUG fixture composition.
class FixtureTaskCommentSubmitPort private constructor(private val catalog: JSONObject): SyntheticTaskCommentPort {
    constructor(assets: AssetManager): this(JSONObject(assets.open("fixtures/task-comment-submit.json").bufferedReader().use {it.readText()}))
    init {require(catalog.getBoolean("fixture_only"))}
    private val rows=catalog.getJSONArray("scenarios")
    override val grants=(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskCommentGrant(g.getInt("business"),g.getInt("task"),g.getInt("actor"),g.getBoolean("update"))}
    override suspend fun execute(attempt: TaskCommentAttempt): SyntheticTaskCommentOutcome {
        val index=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization}
        if(index<0)return SyntheticTaskCommentOutcome.Unknown
        val row=rows.getJSONObject(index)
        return when(row.getString("outcome")) {
            "rejected_without_write"->SyntheticTaskCommentOutcome.RejectedWithoutWrite
            "response"->{val c=JsonContracts.taskCommentAction(row.getJSONObject("response").toString());SyntheticTaskCommentOutcome.Response(201,c.copy(text=attempt.text))}
            else->SyntheticTaskCommentOutcome.Unknown
        }
    }
}
