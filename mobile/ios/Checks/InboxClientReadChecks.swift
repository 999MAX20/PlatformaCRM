import Foundation
import CRMCore

func runInboxClientReadChecks(directory: URL) throws -> Int {
    var count = 0
    func expect(_ value: Bool,_ message: String) throws { guard value else { throw CheckFailure(message: message) }; count += 1 }
    let data = try Data(contentsOf: directory.appendingPathComponent("inbox-101-901.json"))
    func variant(_ change: (inout [String:Any]) -> Void) throws -> InboxThread {
        var object = try JSONSerialization.jsonObject(with: data) as! [String:Any]; change(&object)
        return try JSONDecoder().decode(InboxThread.self,from: JSONSerialization.data(withJSONObject: object))
    }
    try expect(try JSONDecoder().decode(InboxThread.self,from: data).clientReferenceID == 701,"Explicit thread Client ID lost")
    for value in [NSNull(),["id":0],["id":-1],[:]] as [Any] {
        let thread = try variant { $0["details"] = ["client":value,"lead":["id":701]] }
        try expect(thread.clientReferenceID == nil && thread.valid(for:101,id:901),"Unknown Client inferred from Lead or damaged independent thread")
    }
    try expect(try variant { $0.removeValue(forKey:"details") }.clientReferenceID == nil,"Missing details became a Client reference")
    try expect(try variant { $0["details"] = ["lead":["id":701],"phone":"+70000000001"] }.clientReferenceID == nil,"Client inferred from other fields")
    do { _ = try variant { $0["details"] = ["client":["id":"701"]] }; throw CheckFailure(message:"Malformed Client ID accepted") }
    catch is DecodingError { count += 1 }
    return count
}
