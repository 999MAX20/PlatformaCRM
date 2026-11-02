import Foundation
import SwiftUI
import CRMCore

// A local read generation, not a server session/access contract.
struct InboxReadSelection: Equatable { let business: Int; let id: Int; let revision: Int }
struct InboxClientPresentation:Equatable {let request:InboxReadSelection;let selectedID:Int?;let generation:Int}
// Local UI snapshots, never source versions, credentials or permission evidence.
struct InboxClientEntryControl:Equatable {let presentation:InboxClientPresentation}
struct InboxClientControl:Equatable {let presentation:InboxClientPresentation;let profile:ClientReadSelection?;let loading:Bool;let profileLoading:Bool}
struct InboxClientReturnControl:Equatable {let inspector:InboxClientControl;let work:ClientWorkControl?;let edit:ClientEditControl?;let editDialog:ClientEditConfirmation?}
@MainActor final class InboxClientViewModel: ObservableObject {
    @Published private(set) var request: InboxReadSelection?
    @Published private(set) var parent: InboxThread?
    @Published private(set) var selectedID: Int?
    @Published private(set) var loading = false
    let profile: ClientProfileViewModel
    @Published private var revision = 0
    var presentation:InboxClientPresentation? {request.map {InboxClientPresentation(request:$0,selectedID:selectedID,generation:revision)}}
    var entryControl:InboxClientEntryControl? {guard let presentation,selectedID==nil,!loading,parent?.clientReferenceID != nil else {return nil};return InboxClientEntryControl(presentation:presentation)}
    var control:InboxClientControl? {presentation.map {InboxClientControl(presentation:$0,profile:profile.readSelection,loading:loading,profileLoading:profile.loading)}}
    var returnControl:InboxClientReturnControl? {control.map {InboxClientReturnControl(inspector:$0,work:profile.work?.presentation,edit:profile.edit?.control,editDialog:profile.edit?.confirmation)}}
    private let repository: any InboxClientRepository
    private var onThread: (@MainActor (Result<InboxThread,ReadFailure>) -> Void)?
    init(repository: any InboxClientRepository) { self.repository = repository; profile = ClientProfileViewModel(repository: repository) }
    func bind(_ thread: InboxThread, request: InboxReadSelection, onThread: @escaping @MainActor (Result<InboxThread,ReadFailure>) -> Void) {
        clear()
        guard request.revision > 0, thread.valid(for: request.business,id: request.id) else { return }
        self.request = request; parent = thread; self.onThread = onThread
    }
    func open(expected:InboxReadSelection?=nil) async {await openImpl(expected:expected)}
    func open(presentation:InboxClientPresentation?) async {guard let presentation else {return};await openImpl(expected:presentation.request,presentation:presentation)}
    private func openImpl(expected: InboxReadSelection?,presentation:InboxClientPresentation?=nil) async {
        if let presentation,presentation != self.presentation {return}
        if let expected, expected != request { return }
        guard let scope = request, let id = parent?.clientReferenceID else { return }
        back(); selectedID = id; loading = true; let ticket = revision,callback=onThread
        // Re-read the existing bounded thread before using its explicit Client ID.
        // A changed/withheld link closes the dependent profile; no cached join.
        do {
            let fresh = try await repository.thread(business: scope.business,id: scope.id)
            guard current(scope,id,ticket) else { return }
            guard fresh.valid(for: scope.business,id: scope.id) else { throw ReadFailure.invalidPayload }
            parent = fresh
            guard current(scope,id,ticket) else {return}
            callback?(.success(fresh))
            guard current(scope,id,ticket) else {return}
            guard fresh.clientReferenceID == id else { back(); return }
        } catch {
            guard current(scope,id,ticket) else { return }
            if !(error is CancellationError) {
                callback?(.failure(error as? ReadFailure ?? .unavailable))
                guard current(scope,id,ticket) else {return}
                parent = nil
            }
            guard current(scope,id,ticket) else {return}
            back(); return
        }
        guard current(scope,id,ticket) else {return}
        await profile.load(business: scope.business,id: id)
        guard current(scope,id,ticket) else { return }
        loading = false
        if profile.detail == nil && profile.failure == nil { back() }
    }
    private func current(_ scope: InboxReadSelection,_ id: Int,_ ticket: Int) -> Bool { request == scope && selectedID == id && revision == ticket }
    @discardableResult func back(expected: InboxReadSelection? = nil) -> Bool {
        if let expected, expected != request { return false }
        let hadChild = selectedID != nil
        revision += 1; selectedID = nil; loading = false; profile.clear(); return hadChild
    }
    @discardableResult func back(presentation:InboxClientPresentation?) -> Bool {guard let presentation,self.presentation==presentation else {return false};return back(expected:presentation.request)}
    func clear() { back(); request = nil; parent = nil; onThread = nil }
    // Captured UI entry/retry/close; trusted raw methods above remain available.
    func open(entry:InboxClientEntryControl?) async {guard let entry,entryControl==entry else {return};await open(presentation:entry.presentation)}
    func retry(expected:InboxClientControl?) async {
        guard let expected,control==expected,selectedID != nil,!loading,!profile.loading,profile.work?.selected==nil,profile.edit?.control==nil else {return}
        await open(presentation:expected.presentation)
    }
    @discardableResult func close(expected:InboxClientReturnControl?) -> Bool {
        guard let expected,returnControl==expected,selectedID != nil,expected.work?.target==nil,expected.edit==nil,expected.editDialog==nil else {return false}
        return back(presentation:expected.inspector.presentation)
    }
}
