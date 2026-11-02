import Foundation
import SwiftUI
import CRMCore

// Existing feed plus local visit identity, never a server revision or grant.
struct LoadedSearchControl:Equatable {let feed:LoadedSearchFeed;let revision:Int;let feedVisit:Int;let queryRevision:Int;let selected:LoadedSearchHit?}

// Continuous list input excludes the query action stamp, retaining its read/feed visit.
struct LoadedSearchInputControl:Equatable {let feed:LoadedSearchFeed;let revision:Int;let feedVisit:Int}

@MainActor final class LoadedSearchViewModel: ObservableObject {
    @Published private(set) var feed = LoadedSearchFeed(business: nil, epoch: 0, sources: [])
    @Published var query = "" {didSet {if !query.utf8.elementsEqual(oldValue.utf8) {queryRevision += 1}}}
    @Published private(set) var selected: LoadedSearchHit?
    @Published private(set) var detail: AttentionDetail?
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var suppressed: [LoadedSearchIdentity: LoadedSearchToken] = [:]
    let profile: ClientProfileViewModel
    private var revision = 0
    private var queryRevision = 0 // Raw UI action window only, never the independent read ticket.
    private var feedVisit = 0 // Local UI visit only; independent read tickets remain on revision.
    private let repository: APIReadRepository
    init(repository: APIReadRepository) { self.repository = repository; profile = ClientProfileViewModel(repository: repository) }
    var matches: [LoadedSearchHit] { feed.matches(query, excluding: Set(suppressed.keys)) }
    var showsNoMatches: Bool { !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && feed.hasLoadedSource && matches.isEmpty }
    func coverage(_ source: LoadedSearchSource) -> LoadedSearchCoverage {
        source.coverage.ready && suppressed.keys.contains(where: { $0.kind == source.kind }) ? .partial : source.coverage
    }
    func reconcile(_ next: LoadedSearchFeed) {
        guard next != feed else { return }
        feedVisit += 1
        if next.business != feed.business || next.epoch != feed.epoch { back(); query = ""; suppressed = [:] }
        else {
            if let selected, !next.contains(selected) { back() }
            suppressed = suppressed.filter { next.source($0.key.kind)?.token == $0.value }
        }
        feed = next
    }
    func open(_ hit: LoadedSearchHit, retry: Bool = false) async {
        guard feed.contains(hit), (retry && selected == hit) || suppressed[hit.id] == nil else { return }
        revision += 1; let ticket = revision
        selected = hit; detail = nil; failure = nil; loading = true; profile.clear()
        let business = hit.id.business, id = hit.id.id
        if hit.id.kind == .clients {
            await profile.load(business: business, id: id)
            guard current(hit, ticket) else { return }
            loading = false
            if let failure = profile.failure { self.failure = failure; suppressed[hit.id] = hit.token }
            else if let value = profile.detail { confirmTitle(value.client.title, hit: hit) }
            else { back() }
            return
        }
        do {
            let value: AttentionDetail
            switch hit.id.kind {
            case .appointments:
                let result = try await repository.appointment(business: business, id: id)
                guard AttentionDetail.appointment(result).valid(for:business,target:AttentionTarget(kind:.appointment,id:id)) else {throw ReadFailure.invalidPayload}
                value = .appointment(result)
            case .inbox:
                let result = try await repository.thread(business: business, id: id)
                guard result.valid(for: business, id: id) else { throw ReadFailure.invalidPayload }
                value = .conversation(result)
            case .tasks:
                let result = try await repository.taskDetails(business: business, id: id)
                guard result.valid(for: business, id: id) else { throw ReadFailure.invalidPayload }
                value = .task(result)
            case .clients: return
            }
            guard current(hit, ticket) else { return }
            detail = value; loading = false; confirmTitle(value.title, hit: hit)
        } catch {
            guard current(hit, ticket) else { return }
            if error is CancellationError { back() }
            else { loading = false; failure = error as? ReadFailure ?? .unavailable; suppressed[hit.id] = hit.token }
        }
    }
    private func current(_ hit: LoadedSearchHit, _ ticket: Int) -> Bool { ticket == revision && selected == hit && feed.contains(hit) }
    private func confirmTitle(_ title: String?, hit: LoadedSearchHit) {
        // Do not restore an old list title after an independently withheld/changed header.
        if !LoadedSearchHeader.same(title,hit.title) { suppressed[hit.id] = hit.token }
    }
    var control:LoadedSearchControl? {guard let business=feed.business,business>0,feed.epoch>0 else {return nil};return LoadedSearchControl(feed:feed,revision:revision,feedVisit:feedVisit,queryRevision:queryRevision,selected:selected)}
    var inputControl:LoadedSearchInputControl? {guard let control,selected==nil,!loading else {return nil};return LoadedSearchInputControl(feed:control.feed,revision:control.revision,feedVisit:control.feedVisit)}
    func search(_ value:String,input:LoadedSearchInputControl?) {guard let input,inputControl==input else {return};query=value}
    func matches(_ expected:LoadedSearchControl?)->Bool {expected != nil && control==expected}
    func search(_ value:String,expected:LoadedSearchControl?) {guard matches(expected),selected==nil,!loading else {return};query=value}
    func open(_ hit:LoadedSearchHit,expected:LoadedSearchControl?) async {guard matches(expected),selected==nil,!loading,matches.contains(hit) else {return};await open(hit)}
    func retry(expected:LoadedSearchControl?) async {guard matches(expected),!loading,let selected else {return};await open(selected,retry:true)}
    func back(expected:LoadedSearchControl?) {guard matches(expected),selected != nil else {return};back()}
    func sourceTab(_ kind:LoadedSearchKind,expected:LoadedSearchControl?)->Int? {guard matches(expected),selected==nil,feed.source(kind) != nil else {return nil};return kind.tab}
    func back() { revision += 1; selected = nil; detail = nil; loading = false; failure = nil; profile.clear() }
}
