import SwiftUI
import CRMCore

struct HandoffEntryControl:Equatable {let context:ReplyDraftContext;let visit:Int}
struct HandoffControl:Equatable {let selection:ReplyDraftSelection;let visit:Int}
struct HandoffInputControl:Equatable {let editor:HandoffControl}
struct HandoffClearConfirmation:Equatable {let id:Int;let editor:HandoffControl;let contentRevision:Int}
struct HandoffReturnControl:Equatable {let editor:HandoffControl?;let clear:HandoffClearConfirmation?}
@MainActor final class InboxHandoffViewModel:ObservableObject {
    @Published private(set) var session=HandoffDraftSession()
    @Published private var ledger=HandoffLedger()
    private let port:(any SyntheticHandoffPort)?
    @Published private var visit=0
    @Published private(set) var clearConfirmation:HandoffClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    init(port:(any SyntheticHandoffPort)?=nil) {self.port=port}
    private var authorization:SyntheticHandoffAuthorization? {guard let c=session.context else {return nil};return port?.grants.compactMap {$0.authorization(c)}.first}
    var entryControl:HandoffEntryControl? {guard session.available,session.selection==nil,authorization != nil,let c=session.context else {return nil};return HandoffEntryControl(context:c,visit:visit)}
    var control:HandoffControl? {session.selection.map {HandoffControl(selection:$0,visit:visit)}}
    var inputControl:HandoffInputControl? {guard !blocked,session.phase == .editing,let control else {return nil};return HandoffInputControl(editor:control)}
    var returnControl:HandoffReturnControl {HandoffReturnControl(editor:control,clear:clearConfirmation)}
    var record:HandoffRecord? {ledger.visible(authorization)}
    var blocked:Bool {session.context.map {ledger.blocked($0)} ?? false}
    func blocks(_ c:ReplyDraftContext)->Bool {ledger.blocked(c)}
    var retainedAttemptCount:Int {ledger.records.count}
    var externalCommandBlocked:@MainActor ()->Bool = {false}
    var canSubmit:Bool {!externalCommandBlocked() && session.available && session.phase == .review && clearConfirmation==nil && authorization != nil && !blocked}
    private func invalidateVisit() {visit += 1;clearConfirmation=nil}
    func retainOwner(business:Int?,epoch:Int?) {session.retainOwner(business:business,epoch:epoch);invalidateVisit()}
    func beginRead(business:Int,id:Int,epoch:Int?) {session.bind(epoch.map {ReplyDraftContext(business:business,conversation:id,epoch:$0)},available:false);invalidateVisit()}
    func verified(_ thread:InboxThread,business:Int,id:Int,epoch:Int?) {session.bind(epoch.map {ReplyDraftContext(business:business,conversation:id,epoch:$0)},available:thread.valid(for:business,id:id));invalidateVisit()}
    func pause() {session.pause();invalidateVisit()}
    func clear() {session.clear();invalidateVisit()}
    func open(expected:HandoffEntryControl?) {guard let expected,entryControl==expected else {return};if session.open(expected.context) {invalidateVisit()}}
    func update(_ raw:String,input:HandoffInputControl?) {guard !blocked,let input,inputControl==input else {return};let old=session.raw;session.update(raw,selection:input.editor.selection);if !old.utf8.elementsEqual(session.raw.utf8) {contentRevision += 1;clearConfirmation=nil}}
    func prepare(expected:HandoffControl?) {guard !blocked,let expected,control==expected else {return};if session.prepare(expected.selection) {invalidateVisit()}}
    func back(expected:HandoffReturnControl?) {guard let expected,returnControl==expected else {return};if let clear=expected.clear {dismissClear(clear);return};guard let editor=expected.editor else {return};if blocked {session.close(editor.selection)} else {session.back(editor.selection)};invalidateVisit()}
    func close(expected:HandoffReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};session.close(editor.selection);invalidateVisit()}
    func askClear(expected:HandoffControl?) {guard !blocked,let expected,control==expected else {return};dialogRevision += 1;clearConfirmation=HandoffClearConfirmation(id:dialogRevision,editor:expected,contentRevision:contentRevision)}
    func dismissClear(_ expected:HandoffClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:HandoffClearConfirmation) {guard !blocked,clearConfirmation==expected,control==expected.editor,contentRevision==expected.contentRevision else {return};session.discard(expected.editor.selection);contentRevision += 1;invalidateVisit()}
    func submit(_ review:HandoffReview,expected:HandoffControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmit,session.review==review,session.selection==review.selection,session.raw.utf8.elementsEqual(review.value.raw.utf8),let a=authorization,let port,let attempt=ledger.begin(review,authorization:a) else {return};invalidateVisit()
        let outcome:SyntheticHandoffOutcome
        do {let value=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:value} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if record?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(expected:HandoffControl?,record:HandoffRecord) {guard let expected,control==expected,self.record==record,let a=authorization,ledger.acknowledge(a) else {return};if record.phase == .confirmed {session.discard(expected.selection);contentRevision += 1} else {session.back(expected.selection)};invalidateVisit()}
}
