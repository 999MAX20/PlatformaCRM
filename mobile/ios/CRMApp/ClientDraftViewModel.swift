import SwiftUI
import CRMCore

// Local UI visits only; neither source versions nor CREATE grants.
struct ClientDraftEntryControl:Equatable {let context:ClientDraftContext;let visit:Int}
struct ClientDraftControl:Equatable {let selection:ClientDraftSelection;let visit:Int}
struct ClientDraftInputControl:Equatable {let control:ClientDraftControl}
struct ClientDraftClearConfirmation:Equatable {let id:Int;let control:ClientDraftControl;let contentRevision:Int}
struct ClientDraftReturnControl:Equatable {let editor:ClientDraftControl?;let clear:ClientDraftClearConfirmation?}
@MainActor final class ClientDraftViewModel: ObservableObject {
    @Published private(set) var session=ClientDraftSession()
    @Published private var ledger=ClientCreateAttemptLedger()
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var clearConfirmation:ClientDraftClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    var entryControl:ClientDraftEntryControl? {guard session.selection==nil,let context=session.context else {return nil};return ClientDraftEntryControl(context:context,visit:entryVisit)}
    var control:ClientDraftControl? {session.selection.map {ClientDraftControl(selection:$0,visit:viewVisit)}}
    var inputControl:ClientDraftInputControl? {guard !submissionBlocked,session.phase == .editing,let control else {return nil};return ClientDraftInputControl(control:control)}
    var returnControl:ClientDraftReturnControl {ClientDraftReturnControl(editor:control,clear:clearConfirmation)}
    private func invalidateVisit() {entryVisit += 1;viewVisit += 1;clearConfirmation=nil;duplicates?.clear()}
    private let port: (any SyntheticClientCreatePort)?
    let duplicates: ClientDuplicatePreviewViewModel?
    init(port: (any SyntheticClientCreatePort)?=nil,duplicates: (any SyntheticClientDuplicatePreviewSource)?=nil) {self.port=port;self.duplicates=duplicates.map {ClientDuplicatePreviewViewModel(source:$0)}}
    private var authorization: SyntheticClientCreateAuthorization? {
        guard let context=session.context else {return nil}
        return port?.grants.compactMap {$0.authorization(for:context)}.first
    }
    var submission: ClientCreateAttemptRecord? {ledger.visible(authorization)}
    var submissionBlocked: Bool {session.context.map {ledger.blocked($0)} ?? false}
    var canSubmit: Bool {authorization != nil && !submissionBlocked && session.phase == .review}
    var retainedAttemptCount: Int {ledger.records.count}
    func bind(_ context: ClientDraftContext?) {let before=session.context;session.bind(context);if session.context != before {invalidateVisit()}}
    func open(_ context: ClientDraftContext) {if session.open(expected:context) {invalidateVisit()}}
    func update(_ field: ClientDraftField,_ value: String,_ selection: ClientDraftSelection) {guard !submissionBlocked else {return};let before=session.values;session.update(field,value:value,expected:selection);if session.values != before {contentRevision += 1;clearConfirmation=nil}}
    func prepare(_ selection: ClientDraftSelection) {guard !submissionBlocked else {return};if session.prepare(expected:selection) {invalidateVisit()}}
    func back(_ selection: ClientDraftSelection) {guard session.selection==selection else {return};if submissionBlocked {session.close(expected:selection)} else {session.back(expected:selection)};invalidateVisit()}
    func close(_ selection: ClientDraftSelection) {guard session.selection==selection else {return};session.close(expected:selection);invalidateVisit()}
    func discard(_ selection: ClientDraftSelection) {guard !submissionBlocked,session.selection==selection else {return};session.discard(expected:selection);contentRevision += 1;invalidateVisit()}
    func submit(_ expected: ClientDraftReview) async {
        guard session.selection==expected.selection,session.context==expected.selection.context,session.phase == .review,session.review==expected,session.values==expected.values,let authorization,let port,let attempt=ledger.begin(review:expected,authorization:authorization) else {return}
        invalidateVisit()
        let outcome: SyntheticClientCreateOutcome
        do {let result=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:result} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome)
        if submission?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(_ selection: ClientDraftSelection,attemptID: Int) {
        guard session.selection==selection,let authorization,let record=submission,record.attempt.localID==attemptID,ledger.acknowledge(authorization) else {return}
        if record.phase == .confirmed {session.discard(expected:selection);contentRevision += 1} else if session.phase == .review {session.back(expected:selection)}
        invalidateVisit()
    }
    func loadDuplicates(expected: ClientDraftControl?,visit: ClientDuplicatePreviewVisit) async {
        guard let expected,control == expected,clearConfirmation == nil,!submissionBlocked,
              session.phase == .review,let review=session.review,review.selection == expected.selection,let duplicates else {return}
        let input=ClientDuplicatePreviewInput(context:expected.selection.context,phone:review.values.phone,email:review.values.email)
        await duplicates.load(input,expected:visit)
    }
    // Raw trusted APIs above preserve the existing Core/session/ledger behavior.
    func open(expected:ClientDraftEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.context)}
    func update(_ field:ClientDraftField,_ value:String,input:ClientDraftInputControl?) {guard let input,inputControl==input else {return};update(field,value,input.control.selection)}
    func prepare(expected:ClientDraftControl?) {guard let expected,control==expected else {return};prepare(expected.selection)}
    func back(expected:ClientDraftReturnControl?) {guard let expected,returnControl==expected else {return};if let question=expected.clear {dismissClear(question)} else if let editor=expected.editor {back(editor.selection)}}
    func close(expected:ClientDraftReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};close(editor.selection)}
    func submit(_ review:ClientDraftReview,expected:ClientDraftControl?) async {guard let expected,control==expected,clearConfirmation==nil,canSubmit else {return};await submit(review)}
    func acknowledge(expected:ClientDraftControl?,record:ClientCreateAttemptRecord) {guard let expected,control==expected,submission==record else {return};acknowledge(expected.selection,attemptID:record.attempt.localID)}
    func askClear(expected:ClientDraftControl?) {guard let expected,control==expected,!submissionBlocked else {return};duplicates?.clear();dialogRevision += 1;clearConfirmation=ClientDraftClearConfirmation(id:dialogRevision,control:expected,contentRevision:contentRevision)}
    func dismissClear(_ expected:ClientDraftClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:ClientDraftClearConfirmation) {guard clearConfirmation==expected,control==expected.control,contentRevision==expected.contentRevision,!submissionBlocked else {return};discard(expected.control.selection)}
}
