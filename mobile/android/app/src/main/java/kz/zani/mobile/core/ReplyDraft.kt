package kz.zani.mobile.core

object ReplyDraftText { fun stripped(raw: String)=SourceTextTrim.pythonStrip(raw) }
data class ReplyDraftContext(val business: Int,val conversation: Int,val epoch: Int) { val valid get() = business>0 && conversation>0 && epoch>0 }
data class ReplyDraftSelection(val context: ReplyDraftContext,val generation: Int)
enum class ReplyDraftPhase { CLOSED, EDITING, REVIEW }
data class ReplyDraftReview(val selection: ReplyDraftSelection,val text: String,val raw:String)
data class ReplyDraftState(val context: ReplyDraftContext?=null,val available: Boolean=false,val selection: ReplyDraftSelection?=null,val text: String="",val emptyError: Boolean=false,val phase: ReplyDraftPhase=ReplyDraftPhase.CLOSED,val review: ReplyDraftReview?=null)
// Manual per-conversation memory only, not a stored/offline command or SEND grant.
class ReplyDraftSession {
    var state=ReplyDraftState();private set
    private val buffers=mutableMapOf<Int,String>()
    private var generation=0
    private fun stash() {
        val context=state.context ?: return
        if (!state.available) return
        if(state.text.isEmpty()) buffers.remove(context.conversation) else buffers[context.conversation]=state.text
    }
    fun bind(next: ReplyDraftContext?,available: Boolean) {
        if(next==null || !next.valid){clear();return}
        val sameOwner=state.context?.business==next.business && state.context?.epoch==next.epoch
        if(sameOwner) stash() else buffers.clear()
        val changed=state.context!=next || !state.available || !available
        if(changed) { ++generation;state=ReplyDraftState(next,available,text=if(available)buffers[next.conversation] ?: "" else "") }
        else state=state.copy(context=next,available=available)
    }
    fun retainOwner(business: Int?,epoch: Int?) {
        val c=state.context
        if(c==null || c.business!=business || c.epoch!=epoch) clear() else pause()
    }
    fun pause() { stash();++generation;state=state.copy(available=false,selection=null,review=null,phase=ReplyDraftPhase.CLOSED,text="",emptyError=false) }
    fun open(expected: ReplyDraftContext): Boolean {
        if(!state.available || state.context!=expected) return false
        state=state.copy(selection=ReplyDraftSelection(expected,++generation),review=null,phase=ReplyDraftPhase.EDITING,emptyError=false);return true
    }
    fun update(value: String,expected: ReplyDraftSelection) {
        if(state.selection!=expected || !state.available || state.phase!=ReplyDraftPhase.EDITING) return
        state=state.copy(text=value,emptyError=false);stash()
    }
    fun insertTemplate(value: String,expected: ReplyDraftSelection): Boolean {
        if(state.selection!=expected || !state.available || state.phase!=ReplyDraftPhase.EDITING || SourceTextTrim.pythonStrip(value).isEmpty())return false
        state=state.copy(text=QuickReplyInsertion.text(state.text,value),emptyError=false,selection=ReplyDraftSelection(expected.context,++generation));stash();return true
    }
    fun prepare(expected: ReplyDraftSelection): Boolean {
        if(state.selection!=expected || !state.available || state.phase!=ReplyDraftPhase.EDITING) return false
        val preview=ReplyDraftText.stripped(state.text)
        if(preview.isEmpty()){state=state.copy(emptyError=true);return false}
        state=state.copy(emptyError=false,review=ReplyDraftReview(expected,preview,state.text),phase=ReplyDraftPhase.REVIEW);return true
    }
    fun back(expected: ReplyDraftSelection) {
        if(state.selection!=expected) return
        if(state.phase==ReplyDraftPhase.REVIEW)state=state.copy(phase=ReplyDraftPhase.EDITING,review=null) else close(expected)
    }
    fun close(expected: ReplyDraftSelection) {
        if(state.selection!=expected) return
        stash();++generation;state=state.copy(selection=null,review=null,phase=ReplyDraftPhase.CLOSED)
    }
    fun discard(expected: ReplyDraftSelection) {
        if(state.selection!=expected) return
        state.context?.let { buffers.remove(it.conversation) };state=state.copy(text="");close(expected);state=state.copy(emptyError=false)
    }
    fun clear() { ++generation;buffers.clear();state=ReplyDraftState() }
}
