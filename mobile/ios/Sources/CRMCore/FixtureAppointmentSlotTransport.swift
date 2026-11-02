import Foundation

// Explicit DEBUG/test catalogue; exact existing GET queries only, no live fallback/default day.
public struct FixtureAppointmentSlotTransport:ReadTransport {
    private let directory:URL
    public init(directory:URL) {self.directory=directory}
    private struct Catalog:Decodable {let fixture_only:Bool;let reads:[Row]}
    private struct Row:Decodable {let query:[String:String];let response_json:String}
    public func get(_ request:ReadRequest) async throws -> ReadResponse {
        guard request.path=="/api/appointments/available-slots/" else {return ReadResponse(status:404,data:Data())}
        let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("appointment-slot-read-fixtures.json")))
        guard catalog.fixture_only,let row=catalog.reads.first(where:{$0.query==request.query}) else {return ReadResponse(status:404,data:Data())}
        return ReadResponse(status:200,data:Data(row.response_json.utf8))
    }
}
