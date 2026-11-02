import Foundation
import SwiftUI
import CRMCore

enum AppointmentBookingReadKind:String {case client,service,resource}
struct AppointmentBookingControl:Equatable {let source:AppointmentBookingSource;let visit:Int;let review:AppointmentBookingReview?;let record:AppointmentBookingRecord?}
struct AppointmentBookingInputControl:Equatable {let source:AppointmentBookingSource;let visit:Int}
enum AppointmentBookingDirectoryKind:Equatable {case service,resource}
struct AppointmentBookingDirectoryControl:Equatable {let source:AppointmentBookingSource;let visit:Int;let kind:AppointmentBookingDirectoryKind;let authorization:SyntheticAppointmentBookingAuthorization;let service:ServiceDirectoryPresentation?;let resource:ResourceDirectoryPresentation?}
struct AppointmentBookingClientPickerOwner:Equatable {let source:AppointmentBookingSource;let visit:Int;let authorization:SyntheticAppointmentBookingAuthorization;let selection:ClientSearchSelection}
@MainActor final class AppointmentBookingViewModel:ObservableObject {
    let clientChoices:ClientSearchViewModel?
    @Published private(set) var clientPickerOwner:AppointmentBookingClientPickerOwner?
    @Published private(set) var clientSelection:AppointmentBookingClientSelection?
    let serviceChoices:ServiceDirectoryViewModel?
    let resourceChoices:ResourceDirectoryViewModel?
    @Published private(set) var selector:AppointmentBookingDirectoryKind?
    @Published private(set) var directory:AppointmentBookingDirectorySelection?
    private var selectorAuthorization:SyntheticAppointmentBookingAuthorization?
    @Published private(set) var source:AppointmentBookingSource?
    @Published private(set) var presented=false
    @Published private(set) var rawStart=""
    @Published private(set) var client:TaskDraftClientChoice?
    @Published private(set) var service:AppointmentReferenceDetail?
    @Published private(set) var resource:AppointmentRescheduleResource?
    @Published private(set) var loading:AppointmentBookingReadKind?
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var review:AppointmentBookingReview?
    @Published private var visit=0
    @Published private var inputVisit=0
    @Published private var ledger=AppointmentBookingLedger()
    private let port:any SyntheticAppointmentBookingPort
    private let clients:(any ClientProfileRepository)?
    private let references:(any AppointmentReferenceRepository)?
    init(port:any SyntheticAppointmentBookingPort,clients:(any ClientProfileRepository)?,references:(any AppointmentReferenceRepository)?,services:(any ServiceDirectoryRepository)?=nil,resources:(any ResourceDirectoryRepository)?=nil,clientSearch:(any ClientSearchRepository)?=nil) {self.clientChoices=clientSearch.map {ClientSearchViewModel(repository:$0)};self.port=port;self.clients=clients;self.references=references;serviceChoices=services.map {ServiceDirectoryViewModel(repository:$0)};resourceChoices=resources.map {ResourceDirectoryViewModel(repository:$0)}}
    private var authorization:SyntheticAppointmentBookingAuthorization? {guard let source else {return nil};let grants=port.grants.reduce(into:[SyntheticAppointmentBookingGrant]()) {if !$0.contains($1) {$0.append($1)}};let matches=grants.compactMap {$0.authorization(source)};return matches.count==1 ? matches[0]:nil}
    var submission:AppointmentBookingRecord? {authorization.flatMap {ledger.visible($0)}}
    var blocked:Bool {source.map {ledger.blocked($0)} ?? false}
    var used:Bool {source.map {ledger.used($0)} ?? false}
    var canPresent:Bool {source?.valid==true && clients != nil && references != nil && authorization != nil && (!used || blocked)}
    var canOpen:Bool {canPresent && !presented && !blocked && !used}
    var editing:Bool {presented && review==nil && !blocked && loading==nil && selector==nil && clientPickerOwner==nil}
    var control:AppointmentBookingControl? {source.map {AppointmentBookingControl(source:$0,visit:visit,review:review,record:submission)}}
    var inputControl:AppointmentBookingInputControl? {guard editing,let source else {return nil};return AppointmentBookingInputControl(source:source,visit:inputVisit)}
    var retainedAttemptCount:Int {ledger.records.count}
    var linkedResourceAvailable:Bool {source?.resourceID != nil && references != nil}
    var timeValid:Bool {TaskSnoozeValue.parse(rawStart).map {$0.microseconds%1000==0} ?? false}
    var prepared:AppointmentBookingInput? {guard editing,let source,let client,let service,let resource else {return nil};return AppointmentBookingInput(source:source,client:client,service:service,resource:resource,startAt:rawStart,directory:directory,clientSelection:clientSelection)}
    var canReview:Bool {prepared != nil && authorization != nil && !used}
    func bind(_ next:AppointmentBookingSource?) {
        let valid=next?.valid==true ? next:nil;guard source != valid else {return};clearSelectors();directory=nil;clientSelection=nil;source=valid;presented=false;rawStart="";client=nil;service=nil;resource=nil;loading=nil;failure=nil;review=nil;visit += 1;inputVisit += 1
    }
    @discardableResult func open(expected:AppointmentBookingControl?)->Bool {guard let expected,control==expected,canOpen else {return false};presented=true;failure=nil;visit += 1;inputVisit += 1;return true}
    @discardableResult func openCandidate(_ value:AppointmentBookingCandidateTime,expected:AppointmentBookingControl?)->Bool {guard permitsCandidate(value),open(expected:expected) else {return false};rawStart=value.rawStart;visit += 1;inputVisit += 1;return true}
    func setStart(_ value:String,expected:AppointmentBookingInputControl?) {guard let expected,inputControl==expected,!SourceTextIdentity.same(rawStart,value) else {return};rawStart=value;visit += 1}
    func chooseClear(expected:AppointmentBookingControl?) {guard let expected,control==expected,editing else {return};resource = .clear;directory=source.flatMap {AppointmentBookingDirectorySelection(source:$0,service:directory?.service,resource:nil)};failure=nil;visit += 1}
    func load(_ kind:AppointmentBookingReadKind,expected:AppointmentBookingControl?) async {
        guard !Task.isCancelled,let expected,control==expected,editing,let source,let clients,let references else {return}
        if kind == .resource && source.resourceID==nil {return}
        visit += 1;inputVisit += 1;let ticket=visit;loading=kind;failure=nil
        switch kind {case .client:client=nil;clientSelection=nil;case .service:service=nil;directory=AppointmentBookingDirectorySelection(source:source,service:nil,resource:directory?.resource);case .resource:resource=nil;directory=AppointmentBookingDirectorySelection(source:source,service:directory?.service,resource:nil)}
        do {
            switch kind {
            case .client:
                let profile=try await clients.clientProfile(business:source.read.scope.business.id,id:source.clientID);try Task.checkCancellation()
                guard self.source==source,visit==ticket else {return};guard let choice=TaskDraftClientChoice(profile:profile,business:source.read.scope.business.id,id:source.clientID) else {throw ReadFailure.invalidPayload};client=choice
            case .service,.resource:
                let id=kind == .service ? source.serviceID:source.resourceID!,value=try await references.reference(kind == .service ? .service:.resource,business:source.read.scope.business.id,id:id);try Task.checkCancellation()
                guard self.source==source,visit==ticket else {return};guard value.valid(for:source.read.scope.business.id,id:id) else {throw ReadFailure.invalidPayload}
                if kind == .service {service=value} else {resource = .linked(value)}
            }
            loading=nil;visit += 1;inputVisit += 1
        } catch {
            guard self.source==source,visit==ticket else {return};loading=nil;failure=error is CancellationError ? nil:(error as? ReadFailure ?? .unavailable);visit += 1;inputVisit += 1
        }
    }
    func prepareReview(expected:AppointmentBookingControl?) {guard let expected,control==expected,canReview,let input=prepared else {return};visit += 1;inputVisit += 1;review=AppointmentBookingReview(source:expected.source,input:input,visit:visit)}
    // True means the form closed; parent invalidates its captured entry controls as well.
    @discardableResult func back(expected:AppointmentBookingControl?)->Bool {guard let expected,control==expected,!blocked,presented else {return false};if let owner=clientPickerOwner {closeClientPicker(owner);return false};if selector != nil {closeSelector(expected:selectorControl);return false};let closed=review==nil;if closed {clearSelectors();presented=false;loading=nil;failure=nil} else {review=nil};visit += 1;inputVisit += 1;return closed}
    func submit(expected:AppointmentBookingControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let authorization,let attempt=ledger.begin(review,authorization:authorization) else {return};visit += 1;inputVisit += 1
        let outcome:SyntheticAppointmentBookingOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);visit += 1
    }
    func acknowledge(expected:AppointmentBookingControl?,record:AppointmentBookingRecord) {guard let expected,control==expected,submission==record,ledger.acknowledge(record) else {return};review=nil;presented=record.phase == .rejectedFixture;visit += 1;inputVisit += 1}
}


extension AppointmentBookingViewModel {
    var selectorControl:AppointmentBookingDirectoryControl? {
        guard let source,let kind=selector,let authorization=selectorAuthorization else {return nil}
        let s=serviceChoices?.presentation,r=resourceChoices?.presentation
        let current = kind == .service ? (s != nil && r==nil):(r != nil && s==nil)
        guard current else {return nil}
        return AppointmentBookingDirectoryControl(source:source,visit:visit,kind:kind,authorization:authorization,service:s,resource:r)
    }
    func matchesSelector(_ expected:AppointmentBookingDirectoryControl?)->Bool {expected != nil && selectorControl==expected && source==expected?.source && presented}
    private func clearSelectors() {clientChoices?.bind(nil);clientPickerOwner=nil;serviceChoices?.bind(nil);resourceChoices?.bind(nil);selector=nil;selectorAuthorization=nil}
    func openSelector(_ kind:AppointmentBookingDirectoryKind,expected:AppointmentBookingControl?,serviceChild:ServiceDirectoryControl?,resourceChild:ResourceDirectoryControl?) async {
        guard let expected,control==expected,editing,canPresent,!used,let source,let authorization else {return}
        if kind == .service {guard let child=serviceChoices,child.control==serviceChild else {return}}
        else {guard let child=resourceChoices,child.control==resourceChild else {return}}
        clearSelectors();visit += 1;inputVisit += 1;failure=nil;selectorAuthorization=authorization
        switch kind {
        case .service:
            guard let child=serviceChoices else {return};child.bind(ServiceDirectoryOwner(scope:source.read.scope,epoch:source.epoch));guard child.open(expected:child.control) else {return};selector=kind;await child.reload(expected:child.control)
        case .resource:
            guard let child=resourceChoices else {return};child.bind(ResourceDirectoryOwner(scope:source.read.scope,epoch:source.epoch));guard child.open(expected:child.control) else {return};selector=kind;await child.reload(expected:child.control)
        }
    }
    func closeSelector(expected:AppointmentBookingDirectoryControl?) {guard matchesSelector(expected) else {return};clearSelectors();visit += 1;inputVisit += 1}
    func useService(_ choice:ServiceDirectoryReadChoice,child:ServiceDirectoryControl?,expected:AppointmentBookingDirectoryControl?) {
        guard matchesSelector(expected),expected?.kind == .service,authorization==expected?.authorization,!blocked,!used,review==nil,loading==nil,let source,let model=serviceChoices,model.matches(child),model.choice==choice,model.detail==choice.item,model.selected==choice.listed,choice.owner==ServiceDirectoryOwner(scope:source.read.scope,epoch:source.epoch),let proof=AppointmentBookingDirectorySelection(source:source,service:choice.item,resource:directory?.resource) else {return}
        service=choice.item.reference;directory=proof;failure=nil;closeSelector(expected:expected)
    }
    func useResource(_ choice:ResourceDirectoryReadChoice,child:ResourceDirectoryControl?,expected:AppointmentBookingDirectoryControl?) {
        guard matchesSelector(expected),expected?.kind == .resource,authorization==expected?.authorization,!blocked,!used,review==nil,loading==nil,let source,let model=resourceChoices,model.matches(child),model.choice==choice,model.detail==choice.item,model.selected==choice.listed,choice.owner==ResourceDirectoryOwner(scope:source.read.scope,epoch:source.epoch),let proof=AppointmentBookingDirectorySelection(source:source,service:directory?.service,resource:choice.item) else {return}
        resource = .linked(choice.item.reference);directory=proof;failure=nil;closeSelector(expected:expected)
    }
    // Navigation owner is stable while search input/actions/profile reads advance independently.
    func matchesClientPicker(_ expected:AppointmentBookingClientPickerOwner?)->Bool {
        guard let expected,clientPickerOwner==expected,source==expected.source,visit==expected.visit,presented,selector==nil,review==nil,loading==nil,!blocked,!used else {return false}
        return clientChoices?.session.selection==expected.selection
    }
    func openClientPicker(expected:AppointmentBookingControl?,child:ClientSearchControl?) {
        guard let expected,control==expected,editing,canPresent,!used,let source,let authorization,let search=clientChoices,search.control==child else {return}
        clearSelectors();visit += 1;inputVisit += 1;failure=nil
        let context=ClientSearchContext(business:source.read.scope.business.id,epoch:source.epoch)
        search.bind(context);search.open(context)
        guard let selection=search.session.selection else {return}
        clientPickerOwner=AppointmentBookingClientPickerOwner(source:source,visit:visit,authorization:authorization,selection:selection)
    }
    func closeClientPicker(_ expected:AppointmentBookingClientPickerOwner?) {guard matchesClientPicker(expected) else {return};clearSelectors();visit += 1;inputVisit += 1}
    func confirmClient(_ expected:AppointmentBookingClientPickerOwner?,search control:ClientSearchControl?) {
        guard matchesClientPicker(expected),let expected,authorization==expected.authorization,let search=clientChoices,let control,search.matches(control),control.selection==expected.selection,
              search.session.loaded,!search.session.loading,search.session.failure==nil,let selected=search.session.profileSelection,selected==control.profile,search.session.items.contains(where:{$0.id==selected.id}),
              let read=control.read,read==search.profile.readSelection,!search.profile.loading,search.profile.failure==nil,let profile=search.profile.detail,
              let proof=AppointmentBookingClientSelection(source:expected.source,selected:selected,read:read,rawQuery:search.session.query,profile:profile) else {return}
        client=proof.choice;clientSelection=proof;failure=nil;closeClientPicker(expected)
    }
    func permitsCandidate(_ value:AppointmentBookingCandidateTime)->Bool {
        guard let source,value.valid(for:source),canOpen else {return false}
        if let service,service != value.review.context.service {return false}
        if let candidateResource=value.review.context.resource,let resource {
            switch resource {case .clear:return false;case .linked(let selected):if selected != candidateResource {return false}}
        }
        return true
    }
}
