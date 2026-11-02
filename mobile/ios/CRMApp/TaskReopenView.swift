import SwiftUI
import CRMCore

struct TaskReopenControl:Equatable {let source:TaskReopenSource;let visit:Int;let review:TaskReopenReview?;let record:TaskReopenRecord?}
@MainActor final class TaskReopenViewModel:ObservableObject {
    @Published private(set) var source:TaskReopenSource?
    @Published private(set) var review:TaskReopenReview?
    @Published private var ledger=TaskReopenLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskReopenPort
    init(port:any SyntheticTaskReopenPort) {self.port=port}
    private var authorization:SyntheticTaskReopenAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskReopenRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskReopenControl? {source.map {TaskReopenControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskReopenSource?) {let next=next?.identityValid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskReopenControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskReopenReview(source:expected.source,visit:visit)}
    func back(expected:TaskReopenControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskReopenControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskReopenOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskReopenControl?,record:TaskReopenRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskReopenView:View {
    @ObservedObject var model:TaskReopenViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskReopenControl)->Void
    private func key(_ phase:TaskReopenPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskReopenFakeConfirmed";case .rejected:"taskReopenFakeRejected";case .unknown:"taskReopenFakeUnknown"}}
    private func person(_ value:MobileUserRead)->String {switch value {case .notSet:AppCopy.text("taskNoAssignee");case .unknown:AppCopy.text("notAvailable");case .person(let user):user.displayName ?? AppCopy.text("notAvailable")}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskReopenAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskReopenAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskReopenFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("status"),value:AppCopy.text("taskOpen"))
                    LabeledContent(AppCopy.text("taskAssignee"),value:person(review.source.assignee))
                    Text(AppCopy.text("taskReopenClearsMetadata"))
                    Button(AppCopy.text("taskReopenFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskReopenAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskReopenAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}
