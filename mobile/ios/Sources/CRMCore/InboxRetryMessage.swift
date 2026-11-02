import Foundation

// Independently observed generic message, not UPDATE authority or an outcome proof.
public struct InboxRetryMessageSource:Equatable,Sendable {
    public let context:InboxMessageFilesContext
    public let direction:String,senderType:String,text:String,status:String
    private init(_ c:InboxMessageFilesContext,_ direction:String,_ sender:String,_ text:String,_ status:String) {context=c;self.direction=direction;senderType=sender;self.text=text;self.status=status}
    public var valid:Bool {context.valid}
    public var eligible:Bool {valid && direction=="outbound" && ["client","bot","manager","ai"].contains(senderType) && ["received","queued","failed"].contains(status)}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && zip([a.direction,a.senderType,a.text,a.status],[b.direction,b.senderType,b.text,b.status]).allSatisfy {SourceTextIdentity.same($0.0,$0.1)}}
    public static func decode(_ data:Data,context c:InboxMessageFilesContext)->Self? {guard let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {return nil};return decode(row,context:c)}
    static func decode(_ row:[String:Any],context c:InboxMessageFilesContext)->Self? {
        guard c.valid,DirectoryReadJSON.integer(row["id"])==Int64(c.message),DirectoryReadJSON.integer(row["conversation"])==Int64(c.conversation),let direction=row["direction"] as? String,let sender=row["sender_type"] as? String,let text=row["text"] as? String,let status=row["status"] as? String else {return nil}
        return Self(c,direction,sender,text,status)
    }
}
public struct InboxRetryOwner:Equatable,Sendable {
    public let business:Int,conversation:Int,epoch:Int
    public init(business:Int,conversation:Int,epoch:Int) {self.business=business;self.conversation=conversation;self.epoch=epoch}
    public var valid:Bool {business>0 && business<=Int(Int32.max) && conversation>0 && conversation<=Int(Int32.max) && epoch>0}
}
public struct SyntheticInboxRetryGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,update:Bool
    public init(business:Int,conversation:Int,actor:Int,update:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update}
    public func authorization(for owner:InboxRetryOwner)->SyntheticInboxRetryAuthorization? {guard owner.valid,business==owner.business,conversation==owner.conversation,actor>0,update else {return nil};return SyntheticInboxRetryAuthorization(owner:owner,actor:actor)}
}
public struct SyntheticInboxRetryAuthorization:Equatable,Sendable {public let owner:InboxRetryOwner;public let actor:Int;fileprivate init(owner:InboxRetryOwner,actor:Int) {self.owner=owner;self.actor=actor}}
public struct InboxRetryReview:Equatable,Sendable {
    public let source:InboxRetryMessageSource,authorization:SyntheticInboxRetryAuthorization,visit:Int
    public init(source:InboxRetryMessageSource,authorization:SyntheticInboxRetryAuthorization,visit:Int) {self.source=source;self.authorization=authorization;self.visit=visit}
    public var valid:Bool {source.eligible && visit>0 && authorization.owner.valid && authorization.actor>0 && source.context.business==authorization.owner.business && source.context.conversation==authorization.owner.conversation && source.context.epoch==authorization.owner.epoch}
}
public struct InboxRetryAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxRetryReview
    private let body:Data
    init(localID:Int,review:InboxRetryReview) {self.localID=localID;self.review=review;body=Data("{\"message_id\":\(review.source.context.message)}".utf8)}
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/retry-message/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {body}
}
public struct InboxRetryReceipt:Equatable,Sendable {
    public let id:Int,conversation:Int,retryOf:Int,status:String,text:String,senderType:String,createdAt:String,sentAt:InboxObservedText
    private init(_ id:Int,_ conversation:Int,_ retryOf:Int,_ status:String,_ text:String,_ sender:String,_ created:String,_ sent:InboxObservedText) {self.id=id;self.conversation=conversation;self.retryOf=retryOf;self.status=status;self.text=text;senderType=sender;createdAt=created;sentAt=sent}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.conversation==b.conversation && a.retryOf==b.retryOf && a.sentAt==b.sentAt && zip([a.status,a.text,a.senderType,a.createdAt],[b.status,b.text,b.senderType,b.createdAt]).allSatisfy {SourceTextIdentity.same($0.0,$0.1)}}
    public static func decode(_ data:Data,source s:InboxRetryMessageSource)->Self? {
        guard s.eligible,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let id=DirectoryReadJSON.integer(row["id"]),id>0,id<=Int64(Int32.max),id != Int64(s.context.message),DirectoryReadJSON.integer(row["conversation"])==Int64(s.context.conversation),row["direction"] as? String=="outbound",let sender=row["sender_type"] as? String,SourceTextIdentity.same(sender,s.senderType),let text=row["text"] as? String,SourceTextIdentity.same(text,s.text),let status=row["status"] as? String,["queued","sent","failed"].contains(status),let payload=row["payload_json"] as? [String:Any],DirectoryReadJSON.integer(payload["retry_of_message_id"])==Int64(s.context.message),let created=row["created_at"] as? String,!created.isEmpty,row.keys.contains("sent_at"),let sent=InboxObservedText.decode(row,key:"sent_at") else {return nil}
        return Self(Int(id),s.context.conversation,s.context.message,status,text,sender,created,sent)
    }
}
public enum SyntheticInboxRetryOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxRetryPort:Sendable {var grants:[SyntheticInboxRetryGrant] {get};func execute(_ attempt:InboxRetryAttempt) async throws -> SyntheticInboxRetryOutcome}
public enum InboxRetryPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxRetryRecord:Equatable,Sendable {public let attempt:InboxRetryAttempt;public var phase:InboxRetryPhase;public var result:InboxRetryReceipt?}
public struct InboxRetryLedger:Sendable {
    public private(set) var records:[InboxRetryRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ b:Int,_ c:Int)->String {"\(b)/\(c)"}
    public func blocked(business:Int,conversation:Int)->Bool {active[key(business,conversation)] != nil}
    public func visible(_ auth:SyntheticInboxRetryAuthorization?)->InboxRetryRecord? {guard let auth,auth.owner.valid,auth.actor>0,let i=active[key(auth.owner.business,auth.owner.conversation)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxRetryReview)->InboxRetryAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil}
        let a=InboxRetryAttempt(localID:records.count+1,review:review);active[key(review.source.context.business,review.source.context.conversation)]=records.count;records.append(InboxRetryRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ attempt:InboxRetryAttempt,outcome:SyntheticInboxRetryOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==attempt}),records[i].phase == .pending else {return}
        switch outcome {
        case .rejectedWithoutWrite:records[i].phase = .rejected
        case .unknown:records[i].phase = .unknown
        case .response(let status,let data):if status==201,let receipt=InboxRetryReceipt.decode(data,source:attempt.review.source) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}
        }
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxRetryAuthorization,record:InboxRetryRecord)->Bool {
        guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.owner.business,auth.owner.conversation));return true
    }
}
// Explicit synthetic fixture outcomes; no HTTP/provider command implementation.
public struct FixtureInboxRetryPort:SyntheticInboxRetryPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,message_id:Int,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxRetryGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxRetryGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-retry-message.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ attempt:InboxRetryAttempt) async throws -> SyntheticInboxRetryOutcome {
        let s=attempt.review.source,c=s.context;guard attempt.review.valid,grants.compactMap({$0.authorization(for:attempt.review.authorization.owner)}).contains(attempt.review.authorization),let row=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.message_id==c.message}) else {return .rejectedWithoutWrite}
        if row.outcome=="response",let status=row.status,let raw=row.response_json {return .response(status:status,data:Data(raw.utf8))};return row.outcome=="rejected" ? .rejectedWithoutWrite:.unknown
    }
}

public struct FixtureInboxRetryReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String;let query:[String:String];let response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-retry-message.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {guard let row=rows.first(where:{$0.path==request.path && $0.query==request.query}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
