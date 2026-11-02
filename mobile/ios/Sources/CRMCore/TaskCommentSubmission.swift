import Foundation

// Explicit fake-only authorization. Readability never constructs a production UPDATE grant.
public struct SyntheticTaskCommentGrant: Decodable, Equatable, Sendable {
    public let business: Int;public let task: Int;public let actor: Int;public let update: Bool
    public init(business: Int,task: Int,actor: Int,update: Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context: TaskCommentContext) -> SyntheticTaskCommentAuthorization? {
        guard context.valid,context.business==business,context.task==task,actor>0,update else {return nil}
        return SyntheticTaskCommentAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskCommentAuthorization: Equatable, Sendable {
    public let context: TaskCommentContext;public let actor: Int
    fileprivate init(context: TaskCommentContext,actor: Int) {self.context=context;self.actor=actor}
}
public struct TaskCommentAttempt: Equatable, Sendable {
    // RAM correlation only: never an idempotency key, request header or entity version.
    public let localID: Int;public let authorization: SyntheticTaskCommentAuthorization
    public let selection: TaskCommentSelection;public let raw: String;public let text: String
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.localID==rhs.localID && lhs.authorization==rhs.authorization && lhs.selection==rhs.selection && lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.text.utf8.elementsEqual(rhs.text.utf8)}
}
public enum SyntheticTaskCommentOutcome: Sendable {
    case response(status: Int,comment: TaskComment)
    // Only a controlled fake can promise no write. HTTP status/throws alone cannot.
    case rejectedWithoutWrite
    case unknown
}
public protocol SyntheticTaskCommentPort: Sendable {
    var grants: [SyntheticTaskCommentGrant] {get}
    func execute(_ attempt: TaskCommentAttempt) async throws -> SyntheticTaskCommentOutcome
}
public enum TaskCommentAttemptPhase: Equatable, Sendable {case pending,confirmed,rejected,unknown}
public struct TaskCommentAttemptRecord: Equatable, Sendable {
    public let attempt: TaskCommentAttempt;public var phase: TaskCommentAttemptPhase;public var comment: TaskComment?
}
public struct TaskCommentAttemptLedger: Sendable {
    public private(set) var records: [TaskCommentAttemptRecord]=[]
    private var active: [String:Int]=[:]
    public init() {}
    private func key(_ context: TaskCommentContext) -> String {"\(context.business)/\(context.task)"}
    public func blocked(_ context: TaskCommentContext) -> Bool {active[key(context)] != nil}
    public func visible(_ authorization: SyntheticTaskCommentAuthorization?) -> TaskCommentAttemptRecord? {
        guard let authorization,let index=active[key(authorization.context)] else {return nil}
        let record=records[index]
        return record.attempt.authorization==authorization ? record : nil
    }
    public mutating func begin(review: TaskCommentReview,raw: String,authorization: SyntheticTaskCommentAuthorization) -> TaskCommentAttempt? {
        let context=review.selection.read.context
        guard context==authorization.context,context.valid,authorization.actor>0,review.selection.read.revision>0,!review.text.isEmpty,TaskCommentText.preview(raw).utf8.elementsEqual(review.text.utf8),!blocked(context) else {return nil}
        let attempt=TaskCommentAttempt(localID:records.count+1,authorization:authorization,selection:review.selection,raw:raw,text:review.text)
        active[key(context)]=records.count;records.append(TaskCommentAttemptRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt: TaskCommentAttempt,outcome: SyntheticTaskCommentOutcome) {
        guard let index=records.firstIndex(where:{$0.attempt==attempt}),records[index].phase == .pending else {return}
        var phase: TaskCommentAttemptPhase = .unknown;var accepted: TaskComment?
        switch outcome {
        case .rejectedWithoutWrite: phase = .rejected
        case .unknown: break
        case .response(let status,let comment):
            if status==201,comment.id>0,comment.task==attempt.authorization.context.task,comment.author==attempt.authorization.actor,comment.text?.utf8.elementsEqual(attempt.text.utf8)==true,Appointment.instant(comment.created_at) != nil,comment.author_name != nil,comment.author_email != nil {phase = .confirmed;accepted=comment}
        }
        records[index].phase=phase;records[index].comment=accepted
    }
    // Unknown/pending cannot be cleared, replayed or resolved by matching a reread's text.
    @discardableResult public mutating func acknowledge(_ authorization: SyntheticTaskCommentAuthorization) -> Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:key(authorization.context));return true
    }
}

// DEBUG composition injects this separately from the fixture GET repository.
public struct FixtureTaskCommentSubmitPort: SyntheticTaskCommentPort {
    private struct Scenario: Decodable, Sendable {let grant: SyntheticTaskCommentGrant;let outcome: String;let response: TaskComment?}
    private struct Catalog: Decodable {let fixture_only: Bool;let scenarios: [Scenario]}
    private let scenarios: [Scenario]
    public var grants: [SyntheticTaskCommentGrant] {scenarios.map(\.grant)}
    public init(directory: URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-comment-submit.json")),let catalog=try? JSONDecoder().decode(Catalog.self,from:data),catalog.fixture_only {scenarios=catalog.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt: TaskCommentAttempt) async throws -> SyntheticTaskCommentOutcome {
        guard let scenario=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch scenario.outcome {
        case "rejected_without_write": return .rejectedWithoutWrite
        case "response":
            guard let c=scenario.response else {return .unknown}
            return .response(status:201,comment:TaskComment(id:c.id,text:attempt.text,created_at:c.created_at,task:c.task,author:c.author,author_name:c.author_name,author_email:c.author_email))
        default:return .unknown
        }
    }
}
