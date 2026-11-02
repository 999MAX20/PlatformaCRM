import SwiftUI
import CRMCore

struct TaskTitleEditControl:Equatable {let source:TaskTitleEditSource;let visit:Int;let raw:String;let editing:Bool;let review:TaskTitleEditReview?;let record:TaskTitleEditRecord?;let clearID:Int?
    static func ==(lhs:Self,rhs:Self)->Bool {lhs.source==rhs.source && lhs.visit==rhs.visit && lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.editing==rhs.editing && lhs.review==rhs.review && lhs.record==rhs.record && lhs.clearID==rhs.clearID}
}
struct TaskTitleEditInputControl:Equatable {let source:TaskTitleEditSource;let visit:Int}
struct TaskTitleEditClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let raw:String}
@MainActor final class TaskTitleEditViewModel:ObservableObject {
    @Published private(set) var source:TaskTitleEditSource?
    @Published private(set) var review:TaskTitleEditReview?
    @Published private(set) var raw=""
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskTitleEditClear?
    @Published private var ledger=TaskTitleEditLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:String]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskTitleEditPort
    init(port:any SyntheticTaskTitleEditPort) {self.port=port}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskTitleEditAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskTitleEditRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskTitleEditControl? {source.map {TaskTitleEditControl(source:$0,visit:visit,raw:raw,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskTitleEditInputControl? {guard let source,editing,!blocked,!consumed,review==nil,clearConfirmation==nil else {return nil};return TaskTitleEditInputControl(source:source,visit:visit)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskTitleEditSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        source=next;raw=next.flatMap {buffers[key($0.read.context)]} ?? "";editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {
        if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:]}
        ownerBusiness=business;ownerEpoch=epoch;bind(nil)
    }
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
    func open(expected:TaskTitleEditControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;showsIssue=false}
    func update(_ value:String,input:TaskTitleEditInputControl?) {guard let input,inputControl==input else {return};raw=value;buffers[key(input.source.read.context)]=value;showsIssue=false}
    func prepare(expected:TaskTitleEditControl?) {
        guard let expected,control==expected,canPrepare else {return}
        guard let value=TaskTitleValue.parse(raw) else {showsIssue=true;return}
        visit += 1;review=TaskTitleEditReview(source:expected.source,visit:visit,value:value);showsIssue=false
    }
    func back(expected:TaskTitleEditControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false};showsIssue=false;visit += 1}
    func askClear(expected:TaskTitleEditControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskTitleEditClear(id:dialog,read:expected.source.read,visit:visit,raw:raw)}
    func dismissClear(_ expected:TaskTitleEditClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskTitleEditClear) {
        guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,raw==expected.raw,!blocked,!consumed else {return}
        raw="";buffers[key(expected.read.context)]="";clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func submit(expected:TaskTitleEditControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.value.raw.utf8.elementsEqual(raw.utf8),let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskTitleEditOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskTitleEditControl?,record:TaskTitleEditRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read);raw="";buffers[key(expected.source.read.context)]="";editing=false} else {editing=true}
        review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
}
struct TaskTitleEditView:View {
    @ObservedObject var model:TaskTitleEditViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskTitleEditControl)->Void
    private func key(_ phase:TaskTitleEditPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskTitleEditFakeConfirmed";case .rejected:"taskTitleEditFakeRejected";case .unknown:"taskTitleEditFakeUnknown"}}
    var body:some View {
        let input=model.inputControl,question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskTitleEditAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        LabeledContent(AppCopy.text("taskTitleEditRaw"),value:record.attempt.review.value.raw).textSelection(.enabled)
                        LabeledContent(AppCopy.text("taskTitleEditProposed"),value:record.attempt.review.value.title).textSelection(.enabled)
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskTitleEditReturned"),value:result.title)}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskTitleEditFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"));LabeledContent(AppCopy.text("taskTitleEditRaw"),value:review.value.raw).textSelection(.enabled);LabeledContent(AppCopy.text("taskTitleEditProposed"),value:review.value.title).textSelection(.enabled)
                    Text(AppCopy.text("taskTitleEditContract"))
                    Button(AppCopy.text("taskTitleEditFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    TextField(AppCopy.text("taskTitle"),text:Binding(get:{model.raw},set:{if isCurrent() {model.update($0,input:input)}})).accessibilityHint(model.showsIssue ? AppCopy.text("taskTitleEditInputIssue") : "")
                    if model.showsIssue {Text(AppCopy.text("taskTitleEditInputIssue")).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskTitleEditAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {
                    Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskTitleEditAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))
                }
            }
        }
    }
}
