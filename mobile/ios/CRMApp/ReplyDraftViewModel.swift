import SwiftUI
import CRMCore

struct ReplyDraftEntryControl:Equatable {let context:ReplyDraftContext;let visit:Int}
struct ReplyDraftControl:Equatable {let selection:ReplyDraftSelection;let visit:Int}
struct ReplyDraftInputControl:Equatable {let control:ReplyDraftControl}
struct ReplyDraftClearConfirmation:Equatable {let id:Int;let control:ReplyDraftControl;let contentRevision:Int}
struct ReplyDraftReturnControl:Equatable {let editor:ReplyDraftControl?;let picker:QuickReplyControl?;let clear:ReplyDraftClearConfirmation?}
// Owned by Inbox. Template reads are fixture-only; preparing text has no send authority.
@MainActor final class ReplyDraftViewModel: ObservableObject {
    @Published private(set) var session = ReplyDraftSession()
    @Published private var ledger=InboxReplyLedger()
    private let port:(any SyntheticInboxReplyPort)?
    let quickReplies: QuickReplyViewModel?
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var clearConfirmation:ReplyDraftClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    var entryControl:ReplyDraftEntryControl? {guard session.available,session.selection==nil,let context=session.context else {return nil};return ReplyDraftEntryControl(context:context,visit:entryVisit)}
    var control:ReplyDraftControl? {session.selection.map {ReplyDraftControl(selection:$0,visit:viewVisit)}}
    var inputControl:ReplyDraftInputControl? {guard !submissionBlocked,session.phase == .editing,let control else {return nil};return ReplyDraftInputControl(control:control)}
    var returnControl:ReplyDraftReturnControl {ReplyDraftReturnControl(editor:control,picker:quickReplies?.control,clear:clearConfirmation)}
    private func invalidateVisit() {entryVisit += 1;viewVisit += 1;clearConfirmation=nil}
    private var verifiedChannel: String?
    init(quickReplies: (any QuickReplyRepository)? = nil,submission:(any SyntheticInboxReplyPort)?=nil) {self.port=submission;self.quickReplies=quickReplies.map {QuickReplyViewModel(repository:$0)}}
    private var authorization:SyntheticInboxReplyAuthorization? {guard let c=session.context else {return nil};return port?.grants.compactMap {$0.authorization(for:c)}.first}
    var submission:InboxReplyRecord? {ledger.visible(authorization)}
    var submissionBlocked:Bool {session.context.map {ledger.blocked($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    var hasTestPort:Bool {port != nil}
    var externalCommandBlocked:@MainActor ()->Bool = {false}
    var canSubmit:Bool {!externalCommandBlocked() && session.available && session.phase == .review && clearConfirmation==nil && quickReplies?.session.selection==nil && ledger.canBegin(authorization)}
    func submit(_ review:ReplyDraftReview,expected:ReplyDraftControl?) async {
        guard !Task.isCancelled,let expected,control==expected,canSubmit,session.selection==review.selection,session.review==review,review.raw.utf8.elementsEqual(session.text.utf8),let a=authorization,let port,let attempt=ledger.begin(review,authorization:a) else {return}
        syncPicker();invalidateVisit()
        let outcome:SyntheticInboxReplyOutcome
        do {let value=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:value} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(expected:ReplyDraftControl?,record:InboxReplyRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {session.discard(expected:expected.selection);contentRevision += 1}
        else {session.back(expected:expected.selection)}
        syncPicker();invalidateVisit()
    }
    private func syncPicker() {
        let context: QuickReplyContext? = if session.available,session.phase == .editing,let selection=session.selection,let channel=verifiedChannel {QuickReplyContext(draft:selection,channel:channel)} else {nil}
        quickReplies?.bind(context)
    }
    func retainOwner(business: Int?,epoch: Int?) {verifiedChannel=nil;session.retainOwner(business:business,epoch:epoch);syncPicker();invalidateVisit()}
    func beginRead(business: Int,id: Int,epoch: Int?) {
        verifiedChannel=nil;session.bind(epoch.map { ReplyDraftContext(business:business,conversation:id,epoch:$0) },available:false);syncPicker();invalidateVisit()
    }
    func verified(_ thread: InboxThread,business: Int,id: Int,epoch: Int?) {
        let available=thread.valid(for:business,id:id) && thread.sourceStatus == "open"
        verifiedChannel=available ? thread.conversation.channel : nil
        session.bind(epoch.map { ReplyDraftContext(business:business,conversation:id,epoch:$0) },available:available);syncPicker();invalidateVisit()
    }
    func pause() {verifiedChannel=nil;session.pause();syncPicker();invalidateVisit()}
    func clear() {verifiedChannel=nil;session.clear();syncPicker();invalidateVisit()}
    func open(expected:ReplyDraftEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.context)}
    func open(_ context: ReplyDraftContext) {if session.open(expected:context) {syncPicker();invalidateVisit()}}
    func update(_ text: String,_ selection: ReplyDraftSelection) {guard !submissionBlocked else {return};let before=session.text;session.update(text,expected:selection);syncPicker();if !session.text.utf8.elementsEqual(before.utf8) {contentRevision += 1;clearConfirmation=nil}}
    func prepare(_ selection: ReplyDraftSelection) {guard !submissionBlocked else {return};if session.prepare(expected:selection) {syncPicker();invalidateVisit()}}
    func back(_ selection: ReplyDraftSelection) {
        if submissionBlocked {guard session.selection==selection else {return};session.close(expected:selection);syncPicker();invalidateVisit();return}
        if let picker=quickReplies?.session.selection,picker.context.draft==selection {quickReplies?.close(picker);return}
        guard session.selection==selection else {return};session.back(expected:selection);syncPicker();invalidateVisit()
    }
    func close(_ selection: ReplyDraftSelection) {guard session.selection==selection else {return};session.close(expected:selection);syncPicker();invalidateVisit()}
    func discard(_ selection: ReplyDraftSelection) {guard !submissionBlocked,session.selection==selection else {return};session.discard(expected:selection);syncPicker();contentRevision += 1;invalidateVisit()}
    func openQuickReplies(_ selection: ReplyDraftSelection) async {
        guard !submissionBlocked,session.selection==selection,session.phase == .editing,let context=quickReplies?.session.context,context.draft==selection else {return}
        await quickReplies?.open(context)
    }
    @discardableResult func insert(_ choice: QuickReplyChoice,expected: ReplyDraftSelection) -> Bool {
        guard !submissionBlocked,session.selection==expected,session.available,session.phase == .editing,choice.request.selection.context.draft==expected,choice.request.selection.context.channel==verifiedChannel,
              let body=quickReplies?.session.resolve(choice),session.insertTemplate(body,expected:expected) else {return false}
        syncPicker();contentRevision += 1;invalidateVisit();return true
    }
    // Captured UI flow. Picker controls supplement, never replace, Core choice checks.
    func update(_ text:String,input:ReplyDraftInputControl?) {guard let input,inputControl==input,quickReplies?.session.selection==nil else {return};update(text,input.control.selection)}
    func prepare(expected:ReplyDraftControl?) {guard let expected,control==expected,quickReplies?.session.selection==nil else {return};prepare(expected.selection)}
    func back(expected:ReplyDraftReturnControl?) {
        guard let expected,returnControl==expected else {return}
        if let question=expected.clear {dismissClear(question)}
        else if let picker=expected.picker {quickReplies?.close(expected:picker)}
        else if let editor=expected.editor {back(editor.selection)}
    }
    func close(expected:ReplyDraftReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};close(editor.selection)}
    func openQuickReplies(expected:ReplyDraftControl?,entry:QuickReplyEntryControl?) async {
        guard !submissionBlocked,let expected,control==expected,session.available,session.phase == .editing,clearConfirmation==nil,let entry,quickReplies?.entryControl==entry,entry.context.draft==expected.selection else {return}
        await quickReplies?.open(expected:entry)
    }
    @discardableResult func insert(_ choice:QuickReplyChoice,expected:ReplyDraftControl?,picker:QuickReplyControl?) -> Bool {
        guard let expected,control==expected,clearConfirmation==nil,quickReplies?.resolve(choice,expected:picker) != nil else {return false}
        return insert(choice,expected:expected.selection)
    }
    func askClear(expected:ReplyDraftControl?) {
        guard !submissionBlocked,let expected,control==expected,session.available,quickReplies?.session.selection==nil else {return}
        dialogRevision += 1;clearConfirmation=ReplyDraftClearConfirmation(id:dialogRevision,control:expected,contentRevision:contentRevision)
    }
    func dismissClear(_ expected:ReplyDraftClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:ReplyDraftClearConfirmation) {guard !submissionBlocked,clearConfirmation==expected,control==expected.control,contentRevision==expected.contentRevision else {return};discard(expected.control.selection)}
}
