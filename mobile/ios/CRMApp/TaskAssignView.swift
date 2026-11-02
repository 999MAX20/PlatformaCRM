import SwiftUI
import CRMCore

struct TaskAssignControl:Equatable {let source:TaskAssignSource;let visit:Int;let raw:String;let editing:Bool;let review:TaskAssignReview?;let record:TaskAssignRecord?;let clearID:Int?}
struct TaskAssignInputControl:Equatable {let source:TaskAssignSource;let visit:Int}
struct TaskAssignClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let raw:String}
@MainActor final class TaskAssignViewModel:ObservableObject {
    @Published private(set) var source:TaskAssignSource?
    @Published private(set) var review:TaskAssignReview?
    @Published private(set) var raw=""
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskAssignClear?
    @Published private var ledger=TaskAssignLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:String]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskAssignPort
    init(port:any SyntheticTaskAssignPort) {self.port=port}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskAssignAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var eligibleMembers:[Int64] {authorization?.eligibleMembers ?? []}
    var submission:TaskAssignRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskAssignControl? {source.map {TaskAssignControl(source:$0,visit:visit,raw:raw,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskAssignInputControl? {guard let source,editing,!blocked,!consumed,review==nil,clearConfirmation==nil else {return nil};return TaskAssignInputControl(source:source,visit:visit)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskAssignSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        source=next;raw=next.flatMap {buffers[key($0.read.context)]} ?? "";editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {
        if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:]}
        ownerBusiness=business;ownerEpoch=epoch;bind(nil)
    }
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
    func open(expected:TaskAssignControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;showsIssue=false}
    func update(_ value:String,input:TaskAssignInputControl?) {guard let input,inputControl==input else {return};raw=value;buffers[key(input.source.read.context)]=value;showsIssue=false}
    func select(_ id:Int64,input:TaskAssignInputControl?) {guard eligibleMembers.contains(id) else {return};update(String(id),input:input)}
    func prepare(expected:TaskAssignControl?) {
        guard let expected,control==expected,canPrepare else {return}
        guard let value=TaskAssignValue.parse(raw),authorization?.eligibleMembers.contains(value.userID)==true else {showsIssue=true;return}
        visit += 1;review=TaskAssignReview(source:expected.source,visit:visit,value:value);showsIssue=false
    }
    func back(expected:TaskAssignControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false};showsIssue=false;visit += 1}
    func askClear(expected:TaskAssignControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskAssignClear(id:dialog,read:expected.source.read,visit:visit,raw:raw)}
    func dismissClear(_ expected:TaskAssignClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskAssignClear) {
        guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,raw==expected.raw,!blocked,!consumed else {return}
        raw="";buffers[key(expected.read.context)]="";clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func submit(expected:TaskAssignControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.value.raw==raw,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskAssignOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskAssignControl?,record:TaskAssignRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read);raw="";buffers[key(expected.source.read.context)]="";editing=false} else {editing=true}
        review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
}
struct TaskAssignView:View {
    @ObservedObject var model:TaskAssignViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskAssignControl)->Void
    private func key(_ phase:TaskAssignPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskAssignFakeConfirmed";case .rejected:"taskAssignFakeRejected";case .unknown:"taskAssignFakeUnknown"}}
    var body:some View {
        let input=model.inputControl,question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskAssignAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.value.raw).textSelection(.enabled)
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskAssignReturned"),value:String(result.assignee));LabeledContent(AppCopy.text("status"),value:AppCopy.text(result.status=="open" ? "taskOpen":"taskInProgress"))}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskAssignFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"));Text(review.value.raw).textSelection(.enabled)
                    Text(AppCopy.text("taskAssignContract"))
                    Button(AppCopy.text("taskAssignFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    Text(AppCopy.text("taskAssignSyntheticMembers")).font(.caption)
                    ForEach(model.eligibleMembers,id:\.self) {id in Button(String(id)) {if isCurrent() {model.select(id,input:input)}}}
                    TextField(AppCopy.text("taskAssignInput"),text:Binding(get:{model.raw},set:{if isCurrent() {model.update($0,input:input)}}))
                    if model.showsIssue {Text(AppCopy.text("taskAssignInputIssue")).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskAssignAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {
                    Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskAssignAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))
                }
            }
        }
    }
}
