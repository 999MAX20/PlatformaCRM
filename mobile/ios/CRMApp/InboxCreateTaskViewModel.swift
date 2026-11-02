import Foundation
import SwiftUI
import Combine
import CRMCore

struct InboxCreateTaskControl:Equatable {let context:InboxConversationFilesContext;let visit:Int;let reader:InboxTaskSourceControl?;let review:InboxCreateTaskReview?;let record:InboxCreateTaskRecord?}
@MainActor final class InboxCreateTaskViewModel:ObservableObject {
    @Published private(set) var context:InboxConversationFilesContext?
    @Published private(set) var presented=false
    @Published private(set) var review:InboxCreateTaskReview?
    @Published private var ledger=InboxCreateTaskLedger()
    @Published private var visit=0
    let reader:InboxTaskSourceViewModel?
    private let port:(any SyntheticInboxCreateTaskPort)?
    private var observation:AnyCancellable?
    var commandsBlocked:@MainActor ()->Bool={true}
    init(reader:InboxTaskSourceViewModel?,port:(any SyntheticInboxCreateTaskPort)?) {
        self.reader=reader;self.port=port
        reader?.controlsBlocked={ [weak self] in guard let self else {return true};return self.review != nil || self.pending }
        observation=reader?.objectWillChange.sink { [weak self] _ in self?.objectWillChange.send() }
    }
    private var authorization:SyntheticInboxCreateTaskAuthorization? {context.flatMap {c in port?.grants.compactMap {$0.authorization(for:c)}.first}}
    private var currentReference:QualifiedInboxTaskSource? {guard let c=context,let s=reader?.session,s.presented,s.context==c,!s.loading,s.failure==nil,s.canUse,let choice=s.choice,choice.valid,choice.context==c,choice.source==s.source else {return nil};return choice}
    var source:InboxTaskSource? {currentReference?.source}
    var record:InboxCreateTaskRecord? {ledger.visible(authorization)}
    var retainedAttemptCount:Int {ledger.records.count}
    func blocks(business:Int,conversation:Int)->Bool {ledger.blocked(business:business,conversation:conversation)}
    var blocked:Bool {context.map {blocks(business:$0.business,conversation:$0.conversation)} ?? false}
    private var pending:Bool {guard let c=context else {return false};return ledger.records.contains {$0.phase == .pending && $0.attempt.review.source.context.business==c.business && $0.attempt.review.source.context.conversation==c.conversation}}
    var ownsEditor:Bool {review != nil || pending}
    var control:InboxCreateTaskControl? {context.map {InboxCreateTaskControl(context:$0,visit:visit,reader:reader?.control,review:review,record:record)}}
    var canPrepare:Bool {presented && review==nil && authorization != nil && currentReference != nil && !blocked && !commandsBlocked()}
    var canSubmit:Bool {guard let review else {return false};return presented && !blocked && !commandsBlocked() && review.valid && review.authorization==authorization && review.reference==currentReference}
    func hide() {visit += 1;presented=false;review=nil}
    func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard next != context else {return};hide();context=next}
    func show() {guard context != nil else {return};presented=true;visit += 1}
    func prepare(expected:InboxCreateTaskControl?) {guard let expected,control==expected,canPrepare,let reference=currentReference,let auth=authorization else {return};visit += 1;review=InboxCreateTaskReview(reference:reference,authorization:auth,visit:visit)}
    func back(expected:InboxCreateTaskControl?) {guard let expected,control==expected,review != nil,!blocked else {return};review=nil;visit += 1}
    func submit(expected:InboxCreateTaskControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmit,let review,let port,let a=ledger.begin(review) else {return};self.review=nil;visit += 1
        let outcome:SyntheticInboxCreateTaskOutcome;do {let result=try await port.execute(a);outcome=Task.isCancelled ? .unknown:result} catch {outcome = .unknown};ledger.complete(a,outcome:outcome);if context==a.review.source.context {visit += 1}
    }
    func acknowledge(_ record:InboxCreateTaskRecord,expected:InboxCreateTaskControl?) {guard let expected,control==expected,let auth=authorization,ledger.acknowledge(auth,record:record) else {return};if record.phase == .response {reader?.hide();reader?.show()};review=nil;visit += 1}
}
