package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Explicit DEBUG fixture dependency. Never implements generic POST or contact matching.
class FixtureClientDuplicatePreviewSource private constructor(private val catalog:JSONObject):SyntheticClientDuplicatePreviewSource {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/client-duplicate-preview.json").bufferedReader().use {it.readText()}))
    companion object {fun fromFixture(raw:String)=FixtureClientDuplicatePreviewSource(JSONObject(raw))}
    override suspend fun preview(input:ClientDuplicatePreviewInput):ClientDuplicateResponse? {
        if(!input.context.valid || catalog.opt("fixture_only")!=true)return null
        val rows=catalog.getJSONArray("scenarios")
        val matches=(0 until rows.length()).map {rows.getJSONObject(it)}.filter {it.opt("business")==input.context.business && it.opt("phone")==input.phone && it.opt("email")==input.email}
        return matches.singleOrNull()?.let {ClientDuplicateResponse.decode(it.getJSONObject("response").toString())}
    }
}
