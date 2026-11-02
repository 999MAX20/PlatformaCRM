package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.APIReadRepository

// Existing feed and local visit stamp, never a server revision/permission.
data class LoadedSearchControl(val feed:LoadedSearchFeed,val revision:Int,val feedVisit:Int,val queryRevision:Int,val selected:LoadedSearchHit?)

// Continuous input retains the read/feed visit while query list actions expire.
data class LoadedSearchInputControl(val feed:LoadedSearchFeed,val revision:Int,val feedVisit:Int)

data class LoadedSearchState(val feed: LoadedSearchFeed = LoadedSearchFeed.create(null, 0, emptyList()), val query: String = "",
    val selected: LoadedSearchHit? = null, val detail: AttentionDetail? = null, val loading: Boolean = false, val problem: ReadProblem? = null,
    val suppressed: Map<LoadedSearchIdentity, LoadedSearchToken> = emptyMap()) {
    val matches get() = feed.matches(query, suppressed.keys)
    val showsNoMatches get() = query.isNotBlank() && feed.hasLoadedSource && matches.isEmpty()
    fun coverage(source: LoadedSearchSource) = if (source.coverage.ready && suppressed.keys.any { it.kind == source.kind }) LoadedSearchCoverage.PARTIAL else source.coverage
}
class LoadedSearchViewModel(private val repository: APIReadRepository) : ViewModel() {
    var state by mutableStateOf(LoadedSearchState()); private set
    val profile = ClientProfileViewModel(repository)
    private var revision = 0
    private var queryRevision = 0 // Raw UI action window; independent read ticket remains unchanged.
    private var feedVisit = 0 // Local UI visit only; independent read ticket stays on revision.
    fun search(query: String) {if(query!=state.query)++queryRevision;state = state.copy(query = query)}
    fun reconcile(next: LoadedSearchFeed) {
        if (next == state.feed) return
        ++feedVisit
        if (next.business != state.feed.business || next.epoch != state.feed.epoch) { back();search("");state = state.copy(suppressed = emptyMap()) }
        else {
            state.selected?.let { if (!next.contains(it)) back() }
            state = state.copy(suppressed = state.suppressed.filter { next.source(it.key.kind)?.token == it.value })
        }
        state = state.copy(feed = next)
    }
    fun open(hit: LoadedSearchHit, retry: Boolean = false) {
        if (!state.feed.contains(hit) || (!(retry && state.selected == hit) && hit.identity in state.suppressed)) return
        val ticket = ++revision; val business = hit.identity.business; val id = hit.identity.id
        profile.clear(); state = state.copy(selected = hit, detail = null, loading = true, problem = null)
        if (hit.identity.kind == LoadedSearchKind.CLIENTS) {
            profile.loadObserved(business, id, onFinished = {
                if (current(hit, ticket)) {
                    val result = profile.state
                    state = state.copy(loading = false, problem = result.problem)
                    when { result.problem != null -> suppress(hit); result.detail != null -> confirmTitle(result.detail.client.title, hit); else -> back() }
                }
            })
            return
        }
        viewModelScope.launch {
            try {
                val value = when (hit.identity.kind) {
                    LoadedSearchKind.APPOINTMENTS -> repository.appointment(business, id).let {
                        if(business<=0 || id<=0 || it.business!=business || it.appointment.id!=id)throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        val knownStart=runCatching {it.appointment.start}.getOrNull()
                        val knownEnd=runCatching {it.appointment.end}.getOrNull()
                        if(knownStart!=null && knownEnd!=null && !knownEnd.isAfter(knownStart))throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.AppointmentRead(it)
                    }
                    LoadedSearchKind.INBOX -> repository.thread(business, id).let {
                        if (!it.validFor(business, id)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.ThreadRead(it)
                    }
                    LoadedSearchKind.TASKS -> repository.taskDetails(business, id).let {
                        if (!it.validFor(business, id)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.TaskRead(it)
                    }
                    LoadedSearchKind.CLIENTS -> return@launch
                }
                if (!current(hit, ticket)) return@launch
                state = state.copy(detail = value, loading = false); confirmTitle(value.title, hit)
            } catch (error: Exception) {
                if (error is CancellationException) { if (current(hit, ticket)) back(); throw error }
                if (current(hit, ticket)) { state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE); suppress(hit) }
            }
        }
    }
    private fun current(hit: LoadedSearchHit, ticket: Int) = ticket == revision && state.selected == hit && state.feed.contains(hit)
    private fun suppress(hit: LoadedSearchHit) { state = state.copy(suppressed = state.suppressed + (hit.identity to hit.token)) }
    // Independently withheld or byte-different headers never restore the old provided title.
    private fun confirmTitle(title: String?, hit: LoadedSearchHit) { if (title != hit.title) suppress(hit) }
    val control:LoadedSearchControl? get()=state.feed.takeIf {(it.business ?: 0)>0 && it.epoch>0}?.let {LoadedSearchControl(it,revision,feedVisit,queryRevision,state.selected)}
    val inputControl:LoadedSearchInputControl? get()=control?.takeIf {state.selected==null && !state.loading}?.let {LoadedSearchInputControl(it.feed,it.revision,it.feedVisit)}
    fun searchInput(value:String,input:LoadedSearchInputControl?) {if(input!=null && inputControl==input)search(value)}
    fun matches(expected:LoadedSearchControl?)=expected!=null && control==expected
    fun search(value:String,expected:LoadedSearchControl?) {if(matches(expected) && state.selected==null && !state.loading)search(value)}
    fun open(hit:LoadedSearchHit,expected:LoadedSearchControl?) {if(matches(expected) && state.selected==null && !state.loading && hit in state.matches)open(hit)}
    fun retry(expected:LoadedSearchControl?) {val hit=state.selected;if(matches(expected) && !state.loading && hit!=null)open(hit,retry=true)}
    fun back(expected:LoadedSearchControl?) {if(matches(expected) && state.selected!=null)back()}
    fun sourceTab(kind:LoadedSearchKind,expected:LoadedSearchControl?):Int?=if(matches(expected) && state.selected==null && state.feed.source(kind)!=null)kind.tab else null
    fun back() { ++revision; profile.clear(); state = state.copy(selected = null, detail = null, loading = false, problem = null) }
    override fun onCleared() { back(); profile.viewModelScope.cancel(); super.onCleared() }
}
