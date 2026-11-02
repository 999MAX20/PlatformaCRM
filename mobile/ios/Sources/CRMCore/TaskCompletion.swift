import Foundation

// Existing web complete action/TaskSerializer subset. Fake-only; never a mobile request DTO.
public struct TaskCompletionSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var valid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business) && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskCompleteGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskCompleteAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskCompleteAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskCompleteAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskCompletionReview:Equatable,Sendable {public let source:TaskCompletionSource;public let visit:Int;public init(source:TaskCompletionSource,visit:Int) {self.source=source;self.visit=visit}}
public struct TaskCompletionAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskCompleteAuthorization;public let review:TaskCompletionReview}
public enum SyntheticTaskCompleteOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskCompletePort:Sendable {var grants:[SyntheticTaskCompleteGrant] {get};func execute(_ attempt:TaskCompletionAttempt) async throws -> SyntheticTaskCompleteOutcome}
public enum TaskCompletionPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct TaskCompletionResult:Decodable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let completed_by:Int;public let completed_at:String;public let updated_at:String;public let snoozeCleared:Bool
    private enum CodingKeys:String,CodingKey {case id,business,status,completed_by,completed_at,updated_at,snoozed_until}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);completed_by=try c.decode(Int.self,forKey:.completed_by);completed_at=try c.decode(String.self,forKey:.completed_at);updated_at=try c.decode(String.self,forKey:.updated_at)
        if c.contains(.snoozed_until) {snoozeCleared=try c.decodeNil(forKey:.snoozed_until)} else {snoozeCleared=false}
    }
}
public struct TaskCompletionRecord:Equatable,Sendable {public let attempt:TaskCompletionAttempt;public var phase:TaskCompletionPhase;public var result:TaskCompletionResult?}
public struct TaskCompletionLedger:Sendable {
    public private(set) var records:[TaskCompletionRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskCompleteAuthorization?)->TaskCompletionRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskCompletionReview,authorization:SyntheticTaskCompleteAuthorization)->TaskCompletionAttempt? {
        guard review.source.valid,review.visit>0,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskCompletionAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskCompletionRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskCompletionAttempt,outcome:SyntheticTaskCompleteOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskCompletionPhase = .unknown;var result:TaskCompletionResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskCompletionResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status=="done",r.completed_by==attempt.authorization.actor,r.snoozeCleared,Appointment.instant(r.completed_at) != nil,Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskCompleteAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskCompletePort:SyntheticTaskCompletePort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskCompleteGrant;let outcome:String;let response:TaskCompletionFixtureResponse?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private struct TaskCompletionFixtureResponse:Codable,Sendable {let id:Int;let business:Int;let status:String;let completed_by:Int;let completed_at:String;let updated_at:String
        private enum CodingKeys:String,CodingKey {case id,business,status,completed_by,completed_at,updated_at,snoozed_until}
        init(from decoder:any Decoder) throws {let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);completed_by=try c.decode(Int.self,forKey:.completed_by);completed_at=try c.decode(String.self,forKey:.completed_at);updated_at=try c.decode(String.self,forKey:.updated_at);guard c.contains(.snoozed_until),try c.decodeNil(forKey:.snoozed_until) else {throw ReadFailure.invalidPayload}}
        func encode(to encoder:any Encoder) throws {var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(id,forKey:.id);try c.encode(business,forKey:.business);try c.encode(status,forKey:.status);try c.encode(completed_by,forKey:.completed_by);try c.encode(completed_at,forKey:.completed_at);try c.encode(updated_at,forKey:.updated_at);try c.encodeNil(forKey:.snoozed_until)}
    }
    private let rows:[Row]
    public var grants:[SyntheticTaskCompleteGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-complete-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskCompletionAttempt) async throws -> SyntheticTaskCompleteOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let data=try? JSONEncoder().encode(result) else {return .unknown};return .response(status:200,data:data)
    }
}
