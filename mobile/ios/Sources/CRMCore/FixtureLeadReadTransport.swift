import Foundation

// Explicit debug/test GET adapter; never a fallback for real errors or command authority.
public struct FixtureLeadReadTransport:ReadTransport {
    private let directory:URL
    public init(directory:URL) {self.directory=directory}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {
        let raw=try Data(contentsOf:directory.appendingPathComponent("lead-read.json"));return try Self.response(raw,request:request)
    }
    public static func response(_ raw:Data,request:ReadRequest) throws -> ReadResponse {
        let o=try JSONSerialization.jsonObject(with:raw) as! [String:Any]
        guard let b=request.query["business"].flatMap(Int.init),let catalogs=o["catalogues"] as? [[String:Any]],let c=catalogs.first(where:{$0["business"] as? Int==b}),let rows=c["rows"] as? [[String:Any]] else {return ReadResponse(status:404,data:Data())}
        let visible=rows.filter {$0["is_archived"] as? Bool==false}
        let result:[String:Any]
        if request.path=="/api/mobile/v1/leads/",request.query["limit"]=="50",Set(request.query.keys)==["business","limit","search"] {
            let query=SourceTextTrim.pythonStrip(request.query["search"] ?? "").lowercased()
            let filtered=visible.filter {row in let item=row["item"] as! [String:Any];let client=item["client"] as! [String:Any];let service=item["service"] as! [String:Any];return query.isEmpty || [client["name"],client["phone"],client["email"],row["message"],service["name"]].compactMap {$0 as? String}.contains {$0.lowercased().contains(query)}}
            let items=filtered.map {$0["item"] as! [String:Any]}
            result=["business":b,"generated_at":"2026-10-28T10:00:00Z","limit":50,"summary":["total":items.count,"new":items.filter {$0["status"] as? String=="new"}.count,"unassigned":items.filter {$0["responsible_user_id"] is NSNull}.count,"in_progress":items.filter {["contacted","in_progress"].contains($0["status"] as? String ?? "")}.count],"items":Array(items.prefix(50)),"payload_budget":["target_kb":100,"max_items":50]]
        } else if Set(request.query.keys)==["business"],let id=request.path.split(separator:"/").last.flatMap({Int($0)}),request.path=="/api/mobile/v1/leads/\(id)/",let row=visible.first(where:{($0["item"] as? [String:Any])?["id"] as? Int==id}) {
            result=["business":b,"generated_at":"2026-10-28T10:00:00Z","lead":row["item"]!,"details":["message":row["message"]!],"related":["tasks":[],"appointments":[],"conversations":[]],"payload_budget":["target_kb":80,"max_related_per_section":5]]
        } else {return ReadResponse(status:404,data:Data())}
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:result))
    }
}
