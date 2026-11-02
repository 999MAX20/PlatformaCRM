import Foundation

// Reuse existing Task choice vocabulary, not CREATE defaults or authorization.
public struct TaskPriorityValue:Equatable,Sendable {
    public let raw:String
    private init(raw:String) {self.raw=raw}
    public static func parse(_ raw:String)->Self? {TaskDraftValues.priorities.contains(raw) ? Self(raw:raw):nil}
    public func body()->Data? {try? JSONSerialization.data(withJSONObject:["priority":raw])}
}
public struct TaskPriorityEditSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskPriorityEditGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskPriorityEditAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskPriorityEditAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskPriorityEditAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskPriorityEditReview:Equatable,Sendable {public let source:TaskPriorityEditSource;public let visit:Int;public let value:TaskPriorityValue;public init(source:TaskPriorityEditSource,visit:Int,value:TaskPriorityValue) {self.source=source;self.visit=visit;self.value=value}}
public struct TaskPriorityEditAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskPriorityEditAuthorization;public let review:TaskPriorityEditReview}
public enum SyntheticTaskPriorityEditOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskPriorityEditPort:Sendable {var grants:[SyntheticTaskPriorityEditGrant] {get};func execute(_ attempt:TaskPriorityEditAttempt) async throws -> SyntheticTaskPriorityEditOutcome}
public enum TaskPriorityEditPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Existing TaskSerializer selected field lens; omitted fields never become known.
public struct TaskPriorityEditResult:Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let priority:String;public let updated_at:String
    private init(id:Int,business:Int,status:String,priority:String,updatedAt:String) {self.id=id;self.business=business;self.status=status;self.priority=priority;self.updated_at=updatedAt}
    public static func decode(_ data:Data)->Self? {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let status=o["status"] as? String,let priority=o["priority"] as? String,TaskPriorityValue.parse(priority) != nil,let updated=o["updated_at"] as? String,TaskSnoozeValue.parse(updated) != nil else {return nil}
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,let v=Int(exactly:n.int64Value) else {return nil};return v}
        guard let id=integer("id"),let business=integer("business") else {return nil};return Self(id:id,business:business,status:status,priority:priority,updatedAt:updated)
    }
}
public struct TaskPriorityEditRecord:Equatable,Sendable {public let attempt:TaskPriorityEditAttempt;public var phase:TaskPriorityEditPhase;public var result:TaskPriorityEditResult?}
public struct TaskPriorityEditLedger:Sendable {
    public private(set) var records:[TaskPriorityEditRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskPriorityEditAuthorization?)->TaskPriorityEditRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskPriorityEditReview,authorization:SyntheticTaskPriorityEditAuthorization)->TaskPriorityEditAttempt? {
        guard review.source.valid,review.visit>0,TaskPriorityValue.parse(review.value.raw)==review.value,review.value.body() != nil,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskPriorityEditAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskPriorityEditRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskPriorityEditAttempt,outcome:SyntheticTaskPriorityEditOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskPriorityEditPhase = .unknown;var result:TaskPriorityEditResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=TaskPriorityEditResult.decode(data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.priority==attempt.review.value.raw {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskPriorityEditAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskPriorityEditPort:SyntheticTaskPriorityEditPort {
    private struct MetadataRow:Decodable {let grant:SyntheticTaskPriorityEditGrant;let outcome:String}
    private struct Metadata:Decodable {let fixture_only:Bool;let scenarios:[MetadataRow]}
    private struct Row:Sendable {let grant:SyntheticTaskPriorityEditGrant;let outcome:String;let response:Data?}
    private let rows:[Row]
    public var grants:[SyntheticTaskPriorityEditGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-priority-partial-outcome.json")),let metadata=try? JSONDecoder().decode(Metadata.self,from:data),metadata.fixture_only,let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let scenarios=object["scenarios"] as? [[String:Any]],scenarios.count==metadata.scenarios.count {
            rows=metadata.scenarios.enumerated().map {i,row in
                let response:Data?
                if let value=scenarios[i]["response"],JSONSerialization.isValidJSONObject(value) {response=try? JSONSerialization.data(withJSONObject:value)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:TaskPriorityEditAttempt) async throws -> SyntheticTaskPriorityEditOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let response=row.response,var object=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any] else {return .unknown}
        // Explicit test producer echoes exactly the chosen priority after submit.
        object["priority"]=attempt.review.value.raw
        guard let data=try? JSONSerialization.data(withJSONObject:object) else {return .unknown};return .response(status:200,data:data)
    }
}
