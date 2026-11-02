import Foundation

// Same independently loaded mobile GET source; the generic action response below is distinct.
public typealias NotificationMarkUnreadContext = NotificationMarkReadContext
public typealias NotificationMarkUnreadSource = NotificationMarkReadSource
public struct SyntheticNotificationMarkUnreadGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let notification:Int;public let actor:Int;public let update:Bool
    public init(business:Int,notification:Int,actor:Int,update:Bool) {self.business=business;self.notification=notification;self.actor=actor;self.update=update}
    public func authorization(for context:NotificationMarkUnreadContext)->SyntheticNotificationMarkUnreadAuthorization? {
        guard context.valid,context.business==business,context.notification==notification,actor>0,update else {return nil}
        return SyntheticNotificationMarkUnreadAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticNotificationMarkUnreadAuthorization:Equatable,Sendable {
    public let context:NotificationMarkUnreadContext;public let actor:Int
    fileprivate init(context:NotificationMarkUnreadContext,actor:Int) {self.context=context;self.actor=actor}
}
public struct NotificationMarkUnreadReview:Equatable,Sendable {
    public let source:NotificationMarkUnreadSource;public let generation:Int
    public init(source:NotificationMarkUnreadSource,generation:Int) {self.source=source;self.generation=generation}
}
// Existing generic NotificationSerializer, NOT the mobile ok/notification/replayed envelope.
// Decode just the exact subset needed for identity, null marker and preserved source fields.
public struct NotificationMarkUnreadReply:Decodable,Equatable,Sendable {
    public let id:Int;public let business:Int;public let text:String
    public let category:String;public let priority:String;public let status:String;public let channel:String
    public let send_at:String;public let action_url:String;public let appointment:Int?;public let updated_at:String
    private enum CodingKeys:String,CodingKey {case id,business,text,category,priority,status,channel,send_at,action_url,appointment,updated_at,read_at,is_read}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        guard c.contains(.read_at),try c.decodeNil(forKey:.read_at),c.contains(.appointment),try c.decode(Bool.self,forKey:.is_read)==false else {throw ReadFailure.invalidPayload}
        id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);text=try c.decode(String.self,forKey:.text)
        category=try c.decode(String.self,forKey:.category);priority=try c.decode(String.self,forKey:.priority);status=try c.decode(String.self,forKey:.status);channel=try c.decode(String.self,forKey:.channel)
        send_at=try c.decode(String.self,forKey:.send_at);action_url=try c.decode(String.self,forKey:.action_url);appointment=try c.decodeIfPresent(Int.self,forKey:.appointment);updated_at=try c.decode(String.self,forKey:.updated_at)
    }
    public func matches(_ source:NotificationMarkUnreadSource)->Bool {
        let n=source.notification
        return source.valid && id==source.context.notification && business==source.context.business && Appointment.instant(updated_at) != nil && (appointment == nil || appointment!>0) && text==n.text && category==n.category && priority==n.priority && status==n.status && channel==n.channel && send_at==n.send_at && action_url==n.action_url && appointment==n.appointment_id
    }
}
public struct NotificationMarkUnreadAttempt:Equatable,Sendable {
    // Local RAM correlation only, not Idempotency-Key or expected_updated_at.
    public let localID:Int;public let authorization:SyntheticNotificationMarkUnreadAuthorization;public let review:NotificationMarkUnreadReview
}
public enum SyntheticNotificationMarkUnreadOutcome:Sendable {case response(status:Int,reply:NotificationMarkUnreadReply),rejectedWithoutWrite,unknown}
public protocol SyntheticNotificationMarkUnreadPort:Sendable {
    var grants:[SyntheticNotificationMarkUnreadGrant] {get}
    func execute(_ attempt:NotificationMarkUnreadAttempt) async throws -> SyntheticNotificationMarkUnreadOutcome
}
public enum NotificationMarkUnreadPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct NotificationMarkUnreadRecord:Equatable,Sendable {public let attempt:NotificationMarkUnreadAttempt;public var phase:NotificationMarkUnreadPhase;public var reply:NotificationMarkUnreadReply?}
public struct NotificationMarkUnreadLedger:Sendable {
    public private(set) var records:[NotificationMarkUnreadRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:NotificationMarkUnreadContext)->String {"\(c.business)/\(c.notification)"}
    public func blocked(_ c:NotificationMarkUnreadContext)->Bool {active[key(c)] != nil}
    public func visible(_ authorization:SyntheticNotificationMarkUnreadAuthorization?)->NotificationMarkUnreadRecord? {
        guard let authorization,let index=active[key(authorization.context)] else {return nil};let record=records[index]
        return record.attempt.authorization==authorization ? record:nil
    }
    public mutating func begin(_ review:NotificationMarkUnreadReview,authorization:SyntheticNotificationMarkUnreadAuthorization)->NotificationMarkUnreadAttempt? {
        guard review.source.valid,review.generation>0,review.source.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=NotificationMarkUnreadAttempt(localID:records.count+1,authorization:authorization,review:review)
        active[key(authorization.context)]=records.count;records.append(NotificationMarkUnreadRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:NotificationMarkUnreadAttempt,outcome:SyntheticNotificationMarkUnreadOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:NotificationMarkUnreadPhase = .unknown;var accepted:NotificationMarkUnreadReply?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let reply):
            if status==200,reply.matches(attempt.review.source) {phase = .confirmed;accepted=reply}
        }
        records[i].phase=phase;records[i].reply=accepted
    }
    @discardableResult public mutating func acknowledge(_ authorization:SyntheticNotificationMarkUnreadAuthorization)->Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:key(authorization.context));return true
    }
}
public struct FixtureNotificationMarkUnreadPort:SyntheticNotificationMarkUnreadPort {
    private struct Scenario:Decodable,Sendable {let grant:SyntheticNotificationMarkUnreadGrant;let outcome:String;let reply:NotificationMarkUnreadReply?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Scenario]}
    private let scenarios:[Scenario]
    public var grants:[SyntheticNotificationMarkUnreadGrant] {scenarios.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("notification-mark-unread.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {scenarios=c.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt:NotificationMarkUnreadAttempt) async throws -> SyntheticNotificationMarkUnreadOutcome {
        guard let s=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch s.outcome {case "rejected_without_write":return .rejectedWithoutWrite;case "response":guard let reply=s.reply else {return .unknown};return .response(status:200,reply:reply);default:return .unknown}
    }
}
