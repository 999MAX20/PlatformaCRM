import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxLinkLeadSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext
    public let lead:Int?,client:Int?,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ lead:Int?,_ client:Int?,_ updated:String) {context=c;self.lead=lead;self.client=client;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty && [lead,client].allSatisfy {$0==nil || ($0!>0 && $0!<=Int(Int32.max))}}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.lead==b.lead && a.client==b.client && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {
        guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let updated=row["updated_at"] as? String,!updated.isEmpty,let value=row["lead"] else {return nil}
        let lead:Int?
        if value is NSNull {lead=nil} else {guard let n=DirectoryReadJSON.integer(value),n>0,n<=Int64(Int32.max) else {return nil};lead=Int(n)}
        switch TaskCreateClientRead.decode(data) {case .unknown:return nil;case .notSet:return Self(c,lead,nil,updated);case .client(let id):return Self(c,lead,id,updated)}
    }
}
// Qualified mobile VIEW read reference is separate from both the generic source and UPDATE grant.
public struct InboxLinkLeadCandidate:Equatable,Sendable {
    public let source:InboxLinkLeadSource
    public let reference:QualifiedLeadReference
    public init?(source:InboxLinkLeadSource,reference:QualifiedLeadReference) {guard source.valid,reference.context==source.context,reference.readRevision>0,reference.detail.valid(for:source.context.business,id:reference.detail.lead.id) else {return nil};self.source=source;self.reference=reference}
    public var valid:Bool {source.valid && reference.context==source.context && reference.readRevision>0 && reference.detail.valid(for:source.context.business,id:reference.detail.lead.id)}
}
public struct SyntheticInboxLinkLeadGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,leads_update:Bool,conversations_update:Bool
    public init(business:Int,conversation:Int,actor:Int,leadsUpdate:Bool,conversationsUpdate:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;leads_update=leadsUpdate;conversations_update=conversationsUpdate}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxLinkLeadAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),leads_update,conversations_update else {return nil};return SyntheticInboxLinkLeadAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxLinkLeadAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxLinkLeadReview:Equatable,Sendable {
    public let source:InboxLinkLeadSource,authorization:SyntheticInboxLinkLeadAuthorization,candidate:InboxLinkLeadCandidate,visit:Int
    public init(source:InboxLinkLeadSource,authorization:SyntheticInboxLinkLeadAuthorization,candidate:InboxLinkLeadCandidate,visit:Int) {self.source=source;self.authorization=authorization;self.candidate=candidate;self.visit=visit}
    public var valid:Bool {source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxLinkLeadAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxLinkLeadReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/link-lead/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{\"lead_id\":\(review.candidate.reference.detail.lead.id)}".utf8)}
}
public struct InboxLinkLeadReceipt:Equatable,Sendable {
    public let source:InboxLinkLeadSource
    public static func decode(_ data:Data,attempt a:InboxLinkLeadAttempt)->Self? {
        guard a.review.valid,let source=InboxLinkLeadSource.decode(data,context:a.review.source.context),source.lead==a.review.candidate.reference.detail.lead.id,source.client==(a.review.source.client ?? a.review.candidate.reference.detail.lead.client_id) else {return nil};return Self(source:source)
    }
}
public enum SyntheticInboxLinkLeadOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxLinkLeadPort:Sendable {var grants:[SyntheticInboxLinkLeadGrant] {get};func execute(_ attempt:InboxLinkLeadAttempt) async throws -> SyntheticInboxLinkLeadOutcome}
public enum InboxLinkLeadPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxLinkLeadRecord:Equatable,Sendable {public let attempt:InboxLinkLeadAttempt;public var phase:InboxLinkLeadPhase;public var result:InboxLinkLeadReceipt?}
public struct InboxLinkLeadLedger:Sendable {
    public private(set) var records:[InboxLinkLeadRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxLinkLeadAuthorization?)->InboxLinkLeadRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxLinkLeadReview)->InboxLinkLeadAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxLinkLeadAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxLinkLeadRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxLinkLeadAttempt,outcome:SyntheticInboxLinkLeadOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxLinkLeadReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxLinkLeadAuthorization,record:InboxLinkLeadRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxLinkLeadRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkLeadSource}
public struct APIInboxLinkLeadRepository:InboxLinkLeadRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkLeadSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxLinkLeadSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxLinkLeadPort:SyntheticInboxLinkLeadPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,lead_id:Int,original_client:Int?,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxLinkLeadGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxLinkLeadGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-lead.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxLinkLeadAttempt) async throws -> SyntheticInboxLinkLeadOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.lead_id==a.review.candidate.reference.detail.lead.id && $0.original_client==a.review.source.client}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxLinkLeadReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-lead.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
