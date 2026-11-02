import SwiftUI
import CRMCore

// App-local visits only: these are neither source versions nor command authority.
struct ClientEditEntryControl: Equatable {let context: ClientEditContext;let visit: Int}
struct ClientEditControl: Equatable {let selection: ClientEditSelection;let visit: Int}
struct ClientEditInputControl: Equatable {let control: ClientEditControl}
struct ClientEditConfirmation: Equatable {
    let id: Int;let entry: ClientEditEntryControl?;let control: ClientEditControl?;let contentRevision: Int
}
@MainActor final class ClientEditViewModel: ObservableObject {
    @Published private(set) var session=ClientEditSession()
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var confirmation: ClientEditConfirmation?
    private var contentRevision=0,dialogRevision=0
    var entryControl: ClientEditEntryControl? {guard let context=session.context,session.selection==nil else {return nil};return ClientEditEntryControl(context:context,visit:entryVisit)}
    var control: ClientEditControl? {session.selection.map {ClientEditControl(selection:$0,visit:viewVisit)}}
    var inputControl: ClientEditInputControl? {guard session.phase == .editing,let control else {return nil};return ClientEditInputControl(control:control)}
    private func invalidate() {entryVisit += 1;viewVisit += 1;confirmation=nil}
    func begin(_ context: ClientEditContext?) {session.begin(context);invalidate()}
    func receive(_ origin: ClientEditOrigin?,_ context: ClientEditContext) {guard session.context==context else {return};session.receive(origin,expected:context);invalidate()}
    func pause() {session.pause();invalidate()}
    // Raw trusted local APIs retained for existing callers; UI uses captured controls below.
    func open(_ context: ClientEditContext) {if session.open(expected:context) {invalidate()}}
    func update(_ field: ClientDraftField,_ value: String,_ selection: ClientEditSelection) {
        let before=session.values;session.update(field,value:value,expected:selection)
        if session.values != before {contentRevision += 1;confirmation=nil}
    }
    func prepare(_ selection: ClientEditSelection) {if session.prepare(expected:selection) {viewVisit += 1;confirmation=nil}}
    func back(_ selection: ClientEditSelection) {guard session.selection==selection else {return};session.back(expected:selection);invalidate()}
    func close(_ selection: ClientEditSelection) {guard session.selection==selection else {return};session.close(expected:selection);invalidate()}
    func cancel(_ selection: ClientEditSelection) {guard session.selection==selection else {return};session.cancel(expected:selection);contentRevision += 1;invalidate()}
    func discardStored(_ context: ClientEditContext) {guard session.context==context else {return};session.discardStored(expected:context);contentRevision += 1;invalidate()}
    func open(expected: ClientEditEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.context)}
    func update(_ field: ClientDraftField,_ value: String,input: ClientEditInputControl?) {guard let input,inputControl==input else {return};update(field,value,input.control.selection)}
    func prepare(expected: ClientEditControl?) {guard let expected,control==expected else {return};prepare(expected.selection)}
    func back(expected: ClientEditControl?) {guard let expected,control==expected else {return};back(expected.selection)}
    func close(expected: ClientEditControl?) {guard let expected,control==expected else {return};close(expected.selection)}
    func askCancel(expected: ClientEditControl?) {
        guard let expected,control==expected,session.available,session.origin != nil else {return}
        dialogRevision += 1;confirmation=ClientEditConfirmation(id:dialogRevision,entry:nil,control:expected,contentRevision:contentRevision)
    }
    func askDiscard(expected: ClientEditEntryControl?) {
        guard let expected,entryControl==expected,session.needsReset,session.hasStoredChanges else {return}
        dialogRevision += 1;confirmation=ClientEditConfirmation(id:dialogRevision,entry:expected,control:nil,contentRevision:contentRevision)
    }
    func dismiss(_ expected: ClientEditConfirmation) {if confirmation==expected {confirmation=nil}}
    func confirm(_ expected: ClientEditConfirmation) {
        guard confirmation==expected,expected.contentRevision==contentRevision else {return}
        if let captured=expected.control,control==captured {cancel(captured.selection)}
        else if let captured=expected.entry,entryControl==captured,session.needsReset,session.hasStoredChanges {discardStored(captured.context)}
    }
}
