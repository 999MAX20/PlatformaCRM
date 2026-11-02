import Foundation

// Explicit new whole replacement, never an edit/roundtrip of the bounded original excerpt.
public enum TaskDescriptionMode:String,CaseIterable,Codable,Sendable,Hashable {case replaceText="replace",clearText="clear"}
public struct TaskDescriptionValue:Equatable,Sendable {
    public let mode:TaskDescriptionMode;public let raw:String;public let description:String
    private init(mode:TaskDescriptionMode,raw:String,description:String) {self.mode=mode;self.raw=raw;self.description=description}
    public static func make(mode:TaskDescriptionMode?,raw:String)->Self? {
        guard let mode else {return nil}
        if mode == .clearText {return Self(mode:mode,raw:raw,description:"")}
        let value=SourceTextTrim.pythonStrip(raw)
        guard !value.isEmpty,!value.unicodeScalars.contains(where:{$0.value==0}) else {return nil}
        return Self(mode:mode,raw:raw,description:value)
    }
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.mode==rhs.mode && lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.description.utf8.elementsEqual(rhs.description.utf8)}
    public func body()->Data? {try? JSONSerialization.data(withJSONObject:["description":description])}
}
public struct TaskDescriptionEditSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskDescriptionEditGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskDescriptionEditAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskDescriptionEditAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskDescriptionEditAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskDescriptionEditReview:Equatable,Sendable {public let source:TaskDescriptionEditSource;public let visit:Int;public let value:TaskDescriptionValue;public init(source:TaskDescriptionEditSource,visit:Int,value:TaskDescriptionValue) {self.source=source;self.visit=visit;self.value=value}}
public struct TaskDescriptionEditAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskDescriptionEditAuthorization;public let review:TaskDescriptionEditReview}
public enum SyntheticTaskDescriptionEditOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskDescriptionEditPort:Sendable {var grants:[SyntheticTaskDescriptionEditGrant] {get};func execute(_ attempt:TaskDescriptionEditAttempt) async throws -> SyntheticTaskDescriptionEditOutcome}
public enum TaskDescriptionEditPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Existing TaskSerializer selected field lens; omitted fields never become known.
public struct TaskDescriptionEditResult:Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let description:String;public let updated_at:String
    private init(id:Int,business:Int,status:String,description:String,updatedAt:String) {self.id=id;self.business=business;self.status=status;self.description=description;self.updated_at=updatedAt}
    private struct Selected:Decodable {let id:Int;let business:Int;let status:String;let description:String;let updated_at:String}
    public static func decode(_ data:Data)->Self? {
        guard let fields=try? JSONDecoder().decode(Selected.self,from:data),let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],TaskSnoozeValue.parse(fields.updated_at) != nil else {return nil}
        let status=fields.status,description=fields.description,updated=fields.updated_at
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,let v=Int(exactly:n.int64Value) else {return nil};return v}
        guard let id=integer("id"),let business=integer("business"),id==fields.id,business==fields.business else {return nil};return Self(id:id,business:business,status:status,description:description,updatedAt:updated)
    }
}
public struct TaskDescriptionEditRecord:Equatable,Sendable {public let attempt:TaskDescriptionEditAttempt;public var phase:TaskDescriptionEditPhase;public var result:TaskDescriptionEditResult?}
public struct TaskDescriptionEditLedger:Sendable {
    public private(set) var records:[TaskDescriptionEditRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskDescriptionEditAuthorization?)->TaskDescriptionEditRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskDescriptionEditReview,authorization:SyntheticTaskDescriptionEditAuthorization)->TaskDescriptionEditAttempt? {
        guard review.source.valid,review.visit>0,TaskDescriptionValue.make(mode:review.value.mode,raw:review.value.raw)==review.value,review.value.body() != nil,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskDescriptionEditAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskDescriptionEditRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskDescriptionEditAttempt,outcome:SyntheticTaskDescriptionEditOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskDescriptionEditPhase = .unknown;var result:TaskDescriptionEditResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=TaskDescriptionEditResult.decode(data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.description.utf8.elementsEqual(attempt.review.value.description.utf8) {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskDescriptionEditAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskDescriptionEditPort:SyntheticTaskDescriptionEditPort {
    private struct MetadataRow:Decodable {let grant:SyntheticTaskDescriptionEditGrant;let outcome:String}
    private struct Metadata:Decodable {let fixture_only:Bool;let scenarios:[MetadataRow]}
    private struct Row:Sendable {let grant:SyntheticTaskDescriptionEditGrant;let outcome:String;let response:Data?}
    private let rows:[Row]
    public var grants:[SyntheticTaskDescriptionEditGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-description-replace-outcome.json")),let metadata=try? JSONDecoder().decode(Metadata.self,from:data),metadata.fixture_only,let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let scenarios=object["scenarios"] as? [[String:Any]],scenarios.count==metadata.scenarios.count {
            rows=metadata.scenarios.enumerated().map {i,row in
                let response:Data?
                if let value=scenarios[i]["response"],JSONSerialization.isValidJSONObject(value) {response=try? JSONSerialization.data(withJSONObject:value)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:TaskDescriptionEditAttempt) async throws -> SyntheticTaskDescriptionEditOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let response=row.response,var object=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any] else {return .unknown}
        // Explicit test producer echoes exactly the reviewed description after submit.
        object["description"]=attempt.review.value.description
        guard let data=try? JSONSerialization.data(withJSONObject:object) else {return .unknown};return .response(status:200,data:data)
    }
}
