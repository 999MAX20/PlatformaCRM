import SwiftUI
import CRMCore

@MainActor final class NotificationMarkReadViewModel:ObservableObject {
    @Published private(set) var read:NotificationMarkReadSource?
    @Published private(set) var review:NotificationMarkReadReview?
    @Published private var ledger=NotificationMarkReadLedger()
    var peerBlocked:(NotificationMarkReadContext)->Bool = {_ in false}
    var onDispatch:()->Void = {}
    func invalidatePreparedReview() {generation += 1;review=nil}
    func blocks(_ context:NotificationMarkReadContext)->Bool {ledger.blocked(context)}
    private var generation=0
    private let port:(any SyntheticNotificationMarkReadPort)?
    init(port:(any SyntheticNotificationMarkReadPort)?=nil) {self.port=port}
    private var authorization:SyntheticNotificationMarkReadAuthorization? {guard let read else {return nil};return port?.grants.compactMap {$0.authorization(for:read.context)}.first}
    var submission:NotificationMarkReadRecord? {ledger.visible(authorization)}
    var blocked:Bool {read.map {ledger.blocked($0.context) || peerBlocked($0.context)} ?? false}
    var canPrepare:Bool {read?.valid==true && authorization != nil && !blocked && review==nil}
    var retainedAttemptCount:Int {ledger.records.count}
    func bind(_ next:NotificationMarkReadSource?) {guard read != next else {return};generation += 1;read=next;review=nil}
    func prepare(_ expected:NotificationMarkReadSource) {guard read==expected,canPrepare else {return};generation += 1;review=NotificationMarkReadReview(source:expected,generation:generation)}
    func back(_ expected:NotificationMarkReadReview) {guard review==expected,read==expected.source,!blocked else {return};generation += 1;review=nil}
    func submit(_ expected:NotificationMarkReadReview) async {
        guard !Task.isCancelled,review==expected,read==expected.source,!peerBlocked(expected.source.context),let authorization,let port,let attempt=ledger.begin(expected,authorization:authorization) else {return}
        onDispatch()
        let outcome:SyntheticNotificationMarkReadOutcome
        do {let reply=try await port.execute(attempt);outcome=Task.isCancelled ? .unknown:reply} catch {outcome = .unknown}
        ledger.complete(attempt,outcome:outcome)
    }
    func acknowledge(_ expected:NotificationMarkReadSource,attemptID:Int) {
        guard read==expected,let authorization,submission?.attempt.localID==attemptID,ledger.acknowledge(authorization) else {return}
        generation += 1;review=nil
    }
}

struct NotificationMarkReadView:View {
    @ObservedObject var model:NotificationMarkReadViewModel
    let isCurrent:@MainActor ()->Bool
    private func status(_ phase:NotificationMarkReadPhase)->String {
        switch phase {case .pending:"taskCommentFakePending";case .confirmed:"notificationFakeReadConfirmed";case .rejected:"notificationFakeReadRejected";case .unknown:"notificationFakeReadUnknown"}
    }
    var body:some View {
        if let read=model.read {
            if model.blocked {
                if let record=model.submission {
                    Text(AppCopy.text(status(record.phase))).accessibilityAddTraits(.updatesFrequently)
                    if record.phase == .confirmed || record.phase == .rejected {
                        Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"notificationFakeReadEdit")) {if isCurrent() {model.acknowledge(read,attemptID:record.attempt.localID)}}.accessibilityLabel(Text(AppCopy.text("notificationFakeReadReview")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"notificationFakeReadEdit")))
                    }
                } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
            } else if let review=model.review,review.source==read {
                Section(AppCopy.text("notificationFakeReadReview")) {
                    Text(read.notification.text ?? AppCopy.text("notAvailable"))
                    Button(AppCopy.text("notificationFakeReadSubmit")) {Task {if isCurrent() {await model.submit(review)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(review)}}.accessibilityLabel(Text(AppCopy.text("notificationFakeReadReview")+": "+AppCopy.text("back")))
                }
            } else if model.canPrepare {
                Button(AppCopy.text("notificationFakeReadPrepare")) {if isCurrent() {model.prepare(read)}}
            }
        }
    }
}
