import Foundation

// Local read/window identity only; never file access permission or an entity version.
public struct TaskFileMetadataContext:Equatable,Sendable {
    public let business:Int;public let task:Int;public let epoch:Int;public let revision:Int
    public init(business:Int,task:Int,epoch:Int,revision:Int) {self.business=business;self.task=task;self.epoch=epoch;self.revision=revision}
    public var valid:Bool {business>0 && task>0 && epoch>0 && revision>0}
}
// Exact FileAttachmentSerializer metadata subset. URL, bytes, uploader and scan extras are not retained.
public struct TaskFileMetadata:Codable,Equatable,Sendable,Identifiable {
    public let id:Int;public let business:Int;public let original_name:String;public let content_type:String;public let size:Int64
    public let entity_type:String;public let entity_id:String;public let visibility:String;public let created_at:String
    public func valid(for c:TaskFileMetadataContext)->Bool {c.valid && id>0 && business==c.business && entity_type=="task" && entity_id==String(c.task) && visibility=="private" && !original_name.isEmpty && size>=0 && Appointment.instant(created_at) != nil}
    public static func window(_ data:Data,context:TaskFileMetadataContext) throws -> [TaskFileMetadata] {
        struct Page:Decodable {let results:[TaskFileMetadata]}
        let decoder=JSONDecoder(),rows:[TaskFileMetadata]
        if let array=try? decoder.decode([TaskFileMetadata].self,from:data) {rows=array} else {rows=try decoder.decode(Page.self,from:data).results}
        guard context.valid,rows.allSatisfy({$0.valid(for:context)}),Set(rows.map(\.id)).count==rows.count else {throw ReadFailure.invalidPayload};return rows
    }
}
public protocol TaskFileMetadataPort:Sendable {func read(_ context:TaskFileMetadataContext) async throws -> Data}
public struct FixtureTaskFileMetadataPort:TaskFileMetadataPort {
    private struct Row:Decodable,Sendable {let business:Int;let task:Int;let items:[TaskFileMetadata]}
    private struct Catalog:Decodable {let fixture_only:Bool;let scenarios:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("task-file-metadata.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.scenarios} else {rows=[]}}
    public func read(_ context:TaskFileMetadataContext) async throws -> Data {guard context.valid,let row=rows.first(where:{$0.business==context.business && $0.task==context.task}) else {throw ReadFailure.invalidContext};return try JSONEncoder().encode(row.items)}
}
