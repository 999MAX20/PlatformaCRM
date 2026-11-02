import Foundation
import CRMCore

func runClientSourceValidationChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Values:Decodable {let fullName:String;let phone:String;let email:String;let source:String;let notes:String}
    struct Issue:Decodable {let field:String;let problem:String}
    struct Catalog:Decodable {struct Row:Decodable {let name:String;let values:Values;let preview:Values;let webIssues:[Issue];let sourceIssues:[Issue];let issues:[Issue]};let cases:[Row]}
    let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("client-create-validation.json"))),context=ClientDraftContext(business:101,epoch:1)
    func issues(_ values:[ClientDraftIssue])->[String] {values.map {"\($0.field.rawValue):\($0.problem.rawValue)"}}
    func expected(_ values:[Issue])->[String] {values.map {"\($0.field):\($0.problem)"}}
    for row in catalog.cases {
        var session=ClientDraftSession();session.bind(context);_=session.open(expected:context);let s=session.selection!
        for (field,value) in [(ClientDraftField.fullName,row.values.fullName),(.phone,row.values.phone),(.email,row.values.email),(.source,row.values.source),(.notes,row.values.notes)] {session.update(field,value:value,expected:s)}
        let raw=session.values,p=raw.preview
        try expect(p.fullName==row.preview.fullName && p.phone==row.preview.phone && p.email==row.preview.email && p.source==row.preview.source && p.notes==row.preview.notes,"Client source preview differed: \(row.name)")
        try expect(issues(raw.webIssues)==expected(row.webIssues) && issues(raw.sourceIssues)==expected(row.sourceIssues),"Client web/server stages were conflated: \(row.name)")
        try expect(issues(raw.issues)==expected(row.issues),"Client combined field errors differed: \(row.name)")
        let prepared=session.prepare(expected:s)
        try expect(prepared==row.issues.isEmpty && session.values==raw,"Client validation invented constraint or changed raw: \(row.name)")
        if prepared {let review=session.review!;try expect(review.values==raw && review.preview==p,"Client review lost raw or normalized snapshot");session.update(.notes,value:"late",expected:s);try expect(session.review==review,"Late Client input mutated review");session.back(expected:s);try expect(session.values==raw,"Client Back normalized editable input")}
        let edit=ClientEditValues(fullName:raw.fullName,phone:raw.phone,email:raw.email,source:raw.source)
        try expect(issues(edit.issues)==expected(row.issues.filter {$0.field != "notes"}),"Shared ClientEdit validation widened notes or differed: \(row.name)")
        try expect(ClientEditValues.fields == [.fullName,.phone,.email,.source],"Client edit field whitelist expanded")
    }
    return count
}
