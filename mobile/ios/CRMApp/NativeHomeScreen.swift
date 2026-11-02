import SwiftUI
import CRMCore

struct NativeHomeScreen: View {
    @StateObject var attention: AttentionQueueViewModel
    @StateObject var home: HomeTodayViewModel
    @StateObject var agenda: AgendaViewModel
    @StateObject var clients: ClientDirectoryViewModel
    @StateObject var profile: ClientProfileViewModel
    @StateObject var inbox: InboxViewModel
    @StateObject var tasks: TaskListViewModel
    @StateObject var notifications: NotificationCenterViewModel
    @StateObject var search: LoadedSearchViewModel
    private var searchFeed: LoadedSearchFeed { LoadedSearchSources.feed(agenda: agenda, clients: clients, inbox: inbox, tasks: tasks) }
    @State private var tab = 0
    private func closeDetails() { agenda.closeDetail(); clients.back(); profile.clear(); inbox.back(); tasks.back(); notifications.close(); attention.back(); search.back() }
    private func ownsHome(_ control:HomeNavigationControl?)->Bool {guard let control else {return false};return home.matches(control) && agenda.session.selection?.business.id==control.owner.business && agenda.businessEpoch==control.owner.epoch}
    var body: some View {
        let navigation=home.navigationControl
        VStack(spacing: 0) {
            if home.destination != nil,ownsHome(navigation) {
                Button(AppCopy.text("back") + " · " + AppCopy.text("home")) {if ownsHome(navigation) {closeDetails();home.back(expected:navigation);tab=0}}.padding(.vertical, 8)
            }
            TabView(selection: $tab) {
                HomeTodayScreen(agenda: agenda, model: home).tabItem { Label(AppCopy.text("home"), systemImage: "house") }.tag(0)
                AgendaScreen(model: agenda).tabItem { Label(AppCopy.text("appointments"), systemImage: "calendar") }.tag(1)
                ClientDirectoryScreen(agenda: agenda, model: clients, profile: profile, isActive: tab == 2).tabItem { Label(AppCopy.text("clients"), systemImage: "person.2") }.tag(2)
                InboxScreen(agenda: agenda, model: inbox, isActive: tab == 3).tabItem { Label(AppCopy.text("inbox"), systemImage: "tray") }.tag(3)
                TaskListScreen(agenda: agenda, model: tasks, isActive: tab == 4).tabItem { Label(AppCopy.text("tasks"), systemImage: "checklist") }.tag(4)
                NotificationCenterScreen(agenda: agenda, model: notifications).tabItem { Label(AppCopy.text("notifications"), systemImage: "bell") }.tag(5)
                AttentionQueueScreen(agenda: agenda, model: attention).tabItem { Label(AppCopy.text("attention"), systemImage: "exclamationmark.circle") }.tag(6)
                LoadedSearchScreen(agenda: agenda, model: search, feed:searchFeed,openSource:{tab=$0},isCurrentFeed:{searchFeed==$0}).tabItem { Label(AppCopy.text("inboxSearch"), systemImage: "magnifyingglass") }.tag(7)
            }
        }
        .tint(Color(red: 217 / 255, green: 103 / 255, blue: 24 / 255))
        .task { search.reconcile(searchFeed); await agenda.start() }
        .onChange(of: searchFeed) { _, next in search.reconcile(next) }
        .onChange(of: agenda.businessEpoch) { _, next in clients.reconcileOwner(business:agenda.session.selection?.business.id,epoch:next);profile.reconcileOwner(business:agenda.session.selection?.business.id,epoch:next) }
        .onChange(of: agenda.businessEpoch) { _, next in notifications.reconcileOwner(business:agenda.session.selection?.business.id,epoch:next) }
        .onChange(of: agenda.businessEpoch) { _, next in tasks.reconcileCommentOwner(business:agenda.session.selection?.business.id,epoch:next) }
        .onChange(of: agenda.businessEpoch) { _, next in inbox.reconcileHandoffOwner(business:agenda.session.selection?.business.id,epoch:next) }
        .onChange(of: agenda.businessEpoch) { _, next in home.reconcileOwner(business:agenda.session.selection?.business.id,epoch:next);attention.reconcileOwner(business:agenda.session.selection?.business.id,epoch:next) }
        .onChange(of: home.navigationControl,initial:true) { _, control in
            if ownsHome(control),let target=home.takeNavigation(expected:control) {closeDetails();tab=target.tabIndex}
        }
        .onChange(of: tab) { _, next in if next != home.destination?.tabIndex { home.back() }; if next != 6 { attention.back() }; if next != 1 { agenda.closeDetail() }; if next != 7 { search.back() } }
        .onChange(of: agenda.session.selection?.business.id) { _, next in
            if attention.business != nil && attention.business != next { attention.clear() }
            if home.business != nil && home.business != next { home.clear() }
            if notifications.business != nil && notifications.business != next { notifications.clear() }
            if profile.business != nil && profile.business != next { profile.clear() }
        }
    }
}
