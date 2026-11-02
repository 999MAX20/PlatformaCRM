import Foundation
import SwiftUI
import CRMCore

// Composite source identity and local presentation stamps, never entity versions or grants.
struct AttentionControl:Equatable {let business:Int;let epoch:Int;let revision:Int;let detailRevision:Int;let identity:AttentionIdentity?}

@MainActor final class AttentionQueueViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var scopeEpoch:Int?
    @Published private(set) var items: [AttentionItem] = []
    @Published private(set) var limit = 0
    @Published private(set) var loaded = false
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    @Published var query = ""
    @Published private(set) var selectedID: AttentionIdentity?
    @Published private(set) var detail: AttentionDetail?
    @Published private(set) var detailLoading = false
    @Published private(set) var detailFailure: ReadFailure?
    private var revision = 0, detailRevision = 0
    private let repository: any AttentionRepository
    init(repository: any AttentionRepository) { self.repository = repository }
    var selected: AttentionItem? { items.first { $0.id == selectedID } }
    var windowCapped: Bool { loaded && items.count == limit }
    var visible: [AttentionItem] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return items.filter { needle.isEmpty || $0.entity.title?.range(of: needle, options: .caseInsensitive) != nil }
    }
    var showsEmpty: Bool { loaded && !loading && failure == nil && !windowCapped && visible.isEmpty }
    var control:AttentionControl? {guard let business,business>0,let scopeEpoch,scopeEpoch>0 else {return nil};return AttentionControl(business:business,epoch:scopeEpoch,revision:revision,detailRevision:detailRevision,identity:selectedID)}
    func matches(_ expected:AttentionControl?)->Bool {expected != nil && control==expected}
    func load(business next: Int?,epoch:Int?=nil) async {
        revision += 1; let ticket = revision; back()
        if business != next || scopeEpoch != epoch { query = "" }
        scopeEpoch=epoch;business = next; items = []; limit = 0; loaded = false; loading = next != nil; failure = nil
        guard let next else { return }
        guard next > 0,(epoch == nil || epoch!>0) else { loading = false; failure = .invalidContext; return }
        do {
            let page = try await repository.actions(business: next)
            guard ticket == revision else { return }
            guard page.valid(for: next) else { throw ReadFailure.invalidPayload }
            items = page.items; limit = page.limit; loaded = true; loading = false
        } catch {
            guard ticket == revision else { return }; loading = false
            if !(error is CancellationError) { failure = error as? ReadFailure ?? .unavailable }
        }
    }
    func open(_ identity: AttentionIdentity) async {
        guard let item = items.first(where: { $0.id == identity }), let target = item.readTarget, let business else { return }
        detailRevision += 1; let ticket = detailRevision, scope = revision
        selectedID = identity; detail = nil; detailLoading = true; detailFailure = nil
        do {
            let response: AttentionDetail
            switch target.kind {
            case .task: response = .task(try await repository.taskDetails(business: business, id: target.id))
            case .conversation: response = .conversation(try await repository.thread(business: business, id: target.id))
            case .appointment: response = .appointment(try await repository.appointment(business: business, id: target.id))
            }
            guard ticket == detailRevision, scope == revision else { return }
            guard response.valid(for: business, target: target) else { throw ReadFailure.invalidPayload }
            detail = response; detailLoading = false
            items = items.map { row in guard row.id == identity else { return row }; var fresh = row; fresh.entity.title = response.title; return fresh }
        } catch {
            guard ticket == detailRevision, scope == revision else { return }
            if error is CancellationError { back() }
            else { detailLoading = false; detailFailure = error as? ReadFailure ?? .unavailable }
        }
    }
    func back() { detailRevision += 1; selectedID = nil; detail = nil; detailLoading = false; detailFailure = nil }
    func search(_ value:String,expected:AttentionControl?) {guard matches(expected),!loading,selectedID==nil else {return};query=value}
    func retryList(expected:AttentionControl?) async {guard let expected,matches(expected),!loading,selectedID==nil else {return};await load(business:expected.business,epoch:expected.epoch)}
    func open(_ identity:AttentionIdentity,expected:AttentionControl?) async {guard matches(expected),loaded,!loading,failure==nil,selectedID==nil,visible.contains(where:{$0.id==identity}) else {return};await open(identity)}
    func retryDetail(expected:AttentionControl?) async {guard matches(expected),!detailLoading,let selectedID else {return};await open(selectedID)}
    func back(expected:AttentionControl?) {guard matches(expected),selectedID != nil else {return};back()}
    func reconcileOwner(business next:Int?,epoch:Int) {if business != next || scopeEpoch != epoch {clear()}}
    func clear() { revision += 1; back();scopeEpoch=nil; business = nil; items = []; limit = 0; loaded = false; loading = false; failure = nil; query = "" }
}
