import Foundation
import CRMCore

func runTaskCreateValidationChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Catalog: Decodable {struct Row: Decodable {let name:String;let title:String;let description:String;let priority:String;let preview:Preview;let issues:[Issue]};struct Preview:Decodable {let title:String;let description:String;let priority:String};struct Issue:Decodable {let field:String;let problem:String};let cases:[Row]}
    let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("task-create-validation.json")))
    let context=TaskDraftContext(business:101,epoch:1)
    for row in catalog.cases {
        var session=TaskDraftSession();session.bind(context);_=session.open(expected:context);let selection=session.selection!
        session.update(.title,value:row.title,expected:selection);session.update(.description,value:row.description,expected:selection);session.update(.priority,value:row.priority,expected:selection)
        let raw=session.values,preview=raw.preview
        try expect(preview.title==row.preview.title && preview.description==row.preview.description && preview.priority==row.preview.priority,"Source normalization changed: \(row.name)")
        try expect(raw.issues.map {"\($0.field.rawValue):\($0.problem.rawValue)"}==row.issues.map {"\($0.field):\($0.problem)"},"Source field errors changed: \(row.name)")
        let prepared=session.prepare(expected:selection)
        try expect(prepared==row.issues.isEmpty && session.values==raw,"Validation rewrote input/invented limit/minimum: \(row.name)")
        if prepared {
            let review=session.review!;try expect(review.values==raw && review.preview==preview,"Review did not capture separate raw+source snapshot")
            session.update(.description,value:"late mutation",expected:selection);try expect(session.review==review && session.values==raw,"Review accepted mutable late input")
            session.back(expected:selection);try expect(session.values==raw && session.phase == .editing,"Back returned normalized text into raw editor")
        } else {try expect(session.review==nil && session.phase == .editing,"Invalid text reached preview")}
    }
    return count
}
