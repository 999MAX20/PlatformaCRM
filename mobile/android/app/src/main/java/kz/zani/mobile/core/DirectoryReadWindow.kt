package kz.zani.mobile.core

import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener

internal fun directoryReadInteger(value:Any?):Long?=if(value is Int || value is Long)(value as Number).toLong() else null
enum class DirectoryReadLinkPresence {ABSENT,NULL,PRESENT}
enum class DirectoryReadShape {ARRAY,RESULTS}
internal data class DirectoryReadEnvelope(val rows:JSONArray,val shape:DirectoryReadShape,val count:Long?,val next:DirectoryReadLinkPresence,val previous:DirectoryReadLinkPresence) {
    companion object {fun decode(body:String):DirectoryReadEnvelope?=runCatching {
        val tokener=JSONTokener(body);val value=tokener.nextValue();require(tokener.nextClean()=='\u0000');val rows:JSONArray;val shape:DirectoryReadShape;val count:Long?;val next:DirectoryReadLinkPresence;val previous:DirectoryReadLinkPresence
        fun link(o:JSONObject,key:String):DirectoryReadLinkPresence {if(!o.has(key))return DirectoryReadLinkPresence.ABSENT;if(o.isNull(key))return DirectoryReadLinkPresence.NULL;val v=o.get(key);require(v is String && v.isNotEmpty());return DirectoryReadLinkPresence.PRESENT}
        if(value is JSONArray) {rows=value;shape=DirectoryReadShape.ARRAY;count=null;next=DirectoryReadLinkPresence.ABSENT;previous=DirectoryReadLinkPresence.ABSENT}
        else {require(value is JSONObject);rows=value.getJSONArray("results");shape=DirectoryReadShape.RESULTS;count=if(value.has("count")) {val n=directoryReadInteger(value.get("count"));require(n!=null && n>=0 && n>=rows.length());n} else null;next=link(value,"next");previous=link(value,"previous")}
        DirectoryReadEnvelope(rows,shape,count,next,previous)
    }.getOrNull()}
}
