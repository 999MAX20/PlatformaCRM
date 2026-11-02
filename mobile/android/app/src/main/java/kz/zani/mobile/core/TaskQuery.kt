package kz.zani.mobile.core

enum class TaskDueFilter(val wire: String) {ALL(""),TODAY("today"),OVERDUE("overdue")}
data class TaskQuerySelection(val business: Int,val epoch: Int,val revision: Int)
data class TaskDetailSelection(val business: Int,val task: Int,val epoch: Int?,val listRevision: Int,val revision: Int)
data class TaskQueryFilter(val status: String?=null,val due: TaskDueFilter=TaskDueFilter.ALL) {
    fun query(business: Int)=buildMap {put("business","$business");put("limit","50");if(!status.isNullOrEmpty())put("status",status);if(due!=TaskDueFilter.ALL)put("due",due.wire)}
}
