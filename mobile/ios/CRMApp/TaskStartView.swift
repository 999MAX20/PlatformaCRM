import SwiftUI
import CRMCore

struct TaskStartControl:Equatable {let source:TaskStartSource;let visit:Int;let review:TaskStartReview?;let record:TaskStartRecord?}
@MainActor final class TaskStartViewModel:ObservableObject {
    @Published private(set) var source:TaskStartSource?
    @Published private(set) var review:TaskStartReview?
    @Published private var ledger=TaskStartLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskStartPort
    init(port:any SyntheticTaskStartPort) {self.port=port}
    private var authorization:SyntheticTaskStartAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskStartRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskStartControl? {source.map {TaskStartControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskStartSource?) {let next=next?.identityValid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskStartControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskStartReview(source:expected.source,visit:visit)}
    func back(expected:TaskStartControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskStartControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskStartOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskStartControl?,record:TaskStartRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskStartView:View {
    @ObservedObject var model:TaskStartViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskStartControl)->Void
    private func key(_ phase:TaskStartPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskStartFakeConfirmed";case .rejected:"taskStartFakeRejected";case .unknown:"taskStartFakeUnknown"}}
    private func person(_ value:MobileUserRead)->String {switch value {case .notSet:AppCopy.text("taskNoAssignee");case .unknown:AppCopy.text("notAvailable");case .person(let user):user.displayName ?? AppCopy.text("notAvailable")}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskStartAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskStartAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskStartFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("status"),value:AppCopy.text("taskInProgress"))
                    LabeledContent(AppCopy.text("taskAssignee"),value:person(review.source.assignee))
                    Button(AppCopy.text("taskStartFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskStartAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskStartAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}
