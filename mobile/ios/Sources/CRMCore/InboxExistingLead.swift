import Foundation

// Reuse the exact generic Lead/Client projection/repository, never the link command or its grants/picker.
public typealias InboxExistingLeadSource = InboxLinkLeadSource
public typealias InboxExistingLeadRepository = InboxLinkLeadRepository
public typealias APIInboxExistingLeadRepository = APIInboxLinkLeadRepository
public struct SyntheticInboxExistingLeadGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,leads_create:Bool,conversations_update:Bool
    public init(business:Int,conversation:Int,actor:Int,leadsCreate:Bool,conversationsUpdate:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;leads_create=leadsCreate;conversations_update=conversationsUpdate}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxExistingLeadAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),leads_create,conversations_update else {return nil};return SyntheticInboxExistingLeadAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxExistingLeadAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxExistingLeadReview:Equatable,Sendable {
    public let source:InboxExistingLeadSource,authorization:SyntheticInboxExistingLeadAuthorization,visit:Int
    public init(source:InboxExistingLeadSource,authorization:SyntheticInboxExistingLeadAuthorization,visit:Int) {self.source=source;self.authorization=authorization;self.visit=visit}
    public var valid:Bool {source.valid && source.lead.map {$0>0 && $0<=Int(Int32.max)}==true && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxExistingLeadAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxExistingLeadReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/create-lead/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
// Existing generic LeadSerializer only; Lead.client is required and independent of conversation.client.
public struct InboxExistingLeadReceipt:Equatable,Sendable {
    public let id:Int,business:Int,client:Int,message:String,updatedAt:String
    private init(id:Int,business:Int,client:Int,message:String,updatedAt:String) {self.id=id;self.business=business;self.client=client;self.message=message;self.updatedAt=updatedAt}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && a.client==b.client && SourceTextIdentity.same(a.message,b.message) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,attempt a:InboxExistingLeadAttempt)->Self? {
        guard a.review.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let id=a.review.source.lead,DirectoryReadJSON.integer(row["id"])==Int64(id),DirectoryReadJSON.integer(row["business"])==Int64(a.review.source.context.business),let client=DirectoryReadJSON.integer(row["client"]),client>0,client<=Int64(Int32.max),let message=row["message"] as? String,let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        return Self(id:id,business:a.review.source.context.business,client:Int(client),message:message,updatedAt:updated)
    }
}
public enum SyntheticInboxExistingLeadOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxExistingLeadPort:Sendable {var grants:[SyntheticInboxExistingLeadGrant] {get};func execute(_ attempt:InboxExistingLeadAttempt) async throws -> SyntheticInboxExistingLeadOutcome}
public enum InboxExistingLeadPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxExistingLeadRecord:Equatable,Sendable {public let attempt:InboxExistingLeadAttempt;public var phase:InboxExistingLeadPhase;public var result:InboxExistingLeadReceipt?}
public struct InboxExistingLeadLedger:Sendable {
    public private(set) var records:[InboxExistingLeadRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxExistingLeadAuthorization?)->InboxExistingLeadRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxExistingLeadReview)->InboxExistingLeadAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxExistingLeadAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxExistingLeadRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxExistingLeadAttempt,outcome:SyntheticInboxExistingLeadOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxExistingLeadReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxExistingLeadAuthorization,record:InboxExistingLeadRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
// Explicit fixture GET and command adapters are distinct; there is no HTTP command implementation.
public struct FixtureInboxExistingLeadPort:SyntheticInboxExistingLeadPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,original_lead:Int,original_client:Int?,original_updated_at:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxExistingLeadGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxExistingLeadGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-existing-lead.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxExistingLeadAttempt) async throws -> SyntheticInboxExistingLeadOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.original_lead==a.review.source.lead && $0.original_client==a.review.source.client && SourceTextIdentity.same($0.original_updated_at,a.review.source.updatedAt)}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxExistingLeadReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-existing-lead.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
