import Foundation

// Observed generic conversation only. No permission, version or command recovery inference.
public struct InboxLinkClientSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,client:Int?,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ client:Int?,_ updated:String) {context=c;self.client=client;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.client==b.client && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil};switch TaskCreateClientRead.decode(data) {case .unknown:return nil;case .notSet:return Self(c,nil,updated);case .client(let id):return Self(c,id,updated)}}
}
// Reuses the existing independent Client search/profile identity; no new Client DTO or permission.
public struct InboxLinkClientCandidate:Equatable,Sendable {
    public let source:InboxLinkClientSource,selected:ClientSearchProfileSelection,read:ClientReadSelection,rawQuery:String,choice:TaskDraftClientChoice
    public init?(source:InboxLinkClientSource,selected:ClientSearchProfileSelection,read:ClientReadSelection,rawQuery:String,profile:ClientProfile) {
        let c=source.context;guard source.valid,selected.selection.context==ClientSearchContext(business:c.business,epoch:c.epoch),selected.selection.generation>0,selected.generation>0,read.business==c.business,read.id==selected.id,read.revision>0,let choice=TaskDraftClientChoice(profile:profile,business:c.business,id:selected.id) else {return nil};self.source=source;self.selected=selected;self.read=read;self.rawQuery=rawQuery;self.choice=choice
    }
    public var valid:Bool {source.valid && choice.valid(for:source.context.business) && selected.selection.generation>0 && selected.generation>0 && selected.id==choice.id && read.id==choice.id && read.business==choice.business && read.revision>0 && selected.selection.context==ClientSearchContext(business:source.context.business,epoch:source.context.epoch)}
    public static func ==(a:Self,b:Self)->Bool {a.source==b.source && a.selected==b.selected && a.read==b.read && a.choice==b.choice && SourceTextIdentity.same(a.rawQuery,b.rawQuery)}
}
public struct SyntheticInboxLinkClientGrant:Decodable,Sendable {
    public let business:Int,conversation:Int,actor:Int,clients_update:Bool,conversations_update:Bool
    public init(business:Int,conversation:Int,actor:Int,clientsUpdate:Bool,conversationsUpdate:Bool) {self.business=business;self.conversation=conversation;self.actor=actor;clients_update=clientsUpdate;conversations_update=conversationsUpdate}
    public func authorization(for c:InboxConversationFilesContext)->SyntheticInboxLinkClientAuthorization? {guard c.valid,business==c.business,conversation==c.conversation,actor>0,actor<=Int(Int32.max),clients_update,conversations_update else {return nil};return SyntheticInboxLinkClientAuthorization(context:c,actor:actor)}
}
public struct SyntheticInboxLinkClientAuthorization:Equatable,Sendable {public let context:InboxConversationFilesContext;public let actor:Int;fileprivate init(context:InboxConversationFilesContext,actor:Int) {self.context=context;self.actor=actor}}
public struct InboxLinkClientReview:Equatable,Sendable {
    public let source:InboxLinkClientSource,authorization:SyntheticInboxLinkClientAuthorization,candidate:InboxLinkClientCandidate,visit:Int
    public init(source:InboxLinkClientSource,authorization:SyntheticInboxLinkClientAuthorization,candidate:InboxLinkClientCandidate,visit:Int) {self.source=source;self.authorization=authorization;self.candidate=candidate;self.visit=visit}
    public var valid:Bool {source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
}
public struct InboxLinkClientAttempt:Equatable,Sendable {
    public let localID:Int,review:InboxLinkClientReview
    public var path:String {"/api/inbox/conversations/\(review.source.context.conversation)/link-client/"}
    public var query:[String:String] {[:]}
    public var headers:[String:String] {[:]}
    public func preparedBody()->Data {Data("{\"client_id\":\(review.candidate.choice.id)}".utf8)}
}
public struct InboxLinkClientReceipt:Equatable,Sendable {
    public let source:InboxLinkClientSource
    public static func decode(_ data:Data,attempt a:InboxLinkClientAttempt)->Self? {guard a.review.valid,let source=InboxLinkClientSource.decode(data,context:a.review.source.context),source.client==a.review.candidate.choice.id else {return nil};return Self(source:source)}
}
public enum SyntheticInboxLinkClientOutcome:Sendable {case response(status:Int,data:Data),rejectedWithoutWrite,unknown}
public protocol SyntheticInboxLinkClientPort:Sendable {var grants:[SyntheticInboxLinkClientGrant] {get};func execute(_ attempt:InboxLinkClientAttempt) async throws -> SyntheticInboxLinkClientOutcome}
public enum InboxLinkClientPhase:Equatable,Sendable {case pending,response,rejected,unknown}
public struct InboxLinkClientRecord:Equatable,Sendable {public let attempt:InboxLinkClientAttempt;public var phase:InboxLinkClientPhase;public var result:InboxLinkClientReceipt?}
public struct InboxLinkClientLedger:Sendable {
    public private(set) var records:[InboxLinkClientRecord]=[]
    private var active:[String:Int]=[:]
    public init() {}
    private func key(_ c:InboxConversationFilesContext)->String {"\(c.business)/\(c.conversation)"}
    public func blocked(business:Int,conversation:Int)->Bool {active["\(business)/\(conversation)"] != nil}
    public func visible(_ auth:SyntheticInboxLinkClientAuthorization?)->InboxLinkClientRecord? {guard let auth,let i=active[key(auth.context)],records[i].attempt.review.authorization.actor==auth.actor else {return nil};return records[i]}
    public mutating func begin(_ review:InboxLinkClientReview)->InboxLinkClientAttempt? {
        guard review.valid,!blocked(business:review.source.context.business,conversation:review.source.context.conversation) else {return nil};let a=InboxLinkClientAttempt(localID:records.count+1,review:review);active[key(review.source.context)]=records.count;records.append(InboxLinkClientRecord(attempt:a,phase:.pending,result:nil));return a
    }
    public mutating func complete(_ a:InboxLinkClientAttempt,outcome:SyntheticInboxLinkClientOutcome) {
        guard let i=records.firstIndex(where:{$0.attempt==a}),records[i].phase == .pending else {return}
        switch outcome {case .unknown:records[i].phase = .unknown;case .rejectedWithoutWrite:records[i].phase = .rejected;case .response(let status,let data):if status==200,let receipt=InboxLinkClientReceipt.decode(data,attempt:a) {records[i].phase = .response;records[i].result=receipt} else {records[i].phase = .unknown}}
    }
    @discardableResult public mutating func acknowledge(_ auth:SyntheticInboxLinkClientAuthorization,record:InboxLinkClientRecord)->Bool {guard visible(auth)==record,record.phase == .response || record.phase == .rejected else {return false};active.removeValue(forKey:key(auth.context));return true}
}
public protocol InboxLinkClientRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkClientSource}
public struct APIInboxLinkClientRepository:InboxLinkClientRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ context:InboxConversationFilesContext) async throws -> InboxLinkClientSource {
        guard context.valid else {throw ReadFailure.invalidContext};let r=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"));guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};guard let s=InboxLinkClientSource.decode(r.data,context:context) else {throw ReadFailure.invalidPayload};return s
    }
}
// Separate explicit fixture command and GET adapters. No HTTP command implementation.
public struct FixtureInboxLinkClientPort:SyntheticInboxLinkClientPort {
    private struct Scenario:Decodable,Sendable {let business:Int,conversation:Int,actor:Int,client_id:Int,outcome:String;let status:Int?;let response_json:String?}
    private struct Catalog:Decodable {let fixture_only:Bool;let grants:[SyntheticInboxLinkClientGrant];let scenarios:[Scenario]}
    public let grants:[SyntheticInboxLinkClientGrant];private let scenarios:[Scenario]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-client.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {grants=c.grants;scenarios=c.scenarios} else {grants=[];scenarios=[]}}
    public func execute(_ a:InboxLinkClientAttempt) async throws -> SyntheticInboxLinkClientOutcome {let auth=a.review.authorization,c=auth.context;guard a.review.valid,grants.compactMap({$0.authorization(for:c)}).contains(auth),let s=scenarios.first(where:{$0.business==c.business && $0.conversation==c.conversation && $0.actor==auth.actor && $0.client_id==a.review.candidate.choice.id}) else {return .rejectedWithoutWrite};if s.outcome=="response",let status=s.status,let raw=s.response_json {return .response(status:status,data:Data(raw.utf8))};return s.outcome=="rejected" ? .rejectedWithoutWrite:.unknown}
}
public struct FixtureInboxLinkClientReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-link-client.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ q:ReadRequest) async throws -> ReadResponse {guard q.query.isEmpty,let row=rows.first(where:{$0.path==q.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
