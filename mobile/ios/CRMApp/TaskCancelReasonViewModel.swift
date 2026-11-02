import SwiftUI
import CRMCore

// Local presentation controls, never command authority or source versions.
struct TaskCancelReasonEntryControl:Equatable {let read:TaskCommentRead;let visit:Int}
struct TaskCancelReasonControl:Equatable {let selection:TaskCancelReasonSelection;let visit:Int}
struct TaskCancelReasonInputControl:Equatable {let control:TaskCancelReasonControl}
struct TaskCancelReasonClearConfirmation:Equatable {let id:Int;let control:TaskCancelReasonControl;let contentRevision:Int}
struct TaskCancelReasonReturnControl:Equatable {let editor:TaskCancelReasonControl?;let clear:TaskCancelReasonClearConfirmation?}
@MainActor final class TaskCancelReasonViewModel: ObservableObject {
    @Published private(set) var session=TaskCancelReasonSession()
    @Published private var ledger=TaskCancelAttemptLedger()
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var clearConfirmation:TaskCancelReasonClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    var entryControl:TaskCancelReasonEntryControl? {guard session.available,session.selection==nil,let read=session.read else {return nil};return TaskCancelReasonEntryControl(read:read,visit:entryVisit)}
    var control:TaskCancelReasonControl? {session.selection.map {TaskCancelReasonControl(selection:$0,visit:viewVisit)}}
    var inputControl:TaskCancelReasonInputControl? {guard !submissionBlocked,session.phase == .editing,let control else {return nil};return TaskCancelReasonInputControl(control:control)}
    var returnControl:TaskCancelReasonReturnControl {TaskCancelReasonReturnControl(editor:control,clear:clearConfirmation)}
    private func invalidateVisit() {entryVisit += 1;viewVisit += 1;clearConfirmation=nil}
    private var sourceStatus:String?
    private let port: (any SyntheticTaskCancelPort)?
    init(port: (any SyntheticTaskCancelPort)?=nil) {self.port=port}
    private var authorization: SyntheticTaskCancelAuthorization? {
        guard session.available,["open","in_progress"].contains(sourceStatus ?? ""),let context=session.read?.context else {return nil}
        return port?.grants.compactMap {$0.authorization(for:context)}.first
    }
    var submission: TaskCancelAttemptRecord? {ledger.visible(authorization)}
    var currentReadConfirmed:Bool {guard let read=session.read else {return false};return ledger.records.contains {$0.phase == .confirmed && $0.attempt.review.selection.read==read}}
    var submissionBlocked: Bool {session.read.map {ledger.blocked($0.context)} ?? false}
    var canSubmit: Bool {authorization != nil && !submissionBlocked && session.phase == .review}
    var retainedAttemptCount: Int {ledger.records.count}
    func retainOwner(business: Int?,epoch: Int?) {sourceStatus=nil;session.retainOwner(business:business,epoch:epoch);invalidateVisit()}
    func begin(_ read: TaskCommentRead?) {sourceStatus=nil;session.begin(read);invalidateVisit()}
    func receive(_ verified: Bool,status:String?,_ read: TaskCommentRead) {guard session.read==read else {return};session.receive(verified:verified,status:status,expected:read);sourceStatus=session.available ? status:nil;invalidateVisit()}
    func pause() {sourceStatus=nil;session.pause();invalidateVisit()}
    func open(_ read: TaskCommentRead) {if session.open(expected:read) {invalidateVisit()}}
    func update(_ text: String,_ selection: TaskCancelReasonSelection) {guard !submissionBlocked else {return};let before=session.text;session.update(text,expected:selection);if session.text != before {contentRevision += 1;clearConfirmation=nil}}
    func prepare(_ selection: TaskCancelReasonSelection) {guard !submissionBlocked else {return};if session.prepare(expected:selection) {invalidateVisit()}}
    func back(_ selection: TaskCancelReasonSelection) {guard session.selection==selection else {return};if submissionBlocked {session.close(expected:selection)} else {session.back(expected:selection)};invalidateVisit()}
    func close(_ selection: TaskCancelReasonSelection) {guard session.selection==selection else {return};session.close(expected:selection);invalidateVisit()}
    func discard(_ selection: TaskCancelReasonSelection) {guard !submissionBlocked,session.selection==selection else {return};session.discard(expected:selection);contentRevision += 1;invalidateVisit()}
    func submit(_ expected: TaskCancelReasonReview) async {
        let selection=expected.selection
        guard session.selection==selection,session.available,session.phase == .review,let review=session.review,review==expected,let authorization,let port,let sourceStatus,let attempt=ledger.begin(review:review,raw:session.text,status:sourceStatus,authorization:authorization) else {return}
        invalidateVisit()
        let outcome: SyntheticTaskCancelOutcome
        do {let result=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown : result} catch {outcome = .unknown}
        // Completion updates only its retained attempt. Visibility revalidates current owner.
        ledger.complete(attempt,outcome:outcome)
        if submission?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(_ selection: TaskCancelReasonSelection,attemptID: Int) {
        guard session.selection==selection,let authorization,let record=submission,record.attempt.localID==attemptID,ledger.acknowledge(authorization) else {return}
        if record.phase == .confirmed {session.discard(expected:selection);contentRevision += 1} else if session.phase == .review {session.back(expected:selection)}
        invalidateVisit()
    }
    // Raw trusted APIs above retain Core/ledger behavior. UI uses captured controls.
    func open(expected:TaskCancelReasonEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.read)}
    func update(_ text:String,input:TaskCancelReasonInputControl?) {guard let input,inputControl==input else {return};update(text,input.control.selection)}
    func prepare(expected:TaskCancelReasonControl?) {guard let expected,control==expected else {return};prepare(expected.selection)}
    func back(expected:TaskCancelReasonReturnControl?) {
        guard let expected,returnControl==expected else {return}
        if let question=expected.clear {dismissClear(question)} else if let editor=expected.editor {back(editor.selection)}
    }
    func close(expected:TaskCancelReasonReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};close(editor.selection)}
    func submit(_ review:TaskCancelReasonReview,expected:TaskCancelReasonControl?) async {guard let expected,control==expected,clearConfirmation==nil,canSubmit else {return};await submit(review)}
    func acknowledge(expected:TaskCancelReasonControl?,record:TaskCancelAttemptRecord) {guard let expected,control==expected,submission==record else {return};acknowledge(expected.selection,attemptID:record.attempt.localID)}
    func askClear(expected:TaskCancelReasonControl?) {
        guard let expected,control==expected,session.available,!submissionBlocked else {return}
        dialogRevision += 1;clearConfirmation=TaskCancelReasonClearConfirmation(id:dialogRevision,control:expected,contentRevision:contentRevision)
    }
    func dismissClear(_ expected:TaskCancelReasonClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:TaskCancelReasonClearConfirmation) {guard clearConfirmation==expected,control==expected.control,contentRevision==expected.contentRevision,!submissionBlocked else {return};discard(expected.control.selection)}
}
