import Foundation

public struct NotificationMarkReadContext:Equatable,Sendable {
    public let business:Int;public let notification:Int;public let epoch:Int
    public init(business:Int,notification:Int,epoch:Int) {self.business=business;self.notification=notification;self.epoch=epoch}
    public var valid:Bool {business>0 && notification>0 && epoch>0}
}
public struct NotificationMarkReadSource:Equatable,Sendable {
    public let context:NotificationMarkReadContext;public let generation:Int;public let notification:CRMNotification
    public init(context:NotificationMarkReadContext,generation:Int,notification:CRMNotification) {self.context=context;self.generation=generation;self.notification=notification}
    public var valid:Bool {context.valid && generation>0 && notification.id==context.notification && notification.valid && notification.readMarkerPresent}
}
public struct SyntheticNotificationMarkReadGrant:Decodable,Equatable,Sendable {
    public let business:Int;public let notification:Int;public let actor:Int;public let update:Bool
    public init(business:Int,notification:Int,actor:Int,update:Bool) {self.business=business;self.notification=notification;self.actor=actor;self.update=update}
    public func authorization(for context:NotificationMarkReadContext)->SyntheticNotificationMarkReadAuthorization? {
        guard context.valid,context.business==business,context.notification==notification,actor>0,update else {return nil}
        return SyntheticNotificationMarkReadAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticNotificationMarkReadAuthorization:Equatable,Sendable {
    public let context:NotificationMarkReadContext;public let actor:Int
    fileprivate init(context:NotificationMarkReadContext,actor:Int) {self.context=context;self.actor=actor}
}
public struct NotificationMarkReadReview:Equatable,Sendable {
    public let source:NotificationMarkReadSource;public let generation:Int
    public init(source:NotificationMarkReadSource,generation:Int) {self.source=source;self.generation=generation}
}
// Existing MobileNotificationMarkReadView envelope; no Business/actor/version echo.
public struct NotificationMarkReadReply:Decodable,Equatable,Sendable {
    public let ok:Bool;public let notification:CRMNotification;public let replayed:Bool
}
public struct NotificationMarkReadAttempt:Equatable,Sendable {
    // Local RAM correlation only, not Idempotency-Key or expected_updated_at.
    public let localID:Int;public let authorization:SyntheticNotificationMarkReadAuthorization;public let review:NotificationMarkReadReview
}
public enum SyntheticNotificationMarkReadOutcome:Sendable {case response(status:Int,reply:NotificationMarkReadReply),rejectedWithoutWrite,unknown}
public protocol SyntheticNotificationMarkReadPort:Sendable {
    var grants:[SyntheticNotificationMarkReadGrant] {get}
    func execute(_ attempt:NotificationMarkReadAttempt) async throws -> SyntheticNotificationMarkReadOutcome
}
public enum NotificationMarkReadPhase:Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct NotificationMarkReadRecord:Equatable,Sendable {public let attempt:NotificationMarkReadAttempt;public var phase:NotificationMarkReadPhase;public var reply:NotificationMarkReadReply?}
public struct NotificationMarkReadLedger:Sendable {
    public private(set) var records:[NotificationMarkReadRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:NotificationMarkReadContext)->String {"\(c.business)/\(c.notification)"}
    public func blocked(_ c:NotificationMarkReadContext)->Bool {active[key(c)] != nil}
    public func visible(_ authorization:SyntheticNotificationMarkReadAuthorization?)->NotificationMarkReadRecord? {
        guard let authorization,let index=active[key(authorization.context)] else {return nil};let record=records[index]
        return record.attempt.authorization==authorization ? record:nil
    }
    public mutating func begin(_ review:NotificationMarkReadReview,authorization:SyntheticNotificationMarkReadAuthorization)->NotificationMarkReadAttempt? {
        guard review.source.valid,review.generation>0,review.source.context==authorization.context,authorization.actor>0,!blocked(authorization.context) else {return nil}
        let a=NotificationMarkReadAttempt(localID:records.count+1,authorization:authorization,review:review)
        active[key(authorization.context)]=records.count;records.append(NotificationMarkReadRecord(attempt:a,phase:.pending));return a
    }
    public mutating func complete(_ attempt:NotificationMarkReadAttempt,outcome:SyntheticNotificationMarkReadOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        var phase:NotificationMarkReadPhase = .unknown;var accepted:NotificationMarkReadReply?
        switch outcome {
        case .unknown:break
        case .rejectedWithoutWrite:phase = .rejected
        case .response(let status,let reply):
            let n=reply.notification,s=attempt.review.source.notification
            if status==200,reply.ok,n.valid,n.id==attempt.authorization.context.notification,n.readMarkerPresent,n.read_at != nil,(s.read_at == nil || n.read_at==s.read_at),
               n.text==s.text,n.category==s.category,n.priority==s.priority,n.status==s.status,n.channel==s.channel,n.send_at==s.send_at,n.action_url==s.action_url,n.appointment_id==s.appointment_id {
                phase = .confirmed;accepted=reply
            }
        }
        records[i].phase=phase;records[i].reply=accepted
    }
    @discardableResult public mutating func acknowledge(_ authorization:SyntheticNotificationMarkReadAuthorization)->Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:key(authorization.context));return true
    }
}
public struct FixtureNotificationMarkReadPort:SyntheticNotificationMarkReadPort {
    private struct Scenario:Decodable,Sendable {let grant:SyntheticNotificationMarkReadGrant;let outcome:String;let reply:NotificationMarkReadReply?}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Scenario]}
    private let scenarios:[Scenario]
    public var grants:[SyntheticNotificationMarkReadGrant] {scenarios.map(\.grant)}
    public init(directory:URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("notification-mark-read.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {scenarios=c.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt:NotificationMarkReadAttempt) async throws -> SyntheticNotificationMarkReadOutcome {
        guard let s=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch s.outcome {case "rejected_without_write":return .rejectedWithoutWrite;case "response":guard let reply=s.reply else {return .unknown};return .response(status:200,reply:reply);default:return .unknown}
    }
}
