import SwiftUI
import CRMCore

struct TaskClientEditControl:Equatable {let source:TaskClientEditSource;let visit:Int;let draft:TaskClientEditDraft;let editing:Bool;let review:TaskClientEditReview?;let record:TaskClientEditRecord?;let clearID:Int?}
struct TaskClientEditInputControl:Equatable {let source:TaskClientEditSource;let visit:Int;let child:ClientSearchInputControl}
struct TaskClientEditClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let draft:TaskClientEditDraft}
@MainActor final class TaskClientEditViewModel:ObservableObject {
    @Published private(set) var source:TaskClientEditSource?
    @Published private(set) var review:TaskClientEditReview?
    @Published private(set) var draft=TaskClientEditDraft()
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskClientEditClear?
    @Published private var ledger=TaskClientEditLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:TaskClientEditDraft]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    let picker:ClientSearchViewModel
    private let port:any SyntheticTaskClientEditPort
    init(port:any SyntheticTaskClientEditPort,clients:any ClientSearchRepository) {self.port=port;picker=ClientSearchViewModel(repository:clients)}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskClientEditAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskClientEditRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskClientEditControl? {source.map {TaskClientEditControl(source:$0,visit:visit,draft:draft,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskClientEditInputControl? {guard let source,draft.mode == .set,editing,!blocked,!consumed,review==nil,clearConfirmation==nil,!picker.session.loading,picker.session.profileSelection==nil,let child=picker.inputControl else {return nil};return TaskClientEditInputControl(source:source,visit:visit,child:child)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.statusValid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    private func stash() {if let source {buffers[key(source.read.context)]=draft}}
    func bind(_ next:TaskClientEditSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        picker.bind(nil);source=next;draft=next.flatMap {buffers[key($0.read.context)]} ?? TaskClientEditDraft();editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:]};ownerBusiness=business;ownerEpoch=epoch;bind(nil)}
    private func resumePicker() {guard let source else {return};let context=ClientSearchContext(business:source.read.context.business,epoch:source.read.context.epoch);picker.bind(nil);picker.bind(context);picker.open(context);picker.update(draft.query,input:picker.inputControl)}
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;picker.bind(nil);visit += 1}
    func open(expected:TaskClientEditControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;resumePicker();showsIssue=false}
    func choose(_ mode:TaskClientEditMode,expected:TaskClientEditControl?) {guard let expected,control==expected,canPrepare else {return};draft.mode=mode;stash();visit += 1;showsIssue=false}
    func updateQuery(_ raw:String,input:TaskClientEditInputControl?) {
        guard let input,inputControl==input else {return};let before=picker.session.query;picker.update(raw,input:input.child)
        if !picker.session.query.utf8.elementsEqual(before.utf8) {draft.query=picker.session.query;draft.choiceRead=nil;stash();showsIssue=false}
    }
    func readClients(expected:TaskClientEditControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set,picker.matches(child) else {return};visit += 1;await picker.submit(expected:child)}
    func openClient(_ id:Int,expected:TaskClientEditControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set,picker.matches(child) else {return};visit += 1;await picker.openClient(id,expected:child)}
    func retryClient(expected:TaskClientEditControl?,child:ClientSearchControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set,picker.matches(child) else {return};visit += 1;await picker.retryProfile(expected:child)}
    func backClient(expected:TaskClientEditControl?,child:ClientSearchControl?) {guard let expected,control==expected,canPrepare,draft.mode == .set,picker.matches(child) else {return};visit += 1;picker.backProfile(expected:child)}
    func useClient(expected:TaskClientEditControl?,child:ClientSearchControl?) {
        guard let expected,control==expected,canPrepare,draft.mode == .set,let child,picker.matches(child),let selected=picker.session.profileSelection,selected==child.profile,picker.profile.readSelection==child.read,!picker.profile.loading,picker.profile.failure==nil,let profile=picker.profile.detail,
              let choice=TaskDraftClientChoice(profile:profile,business:expected.source.read.context.business,id:selected.id) else {return}
        draft.choice=choice;draft.choiceRead=expected.source.read;stash();showsIssue=false;visit += 1
    }
    func prepare(expected:TaskClientEditControl?) {guard let expected,control==expected,canPrepare else {return};guard draft.change(for:expected.source) != nil else {showsIssue=true;return};visit += 1;review=TaskClientEditReview(source:expected.source,visit:visit,draft:draft);showsIssue=false}
    func back(expected:TaskClientEditControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false;picker.bind(nil)};showsIssue=false;visit += 1}
    func askClear(expected:TaskClientEditControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskClientEditClear(id:dialog,read:expected.source.read,visit:visit,draft:draft)}
    func dismissClear(_ expected:TaskClientEditClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskClientEditClear) {guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,draft==expected.draft,!blocked,!consumed else {return};draft=TaskClientEditDraft();stash();resumePicker();clearConfirmation=nil;showsIssue=false;visit += 1}
    func submit(expected:TaskClientEditControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.draft==draft,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskClientEditOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskClientEditControl?,record:TaskClientEditRecord) {guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return};if record.phase == .confirmed {consumedReads.append(expected.source.read);draft=TaskClientEditDraft();stash();editing=false;picker.bind(nil)} else {editing=true};review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
}
