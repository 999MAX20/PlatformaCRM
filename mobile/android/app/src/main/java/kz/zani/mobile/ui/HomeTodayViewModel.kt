package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.HomeTodayRepository
import java.time.LocalDate
import java.time.ZoneId

// Local owner/read/presentation stamps, not server versions or grants.
data class HomeOwnerControl(val business:Int,val day:String,val epoch:Int,val generation:Int)
enum class HomeSection {HOME,TODAY}
data class HomeSectionControl(val owner:HomeOwnerControl,val section:HomeSection,val revision:Int,val presentation:Int)
data class HomeNavigationControl(val owner:HomeOwnerControl,val generation:Int,val destination:HomeDestination?)

data class HomeTodayState(val business: Int? = null, val day: String? = null, val home: HomeSummary? = null, val today: TodaySummary? = null,
    val homeLoading: Boolean = false, val todayLoading: Boolean = false, val homeProblem: ReadProblem? = null, val todayProblem: ReadProblem? = null,
    val destination: HomeDestination? = null, val navigationPending: Boolean = false,val scopeEpoch:Int?=null)

class HomeTodayViewModel(private val repository: HomeTodayRepository, private val currentDay: (String) -> String = { LocalDate.now(ZoneId.of(it)).toString() }) : ViewModel() {
    var state by mutableStateOf(HomeTodayState()); private set
    private var homeRevision = 0
    private var todayRevision = 0
    private var ownerRevision by mutableStateOf(0)
    private var navigationRevision by mutableStateOf(0)
    fun day(timezone: String) = currentDay(timezone)
    val owner:HomeOwnerControl? get() {val business=state.business?.takeIf {it>0} ?: return null;val day=state.day ?: return null;val epoch=state.scopeEpoch?.takeIf {it>0} ?: return null;return if(runCatching {LocalDate.parse(day).toString()==day}.getOrDefault(false))HomeOwnerControl(business,day,epoch,ownerRevision) else null}
    val homeControl get()=owner?.let {HomeSectionControl(it,HomeSection.HOME,homeRevision,navigationRevision)}
    val todayControl get()=owner?.let {HomeSectionControl(it,HomeSection.TODAY,todayRevision,navigationRevision)}
    val navigationControl get()=owner?.let {HomeNavigationControl(it,navigationRevision,state.destination)}
    fun matches(expected:HomeNavigationControl?)=expected!=null && navigationControl==expected
    fun start(business: Int, day: String,epoch:Int?=null) {
        if (state.business == business && state.day == day && state.scopeEpoch==epoch) return
        clear(); state = HomeTodayState(business = business, day = day,scopeEpoch=epoch)
        if (business < 1 || (epoch!=null && epoch<=0) || runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) {
            state = state.copy(homeProblem = ReadProblem.INVALID_CONTEXT, todayProblem = ReadProblem.INVALID_CONTEXT); return
        }
        reloadHome(); reloadToday()
    }
    fun reloadHome() {
        val business = state.business?.takeIf { it > 0 } ?: return
        val ticket = ++homeRevision; state = state.copy(home = null, homeProblem = null, homeLoading = true)
        viewModelScope.launch {
            try {
                val response = repository.home(business)
                if (ticket != homeRevision) return@launch
                if (!response.validFor(business)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(home = response, homeLoading = false)
            } catch (error: Exception) {
                if (ticket != homeRevision) return@launch
                state = state.copy(homeLoading = false, homeProblem = if (error is CancellationException) null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if (error is CancellationException) throw error
            }
        }
    }
    fun reloadToday() {
        val business = state.business?.takeIf { it > 0 } ?: return; val day = state.day ?: return
        if (runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) return
        val ticket = ++todayRevision; state = state.copy(today = null, todayProblem = null, todayLoading = true)
        viewModelScope.launch {
            try {
                val response = repository.today(business, day)
                if (ticket != todayRevision) return@launch
                if (!response.validFor(business, day)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(today = response, todayLoading = false)
            } catch (error: Exception) {
                if (ticket != todayRevision) return@launch
                state = state.copy(todayLoading = false, todayProblem = if (error is CancellationException) null else (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                if (error is CancellationException) throw error
            }
        }
    }
    fun reloadHome(expected:HomeSectionControl?) {if(expected!=null && homeControl==expected && !state.homeLoading && state.destination==null)reloadHome()}
    fun reloadToday(expected:HomeSectionControl?) {if(expected!=null && todayControl==expected && !state.todayLoading && state.destination==null)reloadToday()}
    fun open(target:HomeDestination,expected:HomeNavigationControl?) {if(matches(expected) && state.destination==null)open(target)}
    fun open(target: HomeDestination) { if ((state.business ?: 0) > 0) {++navigationRevision;state = state.copy(destination = target, navigationPending = true)} }
    fun takeNavigation(expected:HomeNavigationControl?):HomeDestination?=if(matches(expected))takeNavigation() else null
    // A retained UI event acknowledgement. Recreating the composition must not
    // close an already-open child or replay a consumed Home navigation.
    fun takeNavigation(): HomeDestination? {
        if (!state.navigationPending) return null
        val target = state.destination ?: return null
        state = state.copy(navigationPending = false)
        return target
    }
    fun back(expected:HomeNavigationControl?) {if(matches(expected))back()}
    fun back() {++navigationRevision;state = state.copy(destination = null, navigationPending = false) }
    fun reconcileOwner(business:Int?,epoch:Int) {if(state.business!=business || state.scopeEpoch!=epoch)clear()}
    fun clear() {++ownerRevision;++navigationRevision;++homeRevision; ++todayRevision; state = HomeTodayState() }
}
