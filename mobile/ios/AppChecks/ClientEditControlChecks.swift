import Foundation
import CRMCore

@MainActor func checkClientEditControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repository=APIReadRepository(transport:FixtureTransport(directory:directory))
    let provider=FixtureClientEditOriginProvider(directory:directory)
    let profile=try await repository.clientProfile(business:101,id:701)
    guard let origin=await provider.origin(for:profile) else {throw ViewModelCheckFailure(message:"Missing independent fixture origin")}
    var json=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("client-101-701.json"))) as! [String:Any]
    var client=json["client"] as! [String:Any];client["updated_at"]="synthetic changed origin";json["client"]=client
    let changed=try JSONDecoder().decode(ClientProfile.self,from:JSONSerialization.data(withJSONObject:json)).editReadFields.complete!
    let context=ClientEditContext(business:101,client:701,epoch:9),model=ClientEditViewModel()
    model.open(expected:nil);model.prepare(expected:nil);model.askCancel(expected:nil);model.askDiscard(expected:nil)
    try expect(model.control==nil && model.confirmation==nil,"Missing captured authority opened editor/dialog")
    model.begin(context);let unresolved=model.entryControl!;model.open(expected:unresolved)
    try expect(model.control==nil && !model.session.available,"Unknown origin enabled editor")
    model.receive(origin,context);model.open(expected:unresolved)
    try expect(model.control==nil,"Entry captured before origin reply opened new source")
    let entry=model.entryControl!;model.open(expected:entry);let first=model.control!,input=model.inputControl!,selection=first.selection
    model.open(expected:entry)
    try expect(model.control==first,"Duplicate entry replaced current editor")
    model.update(.fullName,"Synthetic first",input:input);model.update(.phone,"Synthetic phone",input:input)
    try expect(model.inputControl==input && model.session.values?.phone=="Synthetic phone","Continuous input visit lost second field edit")
    model.update(.email,"bad address",input:input);model.prepare(expected:first)
    try expect(model.session.phase == .editing && !model.session.issues.isEmpty && model.control==first,"Validation failure lost editable input/visit")
    model.update(.email,origin.values.email,input:input);model.prepare(expected:first);let review=model.control!,snapshot=model.session.review
    try expect(model.session.phase == .review && review != first && model.inputControl==nil && snapshot?.original==origin.values,"Review did not freeze exact source diff")
    model.update(.phone,"late input",input:input);model.back(expected:first);model.close(expected:first);model.prepare(expected:first)
    try expect(model.control==review && model.session.review==snapshot && model.session.values?.phone=="Synthetic phone","Old input/editor action changed review")
    model.back(expected:review);let second=model.control!,secondInput=model.inputControl!
    model.update(.fullName,"Synthetic second",input:secondInput);model.prepare(expected:second);let review2=model.control!
    model.back(expected:review);model.close(expected:review);model.askCancel(expected:review)
    try expect(model.control==review2 && model.session.selection==selection && model.confirmation==nil,"Same-selection prior review acted on a new review")
    model.back(expected:review2);let editing=model.control!,typing=model.inputControl!
    model.askCancel(expected:editing);let question=model.confirmation!;model.update(.fullName,"Synthetic after question",input:typing)
    model.confirm(question)
    try expect(model.confirmation==nil && model.session.values?.fullName=="Synthetic after question" && model.control==editing,"Stale cancellation erased newer typed content")
    model.askCancel(expected:editing);let dismissed=model.confirmation!;model.dismiss(dismissed);model.askCancel(expected:editing);let current=model.confirmation!
    model.dismiss(dismissed);model.confirm(dismissed)
    try expect(current != dismissed && model.confirmation==current && model.session.values?.fullName=="Synthetic after question","Old dialog consumed a replacement confirmation")
    model.dismiss(current);model.close(expected:editing);let closedEntry=model.entryControl!
    try expect(model.session.hasStoredChanges && model.session.values?.fullName=="Synthetic after question","Close discarded unsent RAM input")
    model.open(expected:entry);try expect(model.control==nil,"Old entry reopened a closed editor")
    model.open(expected:closedEntry);let reopened=model.control!;model.confirm(current);model.update(.phone,"old input",input:typing)
    try expect(model.control==reopened && model.session.values?.phone=="Synthetic phone","Old dialog/input reached reopened editor")
    model.askCancel(expected:reopened);model.confirm(model.confirmation!)
    try expect(model.control==nil && model.session.values==origin.values && !model.session.hasStoredChanges,"Current explicit cancellation did not restore exact original")
    model.open(expected:model.entryControl);model.update(.phone,"Retained own phone",input:model.inputControl);model.receive(changed,context)
    let resetEntry=model.entryControl!;model.askDiscard(expected:resetEntry);let reset=model.confirmation!
    try expect(model.session.needsReset && model.session.values==nil && model.session.hasStoredChanges,"Changed origin silently rebased dirty input")
    model.receive(nil,context);model.confirm(reset)
    try expect(model.confirmation==nil && model.session.needsReset && model.session.hasStoredChanges,"Stale reset discarded buffer after same-context reread")
    model.receive(origin,context);try expect(model.session.values?.phone=="Retained own phone","Matching original did not restore own quarantined input")
    model.receive(changed,context);model.askDiscard(expected:resetEntry)
    try expect(model.confirmation==nil,"Stale entry requested reset after source roundtrip")
    model.askDiscard(expected:model.entryControl);let oldReset=model.confirmation!;model.dismiss(oldReset);model.askDiscard(expected:model.entryControl);let freshReset=model.confirmation!
    model.dismiss(oldReset);model.confirm(oldReset)
    try expect(model.confirmation==freshReset && model.session.hasStoredChanges,"Old reset dialog reached new consent")
    model.confirm(freshReset)
    try expect(model.session.origin==changed && model.session.values==changed.values && !model.session.hasStoredChanges,"Current explicit reset lost independently received origin")
    model.open(expected:model.entryControl);model.update(.phone,"Unknown retained",input:model.inputControl);model.receive(nil,context);model.askDiscard(expected:model.entryControl);model.confirm(model.confirmation!)
    try expect(!model.session.available && model.session.values==nil && !model.session.hasStoredChanges,"Reset of unknown source fabricated empty editable values")
    model.receive(origin,context);model.open(expected:model.entryControl);let previous=model.control!,previousInput=model.inputControl!
    model.update(.fullName,"Epoch private input",input:previousInput);model.askCancel(expected:previous);let priorOwner=model.confirmation!
    let next=ClientEditContext(business:101,client:701,epoch:10);model.begin(next);let pending=model.entryControl
    model.receive(origin,context);try expect(model.entryControl==pending && !model.session.available,"Late old owner origin invalidated new pending entry")
    model.receive(origin,next);model.open(expected:model.entryControl);let currentOwner=model.control
    model.confirm(priorOwner);model.back(expected:previous);model.update(.phone,"old owner",input:previousInput)
    try expect(model.control==currentOwner && model.session.values==origin.values,"Prior epoch action leaked or erased private input")
    model.pause();model.confirm(priorOwner);try expect(model.control==nil && model.entryControl==nil && model.session.values==nil,"Parent close left editor/draft visible")
    return count
}
