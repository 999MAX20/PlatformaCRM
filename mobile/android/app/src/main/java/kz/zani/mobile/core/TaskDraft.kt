package kz.zani.mobile.core

// Manual unsaved Task input only. No follow-up, due date or relation inference.
data class TaskDraftContext(val business: Int,val epoch: Int) { val valid get()=business>0 && epoch>0 }
data class TaskDraftSelection(val context: TaskDraftContext,val generation: Int)
enum class TaskDraftField { TITLE, DESCRIPTION, PRIORITY, DUE_AT, REMINDER_AT }
enum class TaskDraftProblem { REQUIRED, TITLE_LENGTH, PRIORITY, CHARACTERS, DATE }
data class TaskDraftIssue(val field: TaskDraftField,val problem: TaskDraftProblem)
data class TaskDraftValues(val title: String="",val description: String="",val priority: String="normal",val dueDate:TaskDraftDueDate=TaskDraftDueDate(),val reminderDate:TaskDraftDueDate=TaskDraftDueDate(),val client:TaskDraftClientChoice?=null,val appointment:TaskDraftAppointmentChoice?=null,val parentTask:TaskDraftParentChoice?=null) {
    companion object { val priorities=listOf("low","normal","high","urgent") }
    val preview get()=TaskDraftPreview(SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(title)),SourceTextTrim.pythonStrip(description),priority,dueDate.selected,reminderDate.selected,client?.id,appointment?.id,parentTask?.id)
    fun validClient(business:Int)=client?.validFor(business) ?: true
    fun validAppointment(business:Int)=appointment?.validFor(business) ?: true
    fun validParent(business:Int)=parentTask?.validFor(business) ?: true
    val issues: List<TaskDraftIssue> get()=buildList {
        val value=preview
        if(value.title.isEmpty())add(TaskDraftIssue(TaskDraftField.TITLE,TaskDraftProblem.REQUIRED))
        if(value.title.codePointCount(0,value.title.length)>255)add(TaskDraftIssue(TaskDraftField.TITLE,TaskDraftProblem.TITLE_LENGTH))
        for((field,text) in listOf(TaskDraftField.TITLE to value.title,TaskDraftField.DESCRIPTION to value.description)) {
            if(text.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})add(TaskDraftIssue(field,TaskDraftProblem.CHARACTERS))
        }
        if(!dueDate.valid)add(TaskDraftIssue(TaskDraftField.DUE_AT,TaskDraftProblem.DATE))
        if(!reminderDate.valid)add(TaskDraftIssue(TaskDraftField.REMINDER_AT,TaskDraftProblem.DATE))
        if(priority !in priorities)add(TaskDraftIssue(TaskDraftField.PRIORITY,TaskDraftProblem.PRIORITY))
    }
}
enum class TaskDraftPhase { CLOSED, EDITING, REVIEW }
data class TaskDraftPreview(val title: String,val description: String,val priority: String,val dueAt:String?=null,val reminderAt:String?=null,val clientID:Int?=null,val appointmentID:Int?=null,val parentTaskID:Int?=null)
data class TaskDraftReview(val selection: TaskDraftSelection,val values: TaskDraftValues,val preview: TaskDraftPreview=values.preview)
data class TaskDraftState(val context: TaskDraftContext? = null,val selection: TaskDraftSelection? = null,val values: TaskDraftValues = TaskDraftValues(),val issues: List<TaskDraftIssue> = emptyList(),val review: TaskDraftReview? = null,val phase: TaskDraftPhase = TaskDraftPhase.CLOSED)
class TaskDraftSession {
    var state = TaskDraftState(); private set
    private var generation = 0
    fun bind(next: TaskDraftContext?) {
        val valid = next?.takeIf { it.valid }
        if (state.context == valid) return
        ++generation; state = TaskDraftState(context=valid)
    }
    fun open(expected: TaskDraftContext): Boolean {
        if (!expected.valid || expected != state.context) return false
        state = state.copy(selection=TaskDraftSelection(expected,++generation),phase=TaskDraftPhase.EDITING,issues=emptyList(),review=null); return true
    }
    fun update(field: TaskDraftField,value: String,expected: TaskDraftSelection) {
        if (state.selection != expected || state.phase != TaskDraftPhase.EDITING) return
        val v = state.values
        val next = when(field) {
            TaskDraftField.TITLE -> v.copy(title=value)
            TaskDraftField.DESCRIPTION -> v.copy(description=value)
            TaskDraftField.PRIORITY -> v.copy(priority=value)
            TaskDraftField.DUE_AT -> if(v.dueDate.mode==TaskDraftDueMode.SET)v.copy(dueDate=v.dueDate.copy(raw=value)) else v
            TaskDraftField.REMINDER_AT -> if(v.reminderDate.mode==TaskDraftDueMode.SET)v.copy(reminderDate=v.reminderDate.copy(raw=value)) else v
        }
        state = state.copy(values=next,issues=state.issues.filterNot { it.field==field })
    }
    fun chooseDue(mode:TaskDraftDueMode,expected:TaskDraftSelection) {if(state.selection!=expected || state.phase!=TaskDraftPhase.EDITING)return;state=state.copy(values=state.values.copy(dueDate=state.values.dueDate.copy(mode=mode)),issues=state.issues.filterNot {it.field==TaskDraftField.DUE_AT})}
    fun chooseReminder(mode:TaskDraftDueMode,expected:TaskDraftSelection) {if(state.selection!=expected || state.phase!=TaskDraftPhase.EDITING)return;state=state.copy(values=state.values.copy(reminderDate=state.values.reminderDate.copy(mode=mode)),issues=state.issues.filterNot {it.field==TaskDraftField.REMINDER_AT})}
    fun chooseClient(choice:TaskDraftClientChoice?,expected:TaskDraftSelection) {if(state.selection!=expected || state.phase!=TaskDraftPhase.EDITING || choice?.validFor(expected.context.business)==false)return;state=state.copy(values=state.values.copy(client=choice))}
    fun chooseAppointment(choice:TaskDraftAppointmentChoice?,expected:TaskDraftSelection) {if(state.selection!=expected || state.phase!=TaskDraftPhase.EDITING || choice?.validFor(expected.context.business)==false)return;state=state.copy(values=state.values.copy(appointment=choice))}
    fun chooseParent(choice:TaskDraftParentChoice?,expected:TaskDraftSelection) {if(state.selection!=expected || state.phase!=TaskDraftPhase.EDITING || choice?.validFor(expected.context.business)==false)return;state=state.copy(values=state.values.copy(parentTask=choice))}
    fun prepare(expected: TaskDraftSelection): Boolean {
        if (state.selection != expected || state.phase != TaskDraftPhase.EDITING) return false
        val issues = state.values.issues; state = state.copy(issues=issues)
        if (issues.isNotEmpty() || !state.values.validClient(expected.context.business) || !state.values.validAppointment(expected.context.business) || !state.values.validParent(expected.context.business)) return false
        state = state.copy(review=TaskDraftReview(expected,state.values),phase=TaskDraftPhase.REVIEW); return true
    }
    fun back(expected: TaskDraftSelection) {
        if (state.selection != expected) return
        if (state.phase==TaskDraftPhase.REVIEW) state = state.copy(review=null,phase=TaskDraftPhase.EDITING) else close(expected)
    }
    fun close(expected: TaskDraftSelection) {
        if (state.selection != expected) return
        ++generation; state = state.copy(selection=null,review=null,phase=TaskDraftPhase.CLOSED)
    }
    fun discard(expected: TaskDraftSelection) {
        if (state.selection != expected) return
        close(expected); state = state.copy(values=TaskDraftValues(),issues=emptyList())
    }
}
