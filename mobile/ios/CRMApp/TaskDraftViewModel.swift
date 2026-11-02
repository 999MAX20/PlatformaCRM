import SwiftUI
import CRMCore

// Local UI visits only; neither source versions nor CREATE grants.
struct TaskDraftEntryControl:Equatable {let context:TaskDraftContext;let visit:Int}
struct TaskDraftControl:Equatable {let selection:TaskDraftSelection;let visit:Int}
struct TaskDraftInputControl:Equatable {let control:TaskDraftControl}
struct TaskDraftClearConfirmation:Equatable {let id:Int;let control:TaskDraftControl;let contentRevision:Int}
struct TaskDraftClientPickerOwner:Equatable {let control:TaskDraftControl;let contentRevision:Int}
struct TaskDraftAppointmentPickerOwner:Equatable {let control:TaskDraftControl;let contentRevision:Int}
struct TaskDraftParentPickerOwner:Equatable {let control:TaskDraftControl;let contentRevision:Int}
struct TaskDraftReturnControl:Equatable {let editor:TaskDraftControl?;let clear:TaskDraftClearConfirmation?}
@MainActor final class TaskDraftViewModel: ObservableObject {
    @Published private(set) var session=TaskDraftSession()
    @Published private var ledger=TaskCreateAttemptLedger()
    @Published private var entryVisit=0
    @Published private var viewVisit=0
    @Published private(set) var clearConfirmation:TaskDraftClearConfirmation?
    private var contentRevision=0,dialogRevision=0
    let clients:ClientSearchViewModel?
    let appointments:TaskAppointmentPickerViewModel?
    let parents:TaskParentPickerViewModel?
    @Published private(set) var parentPickerOwner:TaskDraftParentPickerOwner?
    @Published private(set) var appointmentPickerOwner:TaskDraftAppointmentPickerOwner?
    @Published private(set) var clientPickerOwner:TaskDraftClientPickerOwner?
    var entryControl:TaskDraftEntryControl? {guard session.selection==nil,let context=session.context else {return nil};return TaskDraftEntryControl(context:context,visit:entryVisit)}
    var control:TaskDraftControl? {session.selection.map {TaskDraftControl(selection:$0,visit:viewVisit)}}
    var inputControl:TaskDraftInputControl? {guard !submissionBlocked,clientPickerOwner==nil,appointmentPickerOwner==nil,parentPickerOwner==nil,session.phase == .editing,let control else {return nil};return TaskDraftInputControl(control:control)}
    var returnControl:TaskDraftReturnControl {TaskDraftReturnControl(editor:control,clear:clearConfirmation)}
    private func invalidateVisit() {entryVisit += 1;viewVisit += 1;clearConfirmation=nil}
    private let port: (any SyntheticTaskCreatePort)?
    init(port: (any SyntheticTaskCreatePort)?=nil,clients:(any ClientSearchRepository)?=nil,appointments:(any AgendaRepository)?=nil,parents:(any TaskReadRepository)?=nil) {self.port=port;self.clients=clients.map {ClientSearchViewModel(repository:$0)};self.appointments=appointments.map {TaskAppointmentPickerViewModel(repository:$0)};self.parents=parents.map {TaskParentPickerViewModel(repository:$0)}}
    private var authorization: SyntheticTaskCreateAuthorization? {
        guard let context=session.context else {return nil}
        return port?.grants.compactMap {$0.authorization(for:context)}.first
    }
    var submission: TaskCreateAttemptRecord? {ledger.visible(authorization)}
    var submissionBlocked: Bool {session.context.map {ledger.blocked($0)} ?? false}
    var canSubmit: Bool {authorization != nil && !submissionBlocked && session.phase == .review}
    var retainedAttemptCount: Int {ledger.records.count}
    func bind(_ context: TaskDraftContext?) {let before=session.context;session.bind(context);if session.context != before {resetClientPicker();resetAppointmentPicker();resetParentPicker();invalidateVisit()}}
    func open(_ context: TaskDraftContext) {resetClientPicker();resetAppointmentPicker();resetParentPicker();if session.open(expected:context) {invalidateVisit()}}
    func update(_ field: TaskDraftField,_ value: String,_ selection: TaskDraftSelection) {guard !submissionBlocked,clientPickerOwner==nil,appointmentPickerOwner==nil,parentPickerOwner==nil else {return};let before=session.values;session.update(field,value:value,expected:selection);if session.values != before {contentRevision += 1;clearConfirmation=nil}}
    func chooseDue(_ mode:TaskDraftDueMode,input:TaskDraftInputControl?) {
        guard let input,inputControl==input,!submissionBlocked else {return};let before=session.values
        session.chooseDue(mode,expected:input.control.selection)
        if session.values != before {contentRevision += 1;invalidateVisit()}
    }
    func chooseReminder(_ mode:TaskDraftDueMode,input:TaskDraftInputControl?) {
        guard let input,inputControl==input,!submissionBlocked else {return};let before=session.values
        session.chooseReminder(mode,expected:input.control.selection)
        if session.values != before {contentRevision += 1;invalidateVisit()}
    }
    func prepare(_ selection: TaskDraftSelection) {guard !submissionBlocked,clientPickerOwner==nil,appointmentPickerOwner==nil,parentPickerOwner==nil else {return};if session.prepare(expected:selection) {invalidateVisit()}}
    func back(_ selection: TaskDraftSelection) {guard session.selection==selection else {return};if let owner=clientPickerOwner {closeClientPicker(owner);return};if let owner=appointmentPickerOwner {closeAppointmentPicker(owner);return};if let owner=parentPickerOwner {closeParentPicker(owner);return};if submissionBlocked {session.close(expected:selection)} else {session.back(expected:selection)};invalidateVisit()}
    func close(_ selection: TaskDraftSelection) {guard session.selection==selection else {return};resetClientPicker();resetAppointmentPicker();resetParentPicker();session.close(expected:selection);invalidateVisit()}
    func discard(_ selection: TaskDraftSelection) {guard !submissionBlocked,session.selection==selection else {return};resetClientPicker();resetAppointmentPicker();resetParentPicker();session.discard(expected:selection);contentRevision += 1;invalidateVisit()}
    func submit(_ expected: TaskDraftReview) async {
        guard session.selection==expected.selection,session.context==expected.selection.context,session.phase == .review,session.review==expected,session.values==expected.values,let authorization,let port,let attempt=ledger.begin(review:expected,authorization:authorization) else {return}
        invalidateVisit()
        let outcome: SyntheticTaskCreateOutcome
        do {let result=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:result} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome)
        if submission?.attempt==attempt {invalidateVisit()}
    }
    func acknowledge(_ selection: TaskDraftSelection,attemptID: Int) {
        guard session.selection==selection,let authorization,let record=submission,record.attempt.localID==attemptID,ledger.acknowledge(authorization) else {return}
        if record.phase == .confirmed {session.discard(expected:selection);contentRevision += 1} else if session.phase == .review {session.back(expected:selection)}
        invalidateVisit()
    }
    var clientPickerAvailable:Bool {clients != nil}
    func matchesClientPicker(_ owner:TaskDraftClientPickerOwner?)->Bool {
        guard let owner else {return false};return clientPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && session.phase == .editing && !submissionBlocked
    }
    private func resetClientPicker() {clients?.bind(nil);clientPickerOwner=nil}
    func openClientPicker(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,clearConfirmation==nil,let clients else {return}
        invalidateVisit();guard let control else {return};let owner=TaskDraftClientPickerOwner(control:control,contentRevision:contentRevision)
        let context=ClientSearchContext(business:control.selection.context.business,epoch:control.selection.context.epoch)
        clients.bind(nil);clients.bind(context);clients.open(context);clientPickerOwner=owner
    }
    func closeClientPicker(_ owner:TaskDraftClientPickerOwner?) {guard matchesClientPicker(owner) else {return};resetClientPicker();invalidateVisit()}
    func confirmClient(_ owner:TaskDraftClientPickerOwner?,search:ClientSearchControl?) {
        guard matchesClientPicker(owner),let owner,let clients,let search,clients.matches(search),let selected=clients.session.profileSelection,selected==search.profile,
              clients.profile.readSelection==search.read,!clients.profile.loading,clients.profile.failure==nil,let profile=clients.profile.detail,
              let choice=TaskDraftClientChoice(profile:profile,business:owner.control.selection.context.business,id:selected.id) else {return}
        let before=session.values;session.chooseClient(choice,expected:owner.control.selection)
        if session.values != before {contentRevision += 1};resetClientPicker();invalidateVisit()
    }
    func clearClient(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,session.values.client != nil else {return}
        session.chooseClient(nil,expected:input.control.selection);contentRevision += 1;invalidateVisit()
    }
    var appointmentPickerAvailable:Bool {appointments != nil}
    func matchesAppointmentPicker(_ owner:TaskDraftAppointmentPickerOwner?)->Bool {
        guard let owner else {return false};return appointmentPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && session.phase == .editing && !submissionBlocked
    }
    private func resetAppointmentPicker() {appointments?.begin(nil);appointmentPickerOwner=nil}
    func openAppointmentPicker(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,clearConfirmation==nil,let appointments else {return}
        invalidateVisit();guard let control else {return};appointmentPickerOwner=TaskDraftAppointmentPickerOwner(control:control,contentRevision:contentRevision)
        appointments.begin(control.selection.context)
    }
    func closeAppointmentPicker(_ owner:TaskDraftAppointmentPickerOwner?) {guard matchesAppointmentPicker(owner) else {return};resetAppointmentPicker();invalidateVisit()}
    func confirmAppointment(_ owner:TaskDraftAppointmentPickerOwner?,read:TaskAppointmentPickerControl?) {
        guard matchesAppointmentPicker(owner),let owner,let appointments,let choice=appointments.choice(expected:read),choice.valid(for:owner.control.selection.context.business) else {return}
        let before=session.values;session.chooseAppointment(choice,expected:owner.control.selection)
        if session.values != before {contentRevision += 1};resetAppointmentPicker();invalidateVisit()
    }
    func clearAppointment(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,session.values.appointment != nil else {return}
        session.chooseAppointment(nil,expected:input.control.selection);contentRevision += 1;invalidateVisit()
    }
    var parentPickerAvailable:Bool {parents != nil}
    func matchesParentPicker(_ owner:TaskDraftParentPickerOwner?)->Bool {
        guard let owner else {return false};return parentPickerOwner==owner && control==owner.control && contentRevision==owner.contentRevision && session.phase == .editing && !submissionBlocked
    }
    private func resetParentPicker() {parents?.begin(nil);parentPickerOwner=nil}
    func openParentPicker(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,clearConfirmation==nil,let parents else {return}
        invalidateVisit();guard let control else {return};parentPickerOwner=TaskDraftParentPickerOwner(control:control,contentRevision:contentRevision)
        parents.begin(control.selection.context)
    }
    func closeParentPicker(_ owner:TaskDraftParentPickerOwner?) {guard matchesParentPicker(owner) else {return};resetParentPicker();invalidateVisit()}
    func confirmParent(_ owner:TaskDraftParentPickerOwner?,read:TaskParentPickerControl?) {
        guard matchesParentPicker(owner),let owner,let parents,let choice=parents.choice(expected:read),choice.valid(for:owner.control.selection.context.business) else {return}
        let before=session.values;session.chooseParent(choice,expected:owner.control.selection)
        if session.values != before {contentRevision += 1};resetParentPicker();invalidateVisit()
    }
    func clearParent(input:TaskDraftInputControl?) {
        guard let input,inputControl==input,session.values.parentTask != nil else {return}
        session.chooseParent(nil,expected:input.control.selection);contentRevision += 1;invalidateVisit()
    }
    // Raw trusted APIs above preserve the existing Core/session/ledger behavior.
    func open(expected:TaskDraftEntryControl?) {guard let expected,entryControl==expected else {return};open(expected.context)}
    func update(_ field:TaskDraftField,_ value:String,input:TaskDraftInputControl?) {guard let input,inputControl==input else {return};update(field,value,input.control.selection)}
    func prepare(expected:TaskDraftControl?) {guard let expected,control==expected else {return};prepare(expected.selection)}
    func back(expected:TaskDraftReturnControl?) {guard let expected,returnControl==expected else {return};if let question=expected.clear {dismissClear(question)} else if let editor=expected.editor {back(editor.selection)}}
    func close(expected:TaskDraftReturnControl?) {guard let expected,returnControl==expected,let editor=expected.editor else {return};close(editor.selection)}
    func submit(_ review:TaskDraftReview,expected:TaskDraftControl?) async {guard let expected,control==expected,clearConfirmation==nil,canSubmit else {return};await submit(review)}
    func acknowledge(expected:TaskDraftControl?,record:TaskCreateAttemptRecord) {guard let expected,control==expected,submission==record else {return};acknowledge(expected.selection,attemptID:record.attempt.localID)}
    func askClear(expected:TaskDraftControl?) {guard let expected,control==expected,!submissionBlocked,clientPickerOwner==nil,appointmentPickerOwner==nil,parentPickerOwner==nil else {return};dialogRevision += 1;clearConfirmation=TaskDraftClearConfirmation(id:dialogRevision,control:expected,contentRevision:contentRevision)}
    func dismissClear(_ expected:TaskDraftClearConfirmation) {if clearConfirmation==expected {clearConfirmation=nil}}
    func confirmClear(_ expected:TaskDraftClearConfirmation) {guard clearConfirmation==expected,control==expected.control,contentRevision==expected.contentRevision,!submissionBlocked else {return};discard(expected.control.selection)}
}
