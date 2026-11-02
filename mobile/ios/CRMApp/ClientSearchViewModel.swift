import Foundation
import SwiftUI
import CRMCore

// Local feature/input/window visits; never server versions, permissions or request keys.
struct ClientSearchInputControl:Equatable {let selection:ClientSearchSelection;let generation:Int}
struct ClientSearchControl:Equatable {let selection:ClientSearchSelection;let generation:Int;let profile:ClientSearchProfileSelection?;let read:ClientReadSelection?}

@MainActor final class ClientSearchViewModel: ObservableObject {
    @Published private(set) var session=ClientSearchSession()
    @Published private var windowRevision=0
    @Published private var inputRevision=0
    let profile: ClientProfileViewModel
    private let repository: any ClientSearchRepository
    init(repository: any ClientSearchRepository) {self.repository=repository;profile=ClientProfileViewModel(repository:repository)}
    func bind(_ context: ClientSearchContext?) {
        if session.context != context {profile.clear()}
        let previous=session.context;session.bind(context);if session.context != previous {windowRevision += 1;inputRevision += 1}
    }
    func open(_ context: ClientSearchContext) {
        guard session.context==context else {return}
        profile.clear();if session.open(expected:context) {windowRevision += 1;inputRevision += 1}
    }
    func update(_ query: String,_ selection: ClientSearchSelection) {
        guard session.selection==selection else {return}
        if !query.utf8.elementsEqual(session.query.utf8) {windowRevision += 1;if session.profileSelection != nil {inputRevision += 1};profile.clear()};session.update(query,expected:selection)
    }
    func clear(_ selection: ClientSearchSelection) {
        guard session.selection==selection else {return};windowRevision += 1;inputRevision += 1;profile.clear();session.clear(expected:selection)
    }
    func submit(_ selection: ClientSearchSelection) async {
        let hadProfile=session.profileSelection != nil
        guard let request=session.begin(expected:selection) else {return}
        windowRevision += 1;let ticket=windowRevision;if hadProfile {inputRevision += 1}
        profile.clear()
        do {
            let page=try await repository.searchClients(business:selection.context.business,search:request.query)
            session.accept(page,request:request)
        } catch {
            if error is CancellationError {session.cancel(request:request)}
            else {session.fail(error as? ReadFailure ?? .unavailable,request:request)}
        }
        if windowRevision==ticket {windowRevision += 1}
    }
    func openClient(_ id: Int,_ selection: ClientSearchSelection) async {
        guard session.select(id:id,expected:selection) else {return}
        windowRevision += 1;inputRevision += 1;let ticket=windowRevision,selected=session.profileSelection
        profile.clear();await profile.load(business:selection.context.business,id:id)
        if windowRevision==ticket,session.profileSelection==selected {windowRevision += 1}
    }
    func retryProfile(_ selection: ClientSearchSelection,expectedProfile: ClientSearchProfileSelection) async {
        guard session.selection==selection,session.profileSelection==expectedProfile else {return}
        windowRevision += 1;let ticket=windowRevision
        await profile.load(business:selection.context.business,id:expectedProfile.id)
        if windowRevision==ticket,session.profileSelection==expectedProfile {windowRevision += 1}
    }
    func backProfile(_ selection: ClientSearchSelection) {
        guard let current=session.profileSelection else {return};backProfile(selection,expectedProfile:current)
    }
    func backProfile(_ selection: ClientSearchSelection,expectedProfile: ClientSearchProfileSelection) {
        guard session.selection==selection,session.profileSelection==expectedProfile else {return}
        windowRevision += 1;inputRevision += 1;profile.clear();session.backProfile(expected:selection,profile:expectedProfile)
    }
    var inputControl:ClientSearchInputControl? {session.selection.map {ClientSearchInputControl(selection:$0,generation:inputRevision)}}
    var control:ClientSearchControl? {session.selection.map {ClientSearchControl(selection:$0,generation:windowRevision,profile:session.profileSelection,read:profile.readSelection)}}
    func matches(_ expected:ClientSearchControl?)->Bool {expected != nil && control==expected}
    func update(_ value:String,input:ClientSearchInputControl?) {guard let input,inputControl==input,session.profileSelection==nil else {return};update(value,input.selection)}
    func clear(expected:ClientSearchControl?) {guard let expected,matches(expected),session.profileSelection==nil else {return};clear(expected.selection)}
    func submit(expected:ClientSearchControl?) async {guard let expected,matches(expected),!session.loading,session.profileSelection==nil else {return};await submit(expected.selection)}
    func openClient(_ id:Int,expected:ClientSearchControl?) async {guard let expected,matches(expected),session.profileSelection==nil else {return};await openClient(id,expected.selection)}
    func retryProfile(expected:ClientSearchControl?) async {guard let expected,matches(expected),!profile.loading,let selected=session.profileSelection else {return};await retryProfile(expected.selection,expectedProfile:selected)}
    func backProfile(expected:ClientSearchControl?) {guard let expected,matches(expected),let selected=session.profileSelection else {return};backProfile(expected.selection,expectedProfile:selected)}
    func close(expected:ClientSearchControl?) {guard let expected,matches(expected) else {return};close(expected.selection)}
    func close(_ selection: ClientSearchSelection) {
        guard session.selection==selection else {return};windowRevision += 1;inputRevision += 1;profile.clear();session.close(expected:selection)
    }
}
