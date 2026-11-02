import Foundation
import CRMCore

func runClientDraftChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message:message) }; count += 1 }
    struct Fixture: Decodable { struct Row: Decodable { let email: String; let valid: Bool }; let email_cases: [Row] }
    let f=try JSONDecoder().decode(Fixture.self,from:Data(contentsOf:directory.appendingPathComponent("client-draft-validation.json")))
    for row in f.email_cases {
        var v=ClientDraftValues(); v.fullName="Synthetic client";v.email=row.email
        try expect(!v.issues.contains(where:{$0.field == .email}) == row.valid,"Native email validation diverged from existing JS source for \(row.email.debugDescription)")
        try expect(v.email == row.email,"Validation rewrote input")
    }
    var value=ClientDraftValues();value.fullName=" ";try expect(value.issues.contains(where:{$0.problem == .name}),"Blank Client name accepted")
    value.fullName="A";try expect(value.issues.contains(where:{$0.problem == .name}),"Web min2 omitted")
    value.fullName=" A ";try expect(value.issues.isEmpty,"Input normalization invented a stricter min2 than existing form")
    value.fullName=String(repeating:"Ә",count:255);try expect(value.issues.isEmpty,"Valid source model max255 rejected")
    value.fullName+=String("Ә");try expect(value.issues.contains(where:{$0.problem == .nameLength}),"Source model name limit ignored")
    value.fullName=String(repeating:"🙂",count:255);try expect(value.issues.isEmpty,"UTF16 was confused with source model codepoint limit")
    value.phone=String(repeating:"1",count:33);try expect(value.issues.contains(where:{$0.problem == .phoneLength}),"Source phone32 cap ignored")
    value.phone=String(repeating:"1",count:32);value.notes=String(repeating:"Synthetic note\n",count:2000)
    for source in ClientDraftValues.sources { value.source=source;try expect(value.issues.isEmpty,"Existing source option unavailable") }
    value.source="unsupported";try expect(value.issues.contains(where:{$0.problem == .source}),"Invented source accepted")
    let a=ClientDraftContext(business:101,epoch:1),b=ClientDraftContext(business:202,epoch:2)
    var s=ClientDraftSession();try expect(!s.open(expected:a),"Unbound draft opened")
    s.bind(a);try expect(s.open(expected:a),"Bound draft did not open");let first=s.selection!
    s.update(.fullName,value:"Synthetic client",expected:first);s.update(.notes,value:value.notes,expected:first);s.update(.email,value:"bad address",expected:first)
    try expect(!s.prepare(expected:first) && s.values.email=="bad address" && s.values.notes==value.notes && s.phase == .editing,"Recoverable local error lost typed input")
    s.update(.email,value:"alpha@example.invalid",expected:first);try expect(s.prepare(expected:first),"Valid local review unavailable")
    let review=s.review!;s.update(.fullName,value:"late edit",expected:first)
    try expect(s.values.fullName=="Synthetic client" && s.review==review && s.phase == .review,"Review changed from an editing callback")
    s.back(expected:first);try expect(s.phase == .editing && s.values.notes==value.notes && s.review==nil,"Review Back lost editable draft")
    s.back(expected:first);try expect(s.phase == .closed && s.selection==nil && s.values.fullName=="Synthetic client","Form Back discarded input")
    _=s.open(expected:a);let reopened=s.selection!;try expect(reopened != first,"Reopen reused old callback generation")
    s.update(.fullName,value:"stale",expected:first);s.discard(expected:first)
    try expect(s.selection==reopened && s.values.fullName=="Synthetic client","Late old close/edit cleared reopened draft")
    s.bind(a);try expect(s.selection==reopened,"Same-context read retry reset form")
    s.bind(b);try expect(s.selection==nil && s.review==nil && s.values==ClientDraftValues(),"Business switch retained old input")
    s.update(.fullName,value:"foreign late",expected:reopened);s.close(expected:reopened)
    try expect(s.context==b && s.values==ClientDraftValues(),"Old Business callback entered new draft")
    s.bind(ClientDraftContext(business:101,epoch:3));_=s.open(expected:s.context!);let current=s.selection!
    s.update(.fullName,value:"New input",expected:current);s.discard(expected:current)
    try expect(s.phase == .closed && s.values==ClientDraftValues(),"Explicit clear did not clear local input")
    s.bind(ClientDraftContext(business:0,epoch:4));try expect(s.context==nil && s.selection==nil,"Invalid context accepted")
    count += try runClientDuplicateResponseChecks(directory:directory)
    return count
}

private func runClientDuplicateResponseChecks(directory:URL) throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-duplicate-preview.json"))) as! [String:Any]
    for row in catalog["decode_cases"] as! [[String:Any]] {
        let raw=row["response_json"] as! String,expected=row["valid"] as! Bool
        let parsed=try? ClientDuplicateResponse.decode(Data(raw.utf8))
        try expect((parsed != nil)==expected,"Duplicate response accepted/rejected wrong exact shape: \(row["name"]!)")
        if let parsed {
            let original=try JSONSerialization.jsonObject(with:Data(raw.utf8)) as! [String:Any]
            let rows=original["duplicates"] as! [[String:Any]]
            try expect(parsed.duplicates.count==rows.count,"Duplicate result invented total/default rows")
            for (i,item) in parsed.duplicates.enumerated() {
                try expect(SourceTextIdentity.same(item.full_name,rows[i]["full_name"] as? String) && SourceTextIdentity.same(item.phone,rows[i]["phone"] as? String) && SourceTextIdentity.same(item.email,rows[i]["email"] as? String),"Duplicate display text was normalized or replaced with bounded title")
            }
        }
    }
    let context=ClientDraftContext(business:101,epoch:7)
    let a=ClientDuplicatePreviewInput(context:context,phone:"é",email:"alpha@example.invalid"),b=ClientDuplicatePreviewInput(context:context,phone:"e\u{301}",email:"alpha@example.invalid")
    try expect(a != b && a == a,"Fixture lookup input used contact normalization/canonical display equality")
    return count
}
