package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.TeamMemberReadRepository

class MemberReferenceModel(private val repository:TeamMemberReadRepository) {
    private val session=MemberReferenceSession()
    var state by mutableStateOf(session.state);private set
    private var revision by mutableStateOf(0)
    var controlsBlocked:()->Boolean={false}
    val control get()=revision.let {session.control}
    val input get()=revision.let {session.input}
    val canUse get()=revision.let {session.canUse}
    private fun publish(){state=session.state;++revision}
    fun bind(context:InboxConversationFilesContext?){session.bind(context);publish()}
    fun show(){session.show();publish()}
    fun hide(){session.hide();publish()}
    fun update(raw:String,input:MemberReferenceInput?){if(!controlsBlocked()){session.update(raw,input);publish()}}
    fun clear(expected:MemberReferenceControl?){if(!controlsBlocked()){session.clear(expected);publish()}}
    fun use(expected:MemberReferenceControl?){if(!controlsBlocked()){session.use(expected);publish()}}
    fun clearChoice(expected:MemberReferenceControl?){if(!controlsBlocked()){session.clearChoice(expected);publish()}}
    suspend fun read(expected:MemberReferenceControl?){if(controlsBlocked() || !currentCoroutineContext().isActive)return;val ticket=session.begin(expected) ?: return;publish()
        try {val source=repository.member(ticket.context.business,ticket.id);if(!currentCoroutineContext().isActive)throw CancellationException();session.accept(source,ticket)}catch(e:Exception){if(e is CancellationException)session.cancel(ticket)else session.fail((e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE,ticket)};publish()}
}
