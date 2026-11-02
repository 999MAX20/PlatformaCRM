import Foundation

// Existing reopen_task/TaskSerializer subset; distinct from audit-derived undo_cancel_task.
public struct TaskReopenSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask;public let assignee:MobileUserRead
    public init(read:TaskCommentRead,task:WorkTask,assignee:MobileUserRead) {self.read=read;self.task=task;self.assignee=assignee}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && (task.status=="done" || task.status=="cancelled")}
    public func matchesAssignee(_ value:Int?)->Bool {switch assignee {case .notSet:value==nil;case .unknown:false;case .person(let user):user.valid && value==user.id}}
}
public struct SyntheticTaskReopenGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskReopenAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskReopenAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskReopenAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskReopenReview:Equatable,Sendable {public let source:TaskReopenSource;public let visit:Int;public init(source:TaskReopenSource,visit:Int) {self.source=source;self.visit=visit}}
public struct TaskReopenAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskReopenAuthorization;public let review:TaskReopenReview}
public enum SyntheticTaskReopenOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskReopenPort:Sendable {var grants:[SyntheticTaskReopenGrant] {get};func execute(_ attempt:TaskReopenAttempt) async throws -> SyntheticTaskReopenOutcome}
public enum TaskReopenPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskReopenResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let assignee:Int?;public let updated_at:String
    private enum CodingKeys:String,CodingKey {case id,business,status,assignee,updated_at,completed_at,completed_by,cancelled_at,cancelled_by,cancel_reason}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);updated_at=try c.decode(String.self,forKey:.updated_at)
        guard c.contains(.assignee) else {throw ReadFailure.invalidPayload};assignee=try c.decodeIfPresent(Int.self,forKey:.assignee)
        for key in [CodingKeys.completed_at,.completed_by,.cancelled_at,.cancelled_by] {guard c.contains(key),try c.decodeNil(forKey:key) else {throw ReadFailure.invalidPayload}}
        guard try c.decode(String.self,forKey:.cancel_reason)=="" else {throw ReadFailure.invalidPayload}
    }
    public func encode(to encoder:any Encoder) throws {var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(id,forKey:.id);try c.encode(business,forKey:.business);try c.encode(status,forKey:.status);try c.encode(updated_at,forKey:.updated_at);for key in [CodingKeys.completed_at,.completed_by,.cancelled_at,.cancelled_by] {try c.encodeNil(forKey:key)};try c.encode("",forKey:.cancel_reason);if let assignee {try c.encode(assignee,forKey:.assignee)} else {try c.encodeNil(forKey:.assignee)}}
}
public struct TaskReopenRecord:Equatable,Sendable {public let attempt:TaskReopenAttempt;public var phase:TaskReopenPhase;public var result:TaskReopenResult?}
public struct TaskReopenLedger:Sendable {
    public private(set) var records:[TaskReopenRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskReopenAuthorization?)->TaskReopenRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskReopenReview,authorization:SyntheticTaskReopenAuthorization)->TaskReopenAttempt? {
        guard review.source.valid,review.visit>0,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskReopenAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskReopenRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskReopenAttempt,outcome:SyntheticTaskReopenOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskReopenPhase = .unknown;var result:TaskReopenResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskReopenResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status=="open",attempt.review.source.matchesAssignee(r.assignee),Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskReopenAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskReopenPort:SyntheticTaskReopenPort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskReopenGrant;let outcome:String;let response:TaskReopenResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskReopenGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-reopen-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskReopenAttempt) async throws -> SyntheticTaskReopenOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let data=try? JSONEncoder().encode(result) else {return .unknown};return .response(status:200,data:data)
    }
}
