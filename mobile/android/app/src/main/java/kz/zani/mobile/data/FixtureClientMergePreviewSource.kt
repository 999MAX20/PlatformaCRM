package kz.zani.mobile.data

import android.content.res.AssetManager
import kz.zani.mobile.core.*
import org.json.JSONObject

// Explicit DEBUG catalog metadata is outside existing server DTO. No POST or matching.
class FixtureClientMergePreviewSource private constructor(private val catalog:JSONObject):SyntheticClientMergePreviewSource {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/client-merge-preview.json").bufferedReader().use {it.readText()}))
    companion object {fun fromFixture(raw:String)=FixtureClientMergePreviewSource(JSONObject(raw))}
    private fun group(context:ClientMergePreviewContext):List<ClientMergePreview>? {
        if(!context.valid || catalog.opt("fixture_only")!=true)return null
        val groups=catalog.getJSONArray("catalogs")
        val matches=(0 until groups.length()).map {groups.getJSONObject(it)}.filter {it.opt("business")==context.business && it.opt("target")==context.target}
        val rows=matches.singleOrNull()?.getJSONArray("previews") ?: return null
        val values=(0 until rows.length()).map {ClientMergePreview.decode(rows.getJSONObject(it).toString())}
        if(values.any {it.targetClientId!=context.target} || values.map {it.duplicate.id}.distinct().size!=values.size)return null
        return values
    }
    override suspend fun candidates(context:ClientMergePreviewContext)=group(context)?.map {it.duplicate}
    override suspend fun preview(context:ClientMergePreviewContext,duplicate:Int)=group(context)?.singleOrNull {it.matches(context,duplicate)}
}
