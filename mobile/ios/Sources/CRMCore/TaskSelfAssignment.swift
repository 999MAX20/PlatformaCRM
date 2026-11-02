import Foundation

// Existing assign_task_to_me/TaskSerializer subset. Independent fake UPDATE/member context only.
public struct TaskSelfAssignmentSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var valid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business) && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskSelfAssignGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool;public let active_member:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool,activeMember:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update;self.active_member=activeMember}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskSelfAssignAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update,active_member else {return nil};return SyntheticTaskSelfAssignAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskSelfAssignAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskSelfAssignmentReview:Equatable,Sendable {public let source:TaskSelfAssignmentSource;public let visit:Int;public init(source:TaskSelfAssignmentSource,visit:Int) {self.source=source;self.visit=visit}}
public struct TaskSelfAssignmentAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskSelfAssignAuthorization;public let review:TaskSelfAssignmentReview}
public enum SyntheticTaskSelfAssignOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskSelfAssignPort:Sendable {var grants:[SyntheticTaskSelfAssignGrant] {get};func execute(_ attempt:TaskSelfAssignmentAttempt) async throws -> SyntheticTaskSelfAssignOutcome}
public enum TaskSelfAssignmentPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskSelfAssignmentResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let assignee:Int;public let updated_at:String
}
public struct TaskSelfAssignmentRecord:Equatable,Sendable {public let attempt:TaskSelfAssignmentAttempt;public var phase:TaskSelfAssignmentPhase;public var result:TaskSelfAssignmentResult?}
public struct TaskSelfAssignmentLedger:Sendable {
    public private(set) var records:[TaskSelfAssignmentRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskSelfAssignAuthorization?)->TaskSelfAssignmentRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskSelfAssignmentReview,authorization:SyntheticTaskSelfAssignAuthorization)->TaskSelfAssignmentAttempt? {
        guard review.source.valid,review.visit>0,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskSelfAssignmentAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskSelfAssignmentRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskSelfAssignmentAttempt,outcome:SyntheticTaskSelfAssignOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskSelfAssignmentPhase = .unknown;var result:TaskSelfAssignmentResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskSelfAssignmentResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status=="in_progress",r.assignee==attempt.authorization.actor,Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskSelfAssignAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskSelfAssignPort:SyntheticTaskSelfAssignPort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskSelfAssignGrant;let outcome:String;let response:TaskSelfAssignmentResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskSelfAssignGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-self-assign-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskSelfAssignmentAttempt) async throws -> SyntheticTaskSelfAssignOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let data=try? JSONEncoder().encode(result) else {return .unknown};return .response(status:200,data:data)
    }
}
