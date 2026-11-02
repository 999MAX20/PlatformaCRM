import Foundation

// Exact create-task relation inputs from generic conversation GET; no task/create permission.
public struct InboxTaskSource:Equatable,Sendable {
    public let context:InboxConversationFilesContext,client:Int?,lead:Int?,updatedAt:String
    private init(_ c:InboxConversationFilesContext,_ client:Int?,_ lead:Int?,_ updated:String) {context=c;self.client=client;self.lead=lead;updatedAt=updated}
    public var valid:Bool {context.valid && !updatedAt.isEmpty && [client,lead].allSatisfy {$0==nil || ($0!>0 && $0!<=Int(Int32.max))}}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.client==b.client && a.lead==b.lead && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->Self? {
        guard c.valid,let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(row,business:c.business,conversation:c.conversation),let updated=row["updated_at"] as? String,!updated.isEmpty else {return nil}
        var links:[Int?]=[]
        for key in ["client","lead"] {guard let value=row[key] else {return nil};if value is NSNull {links.append(nil)} else {guard let n=DirectoryReadJSON.integer(value),n>0,n<=Int64(Int32.max) else {return nil};links.append(Int(n))}}
        return Self(c,links[0],links[1],updated)
    }
}
public struct InboxTaskSourceControl:Equatable,Sendable {public let context:InboxConversationFilesContext;public let visit:Int}
public struct InboxTaskSourceTicket:Equatable,Sendable {public let context:InboxConversationFilesContext;public let revision:Int}
public struct QualifiedInboxTaskSource:Equatable,Sendable {
    public let source:InboxTaskSource,readRevision:Int
    fileprivate init(source:InboxTaskSource,readRevision:Int) {self.source=source;self.readRevision=readRevision}
    public var context:InboxConversationFilesContext {source.context}
    public var valid:Bool {source.valid && readRevision>0}
}
public struct InboxTaskSourceSession:Sendable {
    public private(set) var context:InboxConversationFilesContext?
    public private(set) var presented=false,loading=false
    public private(set) var source:InboxTaskSource?
    public private(set) var failure:ReadFailure?
    public private(set) var choice:QualifiedInboxTaskSource?
    private var pending:InboxTaskSourceTicket?
    private var revision=0,visit=0,sourceRevision=0
    public init() {}
    public var control:InboxTaskSourceControl? {context.map {InboxTaskSourceControl(context:$0,visit:visit)}}
    public var canRead:Bool {presented && !loading && context != nil}
    public var canUse:Bool {presented && !loading && failure==nil && source?.context==context && source?.valid==true && sourceRevision>0}
    private mutating func invalidate() {revision += 1;visit += 1;sourceRevision=0;pending=nil;loading=false;source=nil;failure=nil;choice=nil}
    public mutating func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard context != next else {return};hide();context=next}
    public mutating func show() {guard context != nil,!presented else {return};invalidate();presented=true}
    public mutating func hide() {invalidate();presented=false}
    public mutating func begin(expected:InboxTaskSourceControl?)->InboxTaskSourceTicket? {guard let expected,control==expected,canRead,let context else {return nil};invalidate();loading=true;let ticket=InboxTaskSourceTicket(context:context,revision:revision);pending=ticket;return ticket}
    @discardableResult public mutating func accept(_ source:InboxTaskSource,ticket:InboxTaskSourceTicket)->Bool {guard pending==ticket,presented,context==ticket.context else {return false};guard source.valid,source.context==ticket.context else {fail(.invalidPayload,ticket:ticket);return false};pending=nil;loading=false;failure=nil;self.source=source;sourceRevision=ticket.revision;visit += 1;return true}
    public mutating func fail(_ error:ReadFailure,ticket:InboxTaskSourceTicket) {guard pending==ticket,presented,context==ticket.context else {return};pending=nil;loading=false;source=nil;sourceRevision=0;failure=error;choice=nil;visit += 1}
    public mutating func cancel(ticket:InboxTaskSourceTicket) {guard pending==ticket else {return};invalidate()}
    public mutating func use(expected:InboxTaskSourceControl?) {guard let expected,control==expected,canUse,let source else {return};choice=QualifiedInboxTaskSource(source:source,readRevision:sourceRevision);visit += 1}
    public mutating func clearChoice(expected:InboxTaskSourceControl?) {guard let expected,control==expected,presented,!loading else {return};choice=nil;visit += 1}
}
public protocol InboxTaskSourceRepository:Sendable {func source(_ context:InboxConversationFilesContext) async throws -> InboxTaskSource}
public struct APIInboxTaskSourceRepository:InboxTaskSourceRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func source(_ c:InboxConversationFilesContext) async throws -> InboxTaskSource {guard c.valid else {throw ReadFailure.invalidContext};let response=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(c.conversation)/"));guard response.status==200 else {throw response.status==403 ? ReadFailure.denied:response.status==404 ? .notFound:.unavailable};guard let s=InboxTaskSource.decode(response.data,context:c) else {throw ReadFailure.invalidPayload};return s}
}
public struct FixtureInboxTaskSourceTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,status:Int,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let d=try? Data(contentsOf:directory.appendingPathComponent("inbox-task-source.json")),let c=try? JSONDecoder().decode(Catalog.self,from:d),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {guard request.query.isEmpty,let row=rows.first(where:{$0.path==request.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:row.status,data:Data(row.response_json.utf8))}
}
