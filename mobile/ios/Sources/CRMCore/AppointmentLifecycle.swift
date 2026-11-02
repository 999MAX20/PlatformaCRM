import Foundation

public enum AppointmentLifecycleAction:String,Codable,CaseIterable,Hashable,Sendable {case confirm,cancel,reschedule,complete;case noShow="no-show"
    public var expectedStatus:String? {switch self {case .confirm:"confirmed";case .cancel:"cancelled";case .reschedule:nil;case .complete:"completed";case .noShow:"no_show"}}
    public var isGenericTerminal:Bool {self == .complete || self == .noShow}
}
// Current read identity only, never a version/UPDATE grant.
public struct AppointmentLifecycleSource:Equatable,Sendable {
    public let read:DetailSelection;public let epoch:Int;public let appointment:Appointment;public let linkedResourceID:Int?
    public init(read:DetailSelection,epoch:Int,appointment:Appointment,linkedResourceID:Int?=nil) {self.read=read;self.epoch=epoch;self.appointment=appointment;self.linkedResourceID=linkedResourceID}
    public var valid:Bool {epoch>0 && read.revision>0 && read.scope.revision>0 && read.scope.business.id>0 && appointment.id>0 && appointment.id==read.id && (linkedResourceID==nil || linkedResourceID!>0 && linkedResourceID!<=Int(Int32.max))}
    public static func ==(a:Self,b:Self)->Bool {a.read==b.read && a.epoch==b.epoch && a.linkedResourceID==b.linkedResourceID && a.appointment.id==b.appointment.id && a.appointment.client_id==b.appointment.client_id && SourceTextIdentity.same(a.appointment.title,b.appointment.title) && SourceTextIdentity.same(a.appointment.status,b.appointment.status) && SourceTextIdentity.same(a.appointment.start_at,b.appointment.start_at) && SourceTextIdentity.same(a.appointment.end_at,b.appointment.end_at)}
}
public struct SyntheticAppointmentLifecycleGrant:Codable,Equatable,Sendable {
    public let business:Int,appointment:Int,actor:Int;public let update:Bool;public let confirm_key:String?,cancel_key:String?,reschedule_key:String?
    public init(business:Int,appointment:Int,actor:Int,update:Bool,confirmKey:String?,cancelKey:String?,rescheduleKey:String?=nil) {self.business=business;self.appointment=appointment;self.actor=actor;self.update=update;confirm_key=confirmKey;cancel_key=cancelKey;reschedule_key=rescheduleKey}
    public static func ==(a:Self,b:Self)->Bool {a.business==b.business && a.appointment==b.appointment && a.actor==b.actor && a.update==b.update && SourceTextIdentity.same(a.confirm_key,b.confirm_key) && SourceTextIdentity.same(a.cancel_key,b.cancel_key) && SourceTextIdentity.same(a.reschedule_key,b.reschedule_key)}
    public func authorization(_ source:AppointmentLifecycleSource,action:AppointmentLifecycleAction)->SyntheticAppointmentLifecycleAuthorization? {
        guard source.valid,business==source.read.scope.business.id,appointment==source.read.id,actor>0,update else {return nil}
        let provided:String?;switch action {case .confirm:provided=confirm_key;case .cancel:provided=cancel_key;case .reschedule:provided=reschedule_key;case .complete,.noShow:provided=nil}
        guard let key=provided,!SourceTextTrim.pythonStrip(key).isEmpty else {return nil}
        return SyntheticAppointmentLifecycleAuthorization(business:business,appointment:appointment,epoch:source.epoch,actor:actor,action:action,key:key)
    }
}
public struct SyntheticAppointmentLifecycleAuthorization:Equatable,Sendable {
    public let business:Int,appointment:Int,epoch:Int,actor:Int;public let action:AppointmentLifecycleAction;public let key:String?
    public static func ==(a:Self,b:Self)->Bool {a.business==b.business && a.appointment==b.appointment && a.epoch==b.epoch && a.actor==b.actor && a.action==b.action && SourceTextIdentity.same(a.key,b.key)}
    init(business:Int,appointment:Int,epoch:Int,actor:Int,action:AppointmentLifecycleAction,key:String?) {self.business=business;self.appointment=appointment;self.epoch=epoch;self.actor=actor;self.action=action;self.key=key}
}
public struct AppointmentLifecycleReview:Equatable,Sendable {public let source:AppointmentLifecycleSource;public let action:AppointmentLifecycleAction;public let visit:Int;public let reschedule:AppointmentRescheduleInput?;public init(source:AppointmentLifecycleSource,action:AppointmentLifecycleAction,visit:Int,reschedule:AppointmentRescheduleInput?=nil) {self.source=source;self.action=action;self.visit=visit;self.reschedule=reschedule}}
public struct AppointmentLifecycleAttempt:Equatable,Sendable,CustomStringConvertible {
    public let localID:Int;public let authorization:SyntheticAppointmentLifecycleAuthorization;public let review:AppointmentLifecycleReview;public let body:Data
    public var path:String {"\(authorization.action.isGenericTerminal ? "/api/appointments/":"/api/mobile/v1/appointments/")\(authorization.appointment)/\(authorization.action.rawValue)/"}
    public var query:[String:String] {authorization.action.isGenericTerminal ? ["business":String(authorization.business)]:[:]}
    public var method:String {"POST"}
    public var description:String {"AppointmentLifecycleAttempt(localID: \(localID))"}
}
public enum SyntheticAppointmentLifecycleOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticAppointmentLifecyclePort:Sendable {var grants:[SyntheticAppointmentLifecycleGrant] {get};var terminalGrants:[SyntheticAppointmentTerminalGrant] {get};func execute(_ attempt:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome}
public extension SyntheticAppointmentLifecyclePort {var terminalGrants:[SyntheticAppointmentTerminalGrant] {[]}}
// Exact mobile_appointment_item action response; no Business/version/resource/recovery field.
public struct AppointmentLifecycleReceipt:Decodable,Equatable,Sendable {
    public struct Item:Decodable,Equatable,Sendable {
        public let id:Int;public let title:String,status:String;public let client_id:Int?,lead_id:Int?,service_id:Int?;public let start_at:String,end_at:String,href:String
        private enum Keys:String,CodingKey {case id,title,status,client_id,lead_id,service_id,start_at,end_at,href}
        public init(from decoder:any Decoder) throws {
            let c=try decoder.container(keyedBy:Keys.self);id=try c.decode(Int.self,forKey:.id);title=try c.decode(String.self,forKey:.title);status=try c.decode(String.self,forKey:.status)
            client_id=try c.decode(Int?.self,forKey:.client_id);lead_id=try c.decode(Int?.self,forKey:.lead_id);service_id=try c.decode(Int?.self,forKey:.service_id)
            start_at=try c.decode(String.self,forKey:.start_at);end_at=try c.decode(String.self,forKey:.end_at);href=try c.decode(String.self,forKey:.href)
        }
    }
    public let ok:Bool;public let appointment:Item;public let replayed:Bool
    public func matches(_ attempt:AppointmentLifecycleAttempt)->Bool {
        guard !attempt.review.action.isGenericTerminal,ok,appointment.id==attempt.authorization.appointment,appointment.href=="/app/calendar?appointment=\(appointment.id)",
              [appointment.client_id,appointment.lead_id,appointment.service_id].allSatisfy({$0==nil || $0!>0}),Appointment.instant(appointment.start_at) != nil,Appointment.instant(appointment.end_at) != nil else {return false}
        if attempt.review.action == .reschedule {
            guard let input=attempt.review.reschedule,input.valid(for:attempt.review.source) else {return false}
            return SourceTextIdentity.same(appointment.status,attempt.review.source.appointment.status) && TaskSnoozeValue.parse(appointment.start_at)?.microseconds==input.start.microseconds
        }
        return appointment.status==attempt.authorization.action.expectedStatus
    }
}
public enum AppointmentLifecyclePhase:Equatable,Sendable {case pending,acceptedFixture,rejectedFixture,unknown}
public struct AppointmentLifecycleRecord:Equatable,Sendable {public let attempt:AppointmentLifecycleAttempt;public var phase:AppointmentLifecyclePhase;public var receipt:AppointmentLifecycleReceipt?;public var terminalReceipt:AppointmentTerminalReceipt? = nil}
public struct AppointmentLifecycleLedger:Sendable {
    public private(set) var records:[AppointmentLifecycleRecord]=[]
    private var active:[String:Int]=[:];private var consumed:Set<String>=[]
    public init() {}
    private func target(_ s:AppointmentLifecycleSource)->String {"\(s.read.scope.business.id)/\(s.read.id)"}
    private func actionKey(_ s:AppointmentLifecycleSource,_ action:AppointmentLifecycleAction)->String {target(s)+"/"+action.rawValue}
    public func blocked(_ s:AppointmentLifecycleSource)->Bool {active[target(s)] != nil}
    public func used(_ s:AppointmentLifecycleSource,_ action:AppointmentLifecycleAction)->Bool {consumed.contains(actionKey(s,action))}
    public func visible(_ a:SyntheticAppointmentLifecycleAuthorization)->AppointmentLifecycleRecord? {
        guard let row=active["\(a.business)/\(a.appointment)"],records[row].attempt.authorization==a else {return nil};return records[row]
    }
    public mutating func begin(_ review:AppointmentLifecycleReview,authorization a:SyntheticAppointmentLifecycleAuthorization)->AppointmentLifecycleAttempt? {
        let s=review.source
        guard s.valid,review.visit>0,a.business==s.read.scope.business.id,a.appointment==s.read.id,a.epoch==s.epoch,a.action==review.action,!blocked(s),!used(s,review.action) else {return nil}
        guard a.actor>0 else {return nil}
        if review.action.isGenericTerminal {guard a.key==nil else {return nil}} else {guard let key=a.key,!SourceTextTrim.pythonStrip(key).isEmpty else {return nil}}
        var fields:[String:Any]=review.action.isGenericTerminal ? [:]:["business":a.business]
        if review.action == .reschedule {
            guard let input=review.reschedule,input.valid(for:s) else {return nil}
            fields["start_at"]=input.start.raw;fields["reason"]=input.reason;fields["resource"]=input.resource.id.map { $0 as Any } ?? NSNull()
        } else if review.reschedule != nil {return nil}
        guard let body=try? JSONSerialization.data(withJSONObject:fields,options:.sortedKeys) else {return nil}
        let attempt=AppointmentLifecycleAttempt(localID:records.count+1,authorization:a,review:review,body:body);active[target(s)]=records.count;records.append(AppointmentLifecycleRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt:AppointmentLifecycleAttempt,outcome:SyntheticAppointmentLifecycleOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:AppointmentLifecyclePhase = .unknown;var receipt:AppointmentLifecycleReceipt?;var terminal:AppointmentTerminalReceipt?
        switch outcome {case .unknown:break;case .rejectedWithoutWrite:phase = .rejectedFixture
        case .response(let status,let bytes):
            if status==200 {
                if attempt.review.action.isGenericTerminal {if let value=AppointmentTerminalReceipt.decode(bytes),value.matches(attempt) {phase = .acceptedFixture;terminal=value}}
                else if let value=try? JSONDecoder().decode(AppointmentLifecycleReceipt.self,from:bytes),value.matches(attempt) {phase = .acceptedFixture;receipt=value}
            }}
        records[i].phase=phase;records[i].receipt=receipt;records[i].terminalReceipt=terminal
    }
    @discardableResult public mutating func acknowledge(_ record:AppointmentLifecycleRecord)->Bool {
        let s=record.attempt.review.source;guard let i=active[target(s)],records[i]==record,record.phase == .acceptedFixture || record.phase == .rejectedFixture else {return false}
        if record.phase == .acceptedFixture {consumed.insert(actionKey(s,record.attempt.review.action))};active.removeValue(forKey:target(s));return true
    }
}
public struct FixtureAppointmentLifecyclePort:SyntheticAppointmentLifecyclePort {
    private struct Expected:Decodable,Sendable {
        let start_at:String,reason_raw:String;let resource:Int?
        private enum Keys:String,CodingKey {case start_at,reason_raw,resource}
        init(from decoder:any Decoder) throws {let c=try decoder.container(keyedBy:Keys.self);start_at=try c.decode(String.self,forKey:.start_at);reason_raw=try c.decode(String.self,forKey:.reason_raw);resource=try c.decode(Int?.self,forKey:.resource)}
    }
    private struct Row:Decodable,Sendable {let grant:SyntheticAppointmentLifecycleGrant;let action:AppointmentLifecycleAction;let outcome:String;let status:Int?;let response_json:String?;let input:Expected?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public var grants:[SyntheticAppointmentLifecycleGrant] {rows.reduce(into:[]) {if !$0.contains($1.grant) {$0.append($1.grant)}}}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("appointment-lifecycle.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:AppointmentLifecycleAttempt) async throws -> SyntheticAppointmentLifecycleOutcome {
        let matches=rows.filter {$0.action==attempt.review.action && $0.grant.authorization(attempt.review.source,action:$0.action)==attempt.authorization};guard matches.count==1,let row=matches.first else {return .unknown}
        if attempt.review.action == .reschedule {guard let input=attempt.review.reschedule,let expected=row.input,SourceTextIdentity.same(input.start.raw,expected.start_at),SourceTextIdentity.same(input.rawReason,expected.reason_raw),input.resource.id==expected.resource else {return .unknown}}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite}
        guard row.outcome=="response",let status=row.status,let body=row.response_json else {return .unknown};return .response(status:status,data:Data(body.utf8))
    }
}
