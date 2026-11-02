package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable fun NativeHomeScreen(attention: AttentionQueueViewModel, home: HomeTodayViewModel, agenda: AgendaViewModel, clients: ClientDirectoryViewModel, profile: ClientProfileViewModel, inbox: InboxViewModel, tasks: TaskListViewModel, notifications: NotificationCenterViewModel, search: LoadedSearchViewModel, copy: Map<String, String>, language: String) {
    var tab by rememberSaveable { mutableIntStateOf(0) }
    fun closeDetails() { agenda.back(); clients.back(); profile.clear(); inbox.back(); tasks.back(); notifications.close(); attention.back(); search.back() }
    val navigation=home.navigationControl
    fun ownsHome()=navigation!=null && home.matches(navigation) && agenda.state.selection?.business?.id==navigation.owner.business && agenda.state.businessEpoch==navigation.owner.epoch
    fun returnHome() {if(ownsHome()) {closeDetails();home.back(navigation);tab=0}}
    LaunchedEffect(Unit) { agenda.start() }
    LaunchedEffect(navigation) {if(ownsHome())home.takeNavigation(navigation)?.let {closeDetails();tab=it.tabIndex}}
    val feed = LoadedSearchSources.feed(agenda.state, clients.state, inbox.state, tasks.state)
    SideEffect { search.reconcile(feed) }
    val business = agenda.state.selection?.business?.id
    LaunchedEffect(business,agenda.state.businessEpoch) {clients.reconcileOwner(business,agenda.state.businessEpoch);profile.reconcileOwner(business,agenda.state.businessEpoch)}
    LaunchedEffect(business,agenda.state.businessEpoch) {home.reconcileOwner(business,agenda.state.businessEpoch);attention.reconcileOwner(business,agenda.state.businessEpoch)}
    LaunchedEffect(business,agenda.state.businessEpoch) {notifications.reconcileOwner(business,agenda.state.businessEpoch)}
    LaunchedEffect(business,agenda.state.businessEpoch) {tasks.reconcileCommentOwner(business,agenda.state.businessEpoch)}
    LaunchedEffect(business,agenda.state.businessEpoch) {inbox.reconcileHandoffOwner(business,agenda.state.businessEpoch)}
    LaunchedEffect(business) {
        if (attention.state.business != null && attention.state.business != business) attention.load(null)
        if (home.state.business != null && home.state.business != business) home.clear()
        if (notifications.state.business != null && notifications.state.business != business) notifications.load(null)
        if (profile.state.business != null && profile.state.business != business) profile.clear()
    }
    BackHandler(enabled = home.state.destination != null && ownsHome(), onBack = ::returnHome)
    Column(Modifier.fillMaxSize().safeDrawingPadding()) {
        if (home.state.destination != null && ownsHome()) TextButton(onClick = ::returnHome) { Text((copy["back"] ?: "back") + " · " + (copy["home"] ?: "home")) }
        ScrollableTabRow(selectedTabIndex = tab, edgePadding = 0.dp) {
            listOf("home", "appointments", "clients", "inbox", "tasks", "notifications", "attention", "inboxSearch").forEachIndexed { index, key ->
                Tab(selected = tab == index, onClick = {
                    if (index != tab) { closeDetails(); home.back(); tab = index }
                }, text = { Text(copy[key] ?: key) })
            }
        }
        Box(Modifier.weight(1f)) {
            when (tab) {
                0 -> HomeTodayScreen(agenda, home, copy, language)
                1 -> AgendaScreen(agenda, copy, language)
                2 -> ClientDirectoryScreen(agenda, clients, profile, copy, language)
                3 -> InboxScreen(agenda, inbox, copy, language)
                4 -> TaskListScreen(agenda, tasks, copy, language)
                5 -> NotificationCenterScreen(agenda, notifications, copy, language)
                6 -> AttentionQueueScreen(agenda, attention, copy, language)
                else -> LoadedSearchScreen(agenda,search,feed,copy,language,openSource={tab=it},isCurrentFeed={LoadedSearchSources.feed(agenda.state,clients.state,inbox.state,tasks.state)==it})
            }
        }
    }
}
