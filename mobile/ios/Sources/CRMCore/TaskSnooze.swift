import Foundation

// Explicit supported input subset, not a replacement for DRF DateTimeField.
// No default date/zone or future-only policy. The wire string remains exact raw;
// microseconds are local instant comparison only, never a version or command key.
public struct TaskSnoozeValue:Equatable,Sendable {
    public let raw:String;public let microseconds:Int64
    private init(raw:String,microseconds:Int64) {self.raw=raw;self.microseconds=microseconds}
    public static func parse(_ raw:String)->Self? {
        guard raw.utf8.allSatisfy({$0<128}),let regex=try? NSRegularExpression(pattern:#"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})$"#),let match=regex.firstMatch(in:raw,range:NSRange(raw.startIndex...,in:raw)),match.range.length==raw.utf16.count else {return nil}
        func text(_ i:Int)->String {guard let range=Range(match.range(at:i),in:raw) else {return ""};return String(raw[range])}
        let year=Int(text(1))!,month=Int(text(2))!,day=Int(text(3))!,hour=Int(text(4))!,minute=Int(text(5))!,second=Int(text(6))!,fraction=text(7),zone=text(8)
        guard (1...9999).contains(year),(1...12).contains(month),hour<24,minute<60,second<60,zone != "-00:00" else {return nil}
        let leap=year%4==0 && (year%100 != 0 || year%400==0),lengths=[31,leap ? 29:28,31,30,31,30,31,31,30,31,30,31]
        guard day>0,day<=lengths[month-1] else {return nil}
        var offset=0
        if zone != "Z" {
            let parts=zone.dropFirst().split(separator:":"),h=Int(parts[0])!,m=Int(parts[1])!
            guard h<24,m<60 else {return nil};offset=(h*3600+m*60)*(zone.hasPrefix("-") ? -1:1)
        }
        // Proleptic Gregorian civil day, independent of OS locale/calendar cutover.
        let y=year-(month<=2 ? 1:0),era=y/400,yoe=y-era*400
        let doy=(153*(month+(month>2 ? -3:9))+2)/5+day-1
        let days=era*146097+yoe*365+yoe/4-yoe/100+doy-719468
        let micros=Int64(days*86400+hour*3600+minute*60+second-offset)*1_000_000+Int64(fraction+String(repeating:"0",count:6-fraction.count))!
        guard micros >= -62135596800000000,micros<=253402300799999999 else {return nil}
        return Self(raw:raw,microseconds:micros)
    }
}

public struct TaskSnoozeSource:Equatable,Sendable {
    public let read:TaskCommentRead;public let task:WorkTask;public let reminder:TaskScheduleValue
    public init(read:TaskCommentRead,task:WorkTask,reminder:TaskScheduleValue) {self.read=read;self.task=task;self.reminder=reminder}
    public var identityValid:Bool {read.context.valid && read.revision>0 && task.valid && task.id==read.context.task && (task.business==nil || task.business==read.context.business)}
    public var valid:Bool {identityValid && ["open","in_progress"].contains(task.status)}
    public func matchesSchedule(_ value:String?,source:String?)->Bool {if value==nil || source==nil {return value==nil && source==nil};guard let a=TaskSnoozeValue.parse(value!),let b=TaskSnoozeValue.parse(source!) else {return false};return a.microseconds==b.microseconds}
    public func matchesReminder(_ value:String?)->Bool {switch reminder {case .notSet:value==nil;case .unknown:false;case .instant(let source):matchesSchedule(value,source:source)}}
}
public struct SyntheticTaskSnoozeGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let task:Int;public let actor:Int;public let update:Bool
    public init(business:Int,task:Int,actor:Int,update:Bool) {self.business=business;self.task=task;self.actor=actor;self.update=update}
    public func authorization(for context:TaskCommentContext)->SyntheticTaskSnoozeAuthorization? {
        guard context.valid,business==context.business,task==context.task,actor>0,update else {return nil};return SyntheticTaskSnoozeAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticTaskSnoozeAuthorization:Equatable,Sendable {public let context:TaskCommentContext;public let actor:Int;fileprivate init(context:TaskCommentContext,actor:Int) {self.context=context;self.actor=actor}}
public struct TaskSnoozeReview:Equatable,Sendable {public let source:TaskSnoozeSource;public let visit:Int;public let value:TaskSnoozeValue;public init(source:TaskSnoozeSource,visit:Int,value:TaskSnoozeValue) {self.source=source;self.visit=visit;self.value=value}}
public struct TaskSnoozeAttempt:Equatable,Sendable {public let localID:Int;public let authorization:SyntheticTaskSnoozeAuthorization;public let review:TaskSnoozeReview}
public enum SyntheticTaskSnoozeOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticTaskSnoozePort:Sendable {var grants:[SyntheticTaskSnoozeGrant] {get};func execute(_ attempt:TaskSnoozeAttempt) async throws -> SyntheticTaskSnoozeOutcome}
public enum TaskSnoozePhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
// Existing TaskSerializer direct result subset. Explicit nulls stay distinct from missing.
public struct TaskSnoozeResult:Codable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let status:String;public let snoozed_until:String;public let due_at:String?;public let reminder_at:String?;public let updated_at:String
    private enum CodingKeys:String,CodingKey {case id,business,status,snoozed_until,due_at,reminder_at,updated_at}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);status=try c.decode(String.self,forKey:.status);snoozed_until=try c.decode(String.self,forKey:.snoozed_until);updated_at=try c.decode(String.self,forKey:.updated_at)
        guard c.contains(.due_at),c.contains(.reminder_at) else {throw ReadFailure.invalidPayload}
        due_at=try c.decodeIfPresent(String.self,forKey:.due_at);reminder_at=try c.decodeIfPresent(String.self,forKey:.reminder_at)
    }
    public func encode(to encoder:any Encoder) throws {
        var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(id,forKey:.id);try c.encode(business,forKey:.business);try c.encode(status,forKey:.status);try c.encode(snoozed_until,forKey:.snoozed_until);try c.encode(updated_at,forKey:.updated_at)
        if let due_at {try c.encode(due_at,forKey:.due_at)} else {try c.encodeNil(forKey:.due_at)}
        if let reminder_at {try c.encode(reminder_at,forKey:.reminder_at)} else {try c.encodeNil(forKey:.reminder_at)}
    }
}
public struct TaskSnoozeRecord:Equatable,Sendable {public let attempt:TaskSnoozeAttempt;public var phase:TaskSnoozePhase;public var result:TaskSnoozeResult?}
public struct TaskSnoozeLedger:Sendable {
    public private(set) var records:[TaskSnoozeRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:TaskCommentContext)->String {"\(c.business)/\(c.task)"}
    public func blocked(_ c:TaskCommentContext)->Bool {active[key(c)] != nil}
    public func visible(_ a:SyntheticTaskSnoozeAuthorization?)->TaskSnoozeRecord? {guard let a,let i=active[key(a.context)],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:TaskSnoozeReview,authorization:SyntheticTaskSnoozeAuthorization)->TaskSnoozeAttempt? {
        guard review.source.valid,review.visit>0,TaskSnoozeValue.parse(review.value.raw)==review.value,review.source.read.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=TaskSnoozeAttempt(localID:records.count+1,authorization:authorization,review:review);active[key(authorization.context)]=records.count;records.append(TaskSnoozeRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:TaskSnoozeAttempt,outcome:SyntheticTaskSnoozeOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:TaskSnoozePhase = .unknown;var result:TaskSnoozeResult?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let data):
            if status==200,let r=try? JSONDecoder().decode(TaskSnoozeResult.self,from:data),r.id==attempt.authorization.context.task,r.business==attempt.authorization.context.business,r.status==attempt.review.source.task.status,TaskSnoozeValue.parse(r.snoozed_until)?.microseconds==attempt.review.value.microseconds,attempt.review.source.matchesSchedule(r.due_at,source:attempt.review.source.task.due_at),attempt.review.source.matchesReminder(r.reminder_at),Appointment.instant(r.updated_at) != nil {phase = .confirmed;result=r}
        }
        records[i].phase=phase;records[i].result=result
    }
    @discardableResult public mutating func acknowledge(_ a:SyntheticTaskSnoozeAuthorization)->Bool {
        guard let r=visible(a),r.phase == .confirmed || r.phase == .rejected else {return false};active.removeValue(forKey:key(a.context));return true
    }
}
public struct FixtureTaskSnoozePort:SyntheticTaskSnoozePort {
    private struct Row:Decodable,Sendable {let grant:SyntheticTaskSnoozeGrant;let outcome:String;let response:TaskSnoozeResult?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticTaskSnoozeGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-snooze-outcome.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:TaskSnoozeAttempt) async throws -> SyntheticTaskSnoozeOutcome {
        guard let row=rows.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let result=row.response,let base=try? JSONEncoder().encode(result),var body=(try? JSONSerialization.jsonObject(with:base)) as? [String:Any] else {return .unknown}
        // Explicit test producer echo after submit; never source mutation or a real result claim.
        body["snoozed_until"]=attempt.review.value.raw
        guard let data=try? JSONSerialization.data(withJSONObject:body) else {return .unknown};return .response(status:200,data:data)
    }
}
