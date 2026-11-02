import Foundation

public protocol LeadReadRepository:Sendable {
    func leads(business:Int,search:String) async throws -> LeadReadPage
    func lead(business:Int,id:Int) async throws -> LeadReadDetail
}
public struct APILeadReadRepository:LeadReadRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    private func get<T:Decodable>(_ type:T.Type,_ request:ReadRequest) async throws -> T {
        let r=try await transport.get(request)
        switch r.status {case 200:do {return try JSONDecoder().decode(type,from:r.data)} catch {throw ReadFailure.invalidPayload};case 403:throw ReadFailure.denied;case 404:throw ReadFailure.notFound;default:throw ReadFailure.unavailable}
    }
    public func leads(business:Int,search:String) async throws -> LeadReadPage {guard business>0,business<=Int(Int32.max) else {throw ReadFailure.invalidContext};let p=try await get(LeadReadPage.self,ReadRequest(path:"/api/mobile/v1/leads/",query:["business":String(business),"limit":"50","search":SourceTextTrim.pythonStrip(search)]));guard p.valid(for:business) else {throw ReadFailure.invalidPayload};return p}
    public func lead(business:Int,id:Int) async throws -> LeadReadDetail {guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max) else {throw ReadFailure.invalidContext};let p=try await get(LeadReadDetail.self,ReadRequest(path:"/api/mobile/v1/leads/\(id)/",query:["business":String(business)]));guard p.valid(for:business,id:id) else {throw ReadFailure.invalidPayload};return p}
}
