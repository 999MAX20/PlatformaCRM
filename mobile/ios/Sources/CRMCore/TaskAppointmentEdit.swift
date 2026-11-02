import Foundation

public enum TaskAppointmentEditMode:String,Codable,Equatable,Sendable {case set,clear}
public struct TaskAppointmentChange:Equatable,Sendable {
    public let mode:TaskAppointmentEditMode;public let choice:TaskDraftAppointmentChoice?
    public func body()->Data? {
        let value:Any
        if mode == .clear {value=NSNull()} else {guard let choice,choice.valid(for:choice.business) else {return nil};value=choice.id}
        return try? JSONSerialization.data(withJSONObject:["appointment":value])
    }
}
public struct TaskAppointmentEditDraft:Equatable,Sendable {
    public var mode:TaskAppointmentEditMode?;public var choice:TaskDraftAppointmentChoice?;public var choiceRead:TaskCommentRead?;public var day=""
    public init() {}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.mode==rhs.mode && lhs.choice==rhs.choice && lhs.choiceRead==rhs.choiceRead && lhs.day.utf8.elementsEqual(rhs.day.utf8)}
    public func change(for source:TaskAppointmentEditSource)->TaskAppointmentChange? {
        guard source.valid,let mode else {return nil}
        if mode == .set {guard TaskAppointmentDay.valid(day),let choice,choice.valid(for:source.read.context.business),choiceRead==source.read else {return nil}}
        return TaskAppointmentChange(mode:mode,choice:mode == .set ? choice:nil)
    }
}
public struct TaskAppointmentEditSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask;public let original:TaskAppointmentOriginal
    public init(read:TaskCommentRead,task:WorkTask,original:TaskAppointmentOriginal) {self.read=read;self.task=task;self.original=original}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var statusValid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
    public var valid:Bool {statusValid && original.known}
}
public struct SyntheticTaskAppointmentEditGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskAppointmentEditAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskAppointmentEditAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskAppointmentEditAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskAppointmentEditReview:Equatable,Sendable {
    public let source:TaskAppointmentEditSource;public let visit:Int;public let draft:TaskAppointmentEditDraft
    public init(source:TaskAppointmentEditSource,visit:Int,draft:TaskAppointmentEditDraft) {self.source=source;self.visit=visit;self.draft=draft}
    public var change:TaskAppointmentChange? {draft.change(for:source)}
}
public struct TaskAppointmentEditAttempt:Equatable,Sendable {
    public let localID:Int;public let authorization:SyntheticTaskAppointmentEditAuthorization;public let review:TaskAppointmentEditReview
    public func preparedBody()->Data? {guard review.source.valid,review.source.read.context==authorization.context else {return nil};return review.change?.body()}
}
public enum SyntheticTaskAppointmentEditOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskAppointmentEditPort:Sendable {var grants:[SyntheticTaskAppointmentEditGrant] {get};func execute(_ attempt:TaskAppointmentEditAttempt) async throws -> SyntheticTaskAppointmentEditOutcome}
public enum TaskAppointmentEditPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Selected existing TaskSerializer.appointment lens; bounded GET aliases are never command evidence.
public struct TaskAppointmentEditResult:Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let value:Int?;public let updated_at:String
    public static func decode(_ data:Data)->Self? {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let status=o["status"] as? String,let updated=o["updated_at"] as? String,TaskSnoozeValue.parse(updated) != nil else {return nil}
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return nil};return Int(n.int64Value)}
        guard let id=integer("id"),let business=integer("business") else {return nil}
        let value:Int?;switch TaskCreateAppointmentRead.decode(data) {case .unknown:return nil;case .notSet:value=nil;case .appointment(let id):value=id}
        return Self(id:id,business:business,status:status,value:value,updated_at:updated)
    }
    public func matches(_ change:TaskAppointmentChange)->Bool {change.mode == .clear ? value==nil:value==change.choice?.id}
}
public struct TaskAppointmentEditRecord:Equatable,Sendable {public let attempt:TaskAppointmentEditAttempt;public var phase:TaskAppointmentEditPhase;public var result:TaskAppointmentEditResult?}
public struct TaskAppointmentEditLedger:Sendable {
    public private(set) var records:[TaskAppointmentEditRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskAppointmentEditAuthorization?)->TaskAppointmentEditRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskAppointmentEditReview,authorization:SyntheticTaskAppointmentEditAuthorization)->TaskAppointmentEditAttempt? {
        guard review.source.valid,review.visit>0,review.change != nil,review.change?.body() != nil,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskAppointmentEditAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskAppointmentEditRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskAppointmentEditAttempt,outcome:SyntheticTaskAppointmentEditOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskAppointmentEditPhase = .unknown;var result:TaskAppointmentEditResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let change=attempt.review.change,let r=TaskAppointmentEditResult.decode(data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.matches(change) {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskAppointmentEditAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskAppointmentEditPort:SyntheticTaskAppointmentEditPort {
    private struct MetadataRow:Decodable {let grant:SyntheticTaskAppointmentEditGrant;let outcome:String}
    private struct Metadata:Decodable {let fixture_only:Bool;let scenarios:[MetadataRow]}
    private struct Row:Sendable {let grant:SyntheticTaskAppointmentEditGrant;let outcome:String;let response:Data?}
    private let rows:[Row]
    public var grants:[SyntheticTaskAppointmentEditGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-appointment-partial-outcome.json")),let metadata=try? JSONDecoder().decode(Metadata.self,from:data),metadata.fixture_only,let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let scenarios=object["scenarios"] as? [[String:Any]],scenarios.count==metadata.scenarios.count {
            rows=metadata.scenarios.enumerated().map {i,row in
                let response:Data?
                if let value=scenarios[i]["response"],JSONSerialization.isValidJSONObject(value) {response=try? JSONSerialization.data(withJSONObject:value)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:TaskAppointmentEditAttempt) async throws -> SyntheticTaskAppointmentEditOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let response=row.response,var object=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any],attempt.review.change != nil else {return .unknown}
        // Explicit fake producer echoes exactly the one chosen existing relationship field.
        guard let change=attempt.review.change else {return .unknown}
        if change.mode == .clear {object["appointment"]=NSNull()} else {guard let id=change.choice?.id else {return .unknown};object["appointment"]=id}
        guard let data=try? JSONSerialization.data(withJSONObject:object) else {return .unknown};return .response(status:200,data:data)
    }
}
