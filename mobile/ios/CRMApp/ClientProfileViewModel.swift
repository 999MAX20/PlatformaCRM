import Foundation
import SwiftUI
import CRMCore

struct ClientMergeEntryControl:Equatable {let read:ClientReadSelection;let epoch:Int;let visit:Int;let edit:ClientEditEntryControl?;let work:ClientWorkControl?}

@MainActor final class ClientProfileViewModel: ObservableObject {
    @Published private(set) var business: Int?
    @Published private(set) var id: Int?
    @Published private(set) var detail: ClientProfile?
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var scopeEpoch: Int?
    let edit: ClientEditViewModel?
    private let editOriginSource: (any ClientEditOriginProvider)?
    let merge: ClientMergePreviewViewModel?
    @Published private(set) var localOverlayVisit=0
    let work: ClientWorkViewModel?
    private var revision = 0
    private let repository: any ClientProfileRepository
    init(repository: any ClientProfileRepository,editOriginSource: (any ClientEditOriginProvider)? = nil,mergeSource: (any SyntheticClientMergePreviewSource)? = nil) {
        merge=mergeSource.map {ClientMergePreviewViewModel(source:$0)}
        self.repository = repository;self.editOriginSource=editOriginSource;edit=editOriginSource.map {_ in ClientEditViewModel()}
        work = (repository as? any ClientWorkRepository).map { ClientWorkViewModel(repository: $0) }
    }
    func load(business: Int, id: Int, epoch: Int? = nil, onContact: (@MainActor (Int, ClientContact) -> Void)? = nil) async {
        if merge != nil {merge?.clear();localOverlayVisit += 1};work?.clear();scopeEpoch=epoch
        let editContext=epoch.flatMap {$0>0 && business>0 && id>0 ? ClientEditContext(business:business,client:id,epoch:$0) : nil};edit?.begin(editContext)
        revision += 1; let ticket = revision; self.business = business; self.id = id; detail = nil; loading = true; failure = nil
        guard business > 0, id > 0 else { loading = false; failure = .invalidContext; return }
        do {
            let profile = try await repository.clientProfile(business: business, id: id)
            guard ticket == revision else { return }
            guard profile.valid(for: business, id: id) else { throw ReadFailure.invalidPayload }
            let origin: ClientEditOrigin? = if editContext != nil,let editOriginSource {await editOriginSource.origin(for:profile)} else {nil}
            guard ticket==revision else {return}
            if let editContext {edit?.receive(origin,editContext)}
            detail = profile; loading = false
            work?.bind(profile, selection: ClientReadSelection(business: business, id: id, revision: ticket))
            onContact?(business, profile.client)
        } catch {
            guard ticket == revision else { return }; loading = false
            if !(error is CancellationError) { failure = error as? ReadFailure ?? .unavailable }
        }
    }
    private var mergeContext:ClientMergePreviewContext? {
        guard merge != nil,let read=readSelection,let epoch=scopeEpoch,epoch > 0,detail != nil,!loading,failure == nil else {return nil}
        return ClientMergePreviewContext(business:read.business,target:read.id,epoch:epoch,readRevision:read.revision)
    }
    private var mergeOwnerAvailable:Bool {edit?.session.selection == nil && edit?.confirmation == nil && work?.selected == nil}
    var mergeEntry:ClientMergeEntryControl? {guard let context=mergeContext,merge?.context == nil,mergeOwnerAvailable,let read=readSelection else {return nil};return ClientMergeEntryControl(read:read,epoch:context.epoch,visit:localOverlayVisit,edit:edit?.entryControl,work:work?.presentation)}
    func openMerge(expected:ClientMergeEntryControl?) async {guard let expected,mergeEntry == expected,let context=mergeContext,let merge else {return};localOverlayVisit += 1;await merge.open(context)}
    func ownsMerge(_ expected:ClientMergePreviewControl?) -> Bool {guard let expected else {return false};return mergeContext == expected.context && mergeOwnerAvailable && merge?.control == expected}
    func chooseMerge(_ id:Int,expected:ClientMergePreviewControl?) {guard ownsMerge(expected) else {return};merge?.choose(id,expected:expected);objectWillChange.send()}
    func previewMerge(expected:ClientMergePreviewControl?) async {guard ownsMerge(expected) else {return};objectWillChange.send();await merge?.preview(expected:expected);objectWillChange.send()}
    func retryMerge(expected:ClientMergePreviewControl?) async {guard ownsMerge(expected),let context=mergeContext,let merge,!merge.loading else {return};objectWillChange.send();await merge.open(context);objectWillChange.send()}
    @discardableResult func closeMerge(expected:ClientMergePreviewControl?) -> Bool {guard ownsMerge(expected) else {return false};merge?.clear();localOverlayVisit += 1;return true}
    var readSelection:ClientReadSelection? {guard let business,let id,business>0,id>0 else {return nil};return ClientReadSelection(business:business,id:id,revision:revision)}
    func retry(expected:ClientReadSelection?,epoch:Int?,onContact:(@MainActor (Int,ClientContact)->Void)?=nil) async {guard let expected,readSelection==expected,scopeEpoch==epoch,!loading else {return};await load(business:expected.business,id:expected.id,epoch:epoch,onContact:onContact)}
    func reconcileOwner(business next:Int?,epoch:Int) {if business != next || scopeEpoch != epoch {clear()}}
    func clear() { if merge != nil {merge?.clear();localOverlayVisit += 1};edit?.pause();scopeEpoch=nil;work?.clear(); revision += 1; business = nil; id = nil; detail = nil; loading = false; failure = nil }
}
