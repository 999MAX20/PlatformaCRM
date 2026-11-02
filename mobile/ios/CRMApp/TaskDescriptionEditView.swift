import SwiftUI
import CRMCore

struct TaskDescriptionEditControl:Equatable {let source:TaskDescriptionEditSource;let visit:Int;let raw:String;let mode:TaskDescriptionMode?;let editing:Bool;let review:TaskDescriptionEditReview?;let record:TaskDescriptionEditRecord?;let clearID:Int?
    static func ==(lhs:Self,rhs:Self)->Bool {lhs.source==rhs.source && lhs.visit==rhs.visit && lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.mode==rhs.mode && lhs.editing==rhs.editing && lhs.review==rhs.review && lhs.record==rhs.record && lhs.clearID==rhs.clearID}
}
struct TaskDescriptionEditInputControl:Equatable {let source:TaskDescriptionEditSource;let visit:Int}
struct TaskDescriptionEditClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let raw:String}
@MainActor final class TaskDescriptionEditViewModel:ObservableObject {
    @Published private(set) var source:TaskDescriptionEditSource?
    @Published private(set) var review:TaskDescriptionEditReview?
    @Published private(set) var raw=""
    @Published private(set) var mode:TaskDescriptionMode?
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskDescriptionEditClear?
    @Published private var ledger=TaskDescriptionEditLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:String]=[:]
    private var modes:[String:TaskDescriptionMode]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskDescriptionEditPort
    init(port:any SyntheticTaskDescriptionEditPort) {self.port=port}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskDescriptionEditAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskDescriptionEditRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskDescriptionEditControl? {source.map {TaskDescriptionEditControl(source:$0,visit:visit,raw:raw,mode:mode,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskDescriptionEditInputControl? {guard let source,mode == .replaceText,editing,!blocked,!consumed,review==nil,clearConfirmation==nil else {return nil};return TaskDescriptionEditInputControl(source:source,visit:visit)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskDescriptionEditSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:];modes=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        mode=next.flatMap {modes[key($0.read.context)]};source=next;raw=next.flatMap {buffers[key($0.read.context)]} ?? "";editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {
        if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:];modes=[:]}
        ownerBusiness=business;ownerEpoch=epoch;bind(nil)
    }
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
    func open(expected:TaskDescriptionEditControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;showsIssue=false}
    func update(_ value:String,input:TaskDescriptionEditInputControl?) {guard let input,inputControl==input else {return};raw=value;buffers[key(input.source.read.context)]=value;showsIssue=false}
    func choose(_ value:TaskDescriptionMode,expected:TaskDescriptionEditControl?) {guard let expected,control==expected,canPrepare else {return};mode=value;modes[key(expected.source.read.context)]=value;showsIssue=false;visit += 1}
    func prepare(expected:TaskDescriptionEditControl?) {
        guard let expected,control==expected,canPrepare else {return}
        guard let value=TaskDescriptionValue.make(mode:mode,raw:raw) else {showsIssue=true;return}
        visit += 1;review=TaskDescriptionEditReview(source:expected.source,visit:visit,value:value);showsIssue=false
    }
    func back(expected:TaskDescriptionEditControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false};showsIssue=false;visit += 1}
    func askClear(expected:TaskDescriptionEditControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskDescriptionEditClear(id:dialog,read:expected.source.read,visit:visit,raw:raw)}
    func dismissClear(_ expected:TaskDescriptionEditClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskDescriptionEditClear) {
        guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,raw==expected.raw,!blocked,!consumed else {return}
        mode=nil;modes.removeValue(forKey:key(expected.read.context));raw="";buffers[key(expected.read.context)]="";clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func submit(expected:TaskDescriptionEditControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.value.raw.utf8.elementsEqual(raw.utf8),review.value.mode==mode,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskDescriptionEditOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskDescriptionEditControl?,record:TaskDescriptionEditRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read);mode=nil;modes.removeValue(forKey:key(expected.source.read.context));raw="";buffers[key(expected.source.read.context)]="";editing=false} else {editing=true}
        review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
}
struct TaskDescriptionEditView:View {
    @ObservedObject var model:TaskDescriptionEditViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskDescriptionEditControl)->Void
    private func key(_ phase:TaskDescriptionEditPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskDescriptionEditFakeConfirmed";case .rejected:"taskDescriptionEditFakeRejected";case .unknown:"taskDescriptionEditFakeUnknown"}}
    var body:some View {
        let input=model.inputControl,question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskDescriptionEditAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if let mode=model.mode {Text(AppCopy.text(mode == .replaceText ? "taskDescriptionEditReplace":"taskDescriptionEditRemove"))}
                if model.blocked {
                    if let record=model.submission {
                        LabeledContent(AppCopy.text("taskDescriptionEditRaw"),value:record.attempt.review.value.raw).textSelection(.enabled)
                        LabeledContent(AppCopy.text("taskDescriptionEditProposed"),value:record.attempt.review.value.description).textSelection(.enabled)
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskDescriptionEditReturned"),value:result.description)}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskDescriptionEditFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"));LabeledContent(AppCopy.text("taskDescriptionEditRaw"),value:review.value.raw).textSelection(.enabled);LabeledContent(AppCopy.text("taskDescriptionEditProposed"),value:review.value.description).textSelection(.enabled)
                    Text(AppCopy.text("taskDescriptionEditContract"))
                    Button(AppCopy.text("taskDescriptionEditFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    ForEach(TaskDescriptionMode.allCases,id:\.self) {value in
                        Button(AppCopy.text(value == .replaceText ? "taskDescriptionEditReplace":"taskDescriptionEditRemove")) {if isCurrent() {model.choose(value,expected:control)}}.accessibilityAddTraits(model.mode==value ? .isSelected:[])
                    }
                    if model.mode == .replaceText {TextEditor(text:Binding(get:{model.raw},set:{if isCurrent() {model.update($0,input:input)}})).frame(minHeight:100).accessibilityLabel(AppCopy.text("taskDescriptionEditRaw")).accessibilityHint(model.showsIssue ? AppCopy.text("taskDescriptionEditInputIssue") : "")}
                    if model.showsIssue {Text(AppCopy.text("taskDescriptionEditInputIssue")).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(model.mode == .replaceText)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskDescriptionEditAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {
                    Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskDescriptionEditAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))
                }
            }
        }
    }
}
