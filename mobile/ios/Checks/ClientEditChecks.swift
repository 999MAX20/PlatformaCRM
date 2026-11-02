import Foundation
import CRMCore

func runClientEditChecks(directory: URL) async throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("client-101-701.json"))
    let profile=try JSONDecoder().decode(ClientProfile.self,from:data)
    let provider=FixtureClientEditOriginProvider(directory:directory)
    let original=await provider.origin(for:profile)!
    try expect(original.values==ClientEditValues(fullName:"Synthetic Client Alpha",phone:"+70000000001",email:"alpha@example.invalid",source:"manual"),"Original fields were populated from display fallback or notes")
    func modified(_ edit: (inout [String:Any])->Void) throws -> ClientProfile {
        var object=try JSONSerialization.jsonObject(with:data) as! [String:Any]
        var client=object["client"] as! [String:Any];edit(&client);object["client"]=client
        return try JSONDecoder().decode(ClientProfile.self,from:JSONSerialization.data(withJSONObject:object))
    }
    let blank=try modified {$0["phone"]="";$0["email"]=""}
    try expect(blank.editReadFields.complete?.values.phone=="" && blank.editReadFields.complete?.values.email=="","Known blank contact fields became unknown")
    try expect(await provider.origin(for:blank)==nil,"Altered contact was trusted without matching reference")
    for key in ["title","phone","email","source","updated_at"] {
        let missing=try modified {$0.removeValue(forKey:key)}
        let null=try modified {$0[key]=NSNull()}
        try expect(missing.editReadFields.complete==nil && null.editReadFields.complete==nil,"Missing/null \(key) became editable empty/default")
        try expect(await provider.origin(for:missing)==nil && providerOriginUnknown(null),"Unknown field granted edit")
    }
    func wrongType(_ key: String) throws -> ClientEditReadFields {
        var fields:[String:Any] = ["title":"Synthetic","phone":"","email":"","source":"manual","updated_at":"v1"]
        fields[key]=42
        return try JSONDecoder().decode(ClientEditReadFields.self,from:JSONSerialization.data(withJSONObject:fields))
    }
    for key in ["title","phone","email","source","updated_at"] {try expect(try wrongType(key).complete==nil,"Wrong field type became a string")}
    for edit in ["masked","source","version"] {
        let changed=try modified {if edit=="masked" {$0["phone"]="+7***0001"} else if edit=="source" {$0["source"]="telegram"} else {$0["updated_at"]="new-version"}}
        try expect(await provider.origin(for:changed)==nil,"Mismatched independent field/version bypassed fixture reference")
    }
    let unknownSource=try modified {$0["source"]="new-source"}
    try expect(unknownSource.editReadFields.complete==nil,"Unknown source was replaced by manual")
    let longNotes=String(repeating:"Synthetic private note\n",count:3000)
    var object=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    var client=object["client"] as! [String:Any];client["notes"]=String(longNotes.prefix(160));object["client"]=client;object["details"]=["notes":String(longNotes.prefix(1000))]
    let notesProfile=try JSONDecoder().decode(ClientProfile.self,from:JSONSerialization.data(withJSONObject:object))
    try expect(await provider.origin(for:notesProfile)==original,"Read-only notes entered four-field origin")
    try expect(!ClientEditValues.fields.contains(.notes),"Truncated notes were offered for edit")
    var invalid=original.values;invalid.fullName="A";invalid.phone=String(repeating:"1",count:33);invalid.email="bad address";invalid.source="unsupported"
    try expect(Set(invalid.issues.map(\.field))==Set(ClientEditValues.fields),"Edit omitted existing four-field validators")
    for source in ClientDraftValues.sources {var v=original.values;v.source=source;v.phone=String(repeating:"1",count:32);try expect(v.issues.isEmpty,"Existing source/phone32 rejected")}
    var limits=original.values;limits.fullName=String(repeating:"🙂",count:255);try expect(limits.issues.isEmpty,"Name codepoint max255 changed")
    limits.fullName+="🙂";try expect(limits.issues.contains(where:{$0.problem == .nameLength}),"Edit ignored name max255")
    let a=ClientEditContext(business:101,client:701,epoch:40),other=ClientEditContext(business:101,client:702,epoch:40)
    var s=ClientEditSession();try expect(!s.open(expected:a),"Unbound editor opened")
    s.begin(a);try expect(!s.available && s.values==nil && !s.open(expected:a),"Unverified read exposed form")
    s.receive(original,expected:a);try expect(s.open(expected:a),"Confirmed origin did not open")
    let first=s.selection!;try expect(s.prepare(expected:first) && s.review?.changed.isEmpty==true,"Unchanged review invented changes")
    s.back(expected:first);s.update(.fullName,value:"Synthetic changed",expected:first);s.update(.email,value:"bad address",expected:first);s.update(.notes,value:longNotes,expected:first)
    try expect(!s.prepare(expected:first) && s.values?.email=="bad address" && s.values?.fullName=="Synthetic changed","Invalid review lost input")
    s.update(.email,value:original.values.email,expected:first);try expect(s.prepare(expected:first),"Valid edit did not reach diff review")
    let review=s.review!
    try expect(review.changed==[.fullName] && review.original==original.values && review.values.fullName=="Synthetic changed","Review omitted exact original or included unchanged/notes")
    s.update(.phone,value:"late review input",expected:first);try expect(s.review==review && s.values?.phone==original.values.phone,"Review accepted an editor callback")
    s.back(expected:first);s.back(expected:first);try expect(s.phase == .closed && s.values?.fullName=="Synthetic changed","Back discarded local edit")
    _=s.open(expected:a);let reopened=s.selection!;s.cancel(expected:first);s.update(.fullName,value:"old",expected:first)
    try expect(s.selection==reopened && s.values?.fullName=="Synthetic changed","Old sheet callback cleared current input")
    s.pause();try expect(s.context==nil && s.values==nil && s.origin==nil && s.selection==nil,"Parent Back exposed private buffer")
    s.begin(a);s.receive(original,expected:a);try expect(s.values?.fullName=="Synthetic changed","Verified return failed to restore own RAM edit")
    s.begin(other);s.receive(original,expected:other);try expect(s.values==original.values,"Different client inherited prior client input")
    _=s.open(expected:other);s.update(.phone,value:"Synthetic phone B",expected:s.selection!)
    s.begin(a);s.receive(original,expected:a);try expect(s.values?.fullName=="Synthetic changed" && s.values?.phone==original.values.phone,"Per-client buffers mixed")
    let changed=ClientEditOriginForCheck(original:original,version:"v2")
    s.begin(a);s.receive(changed,expected:a)
    try expect(!s.available && s.needsReset && s.hasStoredChanges && s.values==nil && s.review==nil,"Changed version silently rebased local edit")
    s.discardStored(expected:other);try expect(s.needsReset,"Foreign context discarded quarantined edit")
    s.discardStored(expected:a);try expect(s.available && s.values==original.values && s.origin==changed && !s.hasStoredChanges,"Explicit discard did not adopt fresh confirmed origin")
    _=s.open(expected:a);s.update(.phone,value:"Unsent",expected:s.selection!);s.begin(a);s.receive(nil,expected:a)
    try expect(!s.available && s.needsReset && s.values==nil,"Unknown original exposed old input")
    s.discardStored(expected:a);try expect(!s.available && s.values==nil && !s.hasStoredChanges,"Unknown original was seeded with blanks")
    s.begin(a);s.receive(original,expected:a);_=s.open(expected:a);let cancel=s.selection!;s.update(.email,value:"local@example.invalid",expected:cancel);s.cancel(expected:cancel)
    try expect(s.values==original.values && s.selection==nil && !s.hasStoredChanges,"Cancel failed to restore exact original")
    _=s.open(expected:a);s.update(.fullName,value:"Epoch old",expected:s.selection!)
    let nextEpoch=ClientEditContext(business:101,client:701,epoch:41);s.begin(nextEpoch);s.receive(original,expected:a)
    try expect(!s.available && s.values==nil,"Late prior epoch original entered new context")
    s.receive(original,expected:nextEpoch);try expect(s.values==original.values,"Epoch switch retained old private input")
    _=s.open(expected:nextEpoch);s.update(.fullName,value:"Business old",expected:s.selection!)
    let business=ClientEditContext(business:202,client:701,epoch:41);s.begin(business);s.receive(original,expected:business)
    try expect(s.values==original.values,"Business switch retained old private input")
    s.begin(ClientEditContext(business:0,client:701,epoch:41));try expect(s.context==nil && s.values==nil,"Invalid owner retained editable state")
    return count
}

private func providerOriginUnknown(_ profile: ClientProfile) -> Bool {profile.editReadFields.complete==nil}
private func ClientEditOriginForCheck(original: ClientEditOrigin,version: String) -> ClientEditOrigin {
    // Exercise public decoder path; the runtime origin has no public arbitrary initializer.
    let v=original.values
    let data=try! JSONSerialization.data(withJSONObject:["title":v.fullName,"phone":v.phone,"email":v.email,"source":v.source,"updated_at":version])
    return try! JSONDecoder().decode(ClientEditReadFields.self,from:data).complete!
}
