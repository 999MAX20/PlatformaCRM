import SwiftUI
import CRMCore

struct TaskUndoCancelControl:Equatable {let source:TaskUndoCancelSource;let visit:Int;let review:TaskUndoCancelReview?;let record:TaskUndoCancelRecord?}
@MainActor final class TaskUndoCancelViewModel:ObservableObject {
    @Published private(set) var source:TaskUndoCancelSource?
    @Published private(set) var review:TaskUndoCancelReview?
    @Published private var ledger=TaskUndoCancelLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskUndoCancelPort
    init(port:any SyntheticTaskUndoCancelPort) {self.port=port}
    private var authorization:SyntheticTaskUndoCancelAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskUndoCancelRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskUndoCancelControl? {source.map {TaskUndoCancelControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskUndoCancelSource?) {let next=next?.identityValid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskUndoCancelControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskUndoCancelReview(source:expected.source,visit:visit)}
    func back(expected:TaskUndoCancelControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskUndoCancelControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskUndoCancelOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskUndoCancelControl?,record:TaskUndoCancelRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskUndoCancelView:View {
    @ObservedObject var model:TaskUndoCancelViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskUndoCancelControl)->Void
    private func key(_ phase:TaskUndoCancelPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskUndoCancelFakeConfirmed";case .rejected:"taskUndoCancelFakeRejected";case .unknown:"taskUndoCancelFakeUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskUndoCancelAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed,let result=record.result {LabeledContent(AppCopy.text("status"),value:AppCopy.text(result.status=="done" ? "taskDone":result.status=="in_progress" ? "taskInProgress":"taskOpen"));if let completed=result.completed_at {LabeledContent(AppCopy.text("taskUndoCancelCompletionAt"),value:completed)}}
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskUndoCancelAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskUndoCancelFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    Text(AppCopy.text("taskUndoCancelContract"))
                    Button(AppCopy.text("taskUndoCancelFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskUndoCancelAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskUndoCancelAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}
