import Foundation

public enum TaskDateField:String,CaseIterable,Codable,Sendable,Hashable {case dueAt="due_at",reminderAt="reminder_at"}
public enum TaskDateMode:String,Codable,Sendable,Equatable {case setDate="set",clearDate="clear"}
// Typed one-field local intent; no empty-body/default-date/whole-Task serialization.
public struct TaskDateChange:Equatable,Sendable {
    public let field:TaskDateField;public let mode:TaskDateMode;public let raw:String
    public init(field:TaskDateField,mode:TaskDateMode,raw:String) {self.field=field;self.mode=mode;self.raw=raw}
    public var valid:Bool {mode == .clearDate || TaskSnoozeValue.parse(raw) != nil}
    public func body()->Data? {
        guard valid else {return nil};var object:[String:Any]=[:]
        if mode == .clearDate {object[field.rawValue]=NSNull()} else {object[field.rawValue]=raw}
        return try? JSONSerialization.data(withJSONObject:object)
    }
}
public struct TaskDateDraft:Equatable,Sendable {
    public var field:TaskDateField?
    public var dueMode:TaskDateMode?,reminderMode:TaskDateMode?
    public var dueRaw="",reminderRaw=""
    public init() {}
    public var mode:TaskDateMode? {guard let field else {return nil};return field == .dueAt ? dueMode:reminderMode}
    public var raw:String {guard let field else {return ""};return field == .dueAt ? dueRaw:reminderRaw}
    public mutating func select(_ field:TaskDateField) {self.field=field}
    public mutating func choose(_ mode:TaskDateMode) {guard let field else {return};if field == .dueAt {dueMode=mode} else {reminderMode=mode}}
    public mutating func update(_ raw:String) {guard let field else {return};if field == .dueAt {dueRaw=raw} else {reminderRaw=raw}}
    public var change:TaskDateChange? {guard let field,let mode else {return nil};let value=TaskDateChange(field:field,mode:mode,raw:raw);return value.valid ? value:nil}
}
public struct TaskDateEditSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskDateEditGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskDateEditAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskDateEditAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskDateEditAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskDateEditReview:Equatable,Sendable {public let source:TaskDateEditSource;public let visit:Int;public let change:TaskDateChange;public init(source:TaskDateEditSource,visit:Int,change:TaskDateChange) {self.source=source;self.visit=visit;self.change=change}}
public struct TaskDateEditAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskDateEditAuthorization;public let review:TaskDateEditReview}
public enum SyntheticTaskDateEditOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskDateEditPort:Sendable {var grants:[SyntheticTaskDateEditGrant] {get};func execute(_ attempt:TaskDateEditAttempt) async throws -> SyntheticTaskDateEditOutcome}
public enum TaskDateEditPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Lens over the selected existing nullable TaskSerializer field, not a new wire envelope.
// Other response fields are neither retained nor promoted into the GET source.
public struct TaskDateEditResult:Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let field:TaskDateField;public let value:String?;public let updated_at:String
    private init(id:Int,business:Int,status:String,field:TaskDateField,value:String?,updatedAt:String) {self.id=id;self.business=business;self.status=status;self.field=field;self.value=value;self.updated_at=updatedAt}
    public static func decode(_ data:Data,field:TaskDateField)->Self? {
        guard let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],object.keys.contains(field.rawValue),let status=object["status"] as? String,let updated=object["updated_at"] as? String,TaskSnoozeValue.parse(updated) != nil else {return nil}
        func integer(_ key:String)->Int? {guard let n=object[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,let value=Int(exactly:n.int64Value) else {return nil};return value}
        guard let id=integer("id"),let business=integer("business") else {return nil}
        let value:String?
        if object[field.rawValue] is NSNull {value=nil} else {guard let raw=object[field.rawValue] as? String,TaskSnoozeValue.parse(raw) != nil else {return nil};value=raw}
        return Self(id:id,business:business,status:status,field:field,value:value,updatedAt:updated)
    }
    public func matches(_ change:TaskDateChange)->Bool {guard change.valid,change.field==field else {return false};if change.mode == .clearDate {return value==nil};guard let value,let expected=TaskSnoozeValue.parse(change.raw),let actual=TaskSnoozeValue.parse(value) else {return false};return expected.microseconds==actual.microseconds}
}
public struct TaskDateEditRecord:Equatable,Sendable {public let attempt:TaskDateEditAttempt;public var phase:TaskDateEditPhase;public var result:TaskDateEditResult?}
public struct TaskDateEditLedger:Sendable {
    public private(set) var records:[TaskDateEditRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskDateEditAuthorization?)->TaskDateEditRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskDateEditReview,authorization:SyntheticTaskDateEditAuthorization)->TaskDateEditAttempt? {
        guard review.source.valid,review.visit>0,review.change.valid,review.change.body() != nil,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskDateEditAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskDateEditRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskDateEditAttempt,outcome:SyntheticTaskDateEditOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskDateEditPhase = .unknown;var result:TaskDateEditResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=TaskDateEditResult.decode(data,field:attempt.review.change.field),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.matches(attempt.review.change) {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskDateEditAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskDateEditPort:SyntheticTaskDateEditPort {
    private struct MetadataRow:Decodable {let grant:SyntheticTaskDateEditGrant;let outcome:String}
    private struct Metadata:Decodable {let fixture_only:Bool;let scenarios:[MetadataRow]}
    private struct Row:Sendable {let grant:SyntheticTaskDateEditGrant;let outcome:String;let response:Data?}
    private let rows:[Row]
    public var grants:[SyntheticTaskDateEditGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-date-partial-outcome.json")),let metadata=try? JSONDecoder().decode(Metadata.self,from:data),metadata.fixture_only,let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let scenarios=object["scenarios"] as? [[String:Any]],scenarios.count==metadata.scenarios.count {
            rows=metadata.scenarios.enumerated().map {i,row in
                let response:Data?
                if let value=scenarios[i]["response"],JSONSerialization.isValidJSONObject(value) {response=try? JSONSerialization.data(withJSONObject:value)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:TaskDateEditAttempt) async throws -> SyntheticTaskDateEditOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let response=row.response,var object=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any],attempt.review.change.valid else {return .unknown}
        // Explicit fake producer changes exactly the chosen existing date field after submit.
        let change=attempt.review.change
        if change.mode == .clearDate {object[change.field.rawValue]=NSNull()} else {object[change.field.rawValue]=change.raw}
        guard let data=try? JSONSerialization.data(withJSONObject:object) else {return .unknown};return .response(status:200,data:data)
    }
}
