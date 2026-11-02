import Foundation
import CRMCore

func runHandoffReadChecks(directory: URL) throws -> Int {
    var count=0
    func expect(_ value: Bool,_ message: String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let data=try Data(contentsOf:directory.appendingPathComponent("inbox-101-901.json")),base=try JSONSerialization.jsonObject(with:data) as! [String:Any]
    let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("inbox-handoff-read-cases.json"))) as! [String:Any]
    for row in cases["cases"] as! [[String:Any]] {
        var object=base,conversation=object["conversation"] as! [String:Any]
        if row["present"] as! Bool {conversation["handoff_required"]=row["value"] ?? NSNull()} else {conversation.removeValue(forKey:"handoff_required")}
        object["conversation"]=conversation
        var fields=object["details"] as? [String:Any] ?? [:];fields["bot_enabled"]=false;fields["handoff_reason"]="Synthetic safety marker";object["details"]=fields
        let thread=try JSONDecoder().decode(InboxThread.self,from:JSONSerialization.data(withJSONObject:object))
        try expect(thread.valid(for:101,id:901),"Optional handoff flag made valid read unavailable")
        try expect(thread.conversation.handoffState.rawValue==row["expected"] as! String,"Missing/null/string/number flag was coerced or inferred from AI/reason")
        try expect(thread.conversation.unread_count==2 && thread.messages.count==(base["messages"] as! [Any]).count,"Read state affected unread/messages")
    }
    let copyData=try Data(contentsOf:directory.deletingLastPathComponent().appendingPathComponent("ui-copy.json"))
    for locale in ["ru","kk","en"] {
        let copy=try UICopy(data:copyData,preferredLanguage:locale)
        let keys=[HandoffReadState.required.copyKey,HandoffReadState.notRequired.copyKey,HandoffReadState.unknown.copyKey]
        try expect(Set(keys).count==3 && keys.allSatisfy {!copy.text($0).isEmpty && copy.text($0) != $0},"Read true/false/unknown labels missing or collapsed")
    }
    return count
}
