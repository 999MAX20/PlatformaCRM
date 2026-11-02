import Foundation

// Debug/test producer only. It uses a separate complete synthetic dataset;
// application search never filters the Directory's loaded response window.
public enum FixtureClientSearch {
    private static func catalogue(_ data: Data,business: Int) throws -> [String:Any] {
        guard [101,202].contains(business),let value=try JSONSerialization.jsonObject(with:data) as? [String:Any],value["business"] as? Int == business,value["fixture_only"] is String,value["items"] is [[String:Any]] else {throw ReadFailure.invalidPayload}
        return value
    }
    public static func list(_ data: Data,business: Int,search: String) throws -> ReadResponse {
        let source=try catalogue(data,business:business)
        let query=SourceTextTrim.pythonStrip(search)
        let rows=source["items"] as! [[String:Any]]
        // Fixtures are ASCII examples; no claim to certify database collation.
        let matches=query.isEmpty ? rows : rows.filter { row in
            ["title","phone","email","notes"].contains { key in (row[key] as? String)?.range(of:query,options:.caseInsensitive) != nil }
        }
        let response: [String:Any] = ["business":business,"generated_at":source["generated_at"]!,"limit":50,
            "items":Array(matches.prefix(50)),"summary":["total":matches.count,"with_phone":matches.filter { !($0["phone"] as? String ?? "").isEmpty }.count,"with_email":matches.filter { !($0["email"] as? String ?? "").isEmpty }.count],"payload_budget":["target_kb":100,"max_items":50]]
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:response))
    }
    public static func profile(_ data: Data,business: Int,id: Int) throws -> ReadResponse {
        let source=try catalogue(data,business:business)
        guard let row=(source["items"] as! [[String:Any]]).first(where:{$0["id"] as? Int == id}) else {return ReadResponse(status:404,data:Data())}
        let response: [String:Any] = ["business":business,"generated_at":source["generated_at"]!,"client":row,"details":["notes":row["notes"] as? String ?? ""],"related":["appointments":[],"tasks":[],"conversations":[],"leads":[]],"payload_budget":["max_related_per_section":5]]
        return ReadResponse(status:200,data:try JSONSerialization.data(withJSONObject:response))
    }
    public static func isCatalogueID(_ id: Int) -> Bool {(1701...1754).contains(id) || (2701...2754).contains(id)}
}
