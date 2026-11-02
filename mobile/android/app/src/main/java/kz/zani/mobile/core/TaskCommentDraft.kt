package kz.zani.mobile.core

// Read revision is local freshness only, never the Task entity version.
data class TaskCommentContext(val business: Int,val task: Int,val epoch: Int) {val valid get()=business>0 && task>0 && epoch>0}
data class TaskCommentRead(val context: TaskCommentContext,val revision: Int)
data class TaskCommentSelection(val read: TaskCommentRead,val generation: Int)
enum class TaskCommentPhase {CLOSED,EDITING,REVIEW}
// Review identity keeps exact raw text; source trim is separate and does not normalize.
data class TaskCommentReview(val selection: TaskCommentSelection,val text: String)
object TaskCommentText {fun preview(raw: String)=SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(raw))}
data class TaskCommentState(val read: TaskCommentRead?=null,val available: Boolean=false,val selection: TaskCommentSelection?=null,val text: String="",val emptyError: Boolean=false,val phase: TaskCommentPhase=TaskCommentPhase.CLOSED,val review: TaskCommentReview?=null)
class TaskCommentSession {
    var state=TaskCommentState();private set
    private var ownerBusiness: Int?=null;private var ownerEpoch: Int?=null;private var generation=0
    private val buffers=mutableMapOf<Int,String>()
    private fun stash() {val r=state.read;if(state.available && r!=null)buffers[r.context.task]=state.text}
    private fun hide() {++generation;state=TaskCommentState()}
    fun retainOwner(business: Int?,epoch: Int?) {
        stash();hide();if(ownerBusiness!=business || ownerEpoch!=epoch || business==null || epoch==null)buffers.clear()
        ownerBusiness=business;ownerEpoch=epoch
    }
    fun begin(next: TaskCommentRead?) {
        stash();hide()
        if(next==null || !next.context.valid || next.revision<=0) {buffers.clear();ownerBusiness=null;ownerEpoch=null;return}
        if(ownerBusiness!=next.context.business || ownerEpoch!=next.context.epoch)buffers.clear()
        ownerBusiness=next.context.business;ownerEpoch=next.context.epoch;state=state.copy(read=next)
    }
    fun receive(verified: Boolean,expected: TaskCommentRead) {
        if(state.read!=expected)return
        stash();hide();state=state.copy(read=expected,available=verified,text=if(verified)buffers[expected.context.task] ?: "" else "")
    }
    fun pause() {stash();hide()}
    fun open(expected: TaskCommentRead): Boolean {
        if(state.read!=expected || !state.available)return false
        state=state.copy(selection=TaskCommentSelection(expected,++generation),phase=TaskCommentPhase.EDITING,review=null,emptyError=false);return true
    }
    fun update(value: String,expected: TaskCommentSelection) {
        if(state.selection!=expected || !state.available || state.phase!=TaskCommentPhase.EDITING)return
        state=state.copy(text=value,emptyError=false);stash()
    }
    fun prepare(expected: TaskCommentSelection): Boolean {
        if(state.selection!=expected || !state.available || state.phase!=TaskCommentPhase.EDITING)return false
        val preview=TaskCommentText.preview(state.text);state=state.copy(emptyError=preview.isEmpty());if(state.emptyError)return false
        state=state.copy(review=TaskCommentReview(expected,preview),phase=TaskCommentPhase.REVIEW);return true
    }
    fun back(expected: TaskCommentSelection) {if(state.selection!=expected)return;if(state.phase==TaskCommentPhase.REVIEW)state=state.copy(phase=TaskCommentPhase.EDITING,review=null) else close(expected)}
    fun close(expected: TaskCommentSelection) {if(state.selection!=expected)return;stash();++generation;state=state.copy(selection=null,review=null,phase=TaskCommentPhase.CLOSED)}
    fun discard(expected: TaskCommentSelection) {if(state.selection!=expected)return;state=state.copy(text="",emptyError=false);close(expected)}
}
