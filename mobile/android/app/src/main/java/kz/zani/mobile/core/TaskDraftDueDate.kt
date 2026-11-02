package kz.zani.mobile.core

enum class TaskDraftDueMode {OMIT,SET}
// Omission preserves unsent raw, never sends null or claims a default server date.
data class TaskDraftDueDate(val mode:TaskDraftDueMode=TaskDraftDueMode.OMIT,val raw:String="") {
    val valid get()=mode==TaskDraftDueMode.OMIT || TaskSnoozeValue.parse(raw)!=null
    val selected get()=if(mode==TaskDraftDueMode.SET)raw else null
    fun matches(returned:String?):Boolean {if(mode==TaskDraftDueMode.OMIT)return true;val wanted=TaskSnoozeValue.parse(raw) ?: return false;val actual=returned?.let {TaskSnoozeValue.parse(it)} ?: return false;return wanted.microseconds==actual.microseconds}
}
