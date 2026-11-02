import Foundation

// Explicit fixture-only UPDATE context. Generic actions have no source-declared mobile key.
public struct SyntheticAppointmentTerminalGrant:Codable,Equatable,Sendable {
    public let business:Int,appointment:Int,actor:Int;public let update:Bool;public let actions:[AppointmentLifecycleAction]
    public init(business:Int,appointment:Int,actor:Int,update:Bool,actions:[AppointmentLifecycleAction]) {self.business=business;self.appointment=appointment;self.actor=actor;self.update=update;self.actions=actions}
    public func authorization(_ source:AppointmentLifecycleSource,action:AppointmentLifecycleAction)->SyntheticAppointmentLifecycleAuthorization? {
        guard source.valid,business==source.read.scope.business.id,appointment==source.read.id,actor>0,update,action.isGenericTerminal,actions.contains(action) else {return nil}
        return SyntheticAppointmentLifecycleAuthorization(business:business,appointment:appointment,epoch:source.epoch,actor:actor,action:action,key:nil)
    }
}
// Bounded plain AppointmentSerializer lens. Other serializer fields are not saved back.
// The supplied updated_at is observed, never converted into a lock/retry token.
public struct AppointmentTerminalReceipt:Equatable,Sendable {
    public let id:Int,business:Int,client:Int,service:Int;public let lead:Int?,resource:Int?
    public let status:String,start_at:String,end_at:String,created_at:String,updated_at:String;public let is_archived:Bool
    public let raw:Data
    public static func decode(_ data:Data)->Self? {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],o["ok"]==nil,o["appointment"]==nil,o["replayed"]==nil else {return nil}
        func integer(_ key:String)->Int? {guard let v=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:v.objCType)),v.int64Value>0,v.int64Value<=Int64(Int32.max) else {return nil};return Int(v.int64Value)}
        func nullableID(_ key:String)->Bool {o[key] is NSNull || integer(key) != nil}
        guard let id=integer("id"),let business=integer("business"),let client=integer("client"),let service=integer("service"),nullableID("lead"),nullableID("resource"),
              let status=o["status"] as? String,let start=o["start_at"] as? String,let end=o["end_at"] as? String,let created=o["created_at"] as? String,let updated=o["updated_at"] as? String,
              [start,end,created,updated].allSatisfy({TaskSnoozeValue.parse($0) != nil}),let archived=o["is_archived"] as? NSNumber,String(cString:archived.objCType)=="c" else {return nil}
        return Self(id:id,business:business,client:client,service:service,lead:integer("lead"),resource:integer("resource"),status:status,start_at:start,end_at:end,created_at:created,updated_at:updated,is_archived:archived.boolValue,raw:data)
    }
    public func matches(_ attempt:AppointmentLifecycleAttempt)->Bool {attempt.review.action.isGenericTerminal && attempt.authorization.key==nil && id==attempt.authorization.appointment && business==attempt.authorization.business && status==attempt.review.action.expectedStatus}
}
public struct FixtureAppointmentTerminalPort:SyntheticAppointmentLifecyclePort {
    private struct Row:Decodable,Sendable {let grant:SyntheticAppointmentTerminalGrant;let action:AppointmentLifecycleAction;let outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let mobile:FixtureAppointmentLifecyclePort;private let rows:[Row]
    public var grants:[SyntheticAppointmentLifecycleGrant] {mobile.grants}
    public var terminalGrants:[SyntheticAppointmentTerminalGrant] {rows.map(\.grant).reduce(into:[]) {if !$0.contains($1) {$0.append($1)}}}
    public init(directory:URL) {
        mobile=FixtureAppointmentLifecyclePort(directory:directory)
        if let data=try? Data(contentsOf:directory.appendingPathComponent("appointment-terminal.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}
    }
    public func execute(_ attempt:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome {
        if !attempt.review.action.isGenericTerminal {return try await mobile.execute(attempt)}
        let matches=rows.filter {$0.action==attempt.review.action && $0.grant.authorization(attempt.review.source,action:$0.action)==attempt.authorization}
        guard matches.count==1,let row=matches.first else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let status=row.status,let json=row.response_json else {return .unknown};return .response(status:status,data:Data(json.utf8))
    }
}
