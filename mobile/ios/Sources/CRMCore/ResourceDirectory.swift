import Foundation

// Exactly ResourceSerializer seven fields; raw type/timestamps are observations, never eligibility.
public struct ResourceDirectoryItem:Equatable,Sendable,Identifiable {
    public let id:Int;public let business:Int;public let name:String;public let resourceType:String
    public let isActive:Bool;public let createdAt:String;public let updatedAt:String
    fileprivate static func item(_ value:Any)->Self? {
        guard let o=value as? [String:Any],let id=DirectoryReadJSON.integer(o["id"]),id>0,id<=Int64(Int32.max),let business=DirectoryReadJSON.integer(o["business"]),business>0,business<=Int64(Int32.max),let name=o["name"] as? String,let type=o["resource_type"] as? String,let active=o["is_active"] as? NSNumber,String(cString:active.objCType)=="c",let created=o["created_at"] as? String,let updated=o["updated_at"] as? String,TaskSnoozeValue.parse(created) != nil,TaskSnoozeValue.parse(updated) != nil else {return nil}
        return Self(id:Int(id),business:Int(business),name:name,resourceType:type,isActive:active.boolValue,createdAt:created,updatedAt:updated)
    }
    public static func decode(_ data:Data)->Self? {guard let o=try? JSONSerialization.jsonObject(with:data) else {return nil};return item(o)}
    public var reference:AppointmentReferenceDetail {AppointmentReferenceDetail(id:id,business:business,name:name,isActive:isActive,resourceType:resourceType)}
    public var hasKnownType:Bool {["staff","room","hall","box","equipment","other"].contains(resourceType)}
    public var typeCopyKey:String {AppointmentReferenceDetail(id:id,business:business,name:name,isActive:isActive,resourceType:resourceType).resourceTypeCopyKey}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && a.isActive==b.isActive && SourceTextIdentity.same(a.name,b.name) && SourceTextIdentity.same(a.resourceType,b.resourceType) && SourceTextIdentity.same(a.createdAt,b.createdAt) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
}
public typealias ResourceDirectoryLinkPresence=DirectoryReadLinkPresence
public typealias ResourceDirectoryShape=DirectoryReadShape
public struct ResourceDirectoryWindow:Equatable,Sendable {
    public let business:Int;public let items:[ResourceDirectoryItem];public let shape:ResourceDirectoryShape
    public let receivedCount:Int;public let observedCount:Int64?;public let next:ResourceDirectoryLinkPresence;public let previous:ResourceDirectoryLinkPresence
    public static func decode(_ data:Data,business:Int)->Self? {
        guard business>0,business<=Int(Int32.max),let envelope=DirectoryReadEnvelope.decode(data) else {return nil}
        let rows=envelope.rows
        var ids=Set<Int>(),projected=[ResourceDirectoryItem]()
        for row in rows {guard let item=ResourceDirectoryItem.item(row),ids.insert(item.id).inserted else {return nil};if item.business==business {projected.append(item)}}
        return Self(business:business,items:projected,shape:envelope.shape,receivedCount:rows.count,observedCount:envelope.count,next:envelope.next,previous:envelope.previous)
    }
}
public protocol ResourceDirectoryRepository:Sendable {
    func resources(business:Int) async throws -> ResourceDirectoryWindow
    func resource(business:Int,id:Int) async throws -> ResourceDirectoryItem
}
public struct APIResourceDirectoryRepository:ResourceDirectoryRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    private func get(_ path:String) async throws -> Data {
        let r=try await transport.get(ReadRequest(path:path))
        switch r.status {case 200:return r.data;case 403:throw ReadFailure.denied;case 404:throw ReadFailure.notFound;default:throw ReadFailure.unavailable}
    }
    public func resources(business:Int) async throws -> ResourceDirectoryWindow {
        guard business>0,business<=Int(Int32.max) else {throw ReadFailure.invalidContext}
        guard let value=ResourceDirectoryWindow.decode(try await get("/api/resources/"),business:business) else {throw ReadFailure.invalidPayload};return value
    }
    public func resource(business:Int,id:Int) async throws -> ResourceDirectoryItem {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max) else {throw ReadFailure.invalidContext}
        guard let value=ResourceDirectoryItem.decode(try await get("/api/resources/\(id)/")),value.business==business,value.id==id else {throw ReadFailure.invalidPayload};return value
    }
}
// Explicit local fixture port, injected only in DEBUG. No network/fallback/command methods.
public struct FixtureResourceDirectoryTransport:ReadTransport {
    private let directory:URL
    public init(directory:URL) {self.directory=directory}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private struct Row:Decodable {let path:String;let response_json:String}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {
        guard request.query.isEmpty else {return ReadResponse(status:404,data:Data())}
        let c=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("resource-directory.json")))
        guard c.fixture_only,let row=c.reads.first(where:{$0.path==request.path}) else {return ReadResponse(status:404,data:Data())}
        return ReadResponse(status:200,data:Data(row.response_json.utf8))
    }
}
