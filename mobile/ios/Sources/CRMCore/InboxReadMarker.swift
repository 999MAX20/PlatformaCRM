import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxReadMarkerSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,unreadCount:Int64,updatedAt:String
    private init(_ context:InboxConversationFilesContext,_ count:Int64,_ updated:String) {self.context=context;unreadCount=count;updatedAt=updated}
    public var valid:Bool {context.valid && unreadCount>=0 && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.unreadCount==b.unreadCount && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {
        guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let count=DirectoryReadJSON.integer(row["unread_count"]),count>=0,let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil};return Self(c,count,updated)
    }
}
public enum InboxReadMarkerAction:String,Equatable,Sendable {case read="mark-read",unread="mark-unread"}
public struct SyntheticInboxReadMarkerGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,update:Bool
    public init(business:Int,conversation:Int,actor:Int,update:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;self.update=update}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxReadMarkerAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),update else {return nil};return SyntheticInboxReadMarkerAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxReadMarkerAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxReadMarkerReview:Equatable,Sendable {
    public let source:InboxReadMarkerSource,authorization:SyntheticInboxReadMarkerAuthorization,action:InboxReadMarkerAction,visit:Int
    public init(source:InboxReadMarkerSource,authorization:SyntheticInboxReadMarkerAuthorization,action:InboxReadMarkerAction,visit:Int) {self.source=source;self.authorization=authorization;self.action=action;self.visit=visit}
    public var valid:Bool {source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxReadMarkerAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxReadMarkerReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/\(review.action.rawValue)/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
public struct InboxReadMarkerReceipt:Equatable,Sendable {
    public let source:InboxReadMarkerSource
    public static func decode(_ data:Data,attempt a:InboxReadMarkerAttempt)->Self? {guard a.review.valid,let source=InboxReadMarkerSource.decode(data,context:a.review.source.context),(a.review.action == .read ? source.unreadCount==0:source.unreadCount>=1) else {return nil};return Self(source:source)}
}
public enum SyntheticInboxReadMarkerOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxReadMarkerPort:Sendable {var grants:[SyntheticInboxReadMarkerGrant] {get};func execute(_ attempt:InboxReadMarkerAttempt) async throws -> SyntheticInboxReadMarkerOutcome}
public enum InboxReadMarkerPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxReadMarkerRecord:Equatable,Sendable {public let attempt:InboxReadMarkerAttempt;public var phase:InboxReadMarkerPhase;public var result:InboxReadMarkerReceipt?}
public struct InboxReadMarkerLedger:Sendable {
    public private(set) var records:[InboxReadMarkerRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxReadMarkerAuthorization?)->InboxReadMarkerRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxReadMarkerReview)->InboxReadMarkerAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxReadMarkerAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxReadMarkerRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxReadMarkerAttempt,outcome:SyntheticInboxReadMarkerOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxReadMarkerReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxReadMarkerAuthorization,record:InboxReadMarkerRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxReadMarkerRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxReadMarkerSource}
public struct APIInboxReadMarkerRepository:InboxReadMarkerRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxReadMarkerSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxReadMarkerSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxReadMarkerPort:SyntheticInboxReadMarkerPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,action:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxReadMarkerGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxReadMarkerGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-read-marker.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxReadMarkerAttempt) async throws -> SyntheticInboxReadMarkerOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.action==a.review.action.rawValue}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxReadMarkerReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-read-marker.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
