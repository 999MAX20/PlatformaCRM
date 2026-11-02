import Foundation
import SwiftUI
import CRMCore

// Captured local UI identity only: never an entity version, permission or wire key.
struct ClientDirectoryControl: Equatable {let business:Int;let epoch:Int;let generation:Int;let selectedID:Int?}

// A list callback cannot switch a current child. Raw trusted switches remain below.
struct ClientDirectoryListControl:Equatable {let parent:ClientDirectoryControl}
@MainActor final class ClientDirectoryViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var items: [ClientContact] = []
    @Published var query = ""
    @Published private(set) var selectedID: Int?
    @Published private(set) var total = 0
    @Published private(set) var loading = false
    @Published private(set) var loaded = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var searchRevision = 0
    @Published private(set) var scopeEpoch: Int?
    let draft:ClientDraftViewModel
    let serverSearch: ClientSearchViewModel?
    private var revision = 0
    @Published private var controlGeneration = 0
    var control:ClientDirectoryControl? {guard let business,business>0,let scopeEpoch,scopeEpoch>0 else {return nil};return ClientDirectoryControl(business:business,epoch:scopeEpoch,generation:controlGeneration,selectedID:selectedID)}
    func matches(_ expected:ClientDirectoryControl?) -> Bool {expected != nil && control==expected}
    var listControl:ClientDirectoryListControl? {guard let parent=control,selectedID==nil,draft.control==nil,serverSearch?.session.selection==nil else {return nil};return ClientDirectoryListControl(parent:parent)}
    func matchesList(_ expected:ClientDirectoryListControl?) -> Bool {expected != nil && listControl==expected}
    private let repository: any ClientRepository
    init(repository:any ClientRepository,createSubmission:(any SyntheticClientCreatePort)?=nil,duplicateSource:(any SyntheticClientDuplicatePreviewSource)?=nil) { self.repository = repository;draft=ClientDraftViewModel(port:createSubmission,duplicates:duplicateSource);serverSearch=(repository as? any ClientSearchRepository).map {ClientSearchViewModel(repository:$0)} }
    var partial: Bool { total > items.count }
    var selected: ClientContact? { items.first { $0.id == selectedID } }
    var visible: [ClientContact] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        return needle.isEmpty ? items : items.filter { client in
            [client.title, client.phone, client.email].compactMap { $0 }.contains { $0.range(of: needle, options: .caseInsensitive) != nil }
        }
    }
    var showsEmpty: Bool { loaded && !loading && failure == nil && !partial && visible.isEmpty }
    func load(business next: Int?, epoch: Int? = nil) async {
        serverSearch?.bind(next.flatMap { business in epoch.flatMap {$0>0 && business>0 ? ClientSearchContext(business:business,epoch:$0) : nil} })
        draft.bind(next.flatMap { business in epoch.flatMap { $0 > 0 && business > 0 ? ClientDraftContext(business:business,epoch:$0) : nil } })
        searchRevision += 1;controlGeneration += 1
        revision += 1; let ticket = revision
        if business != next || scopeEpoch != epoch { query = "" }
        scopeEpoch = epoch; business = next; items = []; total = 0; selectedID = nil; failure = nil; loaded = false
        loading = next != nil
        guard let next else { return }
        guard next > 0 else { loading = false; failure = .invalidContext; return }
        do {
            let page = try await repository.clients(business: next)
            guard ticket == revision else { return }
            guard page.business == next, page.summary.total >= page.items.count,
                  page.items.allSatisfy({ $0.id > 0 }), Set(page.items.map(\.id)).count == page.items.count else { throw ReadFailure.invalidPayload }
            items = page.items; total = page.summary.total; loading = false; loaded = true
        } catch {
            guard ticket == revision else { return }
            loading = false
            if !(error is CancellationError) { failure = error as? ReadFailure ?? .unavailable; if failure == .denied {serverSearch?.bind(nil)} }
        }
    }
    // UI owner generation only, not current authenticated session/permission evidence.
    func reconcileOwner(business next:Int?,epoch:Int) {
        guard business != next || scopeEpoch != epoch else {return}
        revision += 1;controlGeneration += 1;searchRevision += 1;serverSearch?.bind(nil);draft.bind(nil)
        business=nil;scopeEpoch=nil;items=[];total=0;selectedID=nil;query="";failure=nil;loaded=false;loading=false
    }
    func open(id: Int) { if items.contains(where: { $0.id == id }) { if let selection=draft.session.selection { draft.close(selection) }; selectedID = id;controlGeneration += 1 } }
    func back() { if let selection=serverSearch?.session.selection {serverSearch?.close(selection)}; if let selection=draft.session.selection { draft.close(selection) }; selectedID = nil;controlGeneration += 1 }
    func refreshContact(business: Int, contact: ClientContact) {
        if self.business == business && selectedID == contact.id { searchRevision += 1; items = items.map { $0.id == contact.id ? contact : $0 } }
    }
}

extension ClientDirectoryViewModel {
    func search(_ value:String,expected:ClientDirectoryControl?) {guard matches(expected),!loading,selectedID==nil else {return};query=value}
    @discardableResult func open(id:Int,expected:ClientDirectoryControl?) -> Bool {
        guard matches(expected),loaded,!loading,failure==nil,visible.contains(where:{$0.id==id}) else {return false};open(id:id);return true
    }
    @discardableResult func back(expected:ClientDirectoryControl?) -> Bool {guard matches(expected) else {return false};back();return true}
    func retry(expected:ClientDirectoryControl?) async {guard matches(expected),!loading,let expected else {return};await load(business:expected.business,epoch:expected.epoch)}
    func refreshContact(business:Int,contact:ClientContact,expected:ClientDirectoryControl?) {guard matches(expected),!loading else {return};refreshContact(business:business,contact:contact)}
    @discardableResult func openDraft(expected:ClientDirectoryControl?) -> Bool {
        guard matches(expected),loaded,!loading,failure==nil,let expected else {return false};back();draft.open(ClientDraftContext(business:expected.business,epoch:expected.epoch));return draft.session.selection != nil
    }
    @discardableResult func openSearch(expected:ClientDirectoryControl?) -> Bool {
        guard matches(expected),!loading,let expected,let serverSearch else {return false};back();serverSearch.open(ClientSearchContext(business:expected.business,epoch:expected.epoch));return serverSearch.session.selection != nil
    }
    // UI-only list controls supplement the trusted parent-generation APIs above.
    func search(_ value:String,list:ClientDirectoryListControl?) {guard let list,matchesList(list) else {return};search(value,expected:list.parent)}
    @discardableResult func open(id:Int,list:ClientDirectoryListControl?) -> Bool {guard let list,matchesList(list) else {return false};return open(id:id,expected:list.parent)}
    func retry(list:ClientDirectoryListControl?) async {guard let list,matchesList(list) else {return};await retry(expected:list.parent)}
    @discardableResult func openDraft(expected:ClientDraftEntryControl?,list:ClientDirectoryListControl?) -> Bool {
        guard let expected,let list,matchesList(list),draft.entryControl==expected,expected.context.business==list.parent.business,expected.context.epoch==list.parent.epoch else {return false}
        return openDraft(expected:list.parent)
    }
    @discardableResult func openSearch(list:ClientDirectoryListControl?) -> Bool {guard let list,matchesList(list) else {return false};return openSearch(expected:list.parent)}
}
