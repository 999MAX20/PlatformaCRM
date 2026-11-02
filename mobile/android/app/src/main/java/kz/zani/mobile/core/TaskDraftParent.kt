package kz.zani.mobile.core

import org.json.JSONObject

// Manual optional parent reference only, no inferred fields, graph or lifecycle grant.
data class TaskDraftParentChoice private constructor(val business:Int,val id:Int,val title:String?,val status:String) {
    fun validFor(business:Int)=business>0 && this.business==business && id>0
    companion object {fun make(detail:TaskDetails,business:Int,id:Int):TaskDraftParentChoice?=if(business>0 && id>0 && detail.validFor(business,id))TaskDraftParentChoice(business,id,detail.task.title,detail.task.status) else null}
}
sealed interface TaskCreateParentRead {
    data object Unknown:TaskCreateParentRead
    data object NotSet:TaskCreateParentRead
    data class Parent(val id:Int):TaskCreateParentRead
    fun matches(selected:Int?)=selected==null || (selected>0 && this==Parent(selected))
    companion object {fun decode(raw:String):TaskCreateParentRead=runCatching {
        val o=JSONObject(raw);if(!o.has("parent_task"))return@runCatching Unknown;if(o.isNull("parent_task"))return@runCatching NotSet
        val v=o.get("parent_task");require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());Parent(n.toInt())
    }.getOrDefault(Unknown)}
}
