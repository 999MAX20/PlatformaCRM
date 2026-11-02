import SwiftUI
import CRMCore

struct TaskAppointmentEditControl:Equatable {let source:TaskAppointmentEditSource;let visit:Int;let draft:TaskAppointmentEditDraft;let editing:Bool;let review:TaskAppointmentEditReview?;let record:TaskAppointmentEditRecord?;let clearID:Int?}
struct TaskAppointmentEditInputControl:Equatable {let source:TaskAppointmentEditSource;let visit:Int;let child:TaskAppointmentPickerInputControl}
struct TaskAppointmentEditClear:Equatable {let id:Int;let read:TaskCommentRead;let visit:Int;let draft:TaskAppointmentEditDraft}
@MainActor final class TaskAppointmentEditViewModel:ObservableObject {
    @Published private(set) var source:TaskAppointmentEditSource?
    @Published private(set) var review:TaskAppointmentEditReview?
    @Published private(set) var draft=TaskAppointmentEditDraft()
    @Published private(set) var editing=false
    @Published private(set) var showsIssue=false
    @Published private(set) var clearConfirmation:TaskAppointmentEditClear?
    @Published private var ledger=TaskAppointmentEditLedger()
    @Published private var visit=0
    private var dialog=0
    private var ownerBusiness:Int?,ownerEpoch:Int?
    private var buffers:[String:TaskAppointmentEditDraft]=[:]
    private var consumedReads:[TaskCommentRead]=[]
    let picker:TaskAppointmentPickerViewModel
    private let port:any SyntheticTaskAppointmentEditPort
    init(port:any SyntheticTaskAppointmentEditPort,appointments:any AgendaRepository) {self.port=port;picker=TaskAppointmentPickerViewModel(repository:appointments)}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)/\(c.epoch)"}
    private var authorization:SyntheticTaskAppointmentEditAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskAppointmentEditRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskAppointmentEditControl? {source.map {TaskAppointmentEditControl(source:$0,visit:visit,draft:draft,editing:editing,review:review,record:submission,clearID:clearConfirmation?.id)}}
    var inputControl:TaskAppointmentEditInputControl? {guard let source,draft.mode == .set,editing,!blocked,!consumed,review==nil,clearConfirmation==nil,let child=picker.inputControl else {return nil};return TaskAppointmentEditInputControl(source:source,visit:visit,child:child)}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.statusValid==true || blocked || consumed)}
    var canOpen:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && !editing && review==nil}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && editing && review==nil && clearConfirmation==nil}
    var ownsEditor:Bool {editing || review != nil || clearConfirmation != nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    private func stash() {if let source {buffers[key(source.read.context)]=draft}}
    func bind(_ next:TaskAppointmentEditSource?) {
        let next=next?.identityValid==true ? next:nil;guard source != next else {return}
        if let next {let c=next.read.context;if ownerBusiness != c.business || ownerEpoch != c.epoch {buffers=[:]};ownerBusiness=c.business;ownerEpoch=c.epoch}
        picker.begin(nil);source=next;draft=next.flatMap {buffers[key($0.read.context)]} ?? TaskAppointmentEditDraft();editing=false;review=nil;clearConfirmation=nil;showsIssue=false;visit += 1
    }
    func retainOwner(business:Int?,epoch:Int?) {if ownerBusiness != business || ownerEpoch != epoch || business==nil || epoch==nil {buffers=[:]};ownerBusiness=business;ownerEpoch=epoch;bind(nil)}
    private func resumePicker() {guard let source else {return};picker.begin(TaskDraftContext(business:source.read.context.business,epoch:source.read.context.epoch));picker.updateDay(draft.day,expected:picker.control)}
    func interrupt() {guard !blocked else {return};editing=false;review=nil;clearConfirmation=nil;showsIssue=false;picker.begin(nil);visit += 1}
    func open(expected:TaskAppointmentEditControl?) {guard let expected,control==expected,canOpen else {return};visit += 1;editing=true;resumePicker();showsIssue=false}
    func choose(_ mode:TaskAppointmentEditMode,expected:TaskAppointmentEditControl?) {guard let expected,control==expected,canPrepare else {return};draft.mode=mode;stash();visit += 1;showsIssue=false}
    func updateDay(_ raw:String,input:TaskAppointmentEditInputControl?) {
        guard let input,inputControl==input else {return};let before=picker.day;picker.updateDay(raw,input:input.child)
        if picker.day != before {draft.day=picker.day;draft.choiceRead=nil;stash();showsIssue=false}
    }
    func readAppointments(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set else {return};await picker.read(expected:child)}
    func openAppointment(_ id:Int,expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set else {return};await picker.open(id,expected:child)}
    func retryAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) async {guard let expected,control==expected,canPrepare,draft.mode == .set else {return};await picker.retryDetail(expected:child)}
    func backAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {guard let expected,control==expected,canPrepare,draft.mode == .set else {return};picker.backDetail(expected:child)}
    func useAppointment(expected:TaskAppointmentEditControl?,child:TaskAppointmentPickerControl?) {
        guard let expected,control==expected,canPrepare,draft.mode == .set,let choice=picker.choice(expected:child),choice.valid(for:expected.source.read.context.business) else {return}
        draft.choice=choice;draft.choiceRead=expected.source.read;stash();showsIssue=false;visit += 1
    }
    func prepare(expected:TaskAppointmentEditControl?) {guard let expected,control==expected,canPrepare else {return};guard draft.change(for:expected.source) != nil else {showsIssue=true;return};visit += 1;review=TaskAppointmentEditReview(source:expected.source,visit:visit,draft:draft);showsIssue=false}
    func back(expected:TaskAppointmentEditControl?) {guard let expected,control==expected,!blocked else {return};if let clearConfirmation {dismissClear(clearConfirmation);return};if review != nil {review=nil} else {editing=false;picker.begin(nil)};showsIssue=false;visit += 1}
    func askClear(expected:TaskAppointmentEditControl?) {guard let expected,control==expected,canPrepare else {return};dialog += 1;visit += 1;clearConfirmation=TaskAppointmentEditClear(id:dialog,read:expected.source.read,visit:visit,draft:draft)}
    func dismissClear(_ expected:TaskAppointmentEditClear) {guard clearConfirmation==expected else {return};clearConfirmation=nil;visit += 1}
    func confirmClear(_ expected:TaskAppointmentEditClear) {guard clearConfirmation==expected,source?.read==expected.read,visit==expected.visit,draft==expected.draft,!blocked,!consumed else {return};draft=TaskAppointmentEditDraft();stash();resumePicker();clearConfirmation=nil;showsIssue=false;visit += 1}
    func submit(expected:TaskAppointmentEditControl?) async {
        guard !Task.isCancelled,let expected,control==expected,clearConfirmation==nil,let review,review.source==source,review.draft==draft,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskAppointmentEditOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskAppointmentEditControl?,record:TaskAppointmentEditRecord) {guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return};if record.phase == .confirmed {consumedReads.append(expected.source.read);draft=TaskAppointmentEditDraft();stash();editing=false;picker.begin(nil)} else {editing=true};review=nil;clearConfirmation=nil;showsIssue=false;visit += 1}
}
