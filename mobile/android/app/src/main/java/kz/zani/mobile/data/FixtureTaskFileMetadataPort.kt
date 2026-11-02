package kz.zani.mobile.data

import android.content.res.AssetManager
import org.json.JSONObject
import kz.zani.mobile.core.*

class FixtureTaskFileMetadataPort private constructor(private val catalog:JSONObject):TaskFileMetadataPort {
    constructor(assets:AssetManager):this(JSONObject(assets.open("fixtures/task-file-metadata.json").bufferedReader().use {it.readText()}))
    constructor(source:String):this(JSONObject(source))
    override suspend fun read(context:TaskFileMetadataContext):String {
        require(context.valid && catalog.opt("fixture_only")==true);val rows=catalog.getJSONArray("scenarios")
        fun exactInt(o:JSONObject,key:String,n:Int):Boolean {val raw=o.get(key);return (raw is Int || raw is Long) && (raw as Number).toLong()==n.toLong()}
        val row=(0 until rows.length()).map {rows.getJSONObject(it)}.first {exactInt(it,"business",context.business) && exactInt(it,"task",context.task)}
        return row.getJSONArray("items").toString()
    }
}
