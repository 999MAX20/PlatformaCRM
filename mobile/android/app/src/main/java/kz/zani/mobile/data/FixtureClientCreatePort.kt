package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Explicit DEBUG fixture dependency only. No HTTP implementation or POST transport.
class FixtureClientCreatePort private constructor(private val catalog: JSONObject): SyntheticClientCreatePort {
    constructor(assets: AssetManager):this(JSONObject(assets.open("fixtures/client-create-outcome.json").bufferedReader().use {it.readText()}))
    init {require(catalog.getBoolean("fixture_only"))}
    private val rows=catalog.getJSONArray("scenarios")
    override val grants=(0 until rows.length()).map {n->val g=rows.getJSONObject(n).getJSONObject("grant");SyntheticClientCreateGrant(g.getInt("business"),g.getInt("actor"),g.getBoolean("create"))}
    override suspend fun execute(attempt: ClientCreateAttempt): SyntheticClientCreateOutcome {
        val index=grants.indexOfFirst {it.authorization(attempt.authorization.context)==attempt.authorization}
        if(index<0)return SyntheticClientCreateOutcome.Unknown
        val row=rows.getJSONObject(index)
        return when(row.getString("outcome")) {
            "rejected_without_write"->SyntheticClientCreateOutcome.RejectedWithoutWrite
            "response"->{val v=attempt.review.preview;SyntheticClientCreateOutcome.Response(201,JsonContracts.clientCreateAction(row.getJSONObject("response").toString()).copy(fullName=v.fullName,phone=v.phone,email=v.email,source=v.source,notes=v.notes))}
            else->SyntheticClientCreateOutcome.Unknown
        }
    }
}
