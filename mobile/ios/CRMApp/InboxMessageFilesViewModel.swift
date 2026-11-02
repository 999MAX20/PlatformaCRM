import Foundation
import SwiftUI
import CRMCore

struct InboxMessageFilesOwner:Equatable {let read:InboxConversationFilesContext;let limit:Int;var valid:Bool {read.valid && (1...300).contains(limit)}}
struct InboxMessageFilesControl:Equatable {let owner:InboxMessageFilesOwner;let visit:Int;let context:InboxMessageFilesContext?;let selected:InboxMessageFileMetadata?}
struct InboxMessageFilesPresentation:Equatable {let context:InboxMessageFilesContext;let visit:Int}
@MainActor final class InboxMessageFilesViewModel:ObservableObject {
    @Published private(set) var owner:InboxMessageFilesOwner?
    @Published private(set) var context:InboxMessageFilesContext?
    @Published private(set) var presented=false
    @Published private(set) var window:InboxMessageFileWindow?
    @Published private(set) var selected:InboxMessageFileMetadata?
    @Published private(set) var loading=false
    @Published private(set) var failure:ReadFailure?
    @Published private var visit=0
    @Published private var presentationVisit=0
    private var generation=0
    private let repository:any InboxMessageFilesRepository
    private let retryPort:(any SyntheticInboxRetryPort)?
    @Published private var retryLedger=InboxRetryLedger()
    @Published private(set) var retryReview:InboxRetryReview?
    var commandsBlocked:@MainActor ()->Bool = {true}
    init(repository:any InboxMessageFilesRepository,retryPort:(any SyntheticInboxRetryPort)?=nil) {self.repository=repository;self.retryPort=retryPort}
    private var retryAuthorization:SyntheticInboxRetryAuthorization? {guard let read=owner?.read else {return nil};let o=InboxRetryOwner(business:read.business,conversation:read.conversation,epoch:read.epoch);return retryPort?.grants.compactMap {$0.authorization(for:o)}.first}
    var retryRecord:InboxRetryRecord? {retryLedger.visible(retryAuthorization)}
    var retainedRetryCount:Int {retryLedger.records.count}
    func blocksCommands(business:Int,conversation:Int)->Bool {retryLedger.blocked(business:business,conversation:conversation)}
    var retryBlocked:Bool {guard let read=owner?.read else {return false};return blocksCommands(business:read.business,conversation:read.conversation)}
    var canPrepareRetry:Bool {presented && !loading && failure==nil && selected==nil && retryReview==nil && !retryBlocked && !commandsBlocked() && retryAuthorization != nil && window?.retrySource?.eligible==true}
    var canSubmitRetry:Bool {guard let review=retryReview else {return false};return presented && !loading && selected==nil && failure==nil && !retryBlocked && !commandsBlocked() && review.valid && review.authorization==retryAuthorization && window?.retrySource==review.source && context==review.source.context}
    func prepareRetry(expected:InboxMessageFilesControl?) {guard let expected,control==expected,canPrepareRetry,let source=window?.retrySource,let auth=retryAuthorization else {return};visit += 1;retryReview=InboxRetryReview(source:source,authorization:auth,visit:visit)}
    func backRetry(expected:InboxMessageFilesControl?) {guard let expected,control==expected,retryReview != nil,!retryBlocked else {return};retryReview=nil;visit += 1}
    func submitRetry(_ review:InboxRetryReview,expected:InboxMessageFilesControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmitRetry,retryReview==review,let port=retryPort,let attempt=retryLedger.begin(review) else {return}
        retryReview=nil;visit += 1
        let outcome:SyntheticInboxRetryOutcome
        do {let value=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:value} catch {outcome = .unknown}
        retryLedger.complete(attempt,outcome:outcome);visit += 1
    }
    func acknowledgeRetry(_ record:InboxRetryRecord,expected:InboxMessageFilesControl?) {guard let expected,control==expected,let auth=retryAuthorization,retryLedger.acknowledge(auth,record:record) else {return};visit += 1}
    var control:InboxMessageFilesControl? {owner.map {InboxMessageFilesControl(owner:$0,visit:visit,context:context,selected:selected)}}
    var presentation:InboxMessageFilesPresentation? {guard presented,let context else {return nil};return InboxMessageFilesPresentation(context:context,visit:presentationVisit)}
    private func reset() {generation += 1;visit += 1;window=nil;selected=nil;loading=false;failure=nil;retryReview=nil}
    func bind(_ next:InboxMessageFilesOwner?) {let next=next?.valid==true ? next:nil;guard next != owner else {return};reset();owner=next;context=nil;presented=false;presentationVisit += 1}
    @discardableResult func open(message:Int,expected:InboxMessageFilesControl?)->Bool {
        guard let expected,control==expected,!presented,let owner else {return false};let r=owner.read,c=InboxMessageFilesContext(business:r.business,conversation:r.conversation,message:message,epoch:r.epoch,revision:r.revision,limit:owner.limit);guard c.valid else {return false}
        reset();context=c;presented=true;presentationVisit += 1;return true
    }
    private func current(_ ticket:Int,_ c:InboxMessageFilesContext)->Bool {generation==ticket && context==c && presented}
    func load(expected:InboxMessageFilesControl?) async {
        guard !Task.isCancelled,let expected,control==expected,presented,!loading,selected==nil,retryReview==nil,retryRecord?.phase != .pending,let c=context else {return};reset();let ticket=generation;loading=true
        do {
            let anchor=try await repository.anchor(c);try Task.checkCancellation();guard current(ticket,c) else {return};guard anchor.matches(c) else {throw ReadFailure.invalidPayload}
            let value=try await repository.messages(c,anchor:anchor);try Task.checkCancellation();guard current(ticket,c) else {return};guard value.valid(for:c) else {throw ReadFailure.invalidPayload}
            window=value;loading=false;visit += 1
        } catch {guard current(ticket,c) else {return};window=nil;selected=nil;loading=false;failure=error is CancellationError ? nil:(error as? ReadFailure ?? .unavailable);visit += 1}
    }
    func select(_ row:InboxMessageFileMetadata,expected:InboxMessageFilesControl?) {guard let expected,control==expected,presented,!loading,failure==nil,selected==nil,retryReview==nil,window?.items.contains(row)==true else {return};selected=row;visit += 1}
    func back(expected:InboxMessageFilesControl?) {guard let expected,control==expected,presented,selected != nil else {return};selected=nil;visit += 1}
    func close(expected:InboxMessageFilesPresentation?) {guard let expected,presentation==expected else {return};reset();context=nil;presented=false;presentationVisit += 1}
}
