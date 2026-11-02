import SwiftUI
import CRMCore

// UI visit counters are independent of catalogue/source request versions.
struct QuickReplyEntryControl:Equatable {let context:QuickReplyContext;let visit:Int}
struct QuickReplyControl:Equatable {let selection:QuickReplySelection;let visit:Int}
struct QuickReplyInputControl:Equatable {let selection:QuickReplySelection;let visit:Int}
@MainActor final class QuickReplyViewModel: ObservableObject {
    @Published private(set) var session=QuickReplySession()
    @Published private var entryVisit=0
    @Published private var windowVisit=0
    @Published private var inputVisit=0
    private var readRevision=0
    private let repository: any QuickReplyRepository
    init(repository: any QuickReplyRepository) {self.repository=repository}
    var entryControl:QuickReplyEntryControl? {guard let context=session.context,session.selection==nil else {return nil};return QuickReplyEntryControl(context:context,visit:entryVisit)}
    var control:QuickReplyControl? {session.selection.map {QuickReplyControl(selection:$0,visit:windowVisit)}}
    var inputControl:QuickReplyInputControl? {session.selection.map {QuickReplyInputControl(selection:$0,visit:inputVisit)}}
    private func invalidateVisit() {entryVisit += 1;windowVisit += 1;inputVisit += 1;readRevision += 1}
    func bind(_ context: QuickReplyContext?) {
        let before=session.context,selection=session.selection;session.bind(context)
        if before != session.context || selection != session.selection {invalidateVisit()}
    }
    // Trusted local APIs retain the original Core behavior. UI captures controls.
    func open(_ context: QuickReplyContext) async {if let request=session.open(expected:context) {invalidateVisit();await read(request)}}
    func retry(_ selection: QuickReplySelection) async {if let request=session.retry(expected:selection) {await read(request)}}
    private func read(_ request: QuickReplyRequest) async {
        readRevision += 1;let ticket=readRevision;windowVisit += 1
        let context=request.selection.context
        do {session.accept(try await repository.quickReplies(business:context.draft.context.business,channel:context.channel),request:request)}
        catch {if error is CancellationError {session.cancel(request:request)} else {session.fail(error as? ReadFailure ?? .unavailable,request:request)}}
        if readRevision==ticket && session.selection==request.selection {windowVisit += 1}
    }
    func search(_ query: String,_ selection: QuickReplySelection) {let before=session.query;session.search(query,expected:selection);if !session.query.utf8.elementsEqual(before.utf8) {windowVisit += 1}}
    func close(_ selection: QuickReplySelection) {guard session.selection==selection else {return};session.close(expected:selection);invalidateVisit()}
    func open(expected:QuickReplyEntryControl?) async {guard let expected,entryControl==expected else {return};await open(expected.context)}
    func retry(expected:QuickReplyControl?) async {guard let expected,control==expected,!session.loading else {return};await retry(expected.selection)}
    func search(_ query:String,input:QuickReplyInputControl?) {guard let input,inputControl==input else {return};search(query,input.selection)}
    func close(expected:QuickReplyControl?) {guard let expected,control==expected else {return};close(expected.selection)}
    func resolve(_ choice:QuickReplyChoice,expected:QuickReplyControl?) -> String? {guard let expected,control==expected else {return nil};return session.resolve(choice)}
}
