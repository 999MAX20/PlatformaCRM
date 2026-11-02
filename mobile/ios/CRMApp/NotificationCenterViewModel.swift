import Foundation
import SwiftUI
import Combine
import CRMCore

// Local UI owner/visit identity, never a server version or permission grant.
struct NotificationControl:Equatable {let business:Int;let epoch:Int;let generation:Int;let notification:Int?;let appointment:Int?}

struct NotificationRouteControl:Equatable {let parent:NotificationControl;let generation:Int;let reviewing:Bool}

@MainActor final class NotificationCenterViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var items: [CRMNotification] = []
    @Published private(set) var total = 0
    @Published var query = ""
    @Published var category: String?
    @Published var unreadOnly = false
    @Published private(set) var loaded = false
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var selectedID: Int?
    @Published private(set) var targetActive = false
    @Published private(set) var targetLoading = false
    @Published private(set) var target: AppointmentDetail?
    @Published private(set) var targetFailure: ReadFailure?
    @Published private(set) var scopeEpoch:Int?
    @Published private var controlGeneration=0
    @Published private(set) var routeEditorActive = false
    @Published private(set) var routeInput = ""
    @Published private(set) var routeReviewing = false
    @Published private var routeGeneration = 0
    var routeControl:NotificationRouteControl? {
        guard routeEditorActive,let control,selected != nil,!targetActive,loaded,!loading,failure==nil else {return nil}
        return NotificationRouteControl(parent:control,generation:routeGeneration,reviewing:routeReviewing)
    }
    var routeCandidate:RelativeAppointmentCandidate? {routeReviewing ? RelativeAppointmentCandidate.parse(routeInput):nil}
    var routeCorroborated:Bool {guard let routeCandidate,let selected else {return false};return routeCandidate.corroboratedTarget(from:selected) != nil}
    func matchesRoute(_ expected:NotificationRouteControl?) -> Bool {expected != nil && routeControl==expected}
    func beginRoute(expected:NotificationControl?) {
        guard matches(expected),loaded,!loading,failure==nil,selected != nil,!targetActive,!routeEditorActive else {return}
        controlGeneration += 1;routeGeneration += 1;routeEditorActive=true;routeReviewing=false;syncMarkRead()
    }
    func editRoute(_ raw:String,expected:NotificationRouteControl?) {
        guard matchesRoute(expected),!routeReviewing else {return};routeInput=raw
    }
    func reviewRoute(expected:NotificationRouteControl?) {
        guard matchesRoute(expected),!routeReviewing else {return};routeGeneration += 1;routeReviewing=true
    }
    func backRoute(expected:NotificationRouteControl?) {
        guard matchesRoute(expected) else {return};routeGeneration += 1
        if routeReviewing {routeReviewing=false} else {controlGeneration += 1;routeEditorActive=false;syncMarkRead()}
    }
    private func resetRoute() {routeGeneration += 1;routeEditorActive=false;routeReviewing=false;routeInput=""}
    private var revision = 0, targetRevision = 0
    var control:NotificationControl? {guard let business,business>0,let scopeEpoch,scopeEpoch>0 else {return nil};return NotificationControl(business:business,epoch:scopeEpoch,generation:controlGeneration,notification:selectedID,appointment:selected?.appointmentTarget)}
    func matches(_ expected:NotificationControl?) -> Bool {expected != nil && control==expected}
    let markRead:NotificationMarkReadViewModel
    let markUnread:NotificationMarkUnreadViewModel
    private var markerObservers:Set<AnyCancellable>=[]
    private let repository: any NotificationRepository
    init(repository:any NotificationRepository,markReadSubmission:(any SyntheticNotificationMarkReadPort)?=nil,markUnreadSubmission:(any SyntheticNotificationMarkUnreadPort)?=nil) {
        self.repository=repository;markRead=NotificationMarkReadViewModel(port:markReadSubmission);markUnread=NotificationMarkUnreadViewModel(port:markUnreadSubmission)
        markRead.peerBlocked = {[weak self] in self?.markUnread.blocks($0) ?? false}
        markUnread.peerBlocked = {[weak self] in self?.markRead.blocks($0) ?? false}
        markRead.onDispatch = {[weak self] in self?.markUnread.invalidatePreparedReview()}
        markUnread.onDispatch = {[weak self] in self?.markRead.invalidatePreparedReview()}
        markRead.objectWillChange.sink {[weak self] _ in self?.objectWillChange.send()}.store(in:&markerObservers)
        markUnread.objectWillChange.sink {[weak self] _ in self?.objectWillChange.send()}.store(in:&markerObservers)
    }
    var selected: CRMNotification? { items.first { $0.id == selectedID } }
    var categories: [String] { (items.compactMap(\.category) + [category].compactMap { $0 }).reduce(into: []) { if !$0.contains($1) { $0.append($1) } } }
    var partial: Bool { total > items.count }
    var visible: [CRMNotification] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return items.filter { n in (!unreadOnly || n.unread) && (category == nil || n.category == category) && (needle.isEmpty || n.text?.range(of: needle, options: .caseInsensitive) != nil) }
    }
    var showsEmpty: Bool { loaded && !loading && failure == nil && !partial && visible.isEmpty }
    func load(business next: Int?,epoch:Int?=nil) async {
        markRead.bind(nil);markUnread.bind(nil);revision += 1; let ticket = revision; close()
        if business != next || scopeEpoch != epoch { query = ""; category = nil; unreadOnly = false }
        scopeEpoch=epoch;business = next; items = []; total = 0; loaded = false; loading = next != nil; failure = nil
        guard let next else { return }
        guard next > 0 else { loading = false; failure = .invalidContext; return }
        do {
            let page = try await repository.notifications(business: next)
            guard ticket == revision else { return }
            guard page.valid(for: next) else { throw ReadFailure.invalidPayload }
            items = page.items; total = page.summary.total; loaded = true; loading = false
        } catch {
            guard ticket == revision else { return }; loading = false
            if !(error is CancellationError) { failure = error as? ReadFailure ?? .unavailable }
        }
    }
    func open(id: Int) { if items.contains(where: { $0.id == id }) { close(); selectedID = id;syncMarkRead() } }
    func openTarget() async {await openTargetImpl()}
    func openTarget(expected:NotificationControl?) async {guard let expected else {return};await openTargetImpl(expected:expected)}
    private func openTargetImpl(expected:NotificationControl?=nil) async {
        if let expected {guard matches(expected),!targetLoading,loaded,failure==nil else {return}}
        guard !routeEditorActive,let selected, let id = selected.appointmentTarget, let business else { return }
        controlGeneration += 1;targetRevision += 1; let ticket = targetRevision, scope = revision
        targetActive = true; target = nil; targetLoading = true; targetFailure = nil;syncMarkRead()
        do {
            let payload = try await repository.appointment(business: business, id: id)
            guard ticket == targetRevision, scope == revision else { return }
            guard payload.business == business, payload.appointment.id == id, let start = payload.appointment.start, let end = payload.appointment.end, end > start else { throw ReadFailure.invalidPayload }
            target = payload; targetLoading = false
        } catch {
            guard ticket == targetRevision, scope == revision else { return }
            if error is CancellationError { backTarget() }
            else { targetLoading = false; targetFailure = error as? ReadFailure ?? .unavailable }
        }
    }
    func backTarget() {controlGeneration += 1; targetRevision += 1; targetActive = false; target = nil; targetLoading = false; targetFailure = nil;syncMarkRead() }
    func close() { resetRoute();backTarget(); selectedID = nil;syncMarkRead() }
    private func syncMarkRead() {
        guard !routeEditorActive,!targetActive,loaded,!loading,failure==nil,let control,let selected else {markRead.bind(nil);markUnread.bind(nil);return}
        markRead.bind(NotificationMarkReadSource(context:NotificationMarkReadContext(business:control.business,notification:selected.id,epoch:control.epoch),generation:control.generation,notification:selected))
        markUnread.bind(NotificationMarkUnreadSource(context:NotificationMarkUnreadContext(business:control.business,notification:selected.id,epoch:control.epoch),generation:control.generation,notification:selected))
    }
    func clear() { revision += 1; close();scopeEpoch=nil; business = nil; items = []; total = 0; query = ""; category = nil; unreadOnly = false; loaded = false; loading = false; failure = nil }
}

extension NotificationCenterViewModel {
    func reconcileOwner(business next:Int?,epoch:Int) {if business != next || scopeEpoch != epoch {clear()}}
    func search(_ value:String,expected:NotificationControl?) {guard matches(expected),!loading,selectedID==nil else {return};query=value}
    func filterCategory(_ value:String?,previous:String?,expected:NotificationControl?) {guard matches(expected),!loading,selectedID==nil,category==previous else {return};category=value}
    func filterUnread(_ value:Bool,previous:Bool,expected:NotificationControl?) {guard matches(expected),!loading,selectedID==nil,unreadOnly==previous else {return};unreadOnly=value}
    func open(id:Int,expected:NotificationControl?) {guard matches(expected),loaded,!loading,failure==nil,selectedID==nil,visible.contains(where:{$0.id==id}) else {return};open(id:id)}
    func retryList(expected:NotificationControl?) async {guard let expected,matches(expected),!loading,selectedID==nil else {return};await load(business:expected.business,epoch:expected.epoch)}
    func close(expected:NotificationControl?) {guard matches(expected) else {return};close()}
    func backTarget(expected:NotificationControl?) {guard matches(expected),targetActive else {return};backTarget()}
}
