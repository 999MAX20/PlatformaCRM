import Foundation
import SwiftUI
import Combine
import CRMCore

struct InboxLinkLeadControl:Equatable {let context:InboxConversationFilesContext;let visit:Int;let source:InboxLinkLeadSource?;let picker:LeadReadControl?;let review:InboxLinkLeadReview?;let record:InboxLinkLeadRecord?}
@MainActor final class InboxLinkLeadViewModel:ObservableObject {
    @Published private(set) var context:InboxConversationFilesContext?
    @Published private(set) var presented=false
    @Published private(set) var source:InboxLinkLeadSource?
    @Published private(set) var loading=false
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var review:InboxLinkLeadReview?
    @Published private var ledger=InboxLinkLeadLedger()
    @Published private var visit=0
    private var generation=0
    private let repository:any InboxLinkLeadRepository
    private let port:(any SyntheticInboxLinkLeadPort)?
    let picker:LeadReferenceViewModel?
    private var observation:AnyCancellable?
    var commandsBlocked:@MainActor ()->Bool={true}
    init(repository:any InboxLinkLeadRepository,picker:LeadReferenceViewModel?,port:(any SyntheticInboxLinkLeadPort)?) {
        self.repository=repository;self.picker=picker;self.port=port
        picker?.controlsBlocked={ [weak self] in guard let self else {return true};return self.review != nil || self.pending }
        observation=picker?.objectWillChange.sink { [weak self] _ in self?.objectWillChange.send() }
    }
    private var authorization:SyntheticInboxLinkLeadAuthorization? {context.flatMap {c in port?.grants.compactMap {$0.authorization(for:c)}.first}}
    var record:InboxLinkLeadRecord? {ledger.visible(authorization)}
    var retainedAttemptCount:Int {ledger.records.count}
    func blocks(business:Int,conversation:Int)->Bool {ledger.blocked(business:business,conversation:conversation)}
    var blocked:Bool {context.map {blocks(business:$0.business,conversation:$0.conversation)} ?? false}
    private var pending:Bool {guard let c=context else {return false};return ledger.records.contains {$0.phase == .pending && $0.attempt.review.source.context.business==c.business && $0.attempt.review.source.context.conversation==c.conversation}}
    var ownsEditor:Bool {loading || review != nil}
    var control:InboxLinkLeadControl? {context.map {InboxLinkLeadControl(context:$0,visit:visit,source:source,picker:picker?.control,review:review,record:record)}}
    private var currentReference:QualifiedLeadReference? {guard let c=context,let s=picker?.session,s.presented,s.context==c,!s.loading,s.failure==nil,s.canUse,let choice=s.choice,choice.context==c,choice.detail==s.detail,SourceTextIdentity.same(choice.rawQuery,s.query) else {return nil};return choice}
    var canLoad:Bool {presented && !loading && review==nil && !pending}
    var canPrepare:Bool {presented && !loading && failure==nil && source?.context==context && source != nil && authorization != nil && currentReference != nil && review==nil && !blocked && !commandsBlocked()}
    var canSubmit:Bool {guard let review else {return false};return presented && !loading && failure==nil && !blocked && !commandsBlocked() && review.valid && review.source==source && review.authorization==authorization && review.candidate.reference==currentReference}
    func hide() {generation += 1;visit += 1;presented=false;source=nil;loading=false;failure=nil;review=nil}
    func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard next != context else {return};hide();context=next}
    func show() {guard context != nil else {return};presented=true;visit += 1}
    func load(expected:InboxLinkLeadControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canLoad,let c=context else {return};generation += 1;let ticket=generation;visit += 1;loading=true;source=nil;failure=nil
        do {let s=try await repository.source(c);try Task.checkCancellation();guard ticket==generation,context==c,presented else {return};guard s.context==c else {throw ReadFailure.invalidPayload};source=s;loading=false;visit += 1}
        catch {guard ticket==generation,context==c,presented else {return};loading=false;source=nil;failure=error is CancellationError ? nil:(error as? ReadFailure ?? .unavailable);visit += 1}
    }
    func prepare(expected:InboxLinkLeadControl?) {guard let expected,control==expected,canPrepare,let source,let reference=currentReference,let auth=authorization,let candidate=InboxLinkLeadCandidate(source:source,reference:reference) else {return};visit += 1;review=InboxLinkLeadReview(source:source,authorization:auth,candidate:candidate,visit:visit)}
    func back(expected:InboxLinkLeadControl?) {guard let expected,control==expected,review != nil,!blocked else {return};review=nil;visit += 1}
    func submit(expected:InboxLinkLeadControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmit,let review,let port,let a=ledger.begin(review) else {return};self.review=nil;visit += 1
        let outcome:SyntheticInboxLinkLeadOutcome;do {let result=try await port.execute(a);outcome=Task.isCancelled ? .unknown:result} catch {outcome = .unknown};ledger.complete(a,outcome:outcome);if context==a.review.source.context {visit += 1}
    }
    func acknowledge(_ record:InboxLinkLeadRecord,expected:InboxLinkLeadControl?) {guard let expected,control==expected,let auth=authorization,ledger.acknowledge(auth,record:record) else {return};if record.phase == .response {source=nil;picker?.hide();picker?.show()};review=nil;visit += 1}
}
