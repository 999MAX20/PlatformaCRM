import Foundation

// Existing ServiceSerializer fields. Timestamps and a read choice confer no write authority.
public struct ServiceDirectoryItem:Equatable,Sendable,Identifiable {
    public let id:Int;public let business:Int;public let name:String;public let description:String
    public let durationMinutes:Int;public let priceFrom:String?;public let isActive:Bool
    public let createdAt:String;public let updatedAt:String
    fileprivate static func item(_ value:Any)->Self? {
        guard let o=value as? [String:Any],let id=DirectoryReadJSON.integer(o["id"]),id>0,id<=Int64(Int32.max),let business=DirectoryReadJSON.integer(o["business"]),business>0,business<=Int64(Int32.max),let duration=DirectoryReadJSON.integer(o["duration_minutes"]),duration>=0,duration<=Int64(Int32.max),let name=o["name"] as? String,let description=o["description"] as? String,o["price_from"] != nil,let active=o["is_active"] as? NSNumber,String(cString:active.objCType)=="c",let created=o["created_at"] as? String,let updated=o["updated_at"] as? String,TaskSnoozeValue.parse(created) != nil,TaskSnoozeValue.parse(updated) != nil else {return nil}
        let price:String?
        if o["price_from"] is NSNull {price=nil} else {guard let raw=o["price_from"] as? String else {return nil};price=raw}
        return Self(id:Int(id),business:Int(business),name:name,description:description,durationMinutes:Int(duration),priceFrom:price,isActive:active.boolValue,createdAt:created,updatedAt:updated)
    }
    public var reference:AppointmentReferenceDetail {AppointmentReferenceDetail(id:id,business:business,name:name,isActive:isActive,resourceType:nil)}
    public static func decode(_ data:Data)->Self? {guard let o=try? JSONSerialization.jsonObject(with:data) else {return nil};return item(o)}
    public static func ==(a:Self,b:Self)->Bool {
        a.id==b.id && a.business==b.business && a.durationMinutes==b.durationMinutes && a.isActive==b.isActive && SourceTextIdentity.same(a.name,b.name) && SourceTextIdentity.same(a.description,b.description) && a.priceFrom.map {Data($0.utf8)}==b.priceFrom.map {Data($0.utf8)} && SourceTextIdentity.same(a.createdAt,b.createdAt) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)
    }
}
public typealias ServiceDirectoryLinkPresence=DirectoryReadLinkPresence
public typealias ServiceDirectoryShape=DirectoryReadShape
public struct ServiceDirectoryWindow:Equatable,Sendable {
    public let business:Int;public let items:[ServiceDirectoryItem];public let shape:ServiceDirectoryShape
    public let receivedCount:Int;public let observedCount:Int64?;public let next:ServiceDirectoryLinkPresence;public let previous:ServiceDirectoryLinkPresence
    public static func decode(_ data:Data,business:Int)->Self? {
        guard business>0,business<=Int(Int32.max),let envelope=DirectoryReadEnvelope.decode(data) else {return nil}
        let rows=envelope.rows
        var ids=Set<Int>(),projected=[ServiceDirectoryItem]()
        for row in rows {guard let item=ServiceDirectoryItem.item(row),ids.insert(item.id).inserted else {return nil};if item.business==business {projected.append(item)}}
        return Self(business:business,items:projected,shape:envelope.shape,receivedCount:rows.count,observedCount:envelope.count,next:envelope.next,previous:envelope.previous)
    }
}
public protocol ServiceDirectoryRepository:Sendable {
    func services(business:Int) async throws -> ServiceDirectoryWindow
    func service(business:Int,id:Int) async throws -> ServiceDirectoryItem
}
public struct APIServiceDirectoryRepository:ServiceDirectoryRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    private func get(_ path:String) async throws -> Data {
        let r=try await transport.get(ReadRequest(path:path))
        switch r.status {case 200:return r.data;case 403:throw ReadFailure.denied;case 404:throw ReadFailure.notFound;default:throw ReadFailure.unavailable}
    }
    public func services(business:Int) async throws -> ServiceDirectoryWindow {
        guard business>0,business<=Int(Int32.max) else {throw ReadFailure.invalidContext}
        guard let value=ServiceDirectoryWindow.decode(try await get("/api/services/"),business:business) else {throw ReadFailure.invalidPayload};return value
    }
    public func service(business:Int,id:Int) async throws -> ServiceDirectoryItem {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max) else {throw ReadFailure.invalidContext}
        guard let value=ServiceDirectoryItem.decode(try await get("/api/services/\(id)/")),value.business==business,value.id==id else {throw ReadFailure.invalidPayload};return value
    }
}
// Explicit local fixture port, injected only in DEBUG. No network/fallback/command methods.
public struct FixtureServiceDirectoryTransport:ReadTransport {
    private let directory:URL
    public init(directory:URL) {self.directory=directory}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private struct Row:Decodable {let path:String;let response_json:String}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {
        guard request.query.isEmpty else {return ReadResponse(status:404,data:Data())}
        let c=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("service-directory.json")))
        guard c.fixture_only,let row=c.reads.first(where:{$0.path==request.path}) else {return ReadResponse(status:404,data:Data())}
        return ReadResponse(status:200,data:Data(row.response_json.utf8))
    }
}
