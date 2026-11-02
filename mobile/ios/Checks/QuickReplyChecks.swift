import Foundation
import CRMCore

func runQuickReplyChecks(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    struct Reference: Decodable {struct Row: Decodable {let draft: String;let template: String;let trim: String;let trim_end: String;let inserted: String};let cases: [Row]}
    let reference=try JSONDecoder().decode(Reference.self,from:Data(contentsOf:directory.appendingPathComponent("quick-reply-insertion.json")))
    for row in reference.cases {
        try expect(SourceTextTrim.javascriptTrim(row.draft)==row.trim,"JS trim differs from executed source reference")
        try expect(SourceTextTrim.javascriptTrimEnd(row.draft)==row.trim_end,"JS trimEnd differs from executed source reference")
        try expect(QuickReplyInsertion.text(draft:row.draft,template:row.template)==row.inserted,"Insertion rewrote leading whitespace/template or used Python strip")
    }
    let owner=ReplyDraftContext(business:101,conversation:901,epoch:40)
    var draft=ReplyDraftSession();draft.bind(owner,available:true);_=draft.open(expected:owner);let original=draft.selection!
    let context=QuickReplyContext(draft:original,channel:"website"),source=FixtureQuickReplyRepository(directory:directory)
    let page=try await source.quickReplies(business:101,channel:"website")
    try expect(page.valid(for:context) && page.items.map(\.id)==[9101,9102,9103] && !page.partial,"Fixture fields/scope/order/channel are not source-compatible")
    var picker=QuickReplySession();try expect(picker.open(expected:context)==nil,"Unbound catalogue opened")
    picker.bind(context);let request=picker.open(expected:context)!;let selection=picker.selection!
    try expect(picker.loading && !picker.showsEmpty && picker.choices.isEmpty,"Pending request claimed empty or showed old rows")
    picker.accept(page,request:request);try expect(picker.choices.map(\.id)==[9101,9102,9103],"Consumer changed response order")
    let oldChoice=picker.choices[0];picker.search(" APPOINTMENTS ",expected:selection)
    try expect(picker.choices.map(\.id)==[9102] && picker.resolve(oldChoice)==nil,"Search missed category or accepted hidden stale row")
    picker.search("",expected:selection);try expect(picker.resolve(oldChoice)==nil,"Earlier filter-generation row became actionable again")
    picker.search("СИНТЕТИЧЕСКИЙ",expected:selection);try expect(picker.choices.map(\.id)==[9101,9103],"Source local title/text/category case-insensitive search changed order")
    picker.search("{{client}}",expected:selection);try expect(picker.choices.map(\.id)==[9101],"Literal placeholder search was interpreted")
    let currentChoice=picker.choices[0];picker.close(expected:selection)
    try expect(picker.query=="{{client}}" && picker.resolve(currentChoice)==nil && picker.choices.isEmpty,"Cancel retained action or discarded own search")
    let reopened=picker.open(expected:context)!;picker.accept(page,request:reopened);let fresh=picker.selection!
    picker.search("",expected:fresh);let beforeRetry=picker.choices[0];let retry=picker.retry(expected:fresh)!
    try expect(picker.resolve(beforeRetry)==nil && picker.choices.isEmpty && picker.loading,"Retry retained prior template choices")
    picker.fail(.denied,request:retry);try expect(picker.failure == .denied && !picker.showsEmpty && picker.choices.isEmpty,"Denied source retained templates or claimed empty")
    picker.accept(page,request:reopened);try expect(picker.failure == .denied && picker.choices.isEmpty,"Older response replaced denied current result")
    func changedPage(_ change: (inout [String:Any])->Void) throws -> QuickReplyPage {
        var value=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-replies-101-website.json"))) as! [String:Any]
        change(&value);return try JSONDecoder().decode(QuickReplyPage.self,from:JSONSerialization.data(withJSONObject:value))
    }
    for mode in 0..<7 {
        let bad=try changedPage {object in var rows=object["results"] as! [[String:Any]]
            switch mode {case 0:rows[0]["business"]=202;case 1:rows[0]["channel"]="whatsapp";case 2:rows[0]["is_active"]=false;case 3:rows[0]["sort_order"] = -1;case 4:rows[0]["text"]=" \n";case 5:rows[1]["id"]=rows[0]["id"];default:object["count"] = -1}
            object["results"]=rows
        }
        picker.accept(bad,request:picker.retry(expected:fresh)!)
        try expect(picker.failure == .invalidPayload && picker.choices.isEmpty,"Out-of-scope/inactive/malformed catalogue accepted")
    }
    let partial=try changedPage {$0["count"]=51;$0["next"]="/api/quick-replies/?page=2"}
    picker.accept(partial,request:picker.retry(expected:fresh)!);picker.search("does-not-exist",expected:fresh)
    try expect(picker.partial && !picker.showsEmpty && picker.choices.isEmpty,"Local filter over incomplete page claimed no templates")
    let object=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-replies-101-website.json"))) as! [String:Any]
    let unknown=try JSONDecoder().decode(QuickReplyPage.self,from:JSONSerialization.data(withJSONObject:object["results"]!))
    try expect(unknown.partial && unknown.count==nil,"Array list invented a total/completeness guarantee")
    let empty=try await source.quickReplies(business:202,channel:"instagram")
    var b=ReplyDraftSession();let other=ReplyDraftContext(business:202,conversation:951,epoch:41);b.bind(other,available:true);_=b.open(expected:other)
    let otherContext=QuickReplyContext(draft:b.selection!,channel:"instagram")
    picker.bind(otherContext);let otherRequest=picker.open(expected:otherContext)!;picker.accept(empty,request:otherRequest)
    try expect(picker.showsEmpty && picker.choices.isEmpty,"Confirmed empty catalogue state missing")
    picker.accept(page,request:retry);try expect(picker.showsEmpty && picker.context==otherContext,"Old-Business response entered new picker")
    picker.bind(QuickReplyContext(draft:b.selection!,channel:"email"));try expect(picker.context==nil && picker.selection==nil,"Unknown Conversation channel enabled templates")
    draft.update("  Operator note \n",expected:original)
    try expect(!draft.insertTemplate(" \n",expected:original),"Blank template changed input")
    try expect(draft.insertTemplate(page.items[0].text,expected:original),"Valid local insertion failed")
    let inserted=draft.text,newSelection=draft.selection!
    try expect(inserted=="  Operator note\n"+page.items[0].text && inserted.contains("{{client}}") && newSelection != original,"Inserted text was trimmed/interpolated or reused old UI token")
    draft.update("late input",expected:original);_=draft.insertTemplate(page.items[0].text,expected:original)
    try expect(draft.text==inserted && draft.selection==newSelection,"Old editor/double choice overwrote inserted body")
    _=draft.prepare(expected:newSelection);try expect(!draft.insertTemplate("late template",expected:newSelection) && draft.text==inserted,"Review accepted a late template mutation")
    draft.back(expected:newSelection);draft.close(expected:newSelection);_=draft.open(expected:owner)
    try expect(draft.text==inserted,"Back/close/reopen lost unsent template text")
    let long=String(repeating:"Synthetic template\n",count:2000)
    try expect(draft.insertTemplate(long,expected:draft.selection!) && draft.text.hasSuffix(long),"Invented template length cap truncated input")
    do {
        _=try NativeRequestBuilder(origin:URL(string:"https://fixtures.invalid")!,timeout:30).request(for:ReadRequest(path:"/api/quick-replies/"))
        throw CheckFailure(message:"Web catalogue widened the native network allowlist")
    } catch RequestConfigurationFailure.invalidPath {try expect(true,"Existing native path boundary retained")}
    let rawCases=(try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("quick-reply-raw-unicode-cases.json"))) as! [String:Any])["cases"] as! [[String:Any]]
    for row in rawCases {
        let before=row["before"] as! String,after=row["after"] as! String,changed=row["changed"] as! Bool,literal=row["template"] as! String
        let rawPage=try JSONDecoder().decode(QuickReplyPage.self,from:Data((row["page_json"] as! String).utf8))
        var rawPicker=QuickReplySession();rawPicker.bind(context);let ticket=rawPicker.open(expected:context)!,owner=rawPicker.selection!
        rawPicker.search(before,expected:owner);rawPicker.accept(rawPage,request:ticket);try expect(rawPicker.choices.count==1,"Raw filter fixture lost provided row")
        let prior=rawPicker.choices[0];rawPicker.search(after,expected:owner);let current=rawPicker.choices[0]
        try expect(rawPicker.query.utf8.elementsEqual(after.utf8),"Canonical equivalent raw QuickReply input was dropped")
        try expect((current.filterRevision != prior.filterRevision)==changed && current.id==prior.id,"Byte change failed to revoke choice with identical visible row")
        try expect((rawPicker.resolve(prior)==nil)==changed,"Old raw filter choice remained actionable")
        try expect(rawPicker.resolve(current)!.utf8.elementsEqual(literal.utf8) && rawPicker.items.count==1 && rawPicker.loaded && !rawPicker.partial,"Current choice changed literal/catalogue/completeness")
        try expect(QuickReplyInsertion.text(draft:row["draft"] as! String,template:literal).utf8.elementsEqual((row["inserted"] as! String).utf8),"Raw template insertion normalized/interpolated body")
        rawPicker.close(expected:owner);try expect(rawPicker.resolve(current)==nil && rawPicker.query.utf8.elementsEqual(after.utf8),"Close restored old choice or lost raw filter")
    }
    return count
}
