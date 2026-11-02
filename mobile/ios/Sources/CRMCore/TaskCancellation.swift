import Foundation

// Explicit fake-only UPDATE context, independent of readability and comment submit capability.
public struct SyntheticTaskCancelGrant: Decodable,Equatable,Sendable {
    public let business: Int;public let task: Int;public let actor: Int;public let update: Bool
    public init(business: Int,task: Int,actor: Int,update: Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context: TaskCommentContext) -> SyntheticTaskCancelAuthorization? {
        guard context.valid,context.business==business,context.task==task,actor>0,update else {return nil}
        return SyntheticTaskCancelAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskCancelAuthorization: Equatable,Sendable {
    public let context: TaskCommentContext;public let actor: Int
    fileprivate init(context: TaskCommentContext,actor: Int) {self.context=context;self.actor=actor}
}
public struct TaskCancelAttempt: Equatable,Sendable {
    // Local RAM correlation only, never idempotency/version/wire metadata.
    public let localID: Int;public let authorization: SyntheticTaskCancelAuthorization
    public let review: TaskCancelReasonReview;public let raw: String;public let fromStatus: String
}
public enum SyntheticTaskCancelOutcome: Sendable {
    case response(status: Int,task: WorkTask)
    case rejectedWithoutWrite
    case unknown
}
public protocol SyntheticTaskCancelPort: Sendable {
    var grants: [SyntheticTaskCancelGrant] {get}
    func execute(_ attempt: TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome
}
public enum TaskCancelAttemptPhase: Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskCancelAttemptRecord: Equatable,Sendable {
    public let attempt: TaskCancelAttempt;public var phase: TaskCancelAttemptPhase;public var task: WorkTask?
}
public struct TaskCancelAttemptLedger: Sendable {
    public private(set) var records: [TaskCancelAttemptRecord]=[]
    private var active: [String:Int]=[:]
    public init() {}
    private func key(_ context: TaskCommentContext) -> String {"\(context.business)/\(context.task)"}
    public func blocked(_ context: TaskCommentContext) -> Bool {active[key(context)] != nil}
    public func visible(_ authorization: SyntheticTaskCancelAuthorization?) -> TaskCancelAttemptRecord? {
        guard let authorization,let index=active[key(authorization.context)] else {return nil}
        let record=records[index];return record.attempt.authorization==authorization ? record:nil
    }
    public mutating func begin(review: TaskCancelReasonReview,raw: String,status: String,authorization: SyntheticTaskCancelAuthorization) -> TaskCancelAttempt? {
        let context=review.selection.read.context
        guard context==authorization.context,context.valid,authorization.actor>0,review.selection.read.revision>0,["open","in_progress"].contains(status),TaskCancelReasonText.problem(raw)==nil,TaskCancelReasonText.preview(raw)==review.text,!blocked(context) else {return nil}
        let attempt=TaskCancelAttempt(localID:records.count+1,authorization:authorization,review:review,raw:raw,fromStatus:status)
        active[key(context)]=records.count;records.append(TaskCancelAttemptRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt: TaskCancelAttempt,outcome: SyntheticTaskCancelOutcome) {
        guard let index=records.firstIndex(where:{$0.attempt==attempt}),records[index].phase == .pending else {return}
        var phase: TaskCancelAttemptPhase = .unknown;var accepted: WorkTask?
        switch outcome {
        case .rejectedWithoutWrite:phase = .rejected
        case .unknown:break
        case .response(let status,let task):
            if status==200,task.valid,task.id==attempt.authorization.context.task,task.business==attempt.authorization.context.business,task.status=="cancelled",task.cancelled_by==attempt.authorization.actor,task.cancel_reason==attempt.review.text,Appointment.instant(task.cancelled_at) != nil,Appointment.instant(task.updated_at) != nil {phase = .confirmed;accepted=task}
        }
        records[index].phase=phase;records[index].task=accepted
    }
    // No reread status/text match proves an attempt; pending/unknown cannot be replayed/cleared.
    @discardableResult public mutating func acknowledge(_ authorization: SyntheticTaskCancelAuthorization) -> Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:key(authorization.context));return true
    }
}
public struct FixtureTaskCancelPort: SyntheticTaskCancelPort {
    private struct Scenario: Decodable,Sendable {let grant: SyntheticTaskCancelGrant;let outcome: String;let response: WorkTask?}
    private struct Catalog: Decodable {let fixture_only: Bool;let scenarios: [Scenario]}
    private let scenarios: [Scenario]
    public var grants: [SyntheticTaskCancelGrant] {scenarios.map(\.grant)}
    public init(directory: URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-cancel-outcome.json")),let catalog=try? JSONDecoder().decode(Catalog.self,from:data),catalog.fixture_only {scenarios=catalog.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt: TaskCancelAttempt) async throws -> SyntheticTaskCancelOutcome {
        guard let scenario=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch scenario.outcome {
        case "rejected_without_write":return .rejectedWithoutWrite
        case "response":
            guard let t=scenario.response else {return .unknown}
            return .response(status:200,task:WorkTask(id:t.id,title:t.title,status:t.status,priority:t.priority,due_at:t.due_at,client_id:t.client_id,business:t.business,cancelled_at:t.cancelled_at,cancelled_by:t.cancelled_by,cancel_reason:attempt.review.text,updated_at:t.updated_at))
        default:return .unknown
        }
    }
}
