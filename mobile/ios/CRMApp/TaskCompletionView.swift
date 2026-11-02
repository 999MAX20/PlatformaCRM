import SwiftUI
import CRMCore

struct TaskCompletionControl:Equatable {let source:TaskCompletionSource;let visit:Int;let review:TaskCompletionReview?;let record:TaskCompletionRecord?}
@MainActor final class TaskCompletionViewModel:ObservableObject {
    @Published private(set) var source:TaskCompletionSource?
    @Published private(set) var review:TaskCompletionReview?
    @Published private var ledger=TaskCompletionLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskCompletePort
    init(port:any SyntheticTaskCompletePort) {self.port=port}
    private var authorization:SyntheticTaskCompleteAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskCompletionRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskCompletionControl? {source.map {TaskCompletionControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.valid==true && authorization != nil}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskCompletionSource?) {let next=next?.valid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskCompletionControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskCompletionReview(source:expected.source,visit:visit)}
    func back(expected:TaskCompletionControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskCompletionControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskCompleteOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskCompletionControl?,record:TaskCompletionRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskCompletionView:View {
    @ObservedObject var model:TaskCompletionViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskCompletionControl)->Void
    private func key(_ phase:TaskCompletionPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskCompleteFakeConfirmed";case .rejected:"taskCompleteFakeRejected";case .unknown:"taskCompleteFakeUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskCompleteAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskCompleteAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskCompleteFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("status"),value:AppCopy.text("taskDone"))
                    Button(AppCopy.text("taskCompleteFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskCompleteAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskCompleteAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}
