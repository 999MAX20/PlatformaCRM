import SwiftUI
import CRMCore

// Local presentation controls, never command authority or source versions.
struct TaskCommentEntryControl:Equatable {let read:TaskCommentRead;let visit:Int}
struct TaskCommentControl:Equatable {let selection:TaskCommentSelection;let visit:Int}
struct TaskCommentInputControl:Equatable {let control:TaskCommentControl}
struct TaskCommentClearConfirmation:Equatable {let id:Int;let control:TaskCommentControl;let contentRevision:Int}
struct TaskCommentReturnControl:Equatable {let editor:TaskCommentControl?;let clear:TaskCommentClearConfirmation?}
@MainActor final class TaskCommentViewModel: ObservableObject {
    @Published private(set) var session=TaskCommentSession()
    @Published private var ledger=TaskCommentAttemptLedger()
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var clearConfirmation:TaskCommentClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    var entryControl:TaskCommentEntryControl? {guard session.available,session.selection==nil,let read=session.read else {return nil};return TaskCommentEntryControl(read:read,visit:entryVisit)}
    var control:TaskCommentControl? {session.selection.map {TaskCommentControl(selection:$0,visit:viewVisit)}}
    var inputControl:TaskCommentInputControl? {guard !submissionBlocked,session.phase == .editing,let control else {return nil};return TaskCommentInputControl(control:control)}
    var returnControl:TaskCommentReturnControl {TaskCommentReturnControl(editor:control,clear:clearConfirmation)}
    private func invalidateVisit() {entryVisit += 1;viewVisit += 1;clearConfirmation=nil}
    private let port: (any SyntheticTaskCommentPort)?
    init(port: (any SyntheticTaskCommentPort)?=nil) {self.port=port}
    private var authorization: SyntheticTaskCommentAuthorization? {
        guard session.available,let context=session.read?.context else {return nil}
        return port?.grants.compactMap {$0.authorization(for:context)}.first
    }
    var submission: TaskCommentAttemptRecord? {ledger.visible(authorization)}
    var submissionBlocked: Bool {session.read.map {ledger.blocked($0.context)} ?? false}
    var canSubmit: Bool {authorization != nil && !submissionBlocked && session.phase == .review}
    var retainedAttemptCount: Int {ledger.records.count}
    func retainOwner(business: Int?,epoch: Int?) {session.retainOwner(business:business,epoch:epoch);invalidateVisit()}
    func begin(_ read: TaskCommentRead?) {session.begin(read);invalidateVisit()}
    func receive(_ verified: Bool,_ read: TaskCommentRead) {guard session.read==read else {return};session.receive(verified:verified,expected:read);invalidateVisit()}
    func pause() {session.pause();invalidateVisit()}
    func open(_ read: TaskCommentRead) {if session.open(expected:read) {invalidateVisit()}}
    func update(_ text: String,_ selection: TaskCommentSelection) {guard !submissionBlocked else {return};let before=session.text;session.update(text,expected:selection);if !session.text.utf8.elementsEqual(before.utf8) {contentRevision += 1;clearConfirmation=nil}}
    func prepare(_ selection: TaskCommentSelection) {guard !submissionBlocked else {return};if session.prepare(expected:selection) {invalidateVisit()}}
    func back(_ selection: TaskCommentSelection) {guard session.selection==selection else {return};if submissionBlocked {session.close(expected:selection)} else {session.back(expected:selection)};invalidateVisit()}
    func close(_ selection: TaskCommentSelection) {guard session.selection==selection else {return};session.close(expected:selection);invalidateVisit()}
    func discard(_ selection: TaskCommentSelection) {guard !submissionBlocked,session.selection==selection else {return};session.discard(expected:selection);contentRevision += 1;invalidateVisit()}
    func submit(_ expected: TaskCommentReview) async {
        let selection=expected.selection
        guard session.selection==selection,session.available,session.phase == .review,let review=session.review,review==expected,let authorization,let port,let attempt=ledger.begin(review:review,raw:session.text,authorization:authorization) else {return}
        invalidateVisit()
        let outcome: SyntheticTaskCommentOutcome
        do {let result=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown : result} catch {outcome = .unknown}
        // Completion updates only its retained attempt. Visibility revalidates current owner.
        ledger.complete(attempt,outcome:outcome)
        if submission?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(_ selection: TaskCommentSelection,attemptID: Int) {
        guard session.selection==selection,let authorization,let record=submission,record.attempt.localID==attemptID,ledger.acknowledge(authorization) else {return}
        if record.phase == .confirmed {session.discard(expected:selection);contentRevision += 1} else if session.phase == .review {session.back(expected:selection)}
        invalidateVisit()
    }
    // Raw trusted APIs above retain Core/ledger behavior. UI uses captured controls.
    func open(expected:TaskCommentEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.read)}
    func update(_ text:String,input:TaskCommentInputControl?) {guard let input,inputControl==input else {return};update(text,input.control.selection)}
    func prepare(expected:TaskCommentControl?) {guard let expected,control==expected else {return};prepare(expected.selection)}
    func back(expected:TaskCommentReturnControl?) {
        guard let expected,returnControl==expected else {return}
        if let question=expected.clear {dismissClear(question)} else if let editor=expected.editor {back(editor.selection)}
    }
    func close(expected:TaskCommentReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};close(editor.selection)}
    func submit(_ review:TaskCommentReview,expected:TaskCommentControl?) async {guard let expected,control==expected,clearConfirmation==nil,canSubmit else {return};await submit(review)}
    func acknowledge(expected:TaskCommentControl?,record:TaskCommentAttemptRecord) {guard let expected,control==expected,submission==record else {return};acknowledge(expected.selection,attemptID:record.attempt.localID)}
    func askClear(expected:TaskCommentControl?) {
        guard let expected,control==expected,session.available,!submissionBlocked else {return}
        dialogRevision += 1;clearConfirmation=TaskCommentClearConfirmation(id:dialogRevision,control:expected,contentRevision:contentRevision)
    }
    func dismissClear(_ expected:TaskCommentClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:TaskCommentClearConfirmation) {guard clearConfirmation==expected,control==expected.control,contentRevision==expected.contentRevision,!submissionBlocked else {return};discard(expected.control.selection)}
}
