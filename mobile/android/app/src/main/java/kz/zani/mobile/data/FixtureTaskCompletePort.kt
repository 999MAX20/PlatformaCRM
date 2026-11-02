package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureTaskCompletePort private constructor(private val catalog:JSONObject):SyntheticTaskCompletePort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/task-complete-outcome.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    private val rows=if(catalog.optBoolean("fixture_only",false))catalog.getJSONArray("scenarios") else org.json.JSONArray()
    override val grants=(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticTaskCompleteGrant(g.getInt("business"),g.getInt("task"),g.getInt("actor"),g.getBoolean("update"))}
    override suspend fun execute(attempt:TaskCompletionAttempt):SyntheticTaskCompleteOutcome {
        val i=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization};if(i<0)return SyntheticTaskCompleteOutcome.Unknown
        val row=rows.getJSONObject(i)
        return when(row.getString("outcome")) {"rejected_without_write"->SyntheticTaskCompleteOutcome.RejectedWithoutWrite;"response"->row.optJSONObject("response")?.let {SyntheticTaskCompleteOutcome.Response(200,it.toString())} ?: SyntheticTaskCompleteOutcome.Unknown;else->SyntheticTaskCompleteOutcome.Unknown}
    }
}
