import SwiftUI
import CRMCore

struct TaskSelfAssignmentControl:Equatable {let source:TaskSelfAssignmentSource;let visit:Int;let review:TaskSelfAssignmentReview?;let record:TaskSelfAssignmentRecord?}
@MainActor final class TaskSelfAssignmentViewModel:ObservableObject {
    @Published private(set) var source:TaskSelfAssignmentSource?
    @Published private(set) var review:TaskSelfAssignmentReview?
    @Published private var ledger=TaskSelfAssignmentLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskSelfAssignPort
    init(port:any SyntheticTaskSelfAssignPort) {self.port=port}
    private var authorization:SyntheticTaskSelfAssignAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskSelfAssignmentRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskSelfAssignmentControl? {source.map {TaskSelfAssignmentControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.valid==true && authorization != nil}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskSelfAssignmentSource?) {let next=next?.valid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskSelfAssignmentControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskSelfAssignmentReview(source:expected.source,visit:visit)}
    func back(expected:TaskSelfAssignmentControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskSelfAssignmentControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskSelfAssignOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskSelfAssignmentControl?,record:TaskSelfAssignmentRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskSelfAssignmentView:View {
    @ObservedObject var model:TaskSelfAssignmentViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskSelfAssignmentControl)->Void
    private func key(_ phase:TaskSelfAssignmentPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskSelfAssignFakeConfirmed";case .rejected:"taskSelfAssignFakeRejected";case .unknown:"taskSelfAssignFakeUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskSelfAssignAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskSelfAssignAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskSelfAssignFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("status"),value:AppCopy.text("taskInProgress"))
                    Button(AppCopy.text("taskSelfAssignFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskSelfAssignAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskSelfAssignAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}

struct TaskActionObservedContent<Content:View>:View {
    @ObservedObject var completion:TaskCompletionViewModel
    @ObservedObject var assignment:TaskSelfAssignmentViewModel
    let content:()->Content
    init(completion:TaskCompletionViewModel,assignment:TaskSelfAssignmentViewModel,@ViewBuilder content:@escaping ()->Content) {self.completion=completion;self.assignment=assignment;self.content=content}
    var body:some View {let _=completion.control;let _=assignment.control;return content()}
}
