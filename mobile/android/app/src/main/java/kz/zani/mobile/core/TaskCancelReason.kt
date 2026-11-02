package kz.zani.mobile.core

enum class TaskCancelReasonProblem {MINIMUM,MAXIMUM,CHARACTERS}
object TaskCancelReasonText {
    fun preview(raw: String)=TaskCommentText.preview(raw)
    fun problem(raw: String): TaskCancelReasonProblem? {
        val web=SourceTextTrim.javascriptTrim(raw);val value=preview(raw)
        if(web.length<3 || value.codePointCount(0,value.length)<3)return TaskCancelReasonProblem.MINIMUM
        if(value.codePointCount(0,value.length)>2000)return TaskCancelReasonProblem.MAXIMUM
        if(value.codePoints().anyMatch {it==0 || it in 0xD800..0xDFFF})return TaskCancelReasonProblem.CHARACTERS
        return null
    }
}
data class TaskCancelReasonSelection internal constructor(internal val source: TaskCommentSelection) {val read get()=source.read}
data class TaskCancelReasonReview(val selection: TaskCancelReasonSelection,val text: String)
data class TaskCancelReasonState(val read: TaskCommentRead?,val available: Boolean,val text: String,val phase: TaskCommentPhase,val selection: TaskCancelReasonSelection?,val review: TaskCancelReasonReview?,val problem: TaskCancelReasonProblem?)
class TaskCancelReasonSession {
    private val manual=TaskCommentSession()
    private var problem: TaskCancelReasonProblem?=null
    val state: TaskCancelReasonState get() {val s=manual.state;return TaskCancelReasonState(s.read,s.available,s.text,s.phase,s.selection?.let {TaskCancelReasonSelection(it)},s.review?.let {TaskCancelReasonReview(TaskCancelReasonSelection(it.selection),it.text)},problem)}
    fun retainOwner(business: Int?,epoch: Int?) {manual.retainOwner(business,epoch);problem=null}
    fun begin(read: TaskCommentRead?) {manual.begin(read);problem=null}
    fun receive(verified: Boolean,status: String?,expected: TaskCommentRead) {
        if(manual.state.read!=expected)return
        problem=null;manual.receive(verified && status in listOf("open","in_progress"),expected)
    }
    fun pause() {manual.pause();problem=null}
    fun open(expected: TaskCommentRead): Boolean {val opened=manual.open(expected);if(opened)problem=null;return opened}
    fun update(value: String,expected: TaskCancelReasonSelection) {
        if(manual.state.selection!=expected.source || !manual.state.available || manual.state.phase!=TaskCommentPhase.EDITING)return
        manual.update(value,expected.source);problem=null
    }
    fun prepare(expected: TaskCancelReasonSelection): Boolean {
        if(manual.state.selection!=expected.source || !manual.state.available || manual.state.phase!=TaskCommentPhase.EDITING)return false
        problem=TaskCancelReasonText.problem(manual.state.text);if(problem!=null)return false
        return manual.prepare(expected.source)
    }
    fun back(expected: TaskCancelReasonSelection) {if(manual.state.selection!=expected.source)return;manual.back(expected.source);problem=null}
    fun close(expected: TaskCancelReasonSelection) {if(manual.state.selection!=expected.source)return;manual.close(expected.source);problem=null}
    fun discard(expected: TaskCancelReasonSelection) {if(manual.state.selection!=expected.source)return;manual.discard(expected.source);problem=null}
}
