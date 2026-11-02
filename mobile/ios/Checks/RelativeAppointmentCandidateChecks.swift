import Foundation
import CRMCore

func runRelativeAppointmentCandidateChecks(directory:URL) throws -> Int {
    struct Catalog:Decodable {
        struct Parse:Decodable {let name:String;let raw:String;let candidate_id:String?}
        struct Corroboration:Decodable {let name:String;let raw:String;let source:CRMNotification;let target:Int?}
        let parse_cases:[Parse];let corroboration_cases:[Corroboration]
    }
    let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("relative-appointment-candidate.json")))
    var count=0
    for row in catalog.parse_cases {
        let candidate=RelativeAppointmentCandidate.parse(row.raw)
        guard candidate.map({String($0.appointmentID)})==row.candidate_id, candidate==nil || candidate?.raw==row.raw else {throw CheckFailure(message:"Relative syntax: \(row.name)")};count += 1
    }
    for row in catalog.corroboration_cases {
        guard RelativeAppointmentCandidate.parse(row.raw)?.corroboratedTarget(from:row.source)==row.target else {throw CheckFailure(message:"Independent source: \(row.name)")};count += 1
    }
    return count
}
