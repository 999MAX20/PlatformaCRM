import Foundation

// Existing start_task/TaskSerializer subset. Start does not assign the current actor.
public struct TaskStartSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask;public let assignee:MobileUserRead
    public init(read:TaskCommentRead,task:WorkTask,assignee:MobileUserRead) {self.read=read;self.task=task;self.assignee=assignee}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && task.status=="open"}
    public func matchesAssignee(_ value:Int?)->Bool {switch assignee {case .notSet:value==nil;case .unknown:false;case .person(let user):user.valid && value==user.id}}
}
public struct SyntheticTaskStartGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskStartAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskStartAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskStartAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskStartReview:Equatable,Sendable {public let source:TaskStartSource;public let visit:Int;public init(source:TaskStartSource,visit:Int) {self.source=source;self.visit=visit}}
public struct TaskStartAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskStartAuthorization;public let review:TaskStartReview}
public enum SyntheticTaskStartOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskStartPort:Sendable {var grants:[SyntheticTaskStartGrant] {get};func execute(_ attempt:TaskStartAttempt) async throws -> SyntheticTaskStartOutcome}
public enum TaskStartPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskStartResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let assignee:Int?;public let updated_at:String
    private enum CodingKeys:String,CodingKey {case id,business,status,assignee,updated_at}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);updated_at=try c.decode(String.self,forKey:.updated_at)
        guard c.contains(.assignee) else {throw ReadFailure.invalidPayload};assignee=try c.decodeIfPresent(Int.self,forKey:.assignee)
    }
    public func encode(to encoder:any Encoder) throws {var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(id,forKey:.id);try c.encode(business,forKey:.business);try c.encode(status,forKey:.status);try c.encode(updated_at,forKey:.updated_at);if let assignee {try c.encode(assignee,forKey:.assignee)} else {try c.encodeNil(forKey:.assignee)}}
}
public struct TaskStartRecord:Equatable,Sendable {public let attempt:TaskStartAttempt;public var phase:TaskStartPhase;public var result:TaskStartResult?}
public struct TaskStartLedger:Sendable {
    public private(set) var records:[TaskStartRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskStartAuthorization?)->TaskStartRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskStartReview,authorization:SyntheticTaskStartAuthorization)->TaskStartAttempt? {
        guard review.source.valid,review.visit>0,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskStartAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskStartRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskStartAttempt,outcome:SyntheticTaskStartOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskStartPhase = .unknown;var result:TaskStartResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskStartResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status=="in_progress",attempt.review.source.matchesAssignee(r.assignee),Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskStartAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskStartPort:SyntheticTaskStartPort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskStartGrant;let outcome:String;let response:TaskStartResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskStartGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-start-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskStartAttempt) async throws -> SyntheticTaskStartOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let data=try? JSONEncoder().encode(result) else {return .unknown};return .response(status:200,data:data)
    }
}
