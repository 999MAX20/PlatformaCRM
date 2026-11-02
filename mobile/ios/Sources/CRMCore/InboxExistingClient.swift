import Foundation

// Reuse the exact generic client-only projection/repository, never the link command or its grants/picker.
public typealias InboxExistingClientSource = InboxLinkClientSource
public typealias InboxExistingClientRepository = InboxLinkClientRepository
public typealias APIInboxExistingClientRepository = APIInboxLinkClientRepository
public struct SyntheticInboxExistingClientGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,clients_create:Bool,conversations_update:Bool
    public init(business:Int,conversation:Int,actor:Int,clientsCreate:Bool,conversationsUpdate:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;clients_create=clientsCreate;conversations_update=conversationsUpdate}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxExistingClientAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),clients_create,conversations_update else {return nil};return SyntheticInboxExistingClientAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxExistingClientAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxExistingClientReview:Equatable,Sendable {
    public let source:InboxExistingClientSource,authorization:SyntheticInboxExistingClientAuthorization,visit:Int
    public init(source:InboxExistingClientSource,authorization:SyntheticInboxExistingClientAuthorization,visit:Int) {self.source=source;self.authorization=authorization;self.visit=visit}
    public var valid:Bool {source.valid && source.client.map {$0>0 && $0<=Int(Int32.max)}==true && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxExistingClientAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxExistingClientReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/create-client/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{}".utf8)}
}
// Existing ClientSerializer identity only. Annotation/count/manager/active/role fields are not defaults or grants.
public struct InboxExistingClientReceipt:Equatable,Sendable {
    public let id:Int,business:Int,fullName:String,phone:String,email:String,updatedAt:String
    private struct Wrapper:Decodable {let created:Bool}
    private init(id:Int,business:Int,fullName:String,phone:String,email:String,updatedAt:String) {self.id=id;self.business=business;self.fullName=fullName;self.phone=phone;self.email=email;self.updatedAt=updatedAt}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && SourceTextIdentity.same(a.fullName,b.fullName) && SourceTextIdentity.same(a.phone,b.phone) && SourceTextIdentity.same(a.email,b.email) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,attempt a:InboxExistingClientAttempt)->Self? {
        guard a.review.valid,let root=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let wrapper=try? JSONDecoder().decode(Wrapper.self,from:data),!wrapper.created,let duplicates=root["duplicates"] as? [Any],duplicates.isEmpty,root["requires_confirmation"]==nil,let row=root["client"] as? [String:Any],let id=a.review.source.client,DirectoryReadJSON.integer(row["id"])==Int64(id),DirectoryReadJSON.integer(row["business"])==Int64(a.review.source.context.business),let name=row["full_name"] as? String,let phone=row["phone"] as? String,let email=row["email"] as? String,let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        return Self(id:id,business:a.review.source.context.business,fullName:name,phone:phone,email:email,updatedAt:updated)
    }
}
public enum SyntheticInboxExistingClientOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxExistingClientPort:Sendable {var grants:[SyntheticInboxExistingClientGrant] {get};func execute(_ attempt:InboxExistingClientAttempt) async throws -> SyntheticInboxExistingClientOutcome}
public enum InboxExistingClientPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxExistingClientRecord:Equatable,Sendable {public let attempt:InboxExistingClientAttempt;public var phase:InboxExistingClientPhase;public var result:InboxExistingClientReceipt?}
public struct InboxExistingClientLedger:Sendable {
    public private(set) var records:[InboxExistingClientRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxExistingClientAuthorization?)->InboxExistingClientRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxExistingClientReview)->InboxExistingClientAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxExistingClientAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxExistingClientRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxExistingClientAttempt,outcome:SyntheticInboxExistingClientOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxExistingClientReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxExistingClientAuthorization,record:InboxExistingClientRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
// Explicit fixture GET and command adapters are distinct; there is no HTTP command implementation.
public struct FixtureInboxExistingClientPort:SyntheticInboxExistingClientPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,original_client:Int,original_updated_at:String,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxExistingClientGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxExistingClientGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-existing-client.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxExistingClientAttempt) async throws -> SyntheticInboxExistingClientOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.original_client==a.review.source.client && SourceTextIdentity.same($0.original_updated_at,a.review.source.updatedAt)}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxExistingClientReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-existing-client.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
