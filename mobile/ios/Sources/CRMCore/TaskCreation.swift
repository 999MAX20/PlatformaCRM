import Foundation

// Fake CREATE capability, never inferred from VIEW, UPDATE or displayed person data.
public struct SyntheticTaskCreateGrant: Decodable,Equatable,Sendable {
    public let business: Int;public let actor: Int;public let create: Bool
    public init(business: Int,actor: Int,create: Bool) {self.business=business;self.actor=actor;self.create=create}
    public func authorization(for context: TaskDraftContext) -> SyntheticTaskCreateAuthorization? {
        guard context.valid,context.business==business,actor>0,create else {return nil}
        return SyntheticTaskCreateAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskCreateAuthorization: Equatable,Sendable {
    public let context: TaskDraftContext;public let actor: Int
    fileprivate init(context: TaskDraftContext,actor: Int) {self.context=context;self.actor=actor}
}
public struct TaskCreateAttempt: Equatable,Sendable {
    // Local RAM correlation only, not an HTTP/idempotency key or server entity version.
    public let localID: Int;public let authorization: SyntheticTaskCreateAuthorization;public let review: TaskDraftReview
    // Existing source request-shaped data only; this never performs HTTP.
    public func preparedBody()->Data? {
        guard authorization.context==review.selection.context,review.values.issues.isEmpty,review.values.validClient(for:authorization.context.business),review.values.validAppointment(for:authorization.context.business),review.values.validParent(for:authorization.context.business),review.preview==review.values.preview else {return nil}
        let v=review.preview;var body:[String:Any]=["business":authorization.context.business,"title":v.title,"description":v.description,"priority":v.priority]
        if let due=v.dueAt {body["due_at"]=due}
        if let reminder=v.reminderAt {body["reminder_at"]=reminder}
        if let client=v.clientID {body["client"]=client}
        if let appointment=v.appointmentID {body["appointment"]=appointment}
        if let parent=v.parentTaskID {body["parent_task"]=parent}
        return try? JSONSerialization.data(withJSONObject:body,options:[.sortedKeys])
    }
}
public enum SyntheticTaskCreateOutcome: Sendable {case response(status: Int,task: WorkTask,reminderAt:String?=nil,clientRead:TaskCreateClientRead = .unknown,appointmentRead:TaskCreateAppointmentRead = .unknown,parentRead:TaskCreateParentRead = .unknown),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskCreatePort: Sendable {
    var grants: [SyntheticTaskCreateGrant] {get}
    func execute(_ attempt: TaskCreateAttempt) async throws -> SyntheticTaskCreateOutcome
}
public enum TaskCreateAttemptPhase: Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskCreateAttemptRecord: Equatable,Sendable {public let attempt: TaskCreateAttempt;public var phase: TaskCreateAttemptPhase;public var task: WorkTask?;public var reminderAt:String?=nil;public var clientID:Int?=nil;public var appointmentID:Int?=nil;public var parentTaskID:Int?=nil}
public struct TaskCreateAttemptLedger: Sendable {
    public private(set) var records: [TaskCreateAttemptRecord]=[]
    // One create composer per Business; an unresolved attempt cannot be replayed via new epoch.
    private var active: [Int:Int]=[:]
    public init() {}
    public func blocked(_ context: TaskDraftContext) -> Bool {active[context.business] != nil}
    public func visible(_ authorization: SyntheticTaskCreateAuthorization?) -> TaskCreateAttemptRecord? {
        guard let authorization,let index=active[authorization.context.business] else {return nil}
        let record=records[index];return record.attempt.authorization==authorization ? record:nil
    }
    public mutating func begin(review: TaskDraftReview,authorization: SyntheticTaskCreateAuthorization) -> TaskCreateAttempt? {
        let context=review.selection.context
        guard context.valid,context==authorization.context,authorization.actor>0,review.values.issues.isEmpty,review.values.validClient(for:context.business),review.values.validAppointment(for:context.business),review.values.validParent(for:context.business),review.preview==review.values.preview,!blocked(context) else {return nil}
        let attempt=TaskCreateAttempt(localID:records.count+1,authorization:authorization,review:review)
        active[context.business]=records.count;records.append(TaskCreateAttemptRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt: TaskCreateAttempt,outcome: SyntheticTaskCreateOutcome) {
        guard let index=records.firstIndex(where:{$0.attempt==attempt}),records[index].phase == .pending else {return}
        var phase: TaskCreateAttemptPhase = .unknown;var accepted: WorkTask?;var confirmedReminder:String?
        switch outcome {
        case .rejectedWithoutWrite:phase = .rejected
        case .unknown:break
        case .response(let status,let task,let reminderAt,let clientRead,let appointmentRead,let parentRead):
            let value=attempt.review.preview
            if status==201,task.id>0,task.business==attempt.authorization.context.business,task.created_by==attempt.authorization.actor,task.title.map({$0.utf8.elementsEqual(value.title.utf8)})==true,task.description.map({$0.utf8.elementsEqual(value.description.utf8)})==true,task.priority==value.priority,task.status=="open",attempt.review.values.dueDate.matches(task.due_at),attempt.review.values.reminderDate.matches(reminderAt),clientRead.matches(value.clientID),appointmentRead.matches(value.appointmentID),parentRead.matches(value.parentTaskID),Appointment.instant(task.created_at) != nil,Appointment.instant(task.updated_at) != nil {phase = .confirmed;accepted=task;confirmedReminder=value.reminderAt != nil ? reminderAt:nil}
        }
        records[index].phase=phase;records[index].task=accepted;records[index].reminderAt=confirmedReminder;records[index].clientID=phase == .confirmed ? attempt.review.preview.clientID:nil;records[index].appointmentID=phase == .confirmed ? attempt.review.preview.appointmentID:nil;records[index].parentTaskID=phase == .confirmed ? attempt.review.preview.parentTaskID:nil
    }
    // No title/text/status reread is attempt-specific recovery proof.
    @discardableResult public mutating func acknowledge(_ authorization: SyntheticTaskCreateAuthorization) -> Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:authorization.context.business);return true
    }
}
public struct FixtureTaskCreatePort: SyntheticTaskCreatePort {
    private struct Scenario: Decodable,Sendable {let grant: SyntheticTaskCreateGrant;let outcome: String;let response: WorkTask?}
    private struct Catalog: Decodable {let fixture_only: Bool;let scenarios:[Scenario]}
    private let scenarios:[Scenario]
    public var grants:[SyntheticTaskCreateGrant] {scenarios.map(\.grant)}
    public init(directory: URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-create-outcome.json")),let catalog=try? JSONDecoder().decode(Catalog.self,from:data),catalog.fixture_only {scenarios=catalog.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt:TaskCreateAttempt) async throws -> SyntheticTaskCreateOutcome {
        guard let scenario=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch scenario.outcome {
        case "rejected_without_write":return .rejectedWithoutWrite
        case "response":
            guard let task=scenario.response else {return .unknown};let v=attempt.review.preview
            return .response(status:201,task:WorkTask(id:task.id,title:v.title,status:task.status,priority:v.priority,due_at:v.dueAt ?? task.due_at,business:task.business,updated_at:task.updated_at,description:v.description,created_by:task.created_by,created_at:task.created_at),reminderAt:v.reminderAt,clientRead:v.clientID.map {TaskCreateClientRead.client($0)} ?? .notSet,appointmentRead:v.appointmentID.map {TaskCreateAppointmentRead.appointment($0)} ?? .notSet,parentRead:v.parentTaskID.map { .parent($0) } ?? .notSet)
        default:return .unknown
        }
    }
}
