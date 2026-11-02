import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxLinkDealSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext
    public let deal:Int?,client:Int?,lead:Int?,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ deal:Int?,_ client:Int?,_ lead:Int?,_ updated:String) {context=c;self.deal=deal;self.client=client;self.lead=lead;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty && [deal,client,lead].allSatisfy {$0==nil || ($0!>0 && $0!<=Int(Int32.max))}}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.deal==b.deal && a.client==b.client && a.lead==b.lead && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {
        guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        var links:[Int?]=[]
        for key in ["deal","lead"] {guard let value=row[key] else {return nil};if value is NSNull {links.append(nil)} else {guard let n=DirectoryReadJSON.integer(value),n>0,n<=Int64(Int32.max) else {return nil};links.append(Int(n))}}
        switch TaskCreateClientRead.decode(data) {case .unknown:return nil;case .notSet:return Self(c,links[0],nil,links[1],updated);case .client(let id):return Self(c,links[0],id,links[1],updated)}
    }
}
// Qualified generic Deal VIEW reference is independent of conversation GET and UPDATE grant.
public struct InboxLinkDealCandidate:Equatable,Sendable {
    public let source:InboxLinkDealSource
    public let reference:QualifiedDealReference
    public init?(source:InboxLinkDealSource,reference:QualifiedDealReference) {guard source.valid,reference.valid,reference.context==source.context else {return nil};self.source=source;self.reference=reference}
    public var valid:Bool {source.valid && reference.valid && reference.context==source.context}
}
public struct SyntheticInboxLinkDealGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,deals_update:Bool,conversations_update:Bool
    public init(business:Int,conversation:Int,actor:Int,dealsUpdate:Bool,conversationsUpdate:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;deals_update=dealsUpdate;conversations_update=conversationsUpdate}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxLinkDealAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),deals_update,conversations_update else {return nil};return SyntheticInboxLinkDealAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxLinkDealAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxLinkDealReview:Equatable,Sendable {
    public let source:InboxLinkDealSource,authorization:SyntheticInboxLinkDealAuthorization,candidate:InboxLinkDealCandidate,visit:Int
    public init(source:InboxLinkDealSource,authorization:SyntheticInboxLinkDealAuthorization,candidate:InboxLinkDealCandidate,visit:Int) {self.source=source;self.authorization=authorization;self.candidate=candidate;self.visit=visit}
    public var valid:Bool {source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxLinkDealAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxLinkDealReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/link-deal/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{\"deal_id\":\(review.candidate.reference.source.id)}".utf8)}
}
public struct InboxLinkDealReceipt:Equatable,Sendable {
    public let source:InboxLinkDealSource
    public static func decode(_ data:Data,attempt a:InboxLinkDealAttempt)->Self? {
        guard a.review.valid,let source=InboxLinkDealSource.decode(data,context:a.review.source.context),source.deal==a.review.candidate.reference.source.id,source.client==(a.review.source.client ?? a.review.candidate.reference.source.client),source.lead==(a.review.source.lead ?? a.review.candidate.reference.source.lead) else {return nil};return Self(source:source)
    }
}
public enum SyntheticInboxLinkDealOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxLinkDealPort:Sendable {var grants:[SyntheticInboxLinkDealGrant] {get};func execute(_ attempt:InboxLinkDealAttempt) async throws -> SyntheticInboxLinkDealOutcome}
public enum InboxLinkDealPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxLinkDealRecord:Equatable,Sendable {public let attempt:InboxLinkDealAttempt;public var phase:InboxLinkDealPhase;public var result:InboxLinkDealReceipt?}
public struct InboxLinkDealLedger:Sendable {
    public private(set) var records:[InboxLinkDealRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxLinkDealAuthorization?)->InboxLinkDealRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxLinkDealReview)->InboxLinkDealAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxLinkDealAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxLinkDealRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxLinkDealAttempt,outcome:SyntheticInboxLinkDealOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxLinkDealReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxLinkDealAuthorization,record:InboxLinkDealRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxLinkDealRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkDealSource}
public struct APIInboxLinkDealRepository:InboxLinkDealRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkDealSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxLinkDealSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxLinkDealPort:SyntheticInboxLinkDealPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,deal_id:Int,original_client:Int?,original_lead:Int?,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxLinkDealGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxLinkDealGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-deal.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxLinkDealAttempt) async throws -> SyntheticInboxLinkDealOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.deal_id==a.review.candidate.reference.source.id && $0.original_client==a.review.source.client && $0.original_lead==a.review.source.lead}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxLinkDealReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-deal.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
