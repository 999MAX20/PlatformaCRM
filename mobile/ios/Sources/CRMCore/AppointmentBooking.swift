import Foundation

// Local entry identity and links only; no CREATE grant, inherited fields or server version.
public struct AppointmentBookingSource:Equatable,Sendable {
    public let read:DetailSelection;public let epoch:Int,clientID:Int,serviceID:Int;public let resourceID:Int?
    public init(read:DetailSelection,epoch:Int,clientID:Int,serviceID:Int,resourceID:Int?) {self.read=read;self.epoch=epoch;self.clientID=clientID;self.serviceID=serviceID;self.resourceID=resourceID}
    public var valid:Bool {epoch>0 && read.revision>0 && read.scope.revision>0 && [read.scope.business.id,read.id,clientID,serviceID].allSatisfy {$0>0 && $0<=Int(Int32.max)} && (resourceID==nil || resourceID!>0 && resourceID!<=Int(Int32.max))}
}
public struct AppointmentBookingInput:Equatable,Sendable {
    // Existing unsent, independently scoped Client choice; its Task name grants no authority.
    public let client:TaskDraftClientChoice;public let service:AppointmentReferenceDetail;public let resource:AppointmentRescheduleResource;public let start:TaskSnoozeValue;public let directory:AppointmentBookingDirectorySelection?;public let clientSelection:AppointmentBookingClientSelection?
    public init?(source:AppointmentBookingSource,client:TaskDraftClientChoice,service:AppointmentReferenceDetail,resource:AppointmentRescheduleResource,startAt:String,directory:AppointmentBookingDirectorySelection?=nil,clientSelection:AppointmentBookingClientSelection?=nil) {
        guard source.valid,client.valid(for:source.read.scope.business.id),client.id==(clientSelection?.choice.id ?? source.clientID),service.valid(for:source.read.scope.business.id,id:directory?.service?.id ?? source.serviceID),let start=TaskSnoozeValue.parse(startAt),start.microseconds%1000==0 else {return nil}
        if let clientSelection {guard clientSelection.matches(source:source,client:client) else {return nil}}
        if let directory {guard directory.matches(source:source,service:service,resource:resource) else {return nil}}
        if case .linked(let value)=resource {guard (directory?.resource?.id ?? source.resourceID)==value.id,value.valid(for:source.read.scope.business.id,id:value.id) else {return nil}}
        self.client=client;self.service=service;self.resource=resource;self.start=start;self.directory=directory;self.clientSelection=clientSelection
    }
    public func valid(for source:AppointmentBookingSource)->Bool {Self(source:source,client:client,service:service,resource:resource,startAt:start.raw,directory:directory,clientSelection:clientSelection)==self}
    public func body(business:Int)->Data? {guard client.valid(for:business),service.business==business else {return nil};return try? JSONSerialization.data(withJSONObject:["business":business,"client":client.id,"service":service.id,"start_at":start.raw,"resource":resource.id.map {$0 as Any} ?? NSNull()],options:.sortedKeys)}
}
public struct SyntheticAppointmentBookingGrant:Codable,Equatable,Sendable {
    public let business:Int,from_appointment:Int,actor:Int;public let create:Bool
    public init(business:Int,fromAppointment:Int,actor:Int,create:Bool) {self.business=business;from_appointment=fromAppointment;self.actor=actor;self.create=create}
    public func authorization(_ source:AppointmentBookingSource)->SyntheticAppointmentBookingAuthorization? {guard source.valid,business==source.read.scope.business.id,from_appointment==source.read.id,actor>0,create else {return nil};return SyntheticAppointmentBookingAuthorization(business:business,fromAppointment:from_appointment,epoch:source.epoch,actor:actor)}
}
public struct SyntheticAppointmentBookingAuthorization:Equatable,Sendable {
    public let business:Int,fromAppointment:Int,epoch:Int,actor:Int
    fileprivate init(business:Int,fromAppointment:Int,epoch:Int,actor:Int) {self.business=business;self.fromAppointment=fromAppointment;self.epoch=epoch;self.actor=actor}
}
public struct AppointmentBookingReview:Equatable,Sendable {public let source:AppointmentBookingSource;public let input:AppointmentBookingInput;public let visit:Int;public init(source:AppointmentBookingSource,input:AppointmentBookingInput,visit:Int) {self.source=source;self.input=input;self.visit=visit}}
public struct AppointmentBookingAttempt:Equatable,Sendable,CustomStringConvertible {
    public let localID:Int;public let authorization:SyntheticAppointmentBookingAuthorization;public let review:AppointmentBookingReview;public let body:Data
    public var path:String {"/api/appointments/"};public var method:String {"POST"};public var query:[String:String] {[:]}
    public var description:String {"AppointmentBookingAttempt(localID: \(localID))"}
}
public enum SyntheticAppointmentBookingOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticAppointmentBookingPort:Sendable {var grants:[SyntheticAppointmentBookingGrant] {get};func execute(_ attempt:AppointmentBookingAttempt) async throws -> SyntheticAppointmentBookingOutcome}
// Reuse the existing plain AppointmentSerializer lens, not its terminal-action matcher.
public struct AppointmentBookingReceipt:Equatable,Sendable {
    public let appointment:AppointmentTerminalReceipt
    public static func decode(_ data:Data)->Self? {AppointmentTerminalReceipt.decode(data).map {Self(appointment:$0)}}
    public func matches(_ attempt:AppointmentBookingAttempt)->Bool {let p=appointment,i=attempt.review.input;return p.business==attempt.authorization.business && p.client==i.client.id && p.service==i.service.id && p.resource==i.resource.id && TaskSnoozeValue.parse(p.start_at)?.microseconds==i.start.microseconds}
}
public enum AppointmentBookingPhase:Equatable,Sendable {case pending,acceptedFixture,rejectedFixture,unknown}
public struct AppointmentBookingRecord:Equatable,Sendable {public let attempt:AppointmentBookingAttempt;public var phase:AppointmentBookingPhase;public var receipt:AppointmentBookingReceipt?}
public struct AppointmentBookingLedger:Sendable {
    public private(set) var records:[AppointmentBookingRecord]=[];private var active:[String:Int]=[:];private var consumed:Set<String>=[]
    public init() {}
    private func target(_ s:AppointmentBookingSource)->String {"\(s.read.scope.business.id)/\(s.read.id)"}
    public func blocked(_ s:AppointmentBookingSource)->Bool {active[target(s)] != nil}
    public func used(_ s:AppointmentBookingSource)->Bool {consumed.contains(target(s))}
    public func visible(_ a:SyntheticAppointmentBookingAuthorization)->AppointmentBookingRecord? {guard let i=active["\(a.business)/\(a.fromAppointment)"],records[i].attempt.authorization==a else {return nil};return records[i]}
    public mutating func begin(_ review:AppointmentBookingReview,authorization a:SyntheticAppointmentBookingAuthorization)->AppointmentBookingAttempt? {
        let s=review.source;guard s.valid,review.visit>0,review.input.valid(for:s),a.business==s.read.scope.business.id,a.fromAppointment==s.read.id,a.epoch==s.epoch,a.actor>0,!blocked(s),!used(s),let body=review.input.body(business:a.business) else {return nil}
        let attempt=AppointmentBookingAttempt(localID:records.count+1,authorization:a,review:review,body:body);active[target(s)]=records.count;records.append(AppointmentBookingRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt:AppointmentBookingAttempt,outcome:SyntheticAppointmentBookingOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return};var phase:AppointmentBookingPhase = .unknown;var receipt:AppointmentBookingReceipt?
        switch outcome {case .unknown:break;case .rejectedWithoutWrite:phase = .rejectedFixture
        case .response(let status,let data):if status==201,let value=AppointmentBookingReceipt.decode(data),value.matches(attempt) {phase = .acceptedFixture;receipt=value}}
        records[i].phase=phase;records[i].receipt=receipt
    }
    @discardableResult public mutating func acknowledge(_ record:AppointmentBookingRecord)->Bool {let s=record.attempt.review.source;guard let i=active[target(s)],records[i]==record,record.phase == .acceptedFixture || record.phase == .rejectedFixture else {return false};if record.phase == .acceptedFixture {consumed.insert(target(s))};active.removeValue(forKey:target(s));return true}
}
public struct FixtureAppointmentBookingPort:SyntheticAppointmentBookingPort {
    private struct Input:Decodable,Sendable {let client:Int,service:Int;let resource:Int?;let start_at:String
        private enum Keys:String,CodingKey {case client,service,resource,start_at}
        init(from decoder:any Decoder) throws {let c=try decoder.container(keyedBy:Keys.self);client=try c.decode(Int.self,forKey:.client);service=try c.decode(Int.self,forKey:.service);resource=try c.decode(Int?.self,forKey:.resource);start_at=try c.decode(String.self,forKey:.start_at)}
    }
    private struct Row:Decodable,Sendable {let grant:SyntheticAppointmentBookingGrant;let input:Input;let outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]};private let rows:[Row]
    public var grants:[SyntheticAppointmentBookingGrant] {rows.map(\.grant)}
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("appointment-booking.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func execute(_ attempt:AppointmentBookingAttempt) async throws -> SyntheticAppointmentBookingOutcome {
        let matches=rows.filter {$0.grant.authorization(attempt.review.source)==attempt.authorization};guard matches.count==1,let row=matches.first else {return .unknown};let i=attempt.review.input
        guard row.input.client==i.client.id,row.input.service==i.service.id,row.input.resource==i.resource.id,SourceTextIdentity.same(row.input.start_at,i.start.raw) else {return .unknown}
        if row.outcome=="rejected_without_write" {return .rejectedWithoutWrite};guard row.outcome=="response",let status=row.status,let json=row.response_json else {return .unknown};return .response(status:status,data:Data(json.utf8))
    }
}
