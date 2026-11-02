import Foundation

// Existing undo_cancel_task/TaskSerializer subset: server chooses target; no client audit/target/key fields.
public struct TaskUndoCancelSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && task.status=="cancelled"}

}
public struct SyntheticTaskUndoCancelGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskUndoCancelAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskUndoCancelAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskUndoCancelAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskUndoCancelReview:Equatable,Sendable {public let source:TaskUndoCancelSource;public let visit:Int;public init(source:TaskUndoCancelSource,visit:Int) {self.source=source;self.visit=visit}}
public struct TaskUndoCancelAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskUndoCancelAuthorization;public let review:TaskUndoCancelReview}
public enum SyntheticTaskUndoCancelOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskUndoCancelPort:Sendable {var grants:[SyntheticTaskUndoCancelGrant] {get};func execute(_ attempt:TaskUndoCancelAttempt) async throws -> SyntheticTaskUndoCancelOutcome}
public enum TaskUndoCancelPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskUndoCancelResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let updated_at:String
    public let completed_at:String?;public let completed_by:Int?
    private enum CodingKeys:String,CodingKey {case id,business,status,updated_at,completed_at,completed_by,cancelled_at,cancelled_by,cancel_reason}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);updated_at=try c.decode(String.self,forKey:.updated_at)
        for key in [CodingKeys.cancelled_at,.cancelled_by] {guard c.contains(key),try c.decodeNil(forKey:key) else {throw ReadFailure.invalidPayload}}
        guard try c.decode(String.self,forKey:.cancel_reason)=="",c.contains(.completed_at),c.contains(.completed_by) else {throw ReadFailure.invalidPayload}
        completed_at=try c.decodeIfPresent(String.self,forKey:.completed_at);completed_by=try c.decodeIfPresent(Int.self,forKey:.completed_by)
        guard completed_at.map({Appointment.instant($0) != nil}) ?? true,completed_by.map({$0>0}) ?? true else {throw ReadFailure.invalidPayload}
    }
    public func encode(to encoder:any Encoder) throws {
        var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(id,forKey:.id);try c.encode(business,forKey:.business);try c.encode(status,forKey:.status);try c.encode(updated_at,forKey:.updated_at)
        for key in [CodingKeys.cancelled_at,.cancelled_by] {try c.encodeNil(forKey:key)};try c.encode("",forKey:.cancel_reason)
        if let completed_at {try c.encode(completed_at,forKey:.completed_at)} else {try c.encodeNil(forKey:.completed_at)}
        if let completed_by {try c.encode(completed_by,forKey:.completed_by)} else {try c.encodeNil(forKey:.completed_by)}
    }
}
public struct TaskUndoCancelRecord:Equatable,Sendable {public let attempt:TaskUndoCancelAttempt;public var phase:TaskUndoCancelPhase;public var result:TaskUndoCancelResult?}
public struct TaskUndoCancelLedger:Sendable {
    public private(set) var records:[TaskUndoCancelRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskUndoCancelAuthorization?)->TaskUndoCancelRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskUndoCancelReview,authorization:SyntheticTaskUndoCancelAuthorization)->TaskUndoCancelAttempt? {
        guard review.source.valid,review.visit>0,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskUndoCancelAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskUndoCancelRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskUndoCancelAttempt,outcome:SyntheticTaskUndoCancelOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskUndoCancelPhase = .unknown;var result:TaskUndoCancelResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskUndoCancelResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,["open","in_progress","done"].contains(r.status),Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskUndoCancelAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskUndoCancelPort:SyntheticTaskUndoCancelPort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskUndoCancelGrant;let outcome:String;let response:TaskUndoCancelResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskUndoCancelGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-undo-cancel-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskUndoCancelAttempt) async throws -> SyntheticTaskUndoCancelOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let data=try? JSONEncoder().encode(result) else {return .unknown};return .response(status:200,data:data)
    }
}
