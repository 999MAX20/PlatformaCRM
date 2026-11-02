import Foundation

// Same existing native supported title-only rules; not complete installed DRF acceptance.
// Exact raw survives review/unknown. Only normalized selected title is in the synthetic body.
public struct TaskTitleValue:Equatable,Sendable {
    public let raw:String;public let title:String
    private init(raw:String,title:String) {self.raw=raw;self.title=title}
    public static func parse(_ raw:String)->Self? {
        let value=SourceTextTrim.pythonStrip(SourceTextTrim.javascriptTrim(raw))
        guard !value.isEmpty,value.unicodeScalars.count<=255,!value.unicodeScalars.contains(where:{$0.value==0}) else {return nil}
        return Self(raw:raw,title:value)
    }
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.raw.utf8.elementsEqual(rhs.raw.utf8) && lhs.title.utf8.elementsEqual(rhs.title.utf8)}
    public func body()->Data? {try? JSONSerialization.data(withJSONObject:["title":title])}
}
public struct TaskTitleEditSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask
    public init(read:TaskCommentRead,task:WorkTask) {self.read=read;self.task=task}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
}
public struct SyntheticTaskTitleEditGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskTitleEditAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskTitleEditAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskTitleEditAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskTitleEditReview:Equatable,Sendable {public let source:TaskTitleEditSource;public let visit:Int;public let value:TaskTitleValue;public init(source:TaskTitleEditSource,visit:Int,value:TaskTitleValue) {self.source=source;self.visit=visit;self.value=value}}
public struct TaskTitleEditAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskTitleEditAuthorization;public let review:TaskTitleEditReview}
public enum SyntheticTaskTitleEditOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskTitleEditPort:Sendable {var grants:[SyntheticTaskTitleEditGrant] {get};func execute(_ attempt:TaskTitleEditAttempt) async throws -> SyntheticTaskTitleEditOutcome}
public enum TaskTitleEditPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Existing TaskSerializer selected field lens; omitted fields never become known.
public struct TaskTitleEditResult:Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let title:String;public let updated_at:String
    private init(id:Int,business:Int,status:String,title:String,updatedAt:String) {self.id=id;self.business=business;self.status=status;self.title=title;self.updated_at=updatedAt}
    private struct Selected:Decodable {let id:Int;let business:Int;let status:String;let title:String;let updated_at:String}
    public static func decode(_ data:Data)->Self? {
        guard let fields=try? JSONDecoder().decode(Selected.self,from:data),let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],TaskSnoozeValue.parse(fields.updated_at) != nil else {return nil}
        let status=fields.status,title=fields.title,updated=fields.updated_at
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,let v=Int(exactly:n.int64Value) else {return nil};return v}
        guard let id=integer("id"),let business=integer("business"),id==fields.id,business==fields.business else {return nil};return Self(id:id,business:business,status:status,title:title,updatedAt:updated)
    }
}
public struct TaskTitleEditRecord:Equatable,Sendable {public let attempt:TaskTitleEditAttempt;public var phase:TaskTitleEditPhase;public var result:TaskTitleEditResult?}
public struct TaskTitleEditLedger:Sendable {
    public private(set) var records:[TaskTitleEditRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskTitleEditAuthorization?)->TaskTitleEditRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskTitleEditReview,authorization:SyntheticTaskTitleEditAuthorization)->TaskTitleEditAttempt? {
        guard review.source.valid,review.visit>0,TaskTitleValue.parse(review.value.raw)==review.value,review.value.body() != nil,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskTitleEditAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskTitleEditRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskTitleEditAttempt,outcome:SyntheticTaskTitleEditOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskTitleEditPhase = .unknown;var result:TaskTitleEditResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=TaskTitleEditResult.decode(data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,r.title.utf8.elementsEqual(attempt.review.value.title.utf8) {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskTitleEditAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskTitleEditPort:SyntheticTaskTitleEditPort {
    private struct MetadataRow:Decodable {let grant:SyntheticTaskTitleEditGrant;let outcome:String}
    private struct Metadata:Decodable {let fixture_only:Bool;let scenarios:[MetadataRow]}
    private struct Row:Sendable {let grant:SyntheticTaskTitleEditGrant;let outcome:String;let response:Data?}
    private let rows:[Row]
    public var grants:[SyntheticTaskTitleEditGrant] {rows.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("task-title-partial-outcome.json")),let metadata=try? JSONDecoder().decode(Metadata.self,from:data),metadata.fixture_only,let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let scenarios=object["scenarios"] as? [[String:Any]],scenarios.count==metadata.scenarios.count {
            rows=metadata.scenarios.enumerated().map {i,row in
                let response:Data?
                if let value=scenarios[i]["response"],JSONSerialization.isValidJSONObject(value) {response=try? JSONSerialization.data(withJSONObject:value)} else {response=nil}
                return Row(grant:row.grant,outcome:row.outcome,response:response)
            }
        } else {rows=[]}
    }
    public func execute(_ attempt:TaskTitleEditAttempt) async throws -> SyntheticTaskTitleEditOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let response=row.response,var object=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any] else {return .unknown}
        // Explicit test producer echoes exactly the reviewed normalized title after submit.
        object["title"]=attempt.review.value.title
        guard let data=try? JSONSerialization.data(withJSONObject:object) else {return .unknown};return .response(status:200,data:data)
    }
}
