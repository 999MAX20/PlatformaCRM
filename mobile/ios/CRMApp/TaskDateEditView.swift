import SwiftUI
import CRMCore

struct TaskDateEditControl:Equatable {let source:TaskDateEditSource;let visit:Int;let draft:TaskDateDraft;let editing:Bool;let review:TaskDateEditReview?;let record:TaskDateEditRecord?;let clearID:Int?}
struct TaskDateEditInputControl:Equatable {let source:TaskDateEditSource;let visit:Int;let field:TaskDateField}
struct TaskDateEditClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let draft:TaskDateDraft}
@MainActor final class TaskDateEditViewModel:ObservableObject {
    @Published private(set) var source:TaskDateEditSource?
    @Published private(set) var review:TaskDateEditReview?
    @Published private(set) var draft=TaskDateDraft()
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskDateEditClear?
    @Published private var ledger=TaskDateEditLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:TaskDateDraft]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskDateEditPort
    init(port:any SyntheticTaskDateEditPort) {self.port=port}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskDateEditAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskDateEditRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskDateEditControl? {source.map {TaskDateEditControl(source:$0,visit:visit,draft:draft,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskDateEditInputControl? {guard let source,let field=draft.field,draft.mode == .setDate,editing,!blocked,!consumed,review==nil,clearConfirmation==nil else {return nil};return TaskDateEditInputControl(source:source,visit:visit,field:field)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    private func stash() {if let source {buffers[key(source.read.context)]=draft}}
    func bind(_ next:TaskDateEditSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        source=next;draft=next.flatMap {buffers[key($0.read.context)]} ?? TaskDateDraft();editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:]};ownerBusiness=business;ownerEpoch=epoch;bind(nil)}
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
    func open(expected:TaskDateEditControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;showsIssue=false}
    func select(_ field:TaskDateField,expected:TaskDateEditControl?) {guard let expected,control==expected,canPrepare else {return};draft.select(field);stash();visit += 1;showsIssue=false}
    func choose(_ mode:TaskDateMode,expected:TaskDateEditControl?) {guard let expected,control==expected,canPrepare,draft.field != nil else {return};draft.choose(mode);stash();visit += 1;showsIssue=false}
    func update(_ raw:String,input:TaskDateEditInputControl?) {guard let input,inputControl==input else {return};draft.update(raw);stash();showsIssue=false}
    func prepare(expected:TaskDateEditControl?) {guard let expected,control==expected,canPrepare else {return};guard let change=draft.change else {showsIssue=true;return};visit += 1;review=TaskDateEditReview(source:expected.source,visit:visit,change:change);showsIssue=false}
    func back(expected:TaskDateEditControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false};showsIssue=false;visit += 1}
    func askClear(expected:TaskDateEditControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskDateEditClear(id:dialog,read:expected.source.read,visit:visit,draft:draft)}
    func dismissClear(_ expected:TaskDateEditClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskDateEditClear) {guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,draft==expected.draft,!blocked,!consumed else {return};draft=TaskDateDraft();stash();clearConfirmation=nil;showsIssue=false;visit += 1}
    func submit(expected:TaskDateEditControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.change==draft.change,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskDateEditOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskDateEditControl?,record:TaskDateEditRecord) {guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return};if record.phase == .confirmed {consumedReads.append(expected.source.read);draft=TaskDateDraft();stash();editing=false} else {editing=true};review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
}
struct TaskDateEditView:View {
    @ObservedObject var model:TaskDateEditViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (TaskDateEditControl)->Void
    private func field(_ value:TaskDateField)->String {AppCopy.text(value == .dueAt ? "taskDue":"taskReminderAt")}
    private func mode(_ value:TaskDateMode)->String {AppCopy.text(value == .setDate ? "taskDateSet":"taskDateRemove")}
    private func key(_ phase:TaskDateEditPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskDateFakeConfirmed";case .rejected:"taskDateFakeRejected";case .unknown:"taskDateFakeUnknown"}}
    var body:some View {
        let input=model.inputControl,question=model.clearConfirmation
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskDateAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(field(record.attempt.review.change.field)+" · "+mode(record.attempt.review.change.mode))
                        if record.attempt.review.change.mode == .setDate {Text(record.attempt.review.change.raw).textSelection(.enabled)}
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let result=record.result {LabeledContent(AppCopy.text("taskDateReturned"),value:result.value ?? AppCopy.text("taskScheduleNotSet"))}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskDateFakeConfirmed"))}
                else if let review=model.review {
                    Text(field(review.change.field)+" · "+mode(review.change.mode));if review.change.mode == .setDate {Text(review.change.raw).textSelection(.enabled)}
                    Text(AppCopy.text("taskDateContract"))
                    Button(AppCopy.text("taskDateFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("back")))
                } else if model.editing {
                    Text(AppCopy.text("taskDateChooseField"))
                    ForEach(TaskDateField.allCases,id:\.self) {option in Button(field(option)+(model.draft.field==option ? " ✓":"")) {if isCurrent() {model.select(option,expected:control)}}.accessibilityAddTraits(model.draft.field==option ? .isSelected:[])}
                    if model.draft.field != nil {
                        Button(mode(.setDate)) {if isCurrent() {model.choose(.setDate,expected:control)}}.accessibilityAddTraits(model.draft.mode == .setDate ? .isSelected:[])
                        Button(mode(.clearDate)) {if isCurrent() {model.choose(.clearDate,expected:control)}}.accessibilityAddTraits(model.draft.mode == .clearDate ? .isSelected:[])
                        if let selected=model.draft.mode {Text(mode(selected))}
                        if model.draft.mode == .setDate {TextField(AppCopy.text("taskSnoozeInput"),text:Binding(get:{model.draft.raw},set:{if isCurrent() {model.update($0,input:input)}})).accessibilityHint(model.showsIssue ? AppCopy.text("taskDateInputIssue") : "")}
                    }
                    if model.showsIssue {Text(AppCopy.text("taskDateInputIssue")).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(model.draft.field != nil && model.draft.mode == .setDate)}
                    Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control)}}
                    Button(AppCopy.text("clientDraftClear")) {if isCurrent() {model.askClear(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("clientDraftClear")))
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("back")))
                } else if model.canOpen {Button(AppCopy.text("taskDateAction")) {if isCurrent() {open(control)}}}
            }.alert(AppCopy.text("clientDraftClearQuestion"),isPresented:Binding(get:{model.clearConfirmation != nil},set:{if !$0,let question,isCurrent() {model.dismissClear(question)}})) {
                if let question {Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")));Button(AppCopy.text("back"),role:.cancel) {if isCurrent() {model.dismissClear(question)}}.accessibilityLabel(Text(AppCopy.text("taskDateAction")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("back")))}
            }
        }
    }
}
