import Foundation

// Explicit current selected message, provided read budget and local owner; not a server version/grant.
public struct InboxMessageFilesContext:Equatable,Sendable {
    public let business:Int,conversation:Int,message:Int,epoch:Int,revision:Int,limit:Int
    public init(business:Int,conversation:Int,message:Int,epoch:Int,revision:Int,limit:Int) {self.business=business;self.conversation=conversation;self.message=message;self.epoch=epoch;self.revision=revision;self.limit=limit}
    public var valid:Bool {[business,conversation,message].allSatisfy {$0>0 && $0<=Int(Int32.max)} && epoch>0 && revision>0 && (1...300).contains(limit)}
}
// Source id/business observation only; never VIEW/UPDATE/send or an outcome token.
public struct InboxFilesConversationAnchor:Equatable,Sendable {
    public let business:Int,conversation:Int
    private init(business:Int,conversation:Int) {self.business=business;self.conversation=conversation}
    public static func decode(_ data:Data,context:InboxMessageFilesContext)->Self? {guard context.valid,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(o,business:context.business,conversation:context.conversation) else {return nil};return Self(business:context.business,conversation:context.conversation)}
    public func matches(_ context:InboxMessageFilesContext)->Bool {context.valid && business==context.business && conversation==context.conversation}
}
public struct InboxMessageFileWindow:Equatable,Sendable {
    public let context:InboxMessageFilesContext
    public let items:[InboxMessageFileMetadata]
    public let observation:InboxMessageObservation
    public let retrySource:InboxRetryMessageSource?
    public let count:Int64,providedMessages:Int,hasMore:Bool
    public let next:DirectoryReadLinkPresence,previous:DirectoryReadLinkPresence,nextBefore:DirectoryReadLinkPresence
    private init(context:InboxMessageFilesContext,items:[InboxMessageFileMetadata],observation:InboxMessageObservation,retrySource:InboxRetryMessageSource?,count:Int64,providedMessages:Int,hasMore:Bool,next:DirectoryReadLinkPresence,previous:DirectoryReadLinkPresence,nextBefore:DirectoryReadLinkPresence) {self.context=context;self.items=items;self.observation=observation;self.retrySource=retrySource;self.count=count;self.providedMessages=providedMessages;self.hasMore=hasMore;self.next=next;self.previous=previous;self.nextBefore=nextBefore}
    public var limited:Bool {hasMore || count>Int64(providedMessages)}
    public func valid(for c:InboxMessageFilesContext)->Bool {context==c && c.valid && observation.valid(for:c) && (retrySource==nil || (retrySource!.valid && retrySource!.context==c)) && providedMessages>0 && providedMessages<=c.limit && count>=Int64(providedMessages) && (!hasMore || providedMessages==c.limit) && previous == .null && next == (hasMore ? .present:.null) && nextBefore==next && items.allSatisfy {$0.valid(for:c)} && Set(items.map(\.id)).count==items.count}
    public static func decode(_ data:Data,context c:InboxMessageFilesContext) throws -> Self {
        guard c.valid,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let values=o["results"] as? [Any],values.count<=c.limit,let count=DirectoryReadJSON.integer(o["count"]),count>=Int64(values.count),let more=o["has_more"] as? NSNumber,String(cString:more.objCType)=="c",let next=DirectoryReadJSON.link(o,"next"),let previous=DirectoryReadJSON.link(o,"previous"),previous == .null,let rawCursor=o["next_before_id"] else {throw ReadFailure.invalidPayload}
        let hasMore=more.boolValue,cursor:DirectoryReadLinkPresence
        if rawCursor is NSNull {cursor = .null} else {guard let id=DirectoryReadJSON.integer(rawCursor),id>0,id<=Int64(Int32.max),let raw=o["next"] as? String,raw==String(id) else {throw ReadFailure.invalidPayload};cursor = .present}
        guard next == (hasMore ? .present:.null),cursor==next,!hasMore || values.count==c.limit else {throw ReadFailure.invalidPayload}
        var ids:Set<Int>=[],fileIDs:Set<Int>=[];var selected:[InboxMessageFileMetadata]?;var observation:InboxMessageObservation?;var retrySource:InboxRetryMessageSource?
        for value in values {
            guard let row=value as? [String:Any],let id=DirectoryReadJSON.integer(row["id"]),id>0,id<=Int64(Int32.max),ids.insert(Int(id)).inserted,DirectoryReadJSON.integer(row["conversation"])==Int64(c.conversation),let attachments=row["attachments"] as? [Any],let files=InboxFileMetadata.rows(attachments,business:c.business,entityType:"bot_message",entityID:String(id)),files.allSatisfy({fileIDs.insert($0.id).inserted}) else {throw ReadFailure.invalidPayload}
            let rowContext=InboxMessageFilesContext(business:c.business,conversation:c.conversation,message:Int(id),epoch:c.epoch,revision:c.revision,limit:c.limit)
            guard let observed=InboxMessageObservation.decode(row,context:rowContext) else {throw ReadFailure.invalidPayload}
            if Int(id)==c.message {selected=files;observation=observed;retrySource=InboxRetryMessageSource.decode(row,context:c)}
        }
        guard let selected,let observation else {throw ReadFailure.unavailable}
        return Self(context:c,items:selected,observation:observation,retrySource:retrySource,count:count,providedMessages:values.count,hasMore:hasMore,next:next,previous:previous,nextBefore:cursor)
    }
}
public enum InboxMessageFileSourceIdentity {
    public static func same(_ a:InboxMessage,_ b:InboxMessage)->Bool {a.id==b.id && a.conversation_id==b.conversation_id && a.sourceState==b.sourceState && zip([a.direction,a.sender_type,a.text,a.created_at],[b.direction,b.sender_type,b.text,b.created_at]).allSatisfy {pair in pair.0.map {Data($0.utf8)}==pair.1.map {Data($0.utf8)}}}
}
// Stage boundary lets the owner reject a late anchor before issuing the dependent message GET.
public protocol InboxMessageFilesRepository:Sendable {func anchor(_ context:InboxMessageFilesContext) async throws -> InboxFilesConversationAnchor;func messages(_ context:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor) async throws -> InboxMessageFileWindow}
public struct APIInboxMessageFilesRepository:InboxMessageFilesRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    private func response(_ request:ReadRequest) async throws -> Data {let r=try await transport.get(request);guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable};return r.data}
    public func anchor(_ c:InboxMessageFilesContext) async throws -> InboxFilesConversationAnchor {guard c.valid else {throw ReadFailure.invalidContext};let data=try await response(ReadRequest(path:"/api/inbox/conversations/\(c.conversation)/"));guard let result=InboxFilesConversationAnchor.decode(data,context:c) else {throw ReadFailure.invalidPayload};return result}
    public func messages(_ c:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor) async throws -> InboxMessageFileWindow {guard c.valid,anchor.matches(c) else {throw ReadFailure.invalidContext};let data=try await response(ReadRequest(path:"/api/inbox/conversations/\(c.conversation)/messages/",query:["limit":String(c.limit)]));return try InboxMessageFileWindow.decode(data,context:c)}
}
public struct FixtureInboxMessageFilesTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String;let query:[String:String];let response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-message-files.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {guard let row=rows.first(where:{$0.path==request.path && $0.query==request.query}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
