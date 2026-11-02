package kz.zani.mobile.ui
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*

class LeadReferenceModel(private val repository:LeadReadRepository) {
    private val session=LeadReadSession()
    var state by mutableStateOf(session.state);private set
    private var revision by mutableStateOf(0)
    var controlsBlocked:()->Boolean={false}
    val control get()=revision.let {session.control}
    val input get()=revision.let {session.input}
    private fun publish(){state=session.state;++revision}
    fun bind(context:InboxConversationFilesContext?){session.bind(context);publish()}
    fun show(){session.show();publish()}
    fun hide(){session.hide();publish()}
    fun update(raw:String,input:LeadReadInput?){if(!controlsBlocked()){session.update(raw,input);publish()}}
    fun clear(expected:LeadReadControl?){if(!controlsBlocked()){session.clear(expected);publish()}}
    fun back(expected:LeadReadControl?){if(!controlsBlocked()){session.backProfile(expected);publish()}}
    fun use(expected:LeadReadControl?){if(!controlsBlocked()){session.use(expected);publish()}}
    fun clearChoice(expected:LeadReadControl?){if(!controlsBlocked()){session.clearChoice(expected);publish()}}
    suspend fun search(expected:LeadReadControl?){if(controlsBlocked() || !currentCoroutineContext().isActive)return;val ticket=session.beginList(expected) ?: return;publish()
        try {val page=repository.leads(ticket.context.business,ticket.query);if(!currentCoroutineContext().isActive)throw CancellationException();session.accept(page,ticket)}catch(e:Exception){if(e is CancellationException)session.cancel(ticket)else session.fail((e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE,ticket)};publish()}
    suspend fun open(id:Int,expected:LeadReadControl?){if(controlsBlocked() || !currentCoroutineContext().isActive)return;val ticket=session.beginProfile(id,expected) ?: return;publish()
        try {val profile=repository.lead(ticket.context.business,id);if(!currentCoroutineContext().isActive)throw CancellationException();session.accept(profile,ticket)}catch(e:Exception){if(e is CancellationException)session.cancel(ticket)else session.fail((e as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE,ticket)};publish()}
}
