import Foundation
import CRMCore

func runReadContractChecks(directory: URL) async throws -> Int {
    func variant(_ file: String, _ change: (inout [String: Any]) -> Void) throws -> Data {
        var json = try JSONSerialization.jsonObject(with: Data(contentsOf: directory.appendingPathComponent(file + ".json"))) as! [String: Any]
        change(&json)
        return try JSONSerialization.data(withJSONObject: json)
    }
    var malformed: [Data] = []
    for value: Any in ["501", 501.5, true] {
        malformed.append(try variant("appointment-101-501") { json in
            var item = json["appointment"] as! [String: Any]; item["id"] = value; json["appointment"] = item
        })
    }
    for key in ["title", "status", "start_at", "end_at"] {
        malformed.append(try variant("appointment-101-501") { json in
            var item = json["appointment"] as! [String: Any]; item[key] = 123; json["appointment"] = item
        })
    }
    for key in ["service", "resource"] {
        for value: Any in ["withheld", 1, false] {
            malformed.append(try variant("appointment-101-501") { json in
                var fields = json["details"] as! [String: Any]; fields[key] = value; json["details"] = fields
            })
        }
    }
    malformed.append(try variant("appointment-101-501") { json in
        var fields = json["details"] as! [String: Any]; fields["notes"] = false; json["details"] = fields
    })
    malformed.append(try variant("appointment-101-501") { json in
        var fields = json["details"] as! [String: Any]; var resource = fields["resource"] as! [String: Any]
        resource["id"] = "11"; fields["resource"] = resource; json["details"] = fields
    })
    var count = 0
    for data in malformed {
        let repository = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 200, data: data)))
        do { _ = try await repository.appointment(business: 101, id: 501); throw CheckFailure(message: "Wrong JSON type was accepted") }
        catch let error as ReadFailure {
            guard error == .invalidPayload else { throw CheckFailure(message: "Wrong malformed-payload error") }
            count += 1
        }
    }
    let nulls = try variant("appointment-101-501") { json in
        var item = json["appointment"] as! [String: Any]; item["id"] = 501.0; item["title"] = NSNull(); json["appointment"] = item
        var fields = json["details"] as! [String: Any]; fields["notes"] = NSNull(); fields["service"] = NSNull()
        fields["resource"] = ["id": NSNull(), "name": NSNull()]; json["details"] = fields
        json["future_field"] = ["ignored": true]
    }
    let repository = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 200, data: nulls)))
    let detail = try await repository.appointment(business: 101, id: 501)
    guard detail.appointment.id == 501, detail.appointment.title == nil, detail.details.notes == nil,
          detail.details.service == nil, detail.details.resource?.id == nil, detail.details.resource?.name == nil else {
        throw CheckFailure(message: "Compatible null/unknown fields or integral numeric ID changed")
    }
    return count + 1
}
