package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// No HTTP dependency. Only the explicit DEBUG fixture composition injects this.
class FixtureTaskCancelPort private constructor(private val catalog: JSONObject): SyntheticTaskCancelPort {
    constructor(assets: AssetManager): this(JSONObject(assets.open("fixtures/task-cancel-outcome.json").bufferedReader().use {it.readText()}))
    init {require(catalog.getBoolean("fixture_only"))}
    private val rows=catalog.getJSONArray("scenarios")
    override val grants=(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskCancelGrant(g.getInt("business"),g.getInt("task"),g.getInt("actor"),g.getBoolean("update"))}
    override suspend fun execute(attempt: TaskCancelAttempt): SyntheticTaskCancelOutcome {
        val index=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization}
        if(index<0)return SyntheticTaskCancelOutcome.Unknown
        val row=rows.getJSONObject(index)
        return when(row.getString("outcome")) {
            "rejected_without_write"->SyntheticTaskCancelOutcome.RejectedWithoutWrite
            "response"->SyntheticTaskCancelOutcome.Response(200,JsonContracts.taskCancelAction(row.getJSONObject("response").toString()).copy(cancelReason=attempt.review.text))
            else->SyntheticTaskCancelOutcome.Unknown
        }
    }
    companion object {
        fun fromJSON(json:String):FixtureTaskCancelPort = FixtureTaskCancelPort(JSONObject(json))
    }
}
