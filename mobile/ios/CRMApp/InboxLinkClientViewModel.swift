import Foundation
import SwiftUI
import Combine
import CRMCore

struct InboxLinkClientControl:Equatable {let context:InboxConversationFilesContext;let visit:Int;let source:InboxLinkClientSource?;let editing:Bool;let picker:ClientSearchControl?;let candidate:InboxLinkClientCandidate?;let review:InboxLinkClientReview?;let record:InboxLinkClientRecord?}
struct InboxLinkClientInput:Equatable {let context:InboxConversationFilesContext;let editor:Int;let authorization:SyntheticInboxLinkClientAuthorization;let child:ClientSearchInputControl}
@MainActor final class InboxLinkClientViewModel:ObservableObject {
    @Published private(set) var context:InboxConversationFilesContext?
    @Published private(set) var presented=false
    @Published private(set) var source:InboxLinkClientSource?
    @Published private(set) var loading=false
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var editing=false
    @Published private(set) var candidate:InboxLinkClientCandidate?
    @Published private(set) var review:InboxLinkClientReview?
    @Published private var ledger=InboxLinkClientLedger()
    @Published private var visit=0
    private var generation=0,editor=0
    private var query=""
    private var queryOwner:SyntheticInboxLinkClientAuthorization?
    private let repository:any InboxLinkClientRepository
    private let port:(any SyntheticInboxLinkClientPort)?
    let picker:ClientSearchViewModel?
    private var observations:[AnyCancellable]=[]
    var commandsBlocked:@MainActor ()->Bool = {true}
    init(repository:any InboxLinkClientRepository,clients:(any ClientSearchRepository)?,port:(any SyntheticInboxLinkClientPort)?) {self.repository=repository;self.port=port;picker=clients.map {ClientSearchViewModel(repository:$0)};if let picker {observations.append(picker.objectWillChange.sink { [weak self] _ in self?.objectWillChange.send() });observations.append(picker.profile.objectWillChange.sink { [weak self] _ in self?.objectWillChange.send() })}}
    private var authorization:SyntheticInboxLinkClientAuthorization? {context.flatMap {c in port?.grants.compactMap {$0.authorization(for:c)}.first}}
    var record:InboxLinkClientRecord? {ledger.visible(authorization)}
    var retainedAttemptCount:Int {ledger.records.count}
    func blocks(business:Int,conversation:Int)->Bool {ledger.blocked(business:business,conversation:conversation)}
    var blocked:Bool {context.map {blocks(business:$0.business,conversation:$0.conversation)} ?? false}
    var ownsEditor:Bool {loading || editing || review != nil}
    var control:InboxLinkClientControl? {context.map {InboxLinkClientControl(context:$0,visit:visit,source:source,editing:editing,picker:picker?.control,candidate:candidate,review:review,record:record)}}
    private var pending:Bool {guard let c=context else {return false};return ledger.records.contains {$0.phase == .pending && $0.attempt.review.source.context.business==c.business && $0.attempt.review.source.context.conversation==c.conversation}}
    var canLoad:Bool {presented && !loading && !editing && review==nil && !pending}
    var canOpen:Bool {presented && !loading && failure==nil && source?.context==context && source != nil && authorization != nil && picker != nil && !editing && review==nil && !blocked && !commandsBlocked()}
    var canEdit:Bool {presented && editing && review==nil && !loading && !blocked && !commandsBlocked() && source?.context==context && authorization != nil}
    var input:InboxLinkClientInput? {guard canEdit,let c=context,let auth=authorization,let picker,!picker.session.loading,picker.session.profileSelection==nil,let child=picker.inputControl else {return nil};return InboxLinkClientInput(context:c,editor:editor,authorization:auth,child:child)}
    private var candidateCurrent:Bool {guard let candidate,let picker else {return false};return candidate.source==source && candidate.selected==picker.session.profileSelection && candidate.read==picker.profile.readSelection && SourceTextIdentity.same(candidate.rawQuery,picker.session.query) && picker.profile.failure==nil && picker.profile.detail.flatMap {TaskDraftClientChoice(profile:$0,business:candidate.choice.business,id:candidate.choice.id)}==candidate.choice}
    var canPrepare:Bool {canEdit && candidateCurrent && picker?.session.loading==false && picker?.profile.loading==false}
    var canSubmit:Bool {guard let review else {return false};return presented && editing && !loading && !blocked && !commandsBlocked() && review.valid && candidateCurrent && review.source==source && review.authorization==authorization && review.candidate==candidate}
    private func stash() {if editing,let picker {query=picker.session.query;queryOwner=authorization}}
    func hide() {stash();generation += 1;editor += 1;visit += 1;presented=false;source=nil;loading=false;failure=nil;editing=false;candidate=nil;review=nil;picker?.bind(nil)}
    func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard next != context else {return};hide();context=next;query="";queryOwner=nil}
    func show() {guard context != nil else {return};presented=true;visit += 1}
    func load(expected:InboxLinkClientControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canLoad,let c=context else {return};generation += 1;let ticket=generation;visit += 1;source=nil;candidate=nil;failure=nil;loading=true
        do {let s=try await repository.source(c);try Task.checkCancellation();guard ticket==generation,context==c,presented else {return};guard s.context==c else {throw ReadFailure.invalidPayload};source=s;loading=false;visit += 1}
        catch {guard ticket==generation,context==c,presented else {return};source=nil;loading=false;failure=error is CancellationError ? nil:(error as? ReadFailure ?? .unavailable);visit += 1}
    }
    func open(expected:InboxLinkClientControl?) {guard let expected,control==expected,canOpen,let picker,let c=context else {return};editor += 1;visit += 1;editing=true;candidate=nil;let scope=ClientSearchContext(business:c.business,epoch:c.epoch);picker.bind(nil);picker.bind(scope);picker.open(scope);picker.update(queryOwner==authorization ? query:"",input:picker.inputControl)}
    func update(_ raw:String,input:InboxLinkClientInput?) {guard let input,self.input==input,let picker else {return};let before=picker.session.query;picker.update(raw,input:input.child);if !SourceTextIdentity.same(before,picker.session.query) {candidate=nil;query=picker.session.query;queryOwner=authorization}}
    func search(expected:InboxLinkClientControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canEdit,let picker,picker.matches(child) else {return};visit += 1;candidate=nil;let ticket=generation;await picker.submit(expected:child);if ticket==generation {visit += 1}}
    func openClient(_ id:Int,expected:InboxLinkClientControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canEdit,let picker,picker.matches(child) else {return};visit += 1;candidate=nil;let ticket=generation;await picker.openClient(id,expected:child);if ticket==generation {visit += 1}}
    func retryClient(expected:InboxLinkClientControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canEdit,let picker,picker.matches(child),!picker.profile.loading else {return};visit += 1;candidate=nil;let ticket=generation;await picker.retryProfile(expected:child);if ticket==generation {visit += 1}}
    func backClient(expected:InboxLinkClientControl?,child:ClientSearchControl?) {guard let expected,control==expected,canEdit,let picker,picker.matches(child) else {return};picker.backProfile(expected:child);candidate=nil;visit += 1}
    func useClient(expected:InboxLinkClientControl?,child:ClientSearchControl?) {
        guard let expected,control==expected,canEdit,let source,let picker,let child,picker.matches(child),let selected=picker.session.profileSelection,selected==child.profile,let read=picker.profile.readSelection,read==child.read,!picker.profile.loading,picker.profile.failure==nil,let profile=picker.profile.detail,let value=InboxLinkClientCandidate(source:source,selected:selected,read:read,rawQuery:picker.session.query,profile:profile) else {return};candidate=value;stash();visit += 1
    }
    func clearChoice(expected:InboxLinkClientControl?) {guard let expected,control==expected,canEdit else {return};candidate=nil;visit += 1}
    func prepare(expected:InboxLinkClientControl?) {guard let expected,control==expected,canPrepare,let source,let candidate,let auth=authorization else {return};visit += 1;editor += 1;review=InboxLinkClientReview(source:source,authorization:auth,candidate:candidate,visit:visit)}
    func back(expected:InboxLinkClientControl?) {guard let expected,control==expected,!blocked else {return};if review != nil {review=nil;editor += 1} else {stash();editing=false;candidate=nil;picker?.bind(nil);editor += 1};visit += 1}
    func submit(expected:InboxLinkClientControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmit,let review,let port,let a=ledger.begin(review) else {return};stash();visit += 1;editor += 1;self.review=nil;editing=false;picker?.bind(nil)
        let outcome:SyntheticInboxLinkClientOutcome;do {let value=try await port.execute(a);outcome=Task.isCancelled ? .unknown:value} catch {outcome = .unknown};ledger.complete(a,outcome:outcome);if context==a.review.source.context {visit += 1}
    }
    func acknowledge(_ record:InboxLinkClientRecord,expected:InboxLinkClientControl?) {guard let expected,control==expected,let auth=authorization,ledger.acknowledge(auth,record:record) else {return};if record.phase == .response {source=nil};candidate=nil;review=nil;visit += 1}
}
