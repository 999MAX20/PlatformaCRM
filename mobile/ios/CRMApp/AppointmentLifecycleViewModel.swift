import Foundation
import SwiftUI
import CRMCore

struct AppointmentLifecycleControl:Equatable {let source:AppointmentLifecycleSource;let visit:Int;let review:AppointmentLifecycleReview?;let record:AppointmentLifecycleRecord?}
// Stable continuous-input visit, independent of changing action/review controls.
struct AppointmentRescheduleInputControl:Equatable {let source:AppointmentLifecycleSource;let visit:Int}
@MainActor final class AppointmentLifecycleViewModel:ObservableObject {
    @Published private(set) var source:AppointmentLifecycleSource?
    @Published private(set) var review:AppointmentLifecycleReview?
    @Published private var ledger=AppointmentLifecycleLedger()
    @Published private var visit=0
    @Published private var inputVisit=0
    @Published private(set) var reschedulePresented=false
    @Published private(set) var rawStart=""
    @Published private(set) var rawReason=""
    @Published private(set) var resourceChoice:AppointmentRescheduleResource?
    @Published private(set) var resourceLoading=false
    @Published private(set) var resourceFailure:ReadFailure?
    private let port:any SyntheticAppointmentLifecyclePort
    private let references:(any AppointmentReferenceRepository)?
    init(port:any SyntheticAppointmentLifecyclePort,references:(any AppointmentReferenceRepository)?=nil) {self.port=port;self.references=references}
    private func authorization(_ action:AppointmentLifecycleAction)->SyntheticAppointmentLifecycleAuthorization? {
        guard let source else {return nil};let grants=port.grants.reduce(into:[SyntheticAppointmentLifecycleGrant]()) {if !$0.contains($1) {$0.append($1)}}
        let terminal=port.terminalGrants.reduce(into:[SyntheticAppointmentTerminalGrant]()) {if !$0.contains($1) {$0.append($1)}}
        let matches=grants.compactMap {$0.authorization(source,action:action)}+terminal.compactMap {$0.authorization(source,action:action)};return matches.count==1 ? matches[0]:nil
    }
    var submission:AppointmentLifecycleRecord? {AppointmentLifecycleAction.allCases.compactMap {authorization($0).flatMap {ledger.visible($0)}}.first}
    var blocked:Bool {source.map {ledger.blocked($0)} ?? false}
    var canPresent:Bool {source?.valid==true && AppointmentLifecycleAction.allCases.contains {authorization($0) != nil}}
    var control:AppointmentLifecycleControl? {source.map {AppointmentLifecycleControl(source:$0,visit:visit,review:review,record:submission)}}
    var retainedAttemptCount:Int {ledger.records.count}
    func used(_ action:AppointmentLifecycleAction)->Bool {source.map {ledger.used($0,action)} ?? false}
    func canPrepare(_ action:AppointmentLifecycleAction)->Bool {canPresent && authorization(action) != nil && !blocked && review==nil && !reschedulePresented && !used(action) && (action != .reschedule || source?.canReschedule==true)}
    var editingReschedule:Bool {reschedulePresented && review==nil && !blocked && !resourceLoading}
    var inputControl:AppointmentRescheduleInputControl? {guard editingReschedule,let source else {return nil};return AppointmentRescheduleInputControl(source:source,visit:inputVisit)}
    var linkedResourceAvailable:Bool {references != nil && source?.linkedResourceID != nil}
    var preparedReschedule:AppointmentRescheduleInput? {guard editingReschedule,let source,let resourceChoice else {return nil};return AppointmentRescheduleInput(source:source,startAt:rawStart,reason:rawReason,resource:resourceChoice)}
    var canReviewReschedule:Bool {preparedReschedule != nil && authorization(.reschedule) != nil && !used(.reschedule)}
    var timeInputValid:Bool {TaskSnoozeValue.parse(rawStart).map {$0.microseconds%1000==0} ?? false}
    func bind(_ next:AppointmentLifecycleSource?) {
        let next=next?.valid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1;inputVisit += 1
        reschedulePresented=false;rawStart="";rawReason="";resourceChoice=nil;resourceLoading=false;resourceFailure=nil
    }
    func prepare(_ action:AppointmentLifecycleAction,expected:AppointmentLifecycleControl?) {
        guard let expected,control==expected,canPrepare(action) else {return};visit += 1
        if action == .reschedule {reschedulePresented=true;inputVisit += 1;resourceFailure=nil}
        else {review=AppointmentLifecycleReview(source:expected.source,action:action,visit:visit)}
    }
    func setStart(_ value:String,expected:AppointmentRescheduleInputControl?) {guard let expected,inputControl==expected,!SourceTextIdentity.same(rawStart,value) else {return};rawStart=value;visit += 1}
    func setReason(_ value:String,expected:AppointmentRescheduleInputControl?) {guard let expected,inputControl==expected,!SourceTextIdentity.same(rawReason,value) else {return};rawReason=value;visit += 1}
    func chooseClear(expected:AppointmentLifecycleControl?) {guard let expected,control==expected,editingReschedule else {return};resourceChoice = .clear;resourceFailure=nil;visit += 1}
    func loadLinkedResource(expected:AppointmentLifecycleControl?) async {
        guard !Task.isCancelled,let expected,control==expected,editingReschedule,let source,let id=source.linkedResourceID,let references else {return}
        visit += 1;inputVisit += 1;let ticket=visit;resourceLoading=true;resourceChoice=nil;resourceFailure=nil
        do {
            let value=try await references.reference(.resource,business:source.read.scope.business.id,id:id);try Task.checkCancellation()
            guard self.source==source,visit==ticket else {return};guard value.valid(for:source.read.scope.business.id,id:id) else {throw ReadFailure.invalidPayload}
            resourceChoice = .linked(value);resourceLoading=false;visit += 1;inputVisit += 1
        } catch {
            guard self.source==source,visit==ticket else {return};resourceLoading=false;resourceFailure=error is CancellationError ? nil:(error as? ReadFailure ?? .unavailable);visit += 1;inputVisit += 1
        }
    }
    func reviewReschedule(expected:AppointmentLifecycleControl?) {
        guard let expected,control==expected,canReviewReschedule,let value=preparedReschedule else {return};visit += 1;inputVisit += 1
        review=AppointmentLifecycleReview(source:expected.source,action:.reschedule,visit:visit,reschedule:value)
    }
    func back(expected:AppointmentLifecycleControl?) {
        guard let expected,control==expected,!blocked else {return}
        if review != nil {review=nil} else if reschedulePresented {reschedulePresented=false;resourceLoading=false;resourceFailure=nil} else {return}
        visit += 1;inputVisit += 1
    }
    func submit(expected:AppointmentLifecycleControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization(review.action),let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1;inputVisit += 1;let outcome:SyntheticAppointmentLifecycleOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);visit += 1
    }
    func acknowledge(expected:AppointmentLifecycleControl?,record:AppointmentLifecycleRecord) {
        guard let expected,control==expected,submission==record,ledger.acknowledge(record) else {return};review=nil;visit += 1;inputVisit += 1
        reschedulePresented=record.attempt.review.action == .reschedule && record.phase == .rejectedFixture
    }
}
