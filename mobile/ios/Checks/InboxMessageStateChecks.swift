import Foundation
import CRMCore

func runInboxMessageStateChecks(directory:URL) throws -> Int {
    struct Catalog:Decodable {struct Row:Decodable {let name:String;let expected:String;let response:InboxThread};let fixture_only:Bool;let cases:[Row]}
    let catalog=try JSONDecoder().decode(Catalog.self,from:Data(contentsOf:directory.appendingPathComponent("message-source-states.json")))
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    try expect(catalog.fixture_only && catalog.cases.count==14,"Message source-state fixture lost cases")
    for row in catalog.cases {
        let thread=row.response,message=thread.messages[0]
        try expect(thread.valid(for:101,id:901) && thread.messages.map(\.id)==[9011,9012],"Status changed existing thread validity/identity/order")
        try expect(message.sourceState.rawValue==row.expected,"Source status coerced/defaulted or new delivery enum invented: \(row.name)")
        try expect(message.text=="Synthetic inquiry about available time" && message.sender_type=="client" && thread.messages[1].sourceState == .sent,"Status/error/sent date fields changed message text/actor or inferred another message state")
    }
    try expect(InboxMessageState(nil) == .unknown && InboxMessageState("sent").copyKey=="messageStateSent","Unknown/status copy mapping changed")
    return count
}
