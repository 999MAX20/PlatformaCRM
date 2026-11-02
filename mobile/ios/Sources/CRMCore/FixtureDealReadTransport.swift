import Foundation

// Explicit fixture GET only; not a fallback, full Deal catalogue or command grant.
public struct FixtureDealReadTransport:ReadTransport {
    private struct Row:Decodable,Sendable {let path:String,status:Int,response_json:String}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private let rows:[Row]
    public init(directory:URL) {if let data=try? Data(contentsOf:directory.appendingPathComponent("deal-read.json")),let c=try? JSONDecoder().decode(Catalog.self,from:data),c.fixture_only {rows=c.reads} else {rows=[]}}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {guard request.query.isEmpty else {throw ReadFailure.invalidContext};guard let row=rows.first(where:{$0.path==request.path}) else {return ReadResponse(status:404,data:Data())};return ReadResponse(status:row.status,data:Data(row.response_json.utf8))}
}
