import SwiftUI
import CRMCore

struct TaskWatcherControl:Equatable {let source:TaskWatcherSource;let visit:Int;let review:TaskWatcherReview?;let record:TaskWatcherRecord?}
@MainActor final class TaskWatcherViewModel:ObservableObject {
    @Published private(set) var source:TaskWatcherSource?
    @Published private(set) var review:TaskWatcherReview?
    @Published private var ledger=TaskWatcherLedger()
    @Published private var visit=0
    private var consumedReads:[TaskCommentRead]=[]
    private let port:any SyntheticTaskWatcherPort
    init(port:any SyntheticTaskWatcherPort) {self.port=port}
    private var authorization:SyntheticTaskWatcherAuthorization? {guard let source else {return nil};return port.grants.compactMap {$0.authorization(for:source.read.context)}.first}
    var submission:TaskWatcherRecord? {ledger.visible(authorization)}
    var blocked:Bool {source.map {ledger.blocked($0.read.context)} ?? false}
    var consumed:Bool {source.map {consumedReads.contains($0.read)} ?? false}
    var control:TaskWatcherControl? {source.map {TaskWatcherControl(source:$0,visit:visit,review:review,record:submission)}}
    var canPresent:Bool {source?.identityValid==true && authorization != nil && (source?.valid==true || blocked || consumed)}
    func interrupt() {review=nil;visit += 1}
    var canPrepare:Bool {source?.valid==true && authorization != nil && !blocked && !consumed && review==nil}
    func blocks(context:TaskCommentContext?)->Bool {guard let context,context.valid else {return false};return ledger.blocked(context)}
    func hasConsumed(read:TaskCommentRead?)->Bool {read.map {consumedReads.contains($0)} ?? false}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:TaskWatcherSource?) {let next=next?.identityValid==true ? next:nil;guard source != next else {return};source=next;review=nil;visit += 1}
    func prepare(expected:TaskWatcherControl?) {guard let expected,control==expected,canPrepare else {return};visit += 1;review=TaskWatcherReview(source:expected.source,visit:visit)}
    func back(expected:TaskWatcherControl?) {guard let expected,control==expected,!blocked,review != nil else {return};review=nil;visit += 1}
    func submit(expected:TaskWatcherControl?) async {
        guard !Task.isCancelled,let expected,control==expected,let review,review.source==source,let a=authorization,let attempt=ledger.begin(review,authorization:a) else {return}
        visit += 1
        let outcome:SyntheticTaskWatcherOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome);if submission?.attempt==attempt {visit += 1}
    }
    func acknowledge(expected:TaskWatcherControl?,record:TaskWatcherRecord) {
        guard let expected,control==expected,submission==record,let a=authorization,ledger.acknowledge(a) else {return}
        if record.phase == .confirmed {consumedReads.append(expected.source.read)}
        review=nil;visit += 1
    }
}
struct TaskWatcherView:View {
    @ObservedObject var model:TaskWatcherViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (TaskWatcherControl)->Void
    private func key(_ phase:TaskWatcherPhase)->String {switch phase {case .pending:"taskCommentFakePending";case .confirmed:"taskWatcherFakeConfirmed";case .rejected:"taskWatcherFakeRejected";case .unknown:"taskWatcherFakeUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("taskWatcherAction")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(record.attempt.review.source.task.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(key(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("taskWatcherAction")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if model.consumed {Text(AppCopy.text("taskWatcherFakeConfirmed"))}
                else if let review=model.review {
                    Text(review.source.task.title ?? AppCopy.text("notAvailable"))
                    Text(AppCopy.text("taskWatcherContract"))
                    Button(AppCopy.text("taskWatcherFakeSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("taskWatcherAction")+": "+AppCopy.text("back")))
                } else if model.canPrepare {Button(AppCopy.text("taskWatcherAction")) {if isCurrent() {prepare(control)}}}
            }
        }
    }
}
