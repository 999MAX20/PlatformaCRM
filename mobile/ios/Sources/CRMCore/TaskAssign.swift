import Foundation

// Canonical positive signed64 user ID is a local supported input subset.
// No default actor, no unassign from empty input, no current membership claim.
public struct TaskAssignValue:Equatable,Sendable {
    public let raw:String;public let userID:Int64
    private init(raw:String,userID:Int64) {self.raw=raw;self.userID=userID}
    public static func parse(_ raw:String)->Self? {
        guard !raw.isEmpty,raw.utf8.allSatisfy({$0>=48 && $0<=57}),let id=Int64(raw),id>0,String(id)==raw else {return nil}
        return Self(raw:raw,userID:id)
    }
}
public struct TaskAssignSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
}
// eligible_members belongs ONLY to explicit fake context, never GET or request DTO.
public struct SyntheticTaskAssignGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool;public let eligibleMembers:[Int64]
    private enum CodingKeys:String,CodingKey {case business,task,actor,update;case eligibleMembers="eligible_members"}
    public init(business:Int,task:Int,actor:Int,update:Bool,eligibleMembers:[Int64]) {self.business=business;self.task=task;self.actor=actor;self.update=update;self.eligibleMembers=eligibleMembers}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskAssignAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update,!eligibleMembers.isEmpty,eligibleMembers.allSatisfy({$0>0}),Set(eligibleMembers).count==eligibleMembers.count else {return nil}
        return SyntheticTaskAssignAuthorization(context:context,actor:actor,eligibleMembers:eligibleMembers)
    }
}
public struct SyntheticTaskAssignAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;public let eligibleMembers:[Int64];fileprivate init(context:TaskCommentContext,actor:Int,eligibleMembers:[Int64]) {self.context=context;self.actor=actor;self.eligibleMembers=eligibleMembers}}
public struct TaskAssignReview:Equatable,Sendable {public let source:TaskAssignSource;public let visit:Int;public let value:TaskAssignValue;public init(source:TaskAssignSource,visit:Int,value:TaskAssignValue) {self.source=source;self.visit=visit;self.value=value}}
public struct TaskAssignAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskAssignAuthorization;public let review:TaskAssignReview}
public enum SyntheticTaskAssignOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskAssignPort:Sendable {var grants:[SyntheticTaskAssignGrant] {get};func execute(_ attempt:TaskAssignAttempt) async throws -> SyntheticTaskAssignOutcome}
public enum TaskAssignPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Existing direct TaskSerializer result fields. assignee is the selected FK,
// distinct from request user_id and from the current actor.
public struct TaskAssignResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let assignee:Int64;public let updated_at:String
    public static func decode(_ data:Data)->Self? {
        guard let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {return nil}
        for key in ["id","business","assignee"] {
            guard let number=object[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:number.objCType)),number.int64Value>0 else {return nil}
        }
        return try? JSONDecoder().decode(Self.self,from:data)
    }
}
public struct TaskAssignRecord:Equatable,Sendable {public let attempt:TaskAssignAttempt;public var phase:TaskAssignPhase;public var result:TaskAssignResult?}
public struct TaskAssignLedger:Sendable {
    public private(set) var records:[TaskAssignRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskAssignAuthorization?)->TaskAssignRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskAssignReview,authorization:SyntheticTaskAssignAuthorization)->TaskAssignAttempt? {
        guard review.source.valid,review.visit>0,TaskAssignValue.parse(review.value.raw)==review.value,review.source.read.context==authorization.context,authorization.actor>0,authorization.eligibleMembers.contains(review.value.userID),!blocked(authorization.context) else {return nil}
        let a=TaskAssignAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskAssignRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskAssignAttempt,outcome:SyntheticTaskAssignOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskAssignPhase = .unknown;var result:TaskAssignResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=TaskAssignResult.decode(data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.assignee==attempt.review.value.userID,TaskSnoozeValue.parse(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskAssignAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskAssignPort:SyntheticTaskAssignPort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskAssignGrant;let outcome:String;let response:TaskAssignResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskAssignGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-assign-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskAssignAttempt) async throws -> SyntheticTaskAssignOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let base=try? JSONEncoder().encode(result),var body=(try? JSONSerialization.jsonObject(with:base)) as? [String:Any] else {return .unknown}
        // Explicit test producer echo after submit; never source mutation or a real result claim.
        body["assignee"]=attempt.review.value.userID
        guard let data=try? JSONSerialization.data(withJSONObject:body) else {return .unknown};return .response(status:200,data:data)
    }
}
