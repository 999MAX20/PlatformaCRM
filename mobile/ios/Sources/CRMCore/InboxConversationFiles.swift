import Foundation

// Local independent read owner only; no version, download permission or command authority.
public struct InboxConversationFilesContext:Equatable,Sendable {
    public let business:Int,conversation:Int,epoch:Int,revision:Int
    public init(business:Int,conversation:Int,epoch:Int,revision:Int) {self.business=business;self.conversation=conversation;self.epoch=epoch;self.revision=revision}
    public var valid:Bool {[business,conversation].allSatisfy {$0>0 && $0<=Int(Int32.max)} && epoch>0 && revision>0}
}
public struct InboxFileMetadata:Equatable,Sendable,Identifiable {
    public let id:Int,business:Int
    public let originalName:String,contentType:String
    public let size:Int64
    public let entityType:String,entityID:String,visibility:String,createdAt:String
    private init(id:Int,business:Int,originalName:String,contentType:String,size:Int64,entityType:String,entityID:String,visibility:String,createdAt:String) {self.id=id;self.business=business;self.originalName=originalName;self.contentType=contentType;self.size=size;self.entityType=entityType;self.entityID=entityID;self.visibility=visibility;self.createdAt=createdAt}
    public func valid(for c:InboxConversationFilesContext)->Bool {c.valid && id>0 && id<=Int(Int32.max) && business==c.business && size>=0 && entityType=="bot_conversation" && entityID==String(c.conversation) && visibility=="private" && TaskSnoozeValue.parse(createdAt) != nil}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && a.size==b.size && zip([a.originalName,a.contentType,a.entityType,a.entityID,a.visibility,a.createdAt],[b.originalName,b.contentType,b.entityType,b.entityID,b.visibility,b.createdAt]).allSatisfy {SourceTextIdentity.same($0.0,$0.1)}}
    public func valid(for c:InboxMessageFilesContext)->Bool {c.valid && id>0 && id<=Int(Int32.max) && business==c.business && size>=0 && entityType=="bot_message" && entityID==String(c.message) && visibility=="private" && TaskSnoozeValue.parse(createdAt) != nil}
    static func rows(_ values:[Any],business:Int,entityType:String,entityID:String)->[Self]? {
        var rows:[Self]=[];var ids:Set<Int>=[]
        for value in values {
            guard let row=value as? [String:Any],let id=DirectoryReadJSON.integer(row["id"]),id>0,id<=Int64(Int32.max),DirectoryReadJSON.integer(row["business"])==Int64(business),let name=row["original_name"] as? String,let type=row["content_type"] as? String,let size=DirectoryReadJSON.integer(row["size"]),size>=0,
                  let entity=row["entity_type"] as? String,entity==entityType,let providedID=row["entity_id"] as? String,providedID==entityID,let visibility=row["visibility"] as? String,visibility=="private",let created=row["created_at"] as? String,TaskSnoozeValue.parse(created) != nil,ids.insert(Int(id)).inserted else {return nil}
            rows.append(Self(id:Int(id),business:business,originalName:name,contentType:type,size:size,entityType:entity,entityID:providedID,visibility:visibility,createdAt:created))
        }
        return rows
    }
    public static func decode(_ data:Data,context c:InboxConversationFilesContext)->[Self]? {
        guard c.valid,let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],InboxFileReadJSON.anchor(o,business:c.business,conversation:c.conversation),let values=o["attachments"] as? [Any] else {return nil}
        return rows(values,business:c.business,entityType:"bot_conversation",entityID:String(c.conversation))
    }
}
public typealias InboxConversationFileMetadata = InboxFileMetadata
public typealias InboxMessageFileMetadata = InboxFileMetadata

enum InboxFileReadJSON {
    static func anchor(_ o:[String:Any],business:Int,conversation:Int)->Bool {DirectoryReadJSON.integer(o["id"])==Int64(conversation) && DirectoryReadJSON.integer(o["business"])==Int64(business)}
}
public protocol InboxConversationFilesRepository:Sendable {func files(_ context:InboxConversationFilesContext) async throws -> [InboxConversationFileMetadata]}
public struct APIInboxConversationFilesRepository:InboxConversationFilesRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func files(_ context:InboxConversationFilesContext) async throws -> [InboxConversationFileMetadata] {
        guard context.valid else {throw ReadFailure.invalidContext}
        let response=try await transport.get(ReadRequest(path:"/api/inbox/conversations/\(context.conversation)/"))
        guard response.status==200 else {throw response.status==403 ? ReadFailure.denied:response.status==404 ? .notFound:.unavailable}
        guard let rows=InboxConversationFileMetadata.decode(response.data,context:context) else {throw ReadFailure.invalidPayload};return rows
    }
}
// Explicit DEBUG/check fixture transport. No actual HTTP, fallback, URL following or mutation.
public struct FixtureInboxConversationFilesTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String;let response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("inbox-conversation-files.json")),let value=try? JSONDecoder().decode(Catalog.self,from:data),value.fixture_only {rows=value.reads} else {rows=[]}}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {guard request.query.isEmpty,let row=rows.first(where:{$0.path==request.path}) else {throw ReadFailure.invalidContext};return ReadResponse(status:200,data:Data(row.response_json.utf8))}
}
